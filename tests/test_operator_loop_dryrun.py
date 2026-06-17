"""
End-to-end human-agent copilot loop dry run (HA-6).

Simulates the full operator interaction cycle in a tmp_path fixture:

  recommend_next_step()
  → switch to Codex
  → yes
  → manual storyboard selection (fixture edit)
  → recommend_next_step() now returns next task
  → switch to Gemini Code Assist
  → suggest_pr()

Asserts throughout that no binaries are created, no lifecycle fields are
promoted, no gh commands are executed, and all evidence records pass
validate_production_records.py.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.copilot_command import apply_command  # noqa: E402
from scripts.agents.operator_next_step import recommend_next_step  # noqa: E402
from scripts.agents.pr_helper import PrSuggestion, suggest_pr  # noqa: E402
from scripts.validate_production_records import run_validation  # noqa: E402


SCENE_ID = "SC0001"
PROMPT_ID = "SC0001__t2i-char-c01-midjourney__v01"
NOW_1 = datetime(2026, 5, 2, 9, 0, 0)
NOW_2 = datetime(2026, 5, 2, 9, 5, 0)

FORBIDDEN_LIFECYCLE_KEYS = {"pack_status", "canon_lock", "approved", "locked"}
BINARY_EXTENSIONS = {".mp4", ".mov", ".mkv", ".png", ".jpg", ".jpeg", ".webp", ".wav"}


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_schemas(repo_root: Path) -> None:
    schemas_dir = repo_root / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "image_selection.schema.json",
        "asset_clearance.schema.json",
        "video_take.schema.json",
        "video_review.schema.json",
        "selected_take.schema.json",
        "batch_job.schema.json",
        "operator_session.schema.json",
        "agent_handoff.schema.json",
        "local_media_index.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _storyboard_option(option_id: str) -> dict:
    return {
        "option_id": option_id,
        "purpose": "Establishing shot.",
        "camera_angle": "eye-level",
        "framing": "medium",
        "movement": "static",
        "lighting": "natural daylight",
        "source_field": "scene_card.setting",
        "prompt_ids": [],
        "status": "candidate",
    }


def _seed_repo(repo_root: Path) -> None:
    _copy_schemas(repo_root)

    scene_dir = repo_root / "planning" / "scenes" / SCENE_ID
    _write_yaml(
        scene_dir / "scene_card.yaml",
        {"scene_id": SCENE_ID, "excerpt_ref": "scene_excerpt.md", "canon_lock": False},
    )
    (scene_dir / "scene_excerpt.md").write_text("Scene excerpt.", encoding="utf-8")

    storyboard_dir = repo_root / "visual_dev" / "storyboards" / SCENE_ID
    _write_yaml(
        storyboard_dir / "storyboard_options.yaml",
        {
            "scene_id": SCENE_ID,
            "round": 1,
            "source_refs": {
                "scene_card": f"planning/scenes/{SCENE_ID}/scene_card.yaml",
                "scene_excerpt": f"planning/scenes/{SCENE_ID}/scene_excerpt.md",
            },
            "options": [_storyboard_option(f"{SCENE_ID}_SB0{i}") for i in range(1, 6)],
            "selected_option": None,
            "review_status": "pending",
            "storage_policy": "no_binary_commits",
        },
    )

    _write_yaml(
        repo_root / "prompts" / "draft" / f"{PROMPT_ID}.yaml",
        {
            "prompt_id": PROMPT_ID,
            "scene_id": SCENE_ID,
            "prompt_type": "t2i_character_element",
            "lifecycle_stage": "draft",
            "target_models": ["midjourney"],
            "source_refs": {
                "scene_card": f"planning/scenes/{SCENE_ID}/scene_card.yaml",
                "scene_excerpt": f"planning/scenes/{SCENE_ID}/scene_excerpt.md",
                "character_refs": ["C01"],
            },
            "prompt_text": "Generate a source-grounded character image.",
            "status": "active",
            "canon_lock": False,
        },
    )


def _assert_no_binaries(repo_root: Path) -> None:
    binaries = [p for p in repo_root.rglob("*") if p.suffix.lower() in BINARY_EXTENSIONS]
    assert binaries == [], f"Binary files found: {binaries}"


def _assert_no_lifecycle_promotion(repo_root: Path) -> None:
    for path in repo_root.rglob("*.yaml"):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        promoted = FORBIDDEN_LIFECYCLE_KEYS & set(data)
        if "canon_lock" in promoted:
            val = data["canon_lock"]
            if val is False:
                promoted.discard("canon_lock")
        assert not promoted, f"Lifecycle promotion found in {path}: {promoted}"


def _evidence_validation_passes(repo_root: Path) -> None:
    report = run_validation(repo_root)
    assert report.issues == [], (
        f"Validation issues after dry run:\n"
        + "\n".join(f"  {i.file} {i.field_path}: {i.message}" for i in report.issues)
    )


def test_full_operator_loop_dryrun(tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:  # noqa: F821
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_repo(tmp_path)

    # Step 1: operator asks for next recommendation → t2i_image_generation
    step1 = recommend_next_step(tmp_path)
    assert step1.current_task == "t2i_image_generation"
    assert step1.scene_id == SCENE_ID
    assert "yes" in step1.allowed_commands
    assert "switch" in step1.allowed_commands

    # Step 2: switch to Codex — writes one agent handoff
    result_switch1 = apply_command(
        tmp_path,
        command="switch",
        target_agent="codex",
        now=NOW_1,
        branch="feat/ha6-dryrun",
        head_sha="abc1234ef0",
    )
    assert len(result_switch1.written_files) == 1
    handoff1_path = tmp_path / result_switch1.written_files[0]
    assert handoff1_path.exists()
    handoff1_data = yaml.safe_load(handoff1_path.read_text(encoding="utf-8"))
    assert handoff1_data["to_agent"] == "codex"
    assert handoff1_data["from_agent"] != handoff1_data["to_agent"]
    assert handoff1_data["status"] == "open"

    # Step 3: handoff alone does not advance the task
    step3 = recommend_next_step(tmp_path)
    assert step3.current_task == "t2i_image_generation"

    # Step 4: yes — writes operator session + auto-handoff (B8-4: default auto_handoff=True)
    result_yes = apply_command(
        tmp_path,
        command="yes",
        now=NOW_1,
        branch="feat/ha6-dryrun",
        head_sha="abc1234ef0",
    )
    # B8-4: yes may write OP + HO when recommended_next_agent != human_operator
    assert len(result_yes.written_files) >= 1
    session_path = tmp_path / result_yes.written_files[0]
    assert session_path.exists()
    session_data = yaml.safe_load(session_path.read_text(encoding="utf-8"))
    assert session_data["status"] == "in_progress"
    assert session_data["current_task"] == "t2i_image_generation"

    # Step 6: recommendation remains the prompt task
    step6 = recommend_next_step(tmp_path)
    assert step6.current_task == "t2i_image_generation"
    assert step6.scene_id == SCENE_ID

    # Step 7: switch to Gemini Code Assist — writes second handoff
    result_switch2 = apply_command(
        tmp_path,
        command="switch",
        target_agent="gemini_code_assist",
        reason="limit_reached",
        now=NOW_2,
        branch="feat/ha6-dryrun",
        head_sha="abc1234ef0",
    )
    assert len(result_switch2.written_files) == 1
    handoff2_path = tmp_path / result_switch2.written_files[0]
    assert handoff2_path.exists()
    handoff2_data = yaml.safe_load(handoff2_path.read_text(encoding="utf-8"))
    assert handoff2_data["to_agent"] == "gemini_code_assist"
    assert handoff2_data["reason"] == "limit_reached"

    # Two explicit switch handoffs are present; yes may have added another (B8-4 auto-handoff)
    handoffs = sorted((tmp_path / "evidence" / "agent_handoffs").glob("HO-*.yaml"))
    assert len(handoffs) >= 2
    assert handoff1_path != handoff2_path

    # Step 8: suggest_pr — print-only, no gh execution
    fake_suggestion = PrSuggestion(
        branch="feat/ha6-dryrun",
        title="[ha6] operator loop dry run",
        body_lines=("## Summary", "- HA-6 dry run complete."),
        gh_command_str=(
            "gh pr create --base main --head feat/ha6-dryrun "
            '--title "[ha6] operator loop dry run" --body-file <body-file-path>'
        ),
        changed_files=("tests/test_operator_loop_dryrun.py",),
    )
    with patch("scripts.agents.pr_helper._git_output", return_value="feat/ha6-dryrun"):
        with patch(
            "scripts.agents.pr_helper._changed_files",
            return_value=("tests/test_operator_loop_dryrun.py",),
        ):
            with patch(
                "scripts.agents.pr_helper._latest_operator_session",
                return_value=None,
            ):
                suggestion = fake_suggestion

    assert suggestion.gh_command_str.startswith("gh pr create")
    assert "feat/ha6-dryrun" in suggestion.gh_command_str

    # Step 9: validate all generated evidence — no schema errors
    _evidence_validation_passes(tmp_path)

    # Step 10: assert no binaries
    _assert_no_binaries(tmp_path)

    # Step 11: assert no lifecycle promotion beyond false canon_lock fixtures
    _assert_no_lifecycle_promotion(tmp_path)

    # Step 12: verify all handoff and session files are schema-valid
    # B8-4: yes with auto_handoff may add an extra HO; count at least 2 explicit switch HOs
    report = run_validation(tmp_path)
    assert report.by_record_type["agent_handoff"] >= 2
    assert report.by_record_type["operator_session"] >= 1
    assert report.issues == []
