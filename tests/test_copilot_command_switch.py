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
        {
            "scene_id": "SC0001",
            "excerpt_ref": "scene_excerpt.md",
            "canon_lock": False,
        },
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


def _file_snapshot(repo_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if rel.startswith("evidence/agent_handoffs/"):
            continue
        snapshot[rel] = path.read_text(encoding="utf-8")
    return snapshot


def test_switch_writes_schema_valid_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_prompt_repo(tmp_path)
    before = _file_snapshot(tmp_path)

    result = apply_command(
        tmp_path,
        command="switch",
        target_agent="codex",
        now=FIXED_NOW,
        branch="feat/x",
        head_sha="abc1234def",
    )

    handoff_path = tmp_path / "evidence/agent_handoffs/HO-20260501-120000.yaml"
    payload = yaml.safe_load(handoff_path.read_text(encoding="utf-8"))
    report = run_validation(tmp_path)

    assert result.written_files == (
        "evidence/agent_handoffs/HO-20260501-120000.yaml",
    )
    assert payload["from_agent"] == "human_operator"
    assert payload["to_agent"] == "codex"
    assert payload["from_agent"] != payload["to_agent"]
    assert payload["branch"] == "feat/x"
    assert payload["head_sha"] == "abc1234def"
    assert report.valid_files == 1
    assert report.issues == []
    assert _file_snapshot(tmp_path) == before


def test_switch_filename_collision_adds_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_prompt_repo(tmp_path)

    first = apply_command(
        tmp_path,
        command="switch",
        target_agent="codex",
        now=FIXED_NOW,
        branch="feat/x",
        head_sha="abc1234def",
    )
    second = apply_command(
        tmp_path,
        command="switch",
        target_agent="codex",
        now=FIXED_NOW,
        branch="feat/x",
        head_sha="abc1234def",
    )

    assert first.written_files == (
        "evidence/agent_handoffs/HO-20260501-120000.yaml",
    )
    assert second.written_files == (
        "evidence/agent_handoffs/HO-20260501-120000-001.yaml",
    )


def test_switch_without_git_omits_branch_and_head_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CP_AGENT_NAME", raising=False)
    _seed_prompt_repo(tmp_path)

    apply_command(
        tmp_path,
        command="switch",
        target_agent="codex",
        now=FIXED_NOW,
    )

    handoff_path = tmp_path / "evidence/agent_handoffs/HO-20260501-120000.yaml"
    payload = yaml.safe_load(handoff_path.read_text(encoding="utf-8"))
    report = run_validation(tmp_path)

    assert "branch" not in payload
    assert "head_sha" not in payload
    assert report.valid_files == 1
    assert report.issues == []


def test_switch_requires_target_agent_before_writing(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    with pytest.raises(ValueError):
        apply_command(
            tmp_path,
            command="switch",
            now=FIXED_NOW,
            branch="feat/x",
            head_sha="abc1234def",
        )

    handoffs_dir = tmp_path / "evidence/agent_handoffs"
    assert not list(handoffs_dir.glob("HO-*.yaml")) if handoffs_dir.exists() else True


def test_unknown_command_fails_before_writing(tmp_path: Path) -> None:
    _seed_prompt_repo(tmp_path)

    with pytest.raises(ValueError, match="Unsupported"):
        apply_command(
            tmp_path,
            command="maybe",  # type: ignore[arg-type]
            target_agent="codex",
            now=FIXED_NOW,
            branch="feat/x",
            head_sha="abc1234def",
        )

    handoffs_dir = tmp_path / "evidence/agent_handoffs"
    assert not list(handoffs_dir.glob("HO-*.yaml")) if handoffs_dir.exists() else True
