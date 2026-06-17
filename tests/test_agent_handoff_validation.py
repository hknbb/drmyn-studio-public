from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_production_records import run_validation  # noqa: E402


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


def _valid_handoff() -> dict:
    return {
        "handoff_id": "HO-20260501-120000",
        "created_at": "2026-05-01T12:00:00Z",
        "from_agent": "human_operator",
        "to_agent": "codex",
        "reason": "limit_reached",
        "current_task": "t2i_image_generation",
        "context_files": ["scripts/agents/copilot_command.py"],
        "do_steps": ["Continue from the current recommendation."],
        "expected_outputs": ["A metadata-only implementation patch."],
        "safety_warnings": ["Do not commit binaries."],
        "status": "open",
        "scene_id": "SC0001",
        "session_id": "OP-SC0001-20260501",
        "branch": "feat/test",
        "head_sha": "abc1234def",
        "notes": "Metadata-only handoff.",
    }


def _write_handoff(repo_root: Path, payload: dict) -> None:
    _write_yaml(repo_root / "evidence/agent_handoffs/HO-test.yaml", payload)


def test_valid_minimum_handoff_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload.pop("scene_id")
    payload.pop("session_id")
    payload.pop("branch")
    payload.pop("head_sha")
    payload.pop("notes")
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.total_files == 1
    assert report.valid_files == 1
    assert report.by_record_type["agent_handoff"] == 1
    assert report.issues == []


def test_missing_to_agent_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload.pop("to_agent")
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any("to_agent" in issue.message for issue in report.issues)


def test_from_agent_and_to_agent_must_differ(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["to_agent"] = payload["from_agent"]
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any(issue.field_path == "to_agent" for issue in report.issues)


def test_unknown_agent_enum_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["from_agent"] = "unknown_agent"
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any("unknown_agent" in issue.message for issue in report.issues)


def test_chatgpt_project_agent_is_no_longer_accepted(tmp_path: Path) -> None:
    # `chatgpt_project` was removed from the agent enum; the workflow now uses
    # only Claude Code, Codex, Gemini Code Assist, and the human operator.
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["from_agent"] = "chatgpt_project"
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any("chatgpt_project" in issue.message for issue in report.issues)


def test_head_sha_too_short_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["head_sha"] = "abc123"
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any(issue.field_path == "head_sha" for issue in report.issues)


def test_invalid_branch_prefix_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["branch"] = "claude/foo"
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any(issue.field_path == "branch" for issue in report.issues)


def test_docs_branch_prefix_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["branch"] = "docs/copilot-doctrine"
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.valid_files == 1
    assert report.issues == []


def test_lifecycle_key_smuggle_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["pack_status"] = "locked"
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any(issue.field_path == "pack_status" for issue in report.issues)


def test_lifecycle_text_in_notes_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["notes"] = "Human note mentions pack_status: locked as text only."
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.valid_files == 1
    assert report.issues == []


def test_context_files_reject_unsafe_paths(tmp_path: Path) -> None:
    unsafe_paths = [
        "/abs/path",
        "C:\\Users\\foo",
        "../outside",
        "foo/../bar",
    ]
    for context_path in unsafe_paths:
        safe_name = (
            context_path.replace("\\", "_").replace("/", "_").replace(":", "_")
        )
        repo_root = tmp_path / safe_name
        _copy_schemas(repo_root)
        payload = _valid_handoff()
        payload["context_files"] = [context_path]
        _write_handoff(repo_root, payload)

        report = run_validation(repo_root)

        assert report.invalid_files == 1
        assert any(
            issue.field_path == "context_files.0" for issue in report.issues
        )


def test_context_files_accept_repo_relative_path(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_handoff()
    payload["context_files"] = ["scripts/agents/copilot_command.py"]
    _write_handoff(tmp_path, payload)

    report = run_validation(tmp_path)

    assert report.valid_files == 1
    assert report.issues == []


def test_empty_agent_handoffs_directory_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    (tmp_path / "evidence/agent_handoffs").mkdir(parents=True)

    report = run_validation(tmp_path)

    assert report.total_files == 0
    assert not report.has_errors
