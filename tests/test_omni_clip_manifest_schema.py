"""
Tests for omni_clip_manifest.schema.json.

Validates schema structure, duration enums, and required field enforcement.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


@pytest.fixture
def schema():
    """Load omni_clip_manifest schema."""
    schema_path = Path(__file__).parent.parent / "schemas" / "omni_clip_manifest.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def validator(schema):
    """Create JSON Schema validator."""
    return jsonschema.Draft202012Validator(schema)


def _minimal_omni_clip_manifest(**overrides):
    """Create minimal valid omni_clip_manifest record."""
    record = {
        "schema_version": "0.x-draft",
        "record_type": "omni_clip_manifest",
        "scene_id": "SC0001",
        "clip_id": "CLIP_SC0001_01",
        "source_scene_beat_plan_ref": "planning/scenes/SC0001/scene_beat_plan.yaml",
        "source_dialogue_beats_ref": "planning/scenes/SC0001/dialogue_beats.yaml",
        "total_duration_seconds": 5,
        "continuity_input_mode": "metadata_only",
        "shots": [
            {
                "shot_id": "SHOT_SC0001_01_A",
                "duration_seconds": 5,
                "source_beat_ids": ["ESTABLISH_KITCHEN"],
                "prompt_action": "Establish kitchen space",
                "duration_reason": "Single beat, 5 seconds for establisher",
            }
        ],
        "kling_native_audio": {
            "enabled": False,
            "provider_policy": "kling_native_only",
            "external_tts_allowed": False,
            "adr_vendor_allowed": False,
        },
        "provenance": {
            "created_by": "test_agent",
            "created_at": "2026-05-08T22:00:00Z",
        },
    }
    record.update(overrides)
    return record


def test_minimal_omni_clip_manifest_valid(validator):
    """Minimal omni_clip_manifest record validates."""
    record = _minimal_omni_clip_manifest()
    validator.validate(record)  # should not raise


def test_omni_clip_manifest_duration_seconds_enum(validator):
    """duration_seconds must be integer enum 2..15 (2s multi-shot cutaways allowed)."""
    for valid in [2, 3, 5, 10, 15]:
        record = _minimal_omni_clip_manifest()
        record["shots"][0]["duration_seconds"] = valid
        record["total_duration_seconds"] = valid  # keep sum==total schema-consistent
        validator.validate(record)  # should not raise

    for invalid in [1, 2.5, 3.5, 16, 20]:
        record = _minimal_omni_clip_manifest()
        record["shots"][0]["duration_seconds"] = invalid
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(record)


def test_omni_clip_manifest_total_duration_seconds_enum(validator):
    """total_duration_seconds must be integer enum 2..15."""
    for valid in [2, 3, 5, 10, 15]:
        record = _minimal_omni_clip_manifest(total_duration_seconds=valid)
        record["shots"][0]["duration_seconds"] = valid  # match shot duration
        validator.validate(record)  # should not raise

    for invalid in [1, 16, 20]:
        record = _minimal_omni_clip_manifest(total_duration_seconds=invalid)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(record)


def test_omni_clip_manifest_continuity_input_mode_enum(validator):
    """continuity_input_mode must be in allowed values."""
    for valid in ["metadata_only", "frame_input_eligible", "frame_input_active"]:
        record = _minimal_omni_clip_manifest(continuity_input_mode=valid)
        validator.validate(record)  # should not raise

    record = _minimal_omni_clip_manifest(continuity_input_mode="invalid_mode")
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_shots_min_items(validator):
    """shots array must have at least 1 item."""
    record = _minimal_omni_clip_manifest(shots=[])
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_shot_source_beat_ids_min_items(validator):
    """shot source_beat_ids must have at least 1 item."""
    record = _minimal_omni_clip_manifest()
    record["shots"][0]["source_beat_ids"] = []
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_multi_shot_valid(validator):
    """omni_clip_manifest can have multiple shots."""
    record = _minimal_omni_clip_manifest(total_duration_seconds=10)
    record["shots"] = [
        {
            "shot_id": "SHOT_SC0001_01_A",
            "duration_seconds": 5,
            "source_beat_ids": ["ESTABLISH_KITCHEN"],
            "prompt_action": "Establish kitchen",
            "duration_reason": "First half",
        },
        {
            "shot_id": "SHOT_SC0001_01_B",
            "duration_seconds": 5,
            "source_beat_ids": ["NADIA_PASSAGE_MOVEMENT"],
            "prompt_action": "Nadia moves",
            "duration_reason": "Second half",
        },
    ]
    validator.validate(record)  # should not raise


def test_omni_clip_manifest_kling_native_audio_external_tts_false(validator):
    """external_tts_allowed must be false."""
    record = _minimal_omni_clip_manifest()
    record["kling_native_audio"]["external_tts_allowed"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_kling_native_audio_adr_vendor_false(validator):
    """adr_vendor_allowed must be false."""
    record = _minimal_omni_clip_manifest()
    record["kling_native_audio"]["adr_vendor_allowed"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_kling_native_audio_provider_policy_const(validator):
    """provider_policy must be kling_native_only."""
    record = _minimal_omni_clip_manifest()
    record["kling_native_audio"]["provider_policy"] = "other_policy"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_with_dialogue_line_ids(validator):
    """Shot can include optional dialogue_line_ids."""
    record = _minimal_omni_clip_manifest()
    record["shots"][0]["dialogue_line_ids"] = ["DLG_NADIA_SLEEP_01", "DLG_BIRTA_SLEEP_01"]
    validator.validate(record)  # should not raise


def test_omni_clip_manifest_with_frame_references(validator):
    """Manifest can include optional first/last frame references."""
    record = _minimal_omni_clip_manifest()
    record["first_frame_reference"] = {
        "frame_description": "Nadia in kitchen",
        "visual_continuity_note": "Maintain position",
    }
    record["last_frame_reference"] = {
        "frame_description": "Nadia moving to corridor",
        "visual_continuity_note": "Continuous motion",
    }
    validator.validate(record)  # should not raise


def test_omni_clip_manifest_shot_id_pattern(validator):
    """shot_id must match SHOT_\\w+."""
    record = _minimal_omni_clip_manifest()
    record["shots"][0]["shot_id"] = "INVALID_SHOT_ID"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_clip_id_pattern(validator):
    """clip_id must match CLIP_\\w+."""
    record = _minimal_omni_clip_manifest(clip_id="INVALID_CLIP_ID")
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_scene_id_pattern(validator):
    """scene_id must match SC\\d{4}."""
    record = _minimal_omni_clip_manifest(scene_id="INVALID")
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_required_fields(validator):
    """All required fields must be present."""
    record = _minimal_omni_clip_manifest()
    del record["shots"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_provenance_required(validator):
    """provenance must have created_by and created_at."""
    record = _minimal_omni_clip_manifest()
    del record["provenance"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)


def test_omni_clip_manifest_with_optional_fields(validator):
    """Manifest accepts optional ambient_sound_prompt, notes, etc."""
    record = _minimal_omni_clip_manifest(
        ambient_sound_prompt="Quiet kitchen, footsteps on stone",
        notes="Test notes field",
        prompt_record_ref="prompts/SC0001/CLIP_SC0001_01_prompt.yaml",
    )
    validator.validate(record)  # should not raise


def test_omni_clip_manifest_additional_properties_not_allowed(validator):
    """Additional properties are not allowed."""
    record = _minimal_omni_clip_manifest()
    record["unknown_field"] = "value"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(record)
