"""Streamlit entry point for the copilot dashboard."""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import streamlit as st
except ImportError as exc:  # pragma: no cover - exercised by manual launch
    raise SystemExit(
        "Streamlit is not installed. Install the optional UI dependency first."
    ) from exc

from tools.copilot_dashboard.repo_io import (
    load_latest_recommendation,
    load_recent_handoffs,
    load_recent_sessions,
    load_status_rows,
)
from tools.copilot_dashboard.command_ui import (
    HANDOFF_REASON_OPTIONS,
    TARGET_AGENT_OPTIONS,
    CommandUiResult,
    run_dashboard_command,
)
from tools.copilot_dashboard.review_panels import load_review_panel_data
from tools.copilot_dashboard.pr_panel import PrPanelData, load_pr_panel_data
from tools.copilot_dashboard.asset_intake_panel import (
    load_intake_slot_rows,
    load_placement_preview,
    stage_uploaded_file,
    VIEW_ROLE_OPTIONS,
    ALLOWED_IMAGE_SUFFIXES,
)
from tools.copilot_dashboard.scene_readiness_panel import (
    render_panel as render_scene_readiness_panel,
)


def _stringify_record(record: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in record.items()}


def _show_command_result(result: CommandUiResult) -> None:
    if result.applied:
        st.success(result.message)
        if result.written_files:
            st.write("Written files:")
            st.write(list(result.written_files))
        return
    st.error(result.message)


def _render_command_controls(recommendation: dict[str, Any]) -> None:
    allowed_commands = recommendation.get("allowed_commands") or []

    st.header("Command Controls")
    st.caption("PR merge remains human-controlled. Commands write metadata evidence only.")

    if not allowed_commands:
        st.write("No commands are allowed by the current recommendation.")
        return

    yes_col, no_col = st.columns(2)
    with yes_col:
        if st.button("Yes", disabled="yes" not in allowed_commands):
            _show_command_result(
                run_dashboard_command(
                    REPO_ROOT,
                    command="yes",
                    allowed_commands=allowed_commands,
                )
            )

    with no_col:
        no_note = st.text_area("No note", key="no_note", height=90)
        if st.button("No", disabled="no" not in allowed_commands):
            _show_command_result(
                run_dashboard_command(
                    REPO_ROOT,
                    command="no",
                    note=no_note,
                    allowed_commands=allowed_commands,
                )
            )

    revise_col, switch_col = st.columns(2)
    with revise_col:
        revise_note = st.text_area("Revise note", key="revise_note", height=90)
        if st.button("Revise", disabled="revise" not in allowed_commands):
            _show_command_result(
                run_dashboard_command(
                    REPO_ROOT,
                    command="revise",
                    note=revise_note,
                    allowed_commands=allowed_commands,
                )
            )

    with switch_col:
        target_agent = st.selectbox("Target agent", TARGET_AGENT_OPTIONS)
        reason = st.selectbox("Reason", HANDOFF_REASON_OPTIONS)
        if st.button("Switch", disabled="switch" not in allowed_commands):
            _show_command_result(
                run_dashboard_command(
                    REPO_ROOT,
                    command="switch",
                    target_agent=target_agent,
                    reason=reason,
                    allowed_commands=allowed_commands,
                )
            )


def _render_review_panels() -> None:
    panel_data = load_review_panel_data(REPO_ROOT)
    image_rows = panel_data["image_candidates"]
    video_rows = panel_data["video_takes"]

    st.header("Review Metadata")
    st.caption(
        "Read-only metadata/path refs. No uploads, thumbnails, cache writes, "
        "or review decisions."
    )

    image_tab, video_tab = st.tabs(["Image Candidates", "Video Takes"])
    with image_tab:
        if image_rows:
            st.dataframe(image_rows, hide_index=True, use_container_width=True)
        else:
            st.write("No image candidate metadata records.")

    with video_tab:
        if video_rows:
            st.dataframe(video_rows, hide_index=True, use_container_width=True)
        else:
            st.write("No video take metadata records.")


def _render_staging_wizard() -> None:
    st.subheader("Upload to Local Staging")
    st.caption(
        "Writes only to gitignored visual_dev/intake_staging/C01_WD001/. "
        "No canonical directory writes. No intake_slot mutation. No Git LFS action."
    )
    st.info(
        "Target slot: **C01 / wardrobe / WD001** (B8A scope — only slot approved for staging). "
        f"Accepted formats: {', '.join(sorted(ALLOWED_IMAGE_SUFFIXES))}."
    )

    uploaded_files = st.file_uploader(
        "Select reference image(s)",
        type=[s.lstrip(".") for s in sorted(ALLOWED_IMAGE_SUFFIXES)],
        accept_multiple_files=True,
        key="staging_uploader",
    )
    view_role = st.selectbox("View role", VIEW_ROLE_OPTIONS, key="staging_view_role")
    operator_note = st.text_area(
        "Operator note (optional)", key="staging_operator_note", height=70
    )

    if st.button("Stage files", disabled=not uploaded_files):
        for uf in uploaded_files:
            result = stage_uploaded_file(
                REPO_ROOT,
                uf.read(),
                uf.name,
                view_role,
                operator_note,
            )
            if result.success:
                st.success(f"{result.message} → `{result.staged_path}`")
                st.caption(f"Sidecar: `{result.sidecar_path}`")
            else:
                st.error(result.message)


