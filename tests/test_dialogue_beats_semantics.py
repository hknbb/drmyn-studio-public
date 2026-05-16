"""
A4.1 tests: dialogue_beats semantic validation (cross-reference rules).

Covers:
- target_beat_id must exist in scene_beat_plan.yaml
- speaker_element_id must exist in element_bindings.yaml
- speaker_kling_alias must match binding's kling_alias
- line_id uniqueness within dialogue_beats record
- native_audio_readiness: ready requires voice_capability != none
- dialogue_required: true with native_audio_readiness: blocked is allowed (readiness blocker)
- Missing referenced source files
- External TTS / ADR fields rejected (defensive)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_dialogue_beats import (
    DialogueBeatsReadinessBlocker,
    DialogueBeatsValidationError,
    validate_dialogue_beats,
    validate_dialogue_beats_batch,
)


def _minimal_dialogue_beats(overrides: dict | None = None) -> dict:
    """Create a minimal valid dialogue_beats record for SC0001."""
    base = {
        "schema_version": "0.x-draft",
        "record_type": "dialogue_beats",
        "scene_id": "SC0001",
        "source_scene_beat_plan_ref": "planning/scenes/SC0001/scene_beat_plan.yaml",
        "source_element_bindings_ref": "tests/fixtures/element_bindings_minimal.yaml",
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "I slept.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            }
        ],
        "ambient_sound_prompt": "Quiet kitchen with subtle white-noise machine hum.",
        "kling_native_audio": {
            "enabled": False,
            "provider_policy": "kling_native_only",
            "external_tts_allowed": False,
            "adr_vendor_allowed": False,
        },
        "provenance": {
            "created_by": "hknbb",
            "created_at": "2026-05-08T00:00:00Z",
        },
    }
    if overrides:
        base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid record tests
# ---------------------------------------------------------------------------


def test_valid_minimal_dialogue_beats() -> None:
    """Minimal valid dialogue_beats record with all required fields."""
    record = _minimal_dialogue_beats()
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert errors == []
    assert blockers == []


def test_valid_multiple_dialogue_lines() -> None:
    """Multiple dialogue lines, all cross-references valid."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "I slept.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            },
            {
                "line_id": "DLG_BIRTA_SLEEP_02",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C03",
                "speaker_kling_alias": "@Birta",
                "line_text": "You slept the way you fold laundry.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            },
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert errors == []
    assert blockers == []


def test_valid_all_line_types() -> None:
    """All line_type values are accepted."""
    for line_type in ["spoken", "interrupted", "offscreen", "implied"]:
        record = _minimal_dialogue_beats({
            "dialogue_lines": [
                {
                    "line_id": "DLG_TEST_LINE",
                    "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                    "speaker_element_id": "C01",
                    "speaker_kling_alias": "@Nadia",
                    "line_text": "Test dialogue.",
                    "line_type": line_type,
                    "native_audio_readiness": "blocked",
                    "dialogue_required": False,
                }
            ]
        })
        errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
        assert errors == [], f"Failed for line_type={line_type}: {errors}"


def test_valid_all_readiness_states() -> None:
    """All native_audio_readiness values are accepted."""
    for readiness in ["blocked", "metadata_only", "ready"]:
        record = _minimal_dialogue_beats({
            "dialogue_lines": [
                {
                    "line_id": "DLG_TEST_LINE",
                    "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                    "speaker_element_id": "C01",
                    "speaker_kling_alias": "@Nadia",
                    "line_text": "Test dialogue.",
                    "line_type": "spoken",
                    "native_audio_readiness": readiness,
                    "dialogue_required": False,
                }
            ]
        })
        errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
        # "ready" will trigger an error because C01 has voice_capability: none
        # This is expected and tested separately
        if readiness != "ready":
            assert errors == [], f"Failed for readiness={readiness}: {errors}"


def test_valid_blocked_required_dialogue_produces_blocker_not_error() -> None:
    """
    dialogue_required: true with native_audio_readiness: blocked is ALLOWED.
    Should produce a readiness blocker (warning), not a validation failure.
    """
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_ESSENTIAL",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "This line is essential to the scene.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": True,  # REQUIRED, but BLOCKED
            }
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    # Should not fail validation
    assert errors == []
    # Should produce exactly one blocker
    assert len(blockers) == 1
    assert blockers[0].line_id == "DLG_NADIA_ESSENTIAL"
    assert "voice provisioning" in str(blockers[0]).lower()


