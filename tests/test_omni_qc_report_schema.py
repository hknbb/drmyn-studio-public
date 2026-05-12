from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


@pytest.fixture
def schema():
    schema_path = Path(__file__).parent.parent / "schemas" / "omni_qc_report.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def validator(schema):
    return jsonschema.Draft202012Validator(schema)


def _minimal_record(**overrides):
    record = {
        "schema_version": "0.x-draft",
        "record_type": "omni_qc_report",
        "scene_id": "SC0001",
        "clip_id": "CLIP_SC0001_01",
        "prompt_id": "SC0001__omni-kling-clip-sc0001-01-safe__v01",
        "variant_mode": "safe",
        "render_pass": "visual_test",
        "checks": {
            "identity_consistency": "pass",
            "location_continuity": "pass",
            "camera_stability": "warn",
            "motion_artifacts": "warn",
            "hand_face_artifacts": "pass",
            "audio_sync": "not_applicable",
            "unwanted_speech": "not_applicable",
            "narrative_beat": "pass",
        },
        "failure_risks": ["camera_jump"],
        "retry_rule": {
            "action": "reduce_camera_motion",
            "note": "One variable only.",
        },
        "selected_for_next_pass": False,
        "provenance": {
            "reviewed_by": "hknbb",
            "reviewed_at": "2026-05-11T18:00:00Z",
        },
    }
    record.update(overrides)
    return record


def test_minimal_record_validates(validator):
    validator.validate(_minimal_record())


def test_variant_mode_enum_enforced(validator):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(_minimal_record(variant_mode="wild"))


def test_render_pass_enum_enforced(validator):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(_minimal_record(render_pass="draft_pass"))


def test_retry_rule_action_enum_enforced(validator):
    bad = _minimal_record()
    bad["retry_rule"]["action"] = "change_everything"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)


def test_rejects_unknown_top_level_field(validator):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(_minimal_record(extra_field=True))


def test_audio_fields_allow_not_applicable(validator):
    rec = _minimal_record()
    rec["checks"]["audio_sync"] = "not_applicable"
    rec["checks"]["unwanted_speech"] = "not_applicable"
    validator.validate(rec)


def test_required_fields_enforced(validator):
    rec = _minimal_record()
    del rec["checks"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(rec)
