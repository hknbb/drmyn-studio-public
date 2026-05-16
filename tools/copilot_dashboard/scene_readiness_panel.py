"""Streamlit panel that surfaces compute_scene_readiness() for the dashboard.

Pure presentation layer. The underlying computation lives in
``scripts.agents.scene_readiness`` and writes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.agents.scene_readiness import (
    ElementReadiness,
    SceneReadinessReport,
    ShotReadiness,
    compute_scene_readiness,
)


@dataclass(frozen=True)
class SceneReadinessSummary:
    scene_id: str
    shots_total: int
    shots_ready: int
    shots_blocking: int
    shots_with_structural_issues: int
    elements_total: int
    elements_ready: int
    elements_blocking: int

    @property
    def is_ready(self) -> bool:
        return (
            self.shots_total > 0
            and self.shots_blocking == 0
            and self.shots_with_structural_issues == 0
            and self.elements_total > 0
            and self.elements_blocking == 0
        )


def list_known_scene_ids(repo_root: Path) -> list[str]:
    """Discover scene ids that already carry an omni_sets/<scene_id> directory."""
    omni_sets = Path(repo_root) / "visual_dev" / "omni_sets"
    if not omni_sets.is_dir():
        return []
    scene_ids: list[str] = []
    for child in sorted(omni_sets.iterdir()):
        if child.is_dir() and child.name.startswith("SC"):
            scene_ids.append(child.name)
    return scene_ids


def build_report(repo_root: Path, scene_id: str) -> SceneReadinessReport:
    return compute_scene_readiness(repo_root=Path(repo_root), scene_id=scene_id)


def summarize_report(report: SceneReadinessReport) -> SceneReadinessSummary:
    shots_ready = 0
    shots_with_structural_issues = 0
    for shot in report.shots:
        has_structural_issues = bool(shot.structural_issues)
        if has_structural_issues:
            shots_with_structural_issues += 1
        if shot.computed_gate_status == "all_elements_ready" and not has_structural_issues:
            shots_ready += 1

    shots_blocking = len(report.shots) - shots_ready
    elements_total = sum(len(shot.elements) for shot in report.shots)
    elements_ready = sum(
        1 for shot in report.shots for element in shot.elements if element.is_ready
    )
    elements_blocking = elements_total - elements_ready
    return SceneReadinessSummary(
        scene_id=report.scene_id,
        shots_total=len(report.shots),
        shots_ready=shots_ready,
        shots_blocking=shots_blocking,
        shots_with_structural_issues=shots_with_structural_issues,
        elements_total=elements_total,
        elements_ready=elements_ready,
        elements_blocking=elements_blocking,
    )


def element_rows(shot: ShotReadiness) -> list[dict[str, Any]]:
    """Return a flat tabular view of a shot's element readiness."""
    rows: list[dict[str, Any]] = []
    for element in shot.elements:
        rows.append(
            {
                "element_id": element.element_id,
                "type": element.element_type,
                "role": element.role,
                "required": element.required_state,
                "binding": element.binding_status or "-",
                "binding_ok": "OK" if element.binding_ok else "BLOCK",
                "alias": element.kling_alias or "-",
                "alias_ok": "OK" if element.alias_ok else "BLOCK",
                "pack_manifest": "exists" if element.pack_manifest_present else "MISSING",
                "gpt_pack": (
                    element.gpt_pack_status or "-"
                    if element.gpt_pack_present
                    else "MISSING"
                ),
                "gpt_pack_ok": "OK" if element.gpt_pack_ok else "BLOCK",
                "kling_reference": (
                    element.kling_reference_status or "-"
                    if element.kling_reference_present
                    else "MISSING"
                ),
                "kling_reference_ok": "OK" if element.kling_reference_ok else "BLOCK",
                "approval_gate": "OK" if element.approval_gate_ok else "BLOCK",
                "status": "READY" if element.is_ready else "BLOCKING",
            }
        )
    return rows


def render_panel(st_module: Any, repo_root: Path) -> None:
    """Render the Scene Readiness panel in the given Streamlit module.

    Streamlit is injected as ``st_module`` so the panel can be exercised by
    a fake module in unit tests; production callers pass ``streamlit as st``.
    """
    st_module.header("Scene Readiness")
    st_module.caption(
        "Read-only view of the Kling Omni 3 element-first pipeline gate. "
        "Mirrors `python scripts/agents/operator_next_step.py --scene SC####`."
    )

    known = list_known_scene_ids(repo_root)
    if not known:
        st_module.write(
            "No `visual_dev/omni_sets/SC####` directories found. Author a scene "
            "shot_element_manifest first."
        )
        return

    default_index = 0
    selected = st_module.selectbox(
        "Scene",
        options=known,
        index=default_index,
        key="scene_readiness_selected_scene",
    )
    if not selected:
        return

    report = build_report(repo_root, selected)
    summary = summarize_report(report)

    metric_cols = st_module.columns(4)
    metric_cols[0].metric("Shots", summary.shots_total)
    metric_cols[1].metric("Elements", summary.elements_total)
    metric_cols[2].metric("Ready", summary.elements_ready)
    metric_cols[3].metric("Blocking", summary.elements_blocking)

    if summary.shots_total == 0:
        st_module.warning(
            "No shot_element_manifest found for "
            f"`{selected}`. Author "
            f"`visual_dev/omni_sets/{selected}/shot_element_manifests/<SHOT_ID>.yaml`."
        )
        return

    if summary.is_ready:
        st_module.success(
            f"All {summary.elements_total} required elements satisfy the gate. "
            "Kling Omni adapter may synthesize the shot prompt(s)."
        )
    else:
        structural_note = ""
        if summary.shots_with_structural_issues:
            structural_note = (
                f" Includes {summary.shots_with_structural_issues} shot(s) with "
                "structural manifest issues."
            )
        st_module.error(
            f"Readiness gate blocked: {summary.shots_blocking} of "
            f"{summary.shots_total} shot(s) are not all_elements_ready; "
            f"{summary.elements_blocking} of {summary.elements_total} required "
            f"elements are blocking.{structural_note} See next-step actions per "
            "shot below."
        )

    if report.notes:
        for note in report.notes:
            st_module.info(note)

    for shot in report.shots:
        st_module.subheader(f"Shot {shot.shot_id}")
        meta_cols = st_module.columns(2)
        meta_cols[0].write(f"manifest: `{shot.manifest_path}`")
        meta_cols[1].write(
            f"declared gate: **{shot.declared_gate_status}** · "
            f"computed gate: **{shot.computed_gate_status}**"
        )

        rows = element_rows(shot)
        if rows:
            st_module.dataframe(
                rows,
                hide_index=True,
                use_container_width=True,
            )

        for element in shot.elements:
            if element.is_ready:
                continue
            with st_module.expander(
                f"Blocking: {element.element_id} ({element.role}) — next steps"
            ):
                if element.blockers:
                    st_module.write("**Blockers:**")
                    for blocker in element.blockers:
                        st_module.write(f"- {blocker}")
                if element.next_steps:
                    st_module.write("**Next steps:**")
                    for step in element.next_steps:
                        st_module.write(f"- {step}")
