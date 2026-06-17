"""
B8-4 tests: auto-handoff for yes command and pickup mode.

Covers:
- yes default auto-handoff writes OP + HO
- yes --no-auto-handoff writes OP only
- switch still writes HO as before
- generated HO uses recommended_next_agent and recommended_reason
- pickup requires CP_AGENT_NAME
- pickup rejects unknown CP_AGENT_NAME
- pickup finds latest matching open handoff
- pickup does not write files
- chatgpt_project is never accepted
"""

from __future__ import annotations

import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.copilot_command import apply_command  # noqa: E402
from scripts.agents.run_pipeline import build_parser, run_pickup  # noqa: E402
from scripts.validate_production_records import run_validation  # noqa: E402


PROMPT_ID = "SC0001__t2i-char-c01-midjourney__v01"
FIXED_NOW = datetime(2026, 5, 6, 10, 0, 0)


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
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _seed_storyboard_repo(repo_root: Path) -> None:
    """Seed a repo state where storyboard_selection is the recommended task (routes to gemini_code_assist)."""
    _copy_schemas(repo_root)
    scene_dir = repo_root / "planning/scenes/SC0001"
    _write_yaml(
        scene_dir / "scene_card.yaml",
        {"scene_id": "SC0001", "excerpt_ref": "scene_excerpt.md", "canon_lock": False},
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
                    "option_id": f"SC0001_SB{i:02d}",
                    "purpose": "Establishing shot.",
                    "camera_angle": "eye-level",
                    "framing": "medium",
                    "movement": "static",
                    "lighting": "natural daylight",
                    "source_field": "scene_card.setting",
                    "prompt_ids": [],
                    "status": "candidate",
                }
                for i in range(1, 6)
            ],
            "selected_option": None,
            "review_status": "pending",
            "storage_policy": "no_binary_commits",
        },
    )


