"""Tests for scripts/validators/validate_dialogue_coverage.py."""
from __future__ import annotations

from scripts.validators.validate_dialogue_coverage import validate_dialogue_coverage


def _line(line_id, beat, required=True, line_type="spoken"):
    return {
        "line_id": line_id,
        "target_beat_id": beat,
        "speaker_element_id": "C04",
        "speaker_kling_alias": "@C04_DIMITRI",
        "line_text": "It's time.",
        "line_type": line_type,
        "native_audio_readiness": "blocked",
        "dialogue_required": required,
    }


def _manifest(shots):
    return {"record_type": "omni_clip_manifest", "clip_id": "CLIP_SC0001_01", "shots": shots}


def test_assigned_line_passes():
    lines = [_line("DLG_A", "BEAT_A")]
    manifests = [_manifest([
        {"shot_id": "S1", "source_beat_ids": ["BEAT_A"], "dialogue_line_ids": ["DLG_A"]},
    ])]
    assert validate_dialogue_coverage("SC0001", lines, manifests) == []


def test_required_line_dropped_fails():
    """Beat is covered but the required line is assigned to no shot -> error."""
    lines = [_line("DLG_A", "BEAT_A")]
    manifests = [_manifest([
        {"shot_id": "S1", "source_beat_ids": ["BEAT_A"]},  # no dialogue_line_ids
    ])]
    errs = validate_dialogue_coverage("SC0001", lines, manifests)
    assert any(e.error_code == "DIALOGUE_LINE_DROPPED" for e in errs)


def test_implied_line_not_required_to_be_assigned():
    lines = [_line("DLG_IMP", "BEAT_A", required=False, line_type="implied")]
    manifests = [_manifest([{"shot_id": "S1", "source_beat_ids": ["BEAT_A"]}])]
    assert validate_dialogue_coverage("SC0001", lines, manifests) == []


def test_line_whose_beat_is_not_covered_is_skipped():
    """A line for a beat no clip covers is out of scope for this scene's coverage."""
    lines = [_line("DLG_A", "BEAT_UNCOVERED")]
    manifests = [_manifest([{"shot_id": "S1", "source_beat_ids": ["BEAT_A"]}])]
    assert validate_dialogue_coverage("SC0001", lines, manifests) == []


def test_duplicate_assignment_fails():
    lines = [_line("DLG_A", "BEAT_A")]
    manifests = [_manifest([
        {"shot_id": "S1", "source_beat_ids": ["BEAT_A"], "dialogue_line_ids": ["DLG_A"]},
        {"shot_id": "S2", "source_beat_ids": ["BEAT_A"], "dialogue_line_ids": ["DLG_A"]},
    ])]
    errs = validate_dialogue_coverage("SC0001", lines, manifests)
    assert any(e.error_code == "DIALOGUE_LINE_DUPLICATED" for e in errs)
