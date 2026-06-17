"""
Tests for SC0001 dialogue_beats.yaml production record.

Validates that:
1. dialogue_beats.yaml loads and is well-formed YAML
2. It validates against schemas/dialogue_beats.schema.json
3. Semantic validator returns zero hard errors
4. Semantic validator returns readiness blockers for blocked required lines
5. Exactly 8 dialogue lines are present
6. All source dialogue lines from scene excerpt are represented
7. Speakers are only C01/@Nadia and C03/@Birta
8. All target_beat_ids exist in scene_beat_plan.yaml
9. All line_ids are unique
10. No forbidden fields (duration_seconds, clip_count, shots, etc.)
11. kling_native_audio forbids external TTS and ADR
12. C02 does not appear anywhere
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.validators.validate_dialogue_beats import (
    validate_dialogue_beats,
    DialogueBeatsValidationError,
    DialogueBeatsReadinessBlocker,
)


@pytest.fixture
def repo_root():
    """Return repo root path."""
    return Path(__file__).parent.parent


@pytest.fixture
def dialogue_beats_record(repo_root):
    """Load SC0001 dialogue_beats.yaml."""
    path = repo_root / "planning" / "scenes" / "SC0001" / "dialogue_beats.yaml"
    with open(path, "r", encoding="utf-8") as f:
        record = yaml.safe_load(f)
    return record


@pytest.fixture
def scene_beat_plan(repo_root):
    """Load SC0001 scene_beat_plan.yaml to extract beat_ids."""
    path = repo_root / "planning" / "scenes" / "SC0001" / "scene_beat_plan.yaml"
    with open(path, "r", encoding="utf-8") as f:
        plan = yaml.safe_load(f)
    return plan


@pytest.fixture
def element_bindings(repo_root):
    """Load SC0001 element_bindings.yaml documents."""
    path = repo_root / "visual_dev" / "omni_sets" / "SC0001" / "element_bindings.yaml"
    with open(path, "r", encoding="utf-8") as f:
        bindings_docs = list(yaml.safe_load_all(f))
    return [b for b in bindings_docs if b is not None]


def test_dialogue_beats_yaml_loads(dialogue_beats_record):
    """dialogue_beats.yaml loads as valid YAML."""
    assert dialogue_beats_record is not None
    assert isinstance(dialogue_beats_record, dict)


def test_dialogue_beats_schema_version(dialogue_beats_record):
    """schema_version is 0.x-draft."""
    assert dialogue_beats_record.get("schema_version") == "0.x-draft"


def test_dialogue_beats_record_type(dialogue_beats_record):
    """record_type is dialogue_beats."""
    assert dialogue_beats_record.get("record_type") == "dialogue_beats"


def test_dialogue_beats_scene_id(dialogue_beats_record):
    """scene_id is SC0001."""
    assert dialogue_beats_record.get("scene_id") == "SC0001"


def test_dialogue_beats_required_fields(dialogue_beats_record):
    """All required fields are present."""
    required = [
        "schema_version",
        "record_type",
        "scene_id",
        "source_scene_beat_plan_ref",
        "source_element_bindings_ref",
        "dialogue_lines",
        "ambient_sound_prompt",
        "kling_native_audio",
        "provenance",
    ]
    for field in required:
        assert field in dialogue_beats_record, f"Missing required field: {field}"


def test_dialogue_beats_count(dialogue_beats_record):
    """Exactly 8 dialogue lines are present."""
    lines = dialogue_beats_record.get("dialogue_lines", [])
    assert len(lines) == 8, f"Expected 8 dialogue lines, got {len(lines)}"


def test_dialogue_lines_present(dialogue_beats_record):
    """All 8 source dialogue lines from scene excerpt are represented."""
    lines = dialogue_beats_record.get("dialogue_lines", [])
    texts = [line.get("line_text") for line in lines]

    expected_texts = [
        "You didn't sleep again.",
        "I slept.",
        "You slept the way you fold laundry. Very neat. Not restful.",
        "Jin's formula. There's a new tin in the second shelf, behind the vitamin drops.",
        "I found it. He's still down. Your husband —",
        "Mr. Vale called from the car. He said not to wait on breakfast.",
        "He won't be back before eight.",
        "I'll leave something covered.",
    ]

    for expected in expected_texts:
        assert (
            expected in texts
        ), f"Missing dialogue line: {expected!r}"


def test_dialogue_speakers_only_c01_c03(dialogue_beats_record):
    """Speakers are only C01/@Nadia and C03/@Birta."""
    lines = dialogue_beats_record.get("dialogue_lines", [])
    allowed_element_ids = {"C01", "C03"}
    allowed_aliases = {"@Nadia", "@Birta"}

    for line in lines:
        element_id = line.get("speaker_element_id")
        alias = line.get("speaker_kling_alias")
        assert (
            element_id in allowed_element_ids
        ), f"Unexpected speaker element_id: {element_id}"
        assert (
            alias in allowed_aliases
        ), f"Unexpected speaker alias: {alias}"


def test_no_c02_anywhere(dialogue_beats_record):
    """C02 does not appear anywhere in the record."""
    record_str = json.dumps(dialogue_beats_record)
    assert "C02" not in record_str, "C02 should not appear in dialogue_beats record"


def test_all_target_beat_ids_exist(dialogue_beats_record, scene_beat_plan):
    """All target_beat_ids exist in scene_beat_plan.yaml."""
    lines = dialogue_beats_record.get("dialogue_lines", [])
    source_beats = scene_beat_plan.get("source_beats", [])
    beat_ids = {beat.get("beat_id") for beat in source_beats}

    for line in lines:
        target_beat_id = line.get("target_beat_id")
        assert (
            target_beat_id in beat_ids
        ), f"target_beat_id {target_beat_id!r} not found in scene_beat_plan"


def test_all_line_ids_unique(dialogue_beats_record):
    """All line_ids are unique within the record."""
    lines = dialogue_beats_record.get("dialogue_lines", [])
    line_ids = [line.get("line_id") for line in lines]
    assert len(line_ids) == len(
        set(line_ids)
    ), f"Duplicate line_ids found: {line_ids}"


def test_no_duration_seconds_anywhere(dialogue_beats_record):
    """No duration_seconds field anywhere in record."""
    record_str = json.dumps(dialogue_beats_record)
    assert (
        "duration_seconds" not in record_str
    ), "duration_seconds must not appear in dialogue_beats"


def test_no_clip_count(dialogue_beats_record):
    """No clip_count field."""
    record_str = json.dumps(dialogue_beats_record)
    assert "clip_count" not in record_str, "clip_count must not appear"


def test_no_shots_field(dialogue_beats_record):
    """No shots field."""
    record_str = json.dumps(dialogue_beats_record)
    assert "shots" not in record_str, "shots must not appear"


def test_no_total_duration_seconds(dialogue_beats_record):
    """No total_duration_seconds field."""
    record_str = json.dumps(dialogue_beats_record)
    assert (
        "total_duration_seconds" not in record_str
    ), "total_duration_seconds must not appear"


def test_kling_native_audio_disabled(dialogue_beats_record):
    """kling_native_audio is properly configured (enabled after AUDIO-1a promotion)."""
    kna = dialogue_beats_record.get("kling_native_audio", {})
    assert kna.get("enabled") is True, "kling_native_audio.enabled must be true after AUDIO-1a"
    assert (
        kna.get("provider_policy") == "kling_native_only"
    ), "provider_policy must be kling_native_only"
    assert (
        kna.get("external_tts_allowed") is False
    ), "external_tts_allowed must be false"
    assert (
        kna.get("adr_vendor_allowed") is False
    ), "adr_vendor_allowed must be false"


def test_all_dialogue_required_true(dialogue_beats_record):
    """All dialogue_lines have dialogue_required: true."""
    lines = dialogue_beats_record.get("dialogue_lines", [])
    for line in lines:
        assert (
            line.get("dialogue_required") is True
        ), f"Line {line.get('line_id')} has dialogue_required != true"


def test_all_dialogue_blocked_readiness(dialogue_beats_record):
    """All dialogue_lines have native_audio_readiness: ready (after AUDIO-1a promotion)."""
    lines = dialogue_beats_record.get("dialogue_lines", [])
    for line in lines:
        assert (
            line.get("native_audio_readiness") == "ready"
        ), f"Line {line.get('line_id')} has readiness != ready"


def test_semantic_validation_no_hard_errors(
    dialogue_beats_record, repo_root
):
    """Semantic validator returns zero hard errors."""
    bindings_path = repo_root / "visual_dev" / "omni_sets" / "SC0001" / "element_bindings.yaml"
    if not bindings_path.exists():
        pytest.skip("element_bindings.yaml not yet authored (clean baseline; re-created in PR-1)")
    errors, blockers = validate_dialogue_beats(dialogue_beats_record, repo_root)
    assert (
        len(errors) == 0
    ), f"Expected zero hard errors, got {len(errors)}: {errors}"


def test_semantic_validation_readiness_blockers(
    dialogue_beats_record, repo_root
):
    """After AUDIO-1a promotion all lines are ready; semantic validator returns zero blockers."""
    bindings_path = repo_root / "visual_dev" / "omni_sets" / "SC0001" / "element_bindings.yaml"
    if not bindings_path.exists():
        pytest.skip("element_bindings.yaml not yet authored (clean baseline; re-created in PR-1)")
    errors, blockers = validate_dialogue_beats(dialogue_beats_record, repo_root)

    assert len(blockers) == 0, (
        f"Expected zero readiness blockers after AUDIO-1a promotion, got {len(blockers)}: {blockers}"
    )


def test_dialogue_beats_references(dialogue_beats_record):
    """source_scene_beat_plan_ref and source_element_bindings_ref are correct."""
    assert (
        dialogue_beats_record.get("source_scene_beat_plan_ref")
        == "planning/scenes/SC0001/scene_beat_plan.yaml"
    )
    assert (
        dialogue_beats_record.get("source_element_bindings_ref")
        == "visual_dev/omni_sets/SC0001/element_bindings.yaml"
    )


def test_ambient_sound_prompt_present(dialogue_beats_record):
    """ambient_sound_prompt is present and non-empty."""
    prompt = dialogue_beats_record.get("ambient_sound_prompt", "").strip()
    assert len(prompt) > 0, "ambient_sound_prompt must be non-empty"
    # Prompt should not claim TTS capability, though it may disclaim it
    assert "metadata-only" in prompt.lower() or "kling-native" in prompt.lower(), \
        "ambient_sound_prompt should emphasize metadata-only or Kling-native nature"


def test_provenance_present(dialogue_beats_record):
    """provenance block is present with created_by and created_at."""
    prov = dialogue_beats_record.get("provenance", {})
    assert "created_by" in prov, "provenance.created_by required"
    assert "created_at" in prov, "provenance.created_at required"