def test_valid_optional_fields() -> None:
    """Optional fields (delivery_note, subtext_note, etc.) do not cause errors."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "I slept.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
                "delivery_note": "flat, no inflection",
                "subtext_note": "Nadia is lying.",
                "source_quote_ref": "source/screenplay/closing_price.fountain:line_42",
                "pronunciation_note": "Na-dee-uh",
            }
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert errors == []
    assert blockers == []


def test_valid_scene_level_notes() -> None:
    """Scene-level notes field does not cause errors."""
    record = _minimal_dialogue_beats({
        "notes": "C01 is currently voice-blocked; B3 will provision voice for C01."
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert errors == []


# ---------------------------------------------------------------------------
# Invalid record tests - hard failures
# ---------------------------------------------------------------------------


def test_missing_scene_beat_plan_file() -> None:
    """Error: source_scene_beat_plan_ref points to non-existent file."""
    record = _minimal_dialogue_beats({
        "source_scene_beat_plan_ref": "planning/scenes/SC0001/NONEXISTENT.yaml"
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert len(errors) == 1
    assert errors[0].error_code == "MISSING_SCENE_BEAT_PLAN"


def test_missing_element_bindings_file() -> None:
    """Error: source_element_bindings_ref points to non-existent file."""
    record = _minimal_dialogue_beats({
        "source_element_bindings_ref": "visual_dev/omni_sets/SC0001/NONEXISTENT.yaml"
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert len(errors) == 1
    assert errors[0].error_code == "MISSING_ELEMENT_BINDINGS"


def test_missing_target_beat_id() -> None:
    """Error: target_beat_id not found in scene_beat_plan.yaml."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",
                "target_beat_id": "NONEXISTENT_BEAT",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "I slept.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            }
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert any(e.error_code == "MISSING_BEAT_ID" for e in errors)


def test_missing_speaker_element_id() -> None:
    """Error: speaker_element_id not found in element_bindings.yaml."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_UNKNOWN_SPEAKER",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C99",  # Does not exist
                "speaker_kling_alias": "@UnknownSpeaker",
                "line_text": "Who am I?",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            }
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert any(e.error_code == "MISSING_ELEMENT_ID" for e in errors)


def test_alias_mismatch() -> None:
    """Error: speaker_kling_alias does not match binding."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@WrongAlias",  # C01's kling_alias is @Nadia
                "line_text": "I slept.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            }
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert any(e.error_code == "ALIAS_MISMATCH" for e in errors)


def test_duplicate_line_id() -> None:
    """Error: line_id appears multiple times within the same record."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_DUPLICATE",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "First appearance.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            },
            {
                "line_id": "DLG_DUPLICATE",  # DUPLICATE
                "target_beat_id": "DIALOGUE_FORMULA_VITAMIN",
                "speaker_element_id": "C03",
                "speaker_kling_alias": "@Birta",
                "line_text": "Second appearance.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            },
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert any(e.error_code == "DUPLICATE_LINE_ID" for e in errors)


def test_unwarranted_readiness_ready() -> None:
    """Error: native_audio_readiness: ready but element has voice_capability: none."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",  # C01 has voice_capability: none (per B3)
                "speaker_kling_alias": "@Nadia",
                "line_text": "I slept.",
                "line_type": "spoken",
                "native_audio_readiness": "ready",  # UNWARRANTED: C01 is not voice-capable
                "dialogue_required": False,
            }
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert any(e.error_code == "UNWARRANTED_READINESS" for e in errors)