def _seed_prompt_repo(repo_root: Path) -> None:
    """Seed a repo state where t2i_image_generation is the recommended task (routes to claude_code)."""
    _copy_schemas(repo_root)
    scene_dir = repo_root / "planning/scenes/SC0001"
    _write_yaml(
        scene_dir / "scene_card.yaml",
        {"scene_id": "SC0001", "excerpt_ref": "scene_excerpt.md", "canon_lock": False},
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


# ---------------------------------------------------------------------------
# Auto-handoff: yes command
# ---------------------------------------------------------------------------


def test_yes_auto_handoff_default_writes_op_and_ho(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_prompt_repo(tmp_path)  # t2i_image_generation → claude_code/manual_pickup

    result = apply_command(
        tmp_path,
        command="yes",
        now=FIXED_NOW,
        branch="feat/b8-4",
        head_sha="aabbccdd1234",
    )

    assert len(result.written_files) == 2
    op_path = tmp_path / result.written_files[0]
    ho_path = tmp_path / result.written_files[1]
    assert op_path.exists()
    assert ho_path.exists()

    op_data = yaml.safe_load(op_path.read_text(encoding="utf-8"))
    ho_data = yaml.safe_load(ho_path.read_text(encoding="utf-8"))

    assert op_data["status"] == "in_progress"
    assert ho_data["to_agent"] == "claude_code"
    assert ho_data["reason"] == "manual_pickup"
    assert ho_data["status"] == "open"
    assert ho_data["from_agent"] != ho_data["to_agent"]

    report = run_validation(tmp_path)
    assert report.issues == []


def test_yes_auto_handoff_uses_recommended_next_agent_and_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_prompt_repo(tmp_path)

    result = apply_command(
        tmp_path,
        command="yes",
        now=FIXED_NOW,
        branch="feat/b8-4",
        head_sha="aabbccdd1234",
    )

    assert len(result.written_files) == 2
    ho_path = tmp_path / result.written_files[1]
    ho_data = yaml.safe_load(ho_path.read_text(encoding="utf-8"))

    assert ho_data["to_agent"] == "claude_code"
    assert ho_data["reason"] == "manual_pickup"
    assert "feat/b8-4" in ho_data.get("branch", "")


def test_yes_no_auto_handoff_writes_op_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_storyboard_repo(tmp_path)

    result = apply_command(
        tmp_path,
        command="yes",
        now=FIXED_NOW,
        auto_handoff=False,
    )

    assert len(result.written_files) == 1
    op_path = tmp_path / result.written_files[0]
    assert op_path.exists()
    assert "operator_sessions" in result.written_files[0]

    handoffs_dir = tmp_path / "evidence" / "agent_handoffs"
    assert not list(handoffs_dir.glob("HO-*.yaml")) if handoffs_dir.exists() else True


def test_yes_auto_handoff_skipped_when_recommended_is_human_operator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_prompt_repo(tmp_path)

    from scripts.agents.operator_next_step import OperatorNextStep

    fake_step = OperatorNextStep(
        current_task="t2i_image_generation",
        scene_id="SC0001",
        recommended_next_agent="human_operator",
        recommended_reason="task_complete",
        open_files=[],
        do_steps=["Proceed to next scene."],
        expected_outputs=[],
        next_command_or_manual_step="yes",
        safety_warnings=[],
    )
    with patch("scripts.agents.copilot_command.recommend_next_step", return_value=fake_step):
        result = apply_command(tmp_path, command="yes", now=FIXED_NOW, auto_handoff=True)

    assert len(result.written_files) == 1
    assert "operator_sessions" in result.written_files[0]


def test_yes_auto_handoff_skipped_when_from_eq_to(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # t2i_image_generation routes to claude_code; if we ARE claude_code, from==to → skip HO
    monkeypatch.setenv("CP_AGENT_NAME", "claude_code")
    _seed_prompt_repo(tmp_path)

    result = apply_command(
        tmp_path,
        command="yes",
        now=FIXED_NOW,
        auto_handoff=True,
    )

    assert len(result.written_files) == 1


# ---------------------------------------------------------------------------
# switch: backward compatibility
# ---------------------------------------------------------------------------


def test_switch_still_writes_handoff_via_helper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_prompt_repo(tmp_path)

    result = apply_command(
        tmp_path,
        command="switch",
        target_agent="codex",
        reason="review_requested",
        now=FIXED_NOW,
        branch="feat/b8-4",
        head_sha="aabbcc001122",
    )

    assert len(result.written_files) == 1
    ho_path = tmp_path / result.written_files[0]
    ho_data = yaml.safe_load(ho_path.read_text(encoding="utf-8"))
    assert ho_data["to_agent"] == "codex"
    assert ho_data["reason"] == "review_requested"
    assert ho_data["status"] == "open"
    assert run_validation(tmp_path).issues == []


# ---------------------------------------------------------------------------
# chatgpt_project guard
# ---------------------------------------------------------------------------


def test_chatgpt_project_rejected_as_target_agent(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    with pytest.raises(ValueError, match="[Uu]nknown"):
        apply_command(
            tmp_path,
            command="switch",
            target_agent="chatgpt_project",  # type: ignore[arg-type]
            now=FIXED_NOW,
        )


# ---------------------------------------------------------------------------
# pickup mode
# ---------------------------------------------------------------------------


def _make_args(repo_root: Path) -> object:
    parser = build_parser()
    return parser.parse_args(["--mode", "pickup", "--repo-root", str(repo_root)])


def _write_open_handoff(repo_root: Path, to_agent: str, timestamp: str) -> Path:
    ho_dir = repo_root / "evidence" / "agent_handoffs"
    ho_dir.mkdir(parents=True, exist_ok=True)
    ho_path = ho_dir / f"HO-{timestamp}.yaml"
    _write_yaml(
        ho_path,
        {
            "handoff_id": f"HO-{timestamp}",
            "created_at": "2026-05-06T10:00:00Z",
            "from_agent": "human_operator",
            "to_agent": to_agent,
            "reason": "review_requested",
            "current_task": "image_review",
            "context_files": ["visual_dev/elements/characters/C01/character_refs/image_selection.yaml"],
            "do_steps": ["Review candidate images."],
            "expected_outputs": ["image_selection.yaml updated"],
            "safety_warnings": ["Do not touch lifecycle fields."],
            "status": "open",
            "branch": "feat/b8-4",
            "head_sha": "aabbcc001122",
        },
    )
    return ho_path


def test_pickup_requires_cp_agent_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    args = _make_args(tmp_path)
    rc = run_pickup(args)  # type: ignore[arg-type]
    assert rc == 2
    captured = capsys.readouterr()
    assert "CP_AGENT_NAME" in captured.err


def test_pickup_rejects_unknown_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("CP_AGENT_NAME", "chatgpt_project")
    args = _make_args(tmp_path)
    rc = run_pickup(args)  # type: ignore[arg-type]
    assert rc == 2
    captured = capsys.readouterr()
    assert "chatgpt_project" in captured.err


def test_pickup_prints_latest_matching_open_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("CP_AGENT_NAME", "codex")
    _write_open_handoff(tmp_path, "codex", "20260506-100000")
    _write_open_handoff(tmp_path, "claude_code", "20260506-100100")
    latest_codex = _write_open_handoff(tmp_path, "codex", "20260506-100200")

    args = _make_args(tmp_path)
    rc = run_pickup(args)  # type: ignore[arg-type]
    assert rc == 0

    captured = capsys.readouterr()
    assert "codex" in captured.out
    assert "image_review" in captured.out
    assert "feat/b8-4" in captured.out
    assert "aabbcc001122" in captured.out
    assert "agent_role_contract.md" in captured.out
    assert latest_codex.name in captured.out


def test_pickup_no_matching_handoff_returns_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("CP_AGENT_NAME", "codex")
    _write_open_handoff(tmp_path, "claude_code", "20260506-100000")

    args = _make_args(tmp_path)
    rc = run_pickup(args)  # type: ignore[arg-type]
    assert rc == 2
    captured = capsys.readouterr()
    assert "codex" in captured.err


def test_pickup_does_not_write_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("CP_AGENT_NAME", "codex")
    _write_open_handoff(tmp_path, "codex", "20260506-100000")

    files_before = set(tmp_path.rglob("*"))
    args = _make_args(tmp_path)
    run_pickup(args)  # type: ignore[arg-type]
    files_after = set(tmp_path.rglob("*"))

    assert files_before == files_after


def test_pickup_rejects_human_operator_as_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("CP_AGENT_NAME", "human_operator")
    args = _make_args(tmp_path)
    rc = run_pickup(args)  # type: ignore[arg-type]
    assert rc == 2
