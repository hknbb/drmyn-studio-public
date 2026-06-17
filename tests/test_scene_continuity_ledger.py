from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_scene_continuity_ledger import (  # noqa: E402
    validate_scene_continuity_ledger,
)
from scripts.validate_production_records import run_validation  # noqa: E402


def _state(direction: str, *, summary: str = "s", positions: dict | None = None) -> dict:
    state = {
        "summary": summary,
        "camera_state": {"shot_size": "medium", "subject_screen_position": "center"},
        "screen_direction": direction,
    }
    if positions:
        state["key_positions"] = [
            {"subject": k, "screen_position": v} for k, v in positions.items()
        ]
    return state


def _ledger(chain: list[dict]) -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "scene_continuity_ledger",
        "scene_continuity_ledger_id": "SCL_SC0001_V001",
        "scene_id": "SC0001",
        "source_omni_clip_plan_ref": "planning/scenes/SC0001/omni_clip_plan.yaml",
        "clip_chain": chain,
        "provenance": {"created_by": "t", "created_at": "2026-06-03T00:00:00Z"},
    }


def _write_plan(repo_root: Path, clip_ids: list[str]) -> None:
    plan = {
        "schema_version": "0.x-draft",
        "record_type": "omni_clip_plan",
        "scene_id": "SC0001",
        "clip_summaries": [{"clip_id": c, "clip_manifest_ref": "x"} for c in clip_ids],
    }
    path = repo_root / "planning" / "scenes" / "SC0001" / "omni_clip_plan.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")


def test_valid_chain_passes(tmp_path: Path) -> None:
    _write_plan(tmp_path, ["CLIP_SC0001_01", "CLIP_SC0001_02"])
    ledger = _ledger([
        {"clip_id": "CLIP_SC0001_01", "order": 1,
         "entry_state": _state("left_to_right", positions={"@Nadia": "left"}),
         "exit_state": _state("left_to_right", positions={"@Nadia": "center"})},
        {"clip_id": "CLIP_SC0001_02", "order": 2,
         "entry_state": _state("left_to_right", positions={"@Nadia": "center"}),
         "exit_state": _state("left_to_right", positions={"@Nadia": "right"})},
    ])
    assert validate_scene_continuity_ledger(ledger, tmp_path) == []


def test_screen_direction_flip_fails(tmp_path: Path) -> None:
    _write_plan(tmp_path, ["CLIP_SC0001_01", "CLIP_SC0001_02"])
    ledger = _ledger([
        {"clip_id": "CLIP_SC0001_01", "order": 1,
         "entry_state": _state("left_to_right"), "exit_state": _state("left_to_right")},
        {"clip_id": "CLIP_SC0001_02", "order": 2,
         "entry_state": _state("right_to_left"), "exit_state": _state("right_to_left")},
    ])
    codes = [e.error_code for e in validate_scene_continuity_ledger(ledger, tmp_path)]
    assert "SCREEN_DIRECTION_FLIP" in codes


def test_subject_position_discontinuity_fails(tmp_path: Path) -> None:
    _write_plan(tmp_path, ["CLIP_SC0001_01", "CLIP_SC0001_02"])
    ledger = _ledger([
        {"clip_id": "CLIP_SC0001_01", "order": 1,
         "entry_state": _state("neutral"),
         "exit_state": _state("neutral", positions={"@Nadia": "left"})},
        {"clip_id": "CLIP_SC0001_02", "order": 2,
         "entry_state": _state("neutral", positions={"@Nadia": "right"}),
         "exit_state": _state("neutral")},
    ])
    codes = [e.error_code for e in validate_scene_continuity_ledger(ledger, tmp_path)]
    assert "SUBJECT_POSITION_DISCONTINUITY" in codes


def test_chain_plan_mismatch_fails(tmp_path: Path) -> None:
    _write_plan(tmp_path, ["CLIP_SC0001_01", "CLIP_SC0001_02"])
    ledger = _ledger([
        {"clip_id": "CLIP_SC0001_01", "order": 1,
         "entry_state": _state("neutral"), "exit_state": _state("neutral")},
    ])
    codes = [e.error_code for e in validate_scene_continuity_ledger(ledger, tmp_path)]
    assert "CLIP_CHAIN_PLAN_MISMATCH" in codes


def test_noncontiguous_order_fails(tmp_path: Path) -> None:
    _write_plan(tmp_path, ["CLIP_SC0001_01", "CLIP_SC0001_02"])
    ledger = _ledger([
        {"clip_id": "CLIP_SC0001_01", "order": 1,
         "entry_state": _state("neutral"), "exit_state": _state("neutral")},
        {"clip_id": "CLIP_SC0001_02", "order": 3,
         "entry_state": _state("neutral"), "exit_state": _state("neutral")},
    ])
    codes = [e.error_code for e in validate_scene_continuity_ledger(ledger, tmp_path)]
    assert "ORDER_NOT_CONTIGUOUS" in codes


def test_frame_input_active_without_refs_fails(tmp_path: Path) -> None:
    _write_plan(tmp_path, ["CLIP_SC0001_01"])
    ledger = _ledger([
        {"clip_id": "CLIP_SC0001_01", "order": 1,
         "entry_state": _state("neutral"), "exit_state": _state("neutral"),
         "frame_continuity": {"continuity_input_mode": "frame_input_active"}},
    ])
    codes = [e.error_code for e in validate_scene_continuity_ledger(ledger, tmp_path)]
    assert "FRAME_INPUT_ACTIVE_NO_REFS" in codes


def test_production_validator_counts_and_validates(tmp_path: Path) -> None:
    for schema in (REPO_ROOT / "schemas").glob("*.schema.json"):
        (tmp_path / "schemas").mkdir(parents=True, exist_ok=True)
        (tmp_path / "schemas" / schema.name).write_text(
            schema.read_text(encoding="utf-8"), encoding="utf-8"
        )
    _write_plan(tmp_path, ["CLIP_SC0001_01", "CLIP_SC0001_02"])
    ledger = _ledger([
        {"clip_id": "CLIP_SC0001_01", "order": 1,
         "entry_state": _state("left_to_right"), "exit_state": _state("left_to_right")},
        {"clip_id": "CLIP_SC0001_02", "order": 2,
         "entry_state": _state("left_to_right"), "exit_state": _state("left_to_right")},
    ])
    led_path = tmp_path / "planning" / "scenes" / "SC0001" / "scene_continuity_ledger.yaml"
    led_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

    report = run_validation(tmp_path)
    assert report.by_record_type["scene_continuity_ledger"] == 1
    ledger_issues = [i for i in report.issues if i.record_type == "scene_continuity_ledger"]
    assert ledger_issues == []
