"""
Semantic validator for omni_clip_manifest records.

Enforces cross-field rules that JSON Schema cannot express:
1. sum(shots[].duration_seconds) == total_duration_seconds
2. All source_beat_ids must exist in source_scene_beat_plan
3. All dialogue_line_ids must exist in source_dialogue_beats (when present)
4. No non-splittable source beat is split across multiple shots
5. continuity_input_mode: frame_input_active requires at least one frame reference
6. kling_native_audio forbids external TTS and ADR
7. Referenced source files must exist
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class OmniClipManifestValidationError(ValueError):
    """Raised when a omni_clip_manifest record violates semantic rules."""

    clip_id: str
    error_code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.clip_id}] {self.error_code}: {self.message}"


def _load_yaml_documents(file_path: str | Path) -> list[dict]:
    """Load all YAML documents from a file (multi-document YAML)."""
    path = Path(file_path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    return [d for d in docs if d is not None]


def _load_scene_beat_plan(repo_root: str | Path, ref: str) -> dict[str, dict]:
    """
    Load beat_id -> beat metadata from scene_beat_plan.yaml.
    Returns dict: {beat_id: {content, splittable, ...}, ...}
    """
    full_path = Path(repo_root) / ref
    docs = _load_yaml_documents(full_path)
    beats: dict[str, dict] = {}
    for doc in docs:
        if isinstance(doc, dict):
            source_beats = doc.get("source_beats", [])
            for beat in source_beats:
                beat_id = beat.get("beat_id")
                if beat_id:
                    beats[beat_id] = beat
    return beats


def _load_dialogue_beats(repo_root: str | Path, ref: str) -> set[str]:
    """
    Load line_ids from dialogue_beats.yaml.
    Returns set: {line_id, ...}
    """
    full_path = Path(repo_root) / ref
    doc = _load_yaml_documents(full_path)
    if not doc:
        return set()
    record = doc[0] if isinstance(doc, list) else doc
    if not isinstance(record, dict):
        return set()

    line_ids = set()
    dialogue_lines = record.get("dialogue_lines", [])
    for line in dialogue_lines:
        line_id = line.get("line_id")
        if line_id:
            line_ids.add(line_id)
    return line_ids


def validate_omni_clip_manifest(
    record: dict[str, Any], repo_root: str | Path
) -> list[OmniClipManifestValidationError]:
    """
    Validate a single omni_clip_manifest record for semantic correctness.

    Rules enforced (hard failures):
    1. sum(shots[].duration_seconds) == total_duration_seconds
    2. All source_beat_ids must exist in source_scene_beat_plan
    3. All dialogue_line_ids must exist in source_dialogue_beats (when present)
    4. No source beat with splittable: false is split across multiple shots
    5. continuity_input_mode: frame_input_active requires at least one frame reference
    6. kling_native_audio: external_tts_allowed and adr_vendor_allowed must be false
    7. Referenced source files must exist

    Args:
        record: omni_clip_manifest dict with schema_version, record_type, etc.
        repo_root: root directory of the repository

    Returns:
        List of validation errors (empty if record is valid)
    """
    errors: list[OmniClipManifestValidationError] = []

    clip_id = record.get("clip_id", "UNKNOWN")
    repo_root_path = Path(repo_root)

    # Load references
    scene_beat_plan_ref = record.get("source_scene_beat_plan_ref")
    dialogue_beats_ref = record.get("source_dialogue_beats_ref")

    # Rule 7: Check referenced files exist
    if scene_beat_plan_ref:
        scene_beat_path = repo_root_path / scene_beat_plan_ref
        if not scene_beat_path.exists():
            errors.append(
                OmniClipManifestValidationError(
                    clip_id=clip_id,
                    error_code="MISSING_SCENE_BEAT_PLAN",
                    message=f"source_scene_beat_plan_ref points to missing file: {scene_beat_plan_ref}",
                )
            )
            return errors

    if dialogue_beats_ref:
        dialogue_beats_path = repo_root_path / dialogue_beats_ref
        if not dialogue_beats_path.exists():
            errors.append(
                OmniClipManifestValidationError(
                    clip_id=clip_id,
                    error_code="MISSING_DIALOGUE_BEATS",
                    message=f"source_dialogue_beats_ref points to missing file: {dialogue_beats_ref}",
                )
            )
            return errors

    # Load beat and line metadata
    beats = _load_scene_beat_plan(repo_root, scene_beat_plan_ref) if scene_beat_plan_ref else {}
    line_ids = _load_dialogue_beats(repo_root, dialogue_beats_ref) if dialogue_beats_ref else set()

    # Rule 1: total_duration_seconds == sum(shots[].duration_seconds)
    shots = record.get("shots", [])
    total_duration = record.get("total_duration_seconds", 0)
    shot_durations_sum = sum(shot.get("duration_seconds", 0) for shot in shots)

    # Rule 1b: Kling Omni multi-shot caps at 6 shots (cuts) per single generation.
    if len(shots) > 6:
        errors.append(
            OmniClipManifestValidationError(
                clip_id=clip_id,
                error_code="TOO_MANY_SHOTS",
                message=f"clip has {len(shots)} shots; Kling Omni allows at most 6 shots per generation.",
            )
        )

    if shot_durations_sum != total_duration:
        errors.append(
            OmniClipManifestValidationError(
                clip_id=clip_id,
                error_code="DURATION_MISMATCH",
                message=f"total_duration_seconds={total_duration} but sum(shots[].duration_seconds)={shot_durations_sum}; must match",
            )
        )

    # Validate each shot
    all_source_beat_ids = set()
    for shot_idx, shot in enumerate(shots):
        shot_id = shot.get("shot_id", f"[index {shot_idx}]")
        source_beat_ids = shot.get("source_beat_ids", [])
        dialogue_line_ids = shot.get("dialogue_line_ids", [])

        # Rule 2: source_beat_ids exist in scene_beat_plan
        for beat_id in source_beat_ids:
            if beat_id not in beats and beats:  # only check if we loaded beats
                errors.append(
                    OmniClipManifestValidationError(
                        clip_id=clip_id,
                        error_code="UNKNOWN_BEAT_ID",
                        message=f"shot {shot_id!r}: source_beat_id={beat_id!r} not found in {scene_beat_plan_ref}",
                    )
                )
            all_source_beat_ids.add(beat_id)

        # Rule 3: dialogue_line_ids exist in dialogue_beats
        for line_id in dialogue_line_ids:
            if line_id not in line_ids and line_ids:  # only check if we loaded lines
                errors.append(
                    OmniClipManifestValidationError(
                        clip_id=clip_id,
                        error_code="UNKNOWN_LINE_ID",
                        message=f"shot {shot_id!r}: dialogue_line_id={line_id!r} not found in {dialogue_beats_ref}",
                    )
                )

    # Rule 4: no non-splittable beat is split across multiple shots
    beat_id_to_shot_count: dict[str, int] = {}
    for shot in shots:
        for beat_id in shot.get("source_beat_ids", []):
            beat_id_to_shot_count[beat_id] = beat_id_to_shot_count.get(beat_id, 0) + 1

    for beat_id, shot_count in beat_id_to_shot_count.items():
        if shot_count > 1 and beat_id in beats:
            beat = beats[beat_id]
            if beat.get("splittable", False) is False:
                errors.append(
                    OmniClipManifestValidationError(
                        clip_id=clip_id,
                        error_code="UNSPLITTABLE_BEAT_SPLIT",
                        message=f"beat_id={beat_id!r} has splittable: false but appears in {shot_count} shots; cannot split across multiple shots",
                    )
                )

    # Rule 5: frame_input_active requires at least one frame reference
    continuity_mode = record.get("continuity_input_mode")
    if continuity_mode == "frame_input_active":
        first_frame = record.get("first_frame_reference")
        last_frame = record.get("last_frame_reference")
        if not first_frame and not last_frame:
            errors.append(
                OmniClipManifestValidationError(
                    clip_id=clip_id,
                    error_code="FRAME_INPUT_ACTIVE_NO_REFS",
                    message=f"continuity_input_mode: frame_input_active requires at least one of first_frame_reference or last_frame_reference, but both are missing",
                )
            )

    # Rule 6: Defensive check for external TTS / ADR fields
    kling_native_audio = record.get("kling_native_audio", {})
    if kling_native_audio.get("external_tts_allowed") is not False:
        errors.append(
            OmniClipManifestValidationError(
                clip_id=clip_id,
                error_code="EXTERNAL_TTS_ALLOWED",
                message="kling_native_audio.external_tts_allowed must be false (const)",
            )
        )
    if kling_native_audio.get("adr_vendor_allowed") is not False:
        errors.append(
            OmniClipManifestValidationError(
                clip_id=clip_id,
                error_code="ADR_VENDOR_ALLOWED",
                message="kling_native_audio.adr_vendor_allowed must be false (const)",
            )
        )

    return errors


def validate_omni_clip_manifest_batch(
    records: list[dict[str, Any]], repo_root: str | Path
) -> tuple[dict[str, list[OmniClipManifestValidationError]], dict[str, set[str]]]:
    """
    Validate a batch of omni_clip_manifest records.

    Also enforces batch-level rule:
    - No dialogue_line_id appears in multiple clips

    Args:
        records: list of omni_clip_manifest dicts
        repo_root: root directory of the repository

    Returns:
        Tuple of (errors_by_clip, dialogue_cross_clip_violations) where:
        - errors_by_clip: dict mapping clip_id to validation errors
        - dialogue_cross_clip_violations: dict mapping dialogue_line_id to clip_ids that contain it
    """
    errors_by_clip: dict[str, list[OmniClipManifestValidationError]] = {}
    line_id_to_clips: dict[str, set[str]] = {}

    for record in records:
        clip_id = record.get("clip_id", "UNKNOWN")
        errors = validate_omni_clip_manifest(record, repo_root)
        if errors:
            errors_by_clip[clip_id] = errors

        # Track dialogue line across clips
        shots = record.get("shots", [])
        for shot in shots:
            for line_id in shot.get("dialogue_line_ids", []):
                if line_id not in line_id_to_clips:
                    line_id_to_clips[line_id] = set()
                line_id_to_clips[line_id].add(clip_id)

    # Check for dialogue lines in multiple clips
    cross_clip_violations: dict[str, set[str]] = {}
    for line_id, clip_ids in line_id_to_clips.items():
        if len(clip_ids) > 1:
            cross_clip_violations[line_id] = clip_ids

    return errors_by_clip, cross_clip_violations
