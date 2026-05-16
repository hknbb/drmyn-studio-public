"""Scene-level element pipeline readiness report.

Pure observer that inspects, per scene, the shot_element_manifests on disk
plus the upstream element pipeline records (element_binding, pack_manifest,
gpt_images_perspective_pack, kling_element_reference) and reports which
elements are ready for Kling Omni 3 prompt synthesis and which ones still
need operator action. Writes nothing. Mirrors the contract of
validate_shot_element_manifest.py but in an operator-facing shape: each
blocker is paired with the next concrete step the operator can take.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_shot_element_manifest import (  # noqa: E402
    ACTIVE_STATUSES,
    _active_alias,
    _element_root,
    _element_root_from_binding,
    _find_gpt_images_pack,
    _find_kling_reference,
    _find_pack_manifest,
    _load_scene_bindings,
    _pipeline_status_satisfies,
)


@dataclass
class ElementReadiness:
    element_id: str
    element_type: str
    role: str
    required_state: str
    binding_status: str | None
    binding_ok: bool
    kling_alias: str | None
    alias_ok: bool
    pack_manifest_present: bool
    gpt_pack_present: bool
    gpt_pack_status: str | None
    gpt_pack_ok: bool
    kling_reference_present: bool
    kling_reference_status: str | None
    kling_reference_ok: bool
    operator_approved: bool | None
    all_perspectives_score_85_plus: bool | None
    approval_gate_ok: bool
    element_root: str
    is_ready: bool
    blockers: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


@dataclass
class ShotReadiness:
    shot_id: str
    manifest_id: str | None
    manifest_path: str | None
    declared_gate_status: str | None
    computed_gate_status: str
    elements: list[ElementReadiness] = field(default_factory=list)
    structural_issues: list[str] = field(default_factory=list)


@dataclass
class SceneReadinessReport:
    scene_id: str
    scene_card_path: str | None
    bindings_path: str | None
    shots: list[ShotReadiness] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render(self) -> str:
        lines: list[str] = []
        lines.append(f"# Scene Readiness Report - {self.scene_id}")
        lines.append("")
        if self.scene_card_path:
            lines.append(f"Scene card: {self.scene_card_path}")
        if self.bindings_path:
            lines.append(f"Element bindings: {self.bindings_path}")
        lines.append("")

        if not self.shots:
            lines.append("No shot_element_manifests found for this scene.")
            lines.append(
                "Next step: author "
                f"visual_dev/omni_sets/{self.scene_id}/shot_element_manifests/<SHOT_ID>.yaml"
            )
            return "\n".join(lines)

        ready_count = 0
        blocking_count = 0
        for shot in self.shots:
            lines.append(f"## Shot {shot.shot_id}")
            if shot.manifest_path:
                lines.append(f"  manifest: {shot.manifest_path}")
            if shot.manifest_id:
                lines.append(f"  manifest_id: {shot.manifest_id}")
            lines.append(
                f"  declared gate: {shot.declared_gate_status}   "
                f"computed gate: {shot.computed_gate_status}"
            )
            if shot.structural_issues:
                lines.append("  structural issues:")
                for issue in shot.structural_issues:
                    lines.append(f"    - {issue}")
            lines.append("")
            for element in shot.elements:
                status_tag = "[READY]" if element.is_ready else "[BLOCKING]"
                lines.append(
                    f"  {status_tag} {element.element_id} "
                    f"({element.element_type}, {element.role}, "
                    f"required={element.required_state})"
                )
                lines.append(
                    f"    element_binding: {element.binding_status or '<missing>'}"
                    f"   {'OK' if element.binding_ok else 'BLOCK'}"
                )
                lines.append(
                    f"    kling_alias: {element.kling_alias or '<missing>'}"
                    f"   {'OK' if element.alias_ok else 'BLOCK'}"
                )
                lines.append(
                    f"    pack_manifest: "
                    f"{'exists' if element.pack_manifest_present else 'MISSING'}"
                )
                lines.append(
                    "    gpt_images_perspective_pack: "
                    f"{element.gpt_pack_status or '<missing>' if element.gpt_pack_present else 'MISSING'}"
                    f"   {'OK' if element.gpt_pack_ok else 'BLOCK'}"
                )
                ref_state = (
                    element.kling_reference_status or "<missing>"
                    if element.kling_reference_present
                    else "MISSING"
                )
                lines.append(
                    f"    kling_element_reference: {ref_state}"
                    f"   {'OK' if element.kling_reference_ok else 'BLOCK'}"
                )
                lines.append(
                    "    approval_gate: "
                    f"operator_approved={element.operator_approved!r}, "
                    "all_perspectives_score_85_plus="
                    f"{element.all_perspectives_score_85_plus!r}"
                    f"   {'OK' if element.approval_gate_ok else 'BLOCK'}"
                )
                if element.blockers:
                    lines.append("    blockers:")
                    for blocker in element.blockers:
                        lines.append(f"      - {blocker}")
                if element.next_steps:
                    lines.append("    next steps:")
                    for step in element.next_steps:
                        lines.append(f"      - {step}")
                if element.is_ready:
                    ready_count += 1
                else:
                    blocking_count += 1
                lines.append("")
        lines.append(
            f"Summary: {ready_count} ready, {blocking_count} blocking across "
            f"{len(self.shots)} shot(s)."
        )
        if blocking_count == 0:
            lines.append(
                "All required elements satisfy the Kling Omni 3 pipeline gate. "
                "Adapter may synthesize the shot prompt(s)."
            )
        else:
            lines.append(
                "Kling Omni 3 prompt synthesis remains gated until every "
                "[BLOCKING] element is resolved."
            )
        return "\n".join(lines)


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _next_steps_for_element(
    *,
    binding: dict[str, Any] | None,
    binding_ok: bool,
    pack_manifest_present: bool,
    gpt_pack_present: bool,
    kling_reference_present: bool,
    kling_reference_ok: bool,
    kling_reference_status: str | None,
    gpt_pack_status: str | None,
    gpt_pack_ok: bool,
    kling_alias: str | None,
    alias_ok: bool,
    operator_approved: bool | None,
    all_perspectives_score_85_plus: bool | None,
    approval_gate_ok: bool,
    element_id: str,
    element_type: str,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    next_steps: list[str] = []

    if binding is None:
        blockers.append(
            f"element_binding for {element_id} missing from scene element_bindings.yaml"
        )
        next_steps.append(
            f"Add an element_binding document for {element_id} ({element_type}) "
            "with a valid kling_alias and binding_status: planned at minimum."
        )
    elif not binding_ok:
        binding_status = binding.get("binding_status")
        blockers.append(
            f"element_binding.binding_status is {binding_status!r}; must be created or better"
        )
        if binding_status == "planned":
            next_steps.append(
                f"Register the Kling alias for {element_id} in the Kling Omni UI, then "
                "promote element_binding.binding_status from planned -> created and "
                "populate provenance.activated_by / activated_at."
            )
    elif not alias_ok:
        blockers.append("element_binding.kling_alias is missing or inactive")
        next_steps.append(
            f"Populate a registered Kling @alias for {element_id} in scene "
            "element_bindings.yaml."
        )

    if not pack_manifest_present:
        blockers.append("pack_manifest.yaml missing in element root")
        next_steps.append(
            f"Create a pack_manifest.yaml for {element_id} indexing the pipeline records."
        )

    if not gpt_pack_present:
        blockers.append("gpt_images_perspective_pack.yaml missing in element root")
        next_steps.append(
            "Author a gpt_images_perspective_pack.yaml (downstream_use: "
            "kling_omni_3_shot_prompt) with the three_view_scale_angle_v2 views "
            "front_reference, three_quarter_medium_reference, and "
            "three_quarter_close_reference aligned to the kling_element_reference "
            "schema."
        )
    elif not gpt_pack_ok:
        blockers.append(
            f"gpt_images_perspective_pack.status is {gpt_pack_status!r}; "
            "must be review or better"
        )
        next_steps.append(
            "Complete the three-view GPT Images 2 outputs, register external refs, "
            "and promote gpt_images_perspective_pack.status from draft -> review."
        )

    if not kling_reference_present:
        blockers.append("kling_element_reference.yaml missing in element root")
        next_steps.append(
            "Author a kling_element_reference.yaml linking source MJ reference + "
            "three GPT Images 2 perspectives + approval_gate; start at status: draft."
        )
    elif not kling_reference_ok:
        blockers.append(
            f"kling_element_reference.status is {kling_reference_status!r}; "
            "must be review or better"
        )
        next_steps.append(
            "Run the external Midjourney + ChatGPT Images 2 generation, populate "
            "image_selection.yaml with external paths, score perspectives in a "
            "perspective_qc record, set approval_gate.operator_approved: true, then "
            "promote kling_element_reference.status from draft -> review."
        )

    if kling_reference_present and not approval_gate_ok:
        if operator_approved is not True:
            blockers.append("approval_gate.operator_approved is not true")
            next_steps.append(
                "Complete operator approval for the Kling element reference."
            )
        if all_perspectives_score_85_plus is not True:
            blockers.append("approval_gate.all_perspectives_score_85_plus is not true")
            next_steps.append(
                "Complete perspective QC and set all_perspectives_score_85_plus: true "
                "only after every required view scores at least 85."
            )

    return blockers, next_steps


def _element_readiness(
    *,
    element: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
    repo_root: Path,
) -> ElementReadiness:
    element_id = str(element.get("element_id") or "")
    element_type = str(element.get("element_type") or "")
    role = str(element.get("role") or "")
    required_state = str(element.get("registration_state_required") or "")

    binding = bindings.get(element_id)
    binding_status = binding.get("binding_status") if binding else None
    binding_ok = binding_status in ACTIVE_STATUSES
    kling_alias = _active_alias(binding)
    alias_ok = kling_alias is not None

    if binding:
        root = _element_root_from_binding(repo_root, element_id, element_type, binding)
    else:
        root = _element_root(repo_root, element_id, element_type)

    pack_manifest = _find_pack_manifest(root)
    gpt_pack = _find_gpt_images_pack(root)
    kling_ref = _find_kling_reference(root)

    kling_ref_data = _load_yaml_mapping(kling_ref)
    kling_reference_status = (
        str(kling_ref_data.get("status")) if kling_ref_data else None
    )
    kling_reference_ok = _pipeline_status_satisfies(kling_reference_status)

    gpt_pack_data = _load_yaml_mapping(gpt_pack)
    gpt_pack_status = str(gpt_pack_data.get("status")) if gpt_pack_data else None
    gpt_pack_ok = _pipeline_status_satisfies(gpt_pack_status)

    approval_gate = kling_ref_data.get("approval_gate") if kling_ref_data else None
    operator_approved = (
        approval_gate.get("operator_approved") if isinstance(approval_gate, dict) else None
    )
    all_perspectives_score_85_plus = (
        approval_gate.get("all_perspectives_score_85_plus")
        if isinstance(approval_gate, dict)
        else None
    )
    approval_gate_ok = (
        operator_approved is True and all_perspectives_score_85_plus is True
    )

    blockers, next_steps = _next_steps_for_element(
        binding=binding,
        binding_ok=binding_ok,
        pack_manifest_present=pack_manifest.exists(),
        gpt_pack_present=gpt_pack.exists(),
        kling_reference_present=kling_ref.exists(),
        kling_reference_ok=kling_reference_ok,
        kling_reference_status=kling_reference_status,
        gpt_pack_status=gpt_pack_status,
        gpt_pack_ok=gpt_pack_ok,
        kling_alias=kling_alias,
        alias_ok=alias_ok,
        operator_approved=operator_approved,
        all_perspectives_score_85_plus=all_perspectives_score_85_plus,
        approval_gate_ok=approval_gate_ok,
        element_id=element_id,
        element_type=element_type,
    )

    is_ready = (
        binding_ok
        and alias_ok
        and pack_manifest.exists()
        and gpt_pack.exists()
        and gpt_pack_ok
        and kling_ref.exists()
        and kling_reference_ok
        and approval_gate_ok
    )

    return ElementReadiness(
        element_id=element_id,
        element_type=element_type,
        role=role,
        required_state=required_state,
        binding_status=binding_status,
        binding_ok=binding_ok,
        kling_alias=kling_alias,
        alias_ok=alias_ok,
        pack_manifest_present=pack_manifest.exists(),
        gpt_pack_present=gpt_pack.exists(),
        gpt_pack_status=gpt_pack_status,
        gpt_pack_ok=gpt_pack_ok,
        kling_reference_present=kling_ref.exists(),
        kling_reference_status=kling_reference_status,
        kling_reference_ok=kling_reference_ok,
        operator_approved=operator_approved,
        all_perspectives_score_85_plus=all_perspectives_score_85_plus,
        approval_gate_ok=approval_gate_ok,
        element_root=root.relative_to(repo_root).as_posix() if root.is_absolute() else str(root),
        is_ready=is_ready,
        blockers=blockers,
        next_steps=next_steps,
    )


def _shot_readiness(
    *,
    manifest_path: Path,
    bindings: dict[str, dict[str, Any]],
    repo_root: Path,
) -> ShotReadiness:
    rel_path = manifest_path.relative_to(repo_root).as_posix()
    data = _load_yaml_mapping(manifest_path)
    if data is None:
        return ShotReadiness(
            shot_id=manifest_path.stem,
            manifest_id=None,
            manifest_path=rel_path,
            declared_gate_status=None,
            computed_gate_status="unknown",
            structural_issues=[f"could not parse {rel_path} as a mapping"],
        )

    required_elements = data.get("required_elements") or []
    element_reports: list[ElementReadiness] = []
    for element in required_elements:
        if not isinstance(element, dict):
            continue
        element_reports.append(
            _element_readiness(
                element=element,
                bindings=bindings,
                repo_root=repo_root,
            )
        )

    if not element_reports:
        computed_gate = "pending"
    elif all(report.is_ready for report in element_reports):
        computed_gate = "all_elements_ready"
    else:
        computed_gate = "blocked"

    return ShotReadiness(
        shot_id=str(data.get("shot_id") or manifest_path.stem),
        manifest_id=data.get("manifest_id"),
        manifest_path=rel_path,
        declared_gate_status=data.get("gate_status"),
        computed_gate_status=computed_gate,
        elements=element_reports,
    )


def compute_scene_readiness(
    *,
    repo_root: Path,
    scene_id: str,
) -> SceneReadinessReport:
    repo_root = Path(repo_root).resolve()
    bindings_path = repo_root / "visual_dev" / "omni_sets" / scene_id / "element_bindings.yaml"
    scene_card_path = repo_root / "planning" / "scenes" / scene_id / "scene_card.yaml"
    manifest_dir = (
        repo_root / "visual_dev" / "omni_sets" / scene_id / "shot_element_manifests"
    )

    bindings = _load_scene_bindings(repo_root, scene_id)
    notes: list[str] = []
    if not bindings_path.exists():
        notes.append(
            f"No element_bindings.yaml at {bindings_path.relative_to(repo_root).as_posix()}; "
            "every required element will be reported as missing."
        )

    shots: list[ShotReadiness] = []
    if manifest_dir.exists():
        for manifest_path in sorted(manifest_dir.glob("*.yaml")):
            shots.append(
                _shot_readiness(
                    manifest_path=manifest_path,
                    bindings=bindings,
                    repo_root=repo_root,
                )
            )

    return SceneReadinessReport(
        scene_id=scene_id,
        scene_card_path=(
            scene_card_path.relative_to(repo_root).as_posix()
            if scene_card_path.exists()
            else None
        ),
        bindings_path=(
            bindings_path.relative_to(repo_root).as_posix()
            if bindings_path.exists()
            else None
        ),
        shots=shots,
        notes=notes,
    )


def render_report(report: SceneReadinessReport, *, fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    return report.render()
