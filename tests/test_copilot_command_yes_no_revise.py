from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.copilot_command import apply_command  # noqa: E402
from scripts.validate_production_records import run_validation  # noqa: E402


PROMPT_ID = "SC0001__t2i-char-c01-midjourney__v01"
FIXED_NOW = datetime(2026, 5, 1, 12, 0, 0)


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_schemas(repo_root: Path) -> None:
    schemas_dir = repo_root / "schemas"
    schemas_dir.mkdir(parents=True)
    for name in (
        "image_selection.schema.json",
        "asset_clearance.schema.json",
        "video_take.schema.json",
        "video_review.schema.json",
        "selected_take.schema.json",
        "batch_job.schema.json",
        "operator_session.schema.json",
        "agent_handoff.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _seed_prompt_repo(repo_root: Path) -> None:
    _copy_schemas(repo_root)
    scene_dir = repo_root / "planning/scenes/SC0001"
    _write_yaml(
        scene_dir / "scene_card.yaml",
        {"scene_id": "SC0001", "excerpt_ref": "scene_excerpt.md"},
    )
    (scene_dir / "scene_excerpt.md").write_text("Scene excerpt.", encoding="utf-8")
    _write_yaml(
        repo_root / "prompts/draft" / f"{PROMPT_ID}.yaml",
        {
            "prompt_id": PROMPT_ID,
            "scene_id": "SC0001",
            "prompt_type": "t2i_character_element",
            "lifecycle_stage": "draft",
            "target_models": ["midjourney"],
            "source_refs": {
                "scene_card": "planning/scenes/SC0001/scene_card.yaml",
                "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md",
                "character_refs": ["C01"],
            },
            "prompt_text": "Generate a source-grounded character image.",
            "status": "active",
            "canon_lock": False,
        },
    )


def _seed_storyboard_repo(repo_root: Path) -> None:
    _copy_schemas(repo_root)
    scene_dir = repo_root / "planning/scenes/SC0001"
    _write_yaml(
        scene_dir / "scene_card.yaml",
        {"scene_id": "SC0001", "excerpt_ref": "scene_excerpt.md"},
    )
    (scene_dir / "scene_excerpt.md").write_text("Scene excerpt.", encoding="utf-8")
    _write_yaml(
        repo_root / "visual_dev/storyboards/SC0001/storyboard_options.yaml",
        {
            "scene_id": "SC0001",
            "round": 1,
            "source_refs": {
                "scene_card": "planning/scenes/SC0001/scene_card.yaml",
                "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md",
            },
            "options": [
                {
                    "option_id": f"SC0001_SB{index:02d}",
                    "purpose": "Source-grounded option.",
                    "camera_angle": "Static coverage.",
                    "framing": "Doorway frame.",
                    "movement": "Minimal.",
                    "lighting": "Soft daylight.",
                    "source_field": "scene_card.visual_targets.framing_bias",
                    "prompt_ids": [],
                    "status": "candidate",
                }
                for index in range(1, 6)
            ],
            "selected_option": None,
            "review_status": "pending",
            "storage_policy": "no_binary_commits",
        },
    )


def test_yes_writes_operator_session_in_progress(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    result = apply_command(tmp_path, command="yes", now=FIXED_NOW, auto_handoff=False)

    path = tmp_path / "evidence/operator_sessions/OP-20260501-120000.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    report = run_validation(tmp_path)
    assert result.written_files == ("evidence/operator_sessions/OP-20260501-120000.yaml",)
    assert payload["status"] == "in_progress"
    assert payload["current_task"] == "t2i_image_generation"
    assert payload["recommended_files"]
    assert report.invalid_files == 0


def test_no_requires_note_and_writes_no_file_on_failure(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    with pytest.raises(ValueError, match="note"):
        apply_command(tmp_path, command="no", now=FIXED_NOW)

    assert not (tmp_path / "evidence/operator_sessions").exists()


def test_no_writes_skipped_operator_session_with_note(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    apply_command(
        tmp_path,
        command="no",
        note="Operator wants a different prompt direction.",
        now=FIXED_NOW,
    )

    path = tmp_path / "evidence/operator_sessions/OP-20260501-120000.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert payload["status"] == "skipped"
    assert payload["notes"] == "Operator wants a different prompt direction."
    assert run_validation(tmp_path).invalid_files == 0


def test_revise_prompt_task_writes_prompt_review_brief(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    result = apply_command(
        tmp_path,
        command="revise",
        note="Reduce stylized lighting and keep source-grounded domestic tone.",
        now=FIXED_NOW,
    )

    expected = f"evidence/prompt_reviews/{PROMPT_ID}_brief.yaml"
    path = tmp_path / expected
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert result.written_files == (expected,)
    assert payload["source_prompt_id"] == PROMPT_ID
    assert "revision_reason" in payload["corrected_brief"]
    assert run_validation(tmp_path).invalid_files == 0


def test_revise_non_prompt_task_writes_revision_markdown(tmp_path: Path) -> None:
    _seed_storyboard_repo(tmp_path)

    result = apply_command(
        tmp_path,
        command="revise",
        note="Need a stronger threshold composition before selection.",
        now=FIXED_NOW,
    )

    expected = "evidence/operator_sessions/OP-20260501-120000_revisions.md"
    path = tmp_path / expected
    assert result.written_files == (expected,)
    assert "threshold composition" in path.read_text(encoding="utf-8")
    assert run_validation(tmp_path).invalid_files == 0


def test_revise_requires_note_and_writes_no_file_on_failure(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    with pytest.raises(ValueError, match="note"):
        apply_command(tmp_path, command="revise", now=FIXED_NOW)

    assert not (tmp_path / "evidence/prompt_reviews").exists()
    assert not (tmp_path / "evidence/operator_sessions").exists()


def test_yes_collision_adds_suffix(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    first = apply_command(tmp_path, command="yes", now=FIXED_NOW, auto_handoff=False)
    second = apply_command(tmp_path, command="yes", now=FIXED_NOW, auto_handoff=False)

    assert first.written_files == ("evidence/operator_sessions/OP-20260501-120000.yaml",)
    assert second.written_files == (
        "evidence/operator_sessions/OP-20260501-120000-001.yaml",
    )
