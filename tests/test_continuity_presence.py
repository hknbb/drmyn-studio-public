"""Tests for scripts/validators/validate_continuity_presence.py

Four scenarios per the plan:
  (a) Subject present before and after an intermediate beat but missing from it → error.
  (b) Same gap but with subjects_off_frame acknowledgement → clean.
  (c) Manifest shot missing an element declared by its source beat → BEAT_ELEMENT_DROPPED.
  (d) Manifest shot has a figure whose base_element_id is absent from required_element_ids
      → FIGURE_NOT_ATTACHED.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_continuity_presence import (  # noqa: E402
    validate_presence_gap,
    validate_manifest_superset,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _beat(
    beat_id: str,
    required_element_ids: list[str] | None = None,
    figures: list[dict] | None = None,
    subjects_off_frame: list[str] | None = None,
) -> dict:
    b: dict = {
        "beat_id": beat_id,
        "required_element_ids": required_element_ids or [],
    }
    if figures is not None:
        b["figures"] = figures
    if subjects_off_frame is not None:
        b["subjects_off_frame"] = subjects_off_frame
    return b


def _fig(base: str) -> dict:
    return {
        "figure_id": f"FIG_{base}",
        "base_element_id": base,
        "kling_alias": f"@{base}_ALIAS",
        "role": "test figure",
    }


def _beat_plan(beats: list[dict]) -> dict:
    return {"record_type": "scene_beat_plan", "source_beats": beats}


def _shot(
    shot_id: str,
    source_beat_ids: list[str],
    required_element_ids: list[str] | None = None,
    figures: list[dict] | None = None,
) -> dict:
    s: dict = {
        "shot_id": shot_id,
        "source_beat_ids": source_beat_ids,
        "required_element_ids": required_element_ids or [],
    }
    if figures is not None:
        s["figures"] = figures
    return s


def _manifest(shots: list[dict], clip_id: str = "CLIP_TEST") -> dict:
    return {
        "record_type": "omni_clip_manifest",
        "clip_id": clip_id,
        "shots": shots,
    }


# --------------------------------------------------------------------------- #
# (a) Presence gap without opt-out → CONTINUITY_PRESENCE_GAP
# --------------------------------------------------------------------------- #
def test_presence_gap_detected() -> None:
    """C08 present in first and third beat but missing from second → error."""
    bp = _beat_plan([
        _beat("BEAT_A", required_element_ids=["C01", "C08"]),
        _beat("BEAT_B", required_element_ids=["C04"]),   # C08 silently absent
        _beat("BEAT_C", required_element_ids=["C01", "C08"]),
    ])
    errors = validate_presence_gap(bp, "test_beat_plan.yaml")
    codes = [e.error_code for e in errors]
    assert "CONTINUITY_PRESENCE_GAP" in codes
    # C01 is also dropped in BEAT_B — should be flagged too
    assert sum(1 for c in codes if c == "CONTINUITY_PRESENCE_GAP") >= 2


# --------------------------------------------------------------------------- #
# (b) Same gap with subjects_off_frame acknowledgement → clean
# --------------------------------------------------------------------------- #
def test_presence_gap_suppressed_by_subjects_off_frame() -> None:
    """C08 acknowledged in middle beat via subjects_off_frame → no error."""
    bp = _beat_plan([
        _beat("BEAT_A", required_element_ids=["C01", "C08"]),
        _beat("BEAT_B", required_element_ids=["C04"], subjects_off_frame=["C08", "C01"]),
        _beat("BEAT_C", required_element_ids=["C01", "C08"]),
    ])
    errors = validate_presence_gap(bp, "test_beat_plan.yaml")
    assert errors == [], errors


# --------------------------------------------------------------------------- #
# (c) Beat element dropped in manifest shot → BEAT_ELEMENT_DROPPED
# --------------------------------------------------------------------------- #
def test_beat_element_dropped_in_manifest() -> None:
    """Beat declares C08 but manifest shot omits it → BEAT_ELEMENT_DROPPED."""
    beats_by_id = {
        "BEAT_A": _beat("BEAT_A", required_element_ids=["C01", "C08"]),
    }
    shots = [_shot("SHOT_01", ["BEAT_A"], required_element_ids=["C01"])]  # C08 missing
    m = _manifest(shots)
    errors = validate_manifest_superset(m, beats_by_id, "test_manifest.yaml")
    codes = [e.error_code for e in errors]
    assert "BEAT_ELEMENT_DROPPED" in codes


def test_beat_element_carried_forward_passes() -> None:
    """All beat elements present in shot → clean."""
    beats_by_id = {
        "BEAT_A": _beat("BEAT_A", required_element_ids=["C01", "C08"]),
    }
    shots = [_shot("SHOT_01", ["BEAT_A"], required_element_ids=["C01", "C08"])]
    m = _manifest(shots)
    errors = validate_manifest_superset(m, beats_by_id, "test_manifest.yaml")
    assert errors == [], errors


# --------------------------------------------------------------------------- #
# (d) Figure base_element_id absent from required_element_ids → FIGURE_NOT_ATTACHED
# --------------------------------------------------------------------------- #
def test_figure_not_attached_fails() -> None:
    """Shot has a figure with base C08 but C08 not in required_element_ids → error."""
    beats_by_id: dict = {}
    shots = [_shot(
        "SHOT_01", [],
        required_element_ids=["C01"],
        figures=[_fig("C08")],  # C08 figure but not in required_element_ids
    )]
    m = _manifest(shots)
    errors = validate_manifest_superset(m, beats_by_id, "test_manifest.yaml")
    codes = [e.error_code for e in errors]
    assert "FIGURE_NOT_ATTACHED" in codes


def test_figure_attached_passes() -> None:
    """Figure's base_element_id is in required_element_ids → clean."""
    beats_by_id: dict = {}
    shots = [_shot(
        "SHOT_01", [],
        required_element_ids=["C01", "C08"],
        figures=[_fig("C08")],
    )]
    m = _manifest(shots)
    errors = validate_manifest_superset(m, beats_by_id, "test_manifest.yaml")
    assert errors == [], errors


# --------------------------------------------------------------------------- #
# Locations are excluded from presence-gap tracking
# --------------------------------------------------------------------------- #
def test_location_gap_not_flagged() -> None:
    """LOC001 present in outer beats, absent in middle — should NOT be flagged."""
    bp = _beat_plan([
        _beat("BEAT_A", required_element_ids=["C01", "LOC001"]),
        _beat("BEAT_B", required_element_ids=["C01"]),   # LOC001 out (e.g. insert)
        _beat("BEAT_C", required_element_ids=["C01", "LOC001"]),
    ])
    errors = validate_presence_gap(bp, "test_beat_plan.yaml")
    # No error for LOC001; only check that LOC001 is not in any error message
    for e in errors:
        assert "LOC001" not in e.message
