"""
Tests for omni_clip_plan.schema.json.

Validates schema structure and required field enforcement.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml


@pytest.fixture
def schema():
    """Load omni_clip_plan schema."""
    schema_path = Path(__file__).parent.parent / "schemas" / "omni_clip_plan.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def validator(schema):
    """Create JSON Schema validator."""
    return jsonschema.Draft202012Validator(schema)


def _minimal_omni_clip_plan(**overrides):
    """Create minimal valid omni_clip_plan record."""
    record = {
        "schema_version": "0.x-draft",
        "record_type": "omni_clip_plan",
        "scene_id": "SC0001",
        "source_scene_beat_plan_ref": "planning/scenes/SC0001/scene_beat_plan.yaml",
        "source_dialogue_beats_ref": "planning/scenes/SC0001/dialogue_beats.yaml",
        "clip_summaries": [
            {
                "clip_id": "CLIP_SC0001_01",
                "clip_manifest_ref": "planning/scenes/SC0001/manifests/CLIP_SC0001_01_manifest.yaml",
                "total_duration_seconds": 15,
                "source_beat_count": 5,
            }
        ],
        "packing_strategy": {
            "packer_version": "rhythm_aware_v1",
            "packing_mode": "rhythm_aware_constrained",
        },
        "provenance": {
            "created_by": "test_agent",
            "created_at": "2026-05-08T22:00:00Z",
        },
    }
    record.update(overrides)
    return record


def test_minimal_omni_clip_plan_valid(validator):
    """Minimal omni_clip_plan record validates."""
    record = _minimal_omni_clip_plan()
    validator.validate(record)  # should not raise


def test_omni_clip_plan_schema_version(validator):
    """schema_version must be 0.x-draft."""
    record = _minimal_omni_clip_plan(schema_version="1.0")
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_record_type(validator):
    """record_type must be omni_clip_plan."""
    record = _minimal_omni_clip_plan(record_type="other_type")
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_scene_id_pattern(validator):
    """scene_id must match SC\\d{4}."""
    record = _minimal_omni_clip_plan(scene_id="INVALID")
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_required_fields(validator):
    """All required fields must be present."""
    record = _minimal_omni_clip_plan()
    del record["clip_summaries"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_clip_summaries_min_items(validator):
    """clip_summaries must have at least 1 item."""
    record = _minimal_omni_clip_plan(clip_summaries=[])
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_clip_summary_clip_id_pattern(validator):
    """clip_summary clip_id must match CLIP_\\w+."""
    record = _minimal_omni_clip_plan()
    record["clip_summaries"][0]["clip_id"] = "INVALID_ID"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_clip_summary_total_duration_range(validator):
    """clip_summary total_duration_seconds must be 2..15."""
    record = _minimal_omni_clip_plan()
    record["clip_summaries"][0]["total_duration_seconds"] = 1
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)

    record = _minimal_omni_clip_plan()
    record["clip_summaries"][0]["total_duration_seconds"] = 16
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_packing_mode_enum(validator):
    """packing_strategy.packing_mode must be in allowed values."""
    record = _minimal_omni_clip_plan()
    record["packing_strategy"]["packing_mode"] = "invalid_mode"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_multiple_clips(validator):
    """omni_clip_plan can have multiple clip summaries."""
    record = _minimal_omni_clip_plan()
    record["clip_summaries"].append(
        {
            "clip_id": "CLIP_SC0001_02",
            "clip_manifest_ref": "planning/scenes/SC0001/manifests/CLIP_SC0001_02_manifest.yaml",
            "total_duration_seconds": 10,
            "source_beat_count": 3,
        }
    )
    validator.validate(record)  # should not raise


def test_omni_clip_plan_provenance_required_fields(validator):
    """provenance must have created_by and created_at."""
    record = _minimal_omni_clip_plan(provenance={"created_by": "test"})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_provenance_created_at_present(validator):
    """provenance.created_at must be present."""
    record = _minimal_omni_clip_plan(
        provenance={
            "created_by": "test",
        }
    )
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_additional_properties_not_allowed(validator):
    """Additional properties are not allowed."""
    record = _minimal_omni_clip_plan()
    record["unknown_field"] = "value"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_plan_with_notes(validator):
    """omni_clip_plan accepts optional notes field."""
    record = _minimal_omni_clip_plan(notes="Testing notes field")
    validator.validate(record)  # should not raise
