from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_scene_status_consistency import (  # noqa: E402
    validate_scene_status_consistency,
)


def _manifest(reqs: list[tuple[str, str]], gate: str = "all_elements_ready") -> dict:
    return {
        "record_type": "shot_element_manifest",
        "shot_id": "SH001",
        "gate_status": gate,
        "required_elements": [
            {"element_id": eid, "element_type": "character", "role": "primary_subject",
             "registration_state_required": state}
            for eid, state in reqs
        ],
        "environmental_only_allowed_ids": [],
    }


def test_ready_with_satisfied_bindings_passes() -> None:
    m = _manifest([("C01", "created"), ("LOC001", "created")])
    bindings = {"C01": "created", "LOC001": "created"}
    assert validate_scene_status_consistency("SC0001", [m], bindings) == []


def test_ready_with_missing_binding_fails() -> None:
    m = _manifest([("C01", "created"), ("C08", "created")])
    bindings = {"C01": "created"}  # C08 missing
    errs = validate_scene_status_consistency("SC0014", [m], bindings)
    assert any(e.error_code == "STATUS_CONTRADICTION" and "C08" in e.message for e in errs)


def test_ready_with_insufficient_binding_fails() -> None:
    m = _manifest([("C01", "voice_locked")])
    bindings = {"C01": "created"}  # needs voice_locked
    errs = validate_scene_status_consistency("SC0001", [m], bindings)
    assert any(e.error_code == "STATUS_CONTRADICTION" for e in errs)


def test_pending_gate_not_checked() -> None:
    m = _manifest([("C08", "created")], gate="pending")
    assert validate_scene_status_consistency("SC0014", [m], {}) == []


def test_environmental_only_skipped() -> None:
    m = _manifest([("STYLE001", "created")])
    m["environmental_only_allowed_ids"] = ["STYLE001"]
    assert validate_scene_status_consistency("SC0001", [m], {}) == []