def test_external_tts_allowed_true() -> None:
    """Error: kling_native_audio.external_tts_allowed is true (must be const false)."""
    record = _minimal_dialogue_beats({
        "kling_native_audio": {
            "enabled": False,
            "provider_policy": "kling_native_only",
            "external_tts_allowed": True,  # VIOLATION
            "adr_vendor_allowed": False,
        }
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert any(e.error_code == "EXTERNAL_TTS_ALLOWED" for e in errors)


def test_adr_vendor_allowed_true() -> None:
    """Error: kling_native_audio.adr_vendor_allowed is true (must be const false)."""
    record = _minimal_dialogue_beats({
        "kling_native_audio": {
            "enabled": False,
            "provider_policy": "kling_native_only",
            "external_tts_allowed": False,
            "adr_vendor_allowed": True,  # VIOLATION
        }
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert any(e.error_code == "ADR_VENDOR_ALLOWED" for e in errors)


# ---------------------------------------------------------------------------
# Readiness blocker tests (allowed, but reported)
# ---------------------------------------------------------------------------


def test_multiple_blocked_required_lines_multiple_blockers() -> None:
    """Multiple dialogue lines with blocked required produce multiple blockers."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_ESSENTIAL_01",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "Essential line 1.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": True,
            },
            {
                "line_id": "DLG_BIRTA_ESSENTIAL_02",
                "target_beat_id": "DIALOGUE_FORMULA_VITAMIN",
                "speaker_element_id": "C03",
                "speaker_kling_alias": "@Birta",
                "line_text": "Essential line 2.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": True,
            },
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert errors == []
    assert len(blockers) == 2
    assert blockers[0].line_id == "DLG_NADIA_ESSENTIAL_01"
    assert blockers[1].line_id == "DLG_BIRTA_ESSENTIAL_02"


def test_blocked_optional_dialogue_no_blocker() -> None:
    """dialogue_required: false with blocked readiness does NOT produce a blocker."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_OPTIONAL",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "Optional line.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,  # Not required, so no blocker
            }
        ]
    })
    errors, blockers = validate_dialogue_beats(record, REPO_ROOT)
    assert errors == []
    assert blockers == []  # No blockers


# ---------------------------------------------------------------------------
# Batch validation tests
# ---------------------------------------------------------------------------


def test_batch_validation_multiple_scenes() -> None:
    """Batch validator processes multiple records independently."""
    record1 = _minimal_dialogue_beats({"scene_id": "SC0001"})
    record2 = _minimal_dialogue_beats({"scene_id": "SC0002", "source_scene_beat_plan_ref": "planning/scenes/SC0002/scene_beat_plan.yaml"})

    errors_by_scene, blockers_by_scene = validate_dialogue_beats_batch(
        [record1, record2], REPO_ROOT
    )

    # SC0002 should fail (file doesn't exist), SC0001 should pass
    assert "SC0002" in errors_by_scene
    assert "SC0001" not in errors_by_scene


def test_batch_validation_with_blockers() -> None:
    """Batch validator collects blockers by scene."""
    record = _minimal_dialogue_beats({
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_ESSENTIAL",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "Essential.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": True,
            }
        ]
    })

    errors_by_scene, blockers_by_scene = validate_dialogue_beats_batch(
        [record], REPO_ROOT
    )

    assert "SC0001" in blockers_by_scene
    assert len(blockers_by_scene["SC0001"]) == 1


# ---------------------------------------------------------------------------
# Cross-scene independence tests
# ---------------------------------------------------------------------------


def test_same_line_id_in_different_scenes_allowed() -> None:
    """Same line_id in different scene records is allowed."""
    record1 = _minimal_dialogue_beats({
        "scene_id": "SC0001",
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",
                "target_beat_id": "DIALOGUE_SLEEP_ACCUSATION",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "I slept.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            }
        ]
    })

    record2 = _minimal_dialogue_beats({
        "scene_id": "SC0002",
        "source_scene_beat_plan_ref": "planning/scenes/SC0002/scene_beat_plan.yaml",
        "dialogue_lines": [
            {
                "line_id": "DLG_NADIA_SLEEP_01",  # Same ID as SC0001
                "target_beat_id": "SOME_BEAT",
                "speaker_element_id": "C01",
                "speaker_kling_alias": "@Nadia",
                "line_text": "I slept again.",
                "line_type": "spoken",
                "native_audio_readiness": "blocked",
                "dialogue_required": False,
            }
        ]
    })

    # SC0001 should pass, SC0002 should fail (missing file)
    errors1, _ = validate_dialogue_beats(record1, REPO_ROOT)
    assert errors1 == []

    errors2, _ = validate_dialogue_beats(record2, REPO_ROOT)
    assert any(e.error_code == "MISSING_SCENE_BEAT_PLAN" for e in errors2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