def _render_placement_preview() -> None:
    preview = load_placement_preview(REPO_ROOT)

    st.subheader("Placement Preview")
    st.caption(
        "Read-only preview from staged files and sidecars. No file moves. "
        "No canonical writes. No intake_slot mutation."
    )
    st.info(preview["git_lfs_reminder"])

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("staged files", preview["staged_count"])
    metric2.metric("committed", preview["committed_count"])
    metric3.metric("duplicate targets", len(preview["duplicate_targets"]))

    st.write(f"**Target slot:** `{preview['slot_path']}`")
    if preview["required_views"]:
        st.write("**Required views:** " + ", ".join(preview["required_views"]))
    if preview["missing_views_now"]:
        st.write("**Missing now:** " + ", ".join(preview["missing_views_now"]))
    else:
        st.write("**Missing now:** none")
    if preview["missing_views_after_preview"]:
        st.write(
            "**Missing after staged preview:** "
            + ", ".join(preview["missing_views_after_preview"])
        )
    else:
        st.success("Staged preview covers all currently required views.")

    if not preview["slot_exists"]:
        st.warning("Approved target intake slot is missing from the repo.")
    for warning in preview["warnings"]:
        st.warning(warning)

    rows = preview["rows"]
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.write("No staged files found in the local intake staging area.")


def _render_asset_intake_panel() -> None:
    rows = load_intake_slot_rows(REPO_ROOT)

    st.header("Asset Intake Readiness")
    st.caption(
        "Readiness panel is read-only. Staging wizard writes only to gitignored staging area."
    )
    st.info(
        "B8A first canonical asset intake is limited to **C01 / wardrobe / WD001**. "
        "Canonical reference images must be human-sourced, reviewed, and Git LFS tracked. "
        "Generated T2I production outputs are not canonical references. "
        "Do not lock packs or promote lifecycle state from this panel."
    )

    if not rows:
        st.write("No intake slot records found.")
    else:
        first_slot_rows = [r for r in rows if r["is_first_intake_slot"]]
        other_rows = [r for r in rows if not r["is_first_intake_slot"]]

        if first_slot_rows:
            st.subheader("B8A — First Intake Slot (C01 / WD001)")
            row = first_slot_rows[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("source_status", row["source_status"])
            col2.metric("committed", row["committed_count"])
            col3.metric("storage_policy", row["storage_policy"])
            st.write(f"**Required views:** {row['required_views']}")
            if row["missing_views"] != "—":
                st.warning(f"Missing views: {row['missing_views']}")
            else:
                st.success("All required views committed.")
            for field in ("copyright_review", "provenance_review"):
                status = row[field]
                if status == "pending":
                    st.warning(f"{field}: pending")
                elif status == "approved":
                    st.success(f"{field}: approved")
                else:
                    st.write(f"{field}: {status}")
            st.write(f"**intake_ready_to_proceed:** {row['intake_ready_to_proceed']}")
            st.write(f"**Context:** {row['context']}")
            st.caption(f"slot: `{row['slot_path']}`")

        if other_rows:
            st.subheader("Other Intake Slots")
            display = [
                {
                    "slot_path": r["slot_path"],
                    "element_id": r["element_id"],
                    "group_id": r["group_id"],
                    "element_type": r["element_type"],
                    "source_status": r["source_status"],
                    "storage_policy": r["storage_policy"],
                    "copyright_review": r["copyright_review"],
                    "provenance_review": r["provenance_review"],
                    "committed": r["committed_count"],
                    "missing_views": r["missing_views"],
                    "intake_ready_to_proceed": r["intake_ready_to_proceed"],
                }
                for r in other_rows
            ]
            st.dataframe(display, hide_index=True, use_container_width=True)
            ready_outside_b8a = [
                r for r in other_rows if r["source_status"] != "not_collected"
            ]
            if ready_outside_b8a:
                st.warning(
                    "Warning: slot(s) outside WD001 show source_status != not_collected. "
                    "B8A scope guard: only C01/WD001 is approved for first intake."
                )

    _render_staging_wizard()
    _render_placement_preview()


def _render_pr_panel() -> None:
    data = load_pr_panel_data(REPO_ROOT)

    st.header("PR Helper")
    st.caption("Suggestion only. This dashboard does not call gh, push, or create PRs.")

    if not data.available:
        st.warning(data.message)
        return

    assert isinstance(data, PrPanelData)
    st.write(f"Branch: `{data.branch}`")
    st.write(f"Title: `{data.title}`")

    if data.changed_files:
        st.write("Changed files:")
        st.dataframe(
            [{"path": path} for path in data.changed_files],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.write("No changed files detected against base.")

    st.text_area("PR body preview", value=data.body_preview, height=260)
    st.code(data.gh_command_str, language="bash")


def main() -> None:
    st.set_page_config(page_title="Copilot Dashboard", layout="wide")
    st.title("Human-Agent Copilot")

    recommendation = load_latest_recommendation(REPO_ROOT)
    status_rows = load_status_rows(REPO_ROOT)
    sessions = load_recent_sessions(REPO_ROOT)
    handoffs = load_recent_handoffs(REPO_ROOT)

    st.header("Latest Recommendation")
    st.json(recommendation)

    st.header("Production Status")
    if status_rows:
        st.dataframe(status_rows, hide_index=True, use_container_width=True)
    else:
        st.write("No production status rows.")

    left, right = st.columns(2)
    with left:
        st.header("Recent Sessions")
        if sessions:
            st.dataframe(
                [_stringify_record(record) for record in sessions],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.write("No operator sessions.")

    with right:
        st.header("Recent Handoffs")
        if handoffs:
            st.dataframe(
                [_stringify_record(record) for record in handoffs],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.write("No agent handoffs.")

    st.header("Allowed Commands")
    commands = recommendation.get("allowed_commands") or []
    if commands:
        st.write(", ".join(str(command) for command in commands))
    else:
        st.write("No allowed commands.")

    _render_command_controls(recommendation)
    render_scene_readiness_panel(st, REPO_ROOT)
    _render_review_panels()
    _render_asset_intake_panel()
    _render_pr_panel()


if __name__ == "__main__":
    main()
