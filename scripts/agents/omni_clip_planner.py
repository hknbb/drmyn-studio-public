"""
Deterministic rhythm-aware omni clip planner for Kling production.

Entry point: plan_omni_clips()

Hard constraints enforced (v2 plan §13 / §6 B6):
1. Every shot duration is an integer in {2..15}.
2. Every clip total duration <= 15s.
3. short_insert beats merge into neighboring shots unless explicitly marked
   standalone_insert: true for load-bearing cutaways.
4. Dialogue lines are not split across clips (guaranteed: beats are not split).
5. Beats with splittable: false appear in exactly one shot.
6. Dialogue-heavy clips default to continuity_input_mode: metadata_only.
7. Every shot carries a non-empty duration_reason.
8. Output is deterministic for the same input beats.
9. Packer version is recorded in every generated clip plan.

Soft preferences:
- Cut after transition beats when possible.
- Cut after completed dialogue exchanges when budget allows.
- Prefer object-discovery beats (pulse_check / insert) merged into neighbors.
"""
from __future__ import annotations

import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


PACKER_VERSION: str = "rhythm_aware_v1"
SCHEMA_VERSION: str = "0.x-draft"

VALID_SHOT_DURATIONS: frozenset[int] = frozenset(range(2, 16))
MAX_CLIP_DURATION: int = 15
MIN_SHOT_DURATION: int = 2
MIN_STABLE_SHOT_DURATION: int = 3

# Base durations by semantic_duration_hint
_HINT_BASE: dict[str, int] = {
    "short_insert": 2,   # merge contribution; never a standalone shot
    "normal": 5,
    "long_hold": 10,
}

# Per-role duration deltas applied on top of hint base
_ROLE_DELTA: dict[str, int] = {
    "establish": 0,
    "action": 0,
    "dialogue": 0,    # computed separately from word count
    "hold": 1,        # holds benefit from extra space
    "transition": -1, # transitions prefer shorter durations
    "pulse_check": 0,
    "insert": 0,
}

# Film dialogue pacing: ~150 wpm delivery with reaction pauses
_DIALOGUE_WPS: float = 2.5    # words per second
_PAUSE_PER_TURN: float = 0.5  # seconds pause/reaction between turns


@dataclass
class _Shot:
    """Resolved shot candidate produced by _resolve_shots()."""

    beat_ids: list[str]
    duration: int
    prompt_action: str
    duration_reason: str
    line_ids: list[str] = field(default_factory=list)
    is_dialogue: bool = False
    is_transition: bool = False
    required_element_ids: list[str] = field(default_factory=list)
    camera: dict[str, Any] = field(default_factory=dict)
    lighting: dict[str, Any] = field(default_factory=dict)
    motion: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# YAML loaders
# ---------------------------------------------------------------------------

def _load_beats(path: Path) -> list[dict]:
    """Load source_beats list from scene_beat_plan.yaml."""
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return doc.get("source_beats", [])


def _load_dialogue_record(path: Path) -> dict:
    """Load dialogue_beats.yaml as a single YAML document."""
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _build_dialogue_map(record: dict) -> dict[str, list[dict]]:
    """Return {beat_id: [line_dict, ...]} from a dialogue_beats record."""
    result: dict[str, list[dict]] = {}
    for line in record.get("dialogue_lines", []):
        bid = line.get("target_beat_id")
        if bid:
            result.setdefault(bid, []).append(line)
    return result


# ---------------------------------------------------------------------------
# Duration estimation
# ---------------------------------------------------------------------------

def _dialogue_duration(lines: list[dict]) -> int:
    """Compute shot duration for a dialogue beat from word counts across lines."""
    if not lines:
        return MIN_STABLE_SHOT_DURATION
    total_words = sum(len(ln.get("line_text", "").split()) for ln in lines)
    secs = total_words / _DIALOGUE_WPS + len(lines) * _PAUSE_PER_TURN
    return max(MIN_STABLE_SHOT_DURATION, min(MAX_CLIP_DURATION, round(secs)))


def _beat_duration(beat: dict, lines: list[dict]) -> int:
    """Compute integer duration (seconds) for a single beat."""
    hint = beat.get("semantic_duration_hint", "normal")
    role = beat.get("narrative_role", "action")

    if hint == "short_insert":
        return _HINT_BASE["short_insert"]

    base = _HINT_BASE.get(hint, 5)

    if role == "dialogue" and lines:
        return _dialogue_duration(lines)

    delta = _ROLE_DELTA.get(role, 0)
    return max(MIN_STABLE_SHOT_DURATION, min(MAX_CLIP_DURATION, base + delta))


# ---------------------------------------------------------------------------
# Beat → shot resolution (merge short_inserts)
# ---------------------------------------------------------------------------

def _resolve_shots(
    beats: list[dict],
    dmap: dict[str, list[dict]],
) -> list[_Shot]:
    """
    Convert beats into _Shot candidates, merging short_insert beats into neighbors.

    Merge rules (deterministic):
    1. A short_insert marked standalone_insert: true remains a 2s shot.
    2. A short_insert following a beat with may_merge_with_next: true merges BACKWARD
       into that preceding beat's shot (adding its 2s contribution).
    3. If the preceding beat has may_merge_with_next: false, the insert merges FORWARD
       into the next non-insert beat's shot.
    4. Trailing short_inserts (no following non-insert beat) merge BACKWARD into the
       last accumulated shot, regardless of may_merge_with_next.
    5. Multiple consecutive non-standalone short_inserts are accumulated and merged together.
    """
    def _as_mapping(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _merge_motion_max(shots: list[_Shot], anchor: _Shot) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for key in ("subject_intensity", "camera_intensity"):
            values: list[float] = []
            for s in shots:
                raw = s.motion.get(key)
                if isinstance(raw, (int, float)):
                    values.append(float(raw))
            if values:
                merged[key] = max(values)

        anchor_blocking = anchor.motion.get("blocking_notes")
        if isinstance(anchor_blocking, str) and anchor_blocking.strip():
            merged["blocking_notes"] = anchor_blocking.strip()
        return merged

    def _is_standalone_insert(beat: dict[str, Any]) -> bool:
        return (
            beat.get("semantic_duration_hint") == "short_insert"
            and beat.get("standalone_insert") is True
        )

    # Build raw candidates with per-beat durations
    raw: list[tuple[dict, _Shot]] = []
    for beat in beats:
        bid = beat["beat_id"]
        lines = dmap.get(bid, [])
        dur = _beat_duration(beat, lines)
        role = beat.get("narrative_role", "action")
        hint = beat.get("semantic_duration_hint", "normal")
        # Truncate long content to keep prompt_action readable
        content = beat.get("content", "")
        if len(content) > 120:
            content = content[:117] + "..."
        elem_ids: list[str] = list(beat.get("required_element_ids") or [])
        shot = _Shot(
            beat_ids=[bid],
            duration=dur,
            prompt_action=content,
            duration_reason=f"{hint}/{role} {dur}s",
            line_ids=[ln["line_id"] for ln in lines],
            is_dialogue=(role == "dialogue"),
            is_transition=(role == "transition"),
            required_element_ids=elem_ids,
            camera=_as_mapping(beat.get("camera")),
            lighting=_as_mapping(beat.get("lighting")),
            motion=_as_mapping(beat.get("motion")),
        )
        # One beat -> one shot. The old "split a long_hold into 3s + remainder"
        # path produced two IDENTICAL same-framing shots (wide -> wide), which
        # reads as a static hold cut in half, not cinematic coverage. True
        # coverage (varied framing, reaction cutaways, inserts) is authored at the
        # manifest level by the director pass, not fabricated here.
        raw.append((beat, shot))

    def _union_elements(shots: list[_Shot]) -> list[str]:
        seen: dict[str, None] = {}
        for s in shots:
            for eid in s.required_element_ids:
                seen[eid] = None
        return list(seen)

    result: list[_Shot] = []
    i = 0
    n = len(raw)

    while i < n:
        beat, shot = raw[i]
        is_insert = beat.get("semantic_duration_hint") == "short_insert"

        if not is_insert:
            # Regular beat: absorb following short_inserts backward if allowed
            may_merge = beat.get("may_merge_with_next", True)
            j = i + 1

            if may_merge:
                while j < n:
                    nxt_beat, nxt_shot = raw[j]
                    if nxt_beat.get("semantic_duration_hint") != "short_insert":
                        break
                    if _is_standalone_insert(nxt_beat):
                        break
                    # Absorb nxt_shot into current shot
                    new_dur = min(MAX_CLIP_DURATION, shot.duration + nxt_shot.duration)
                    shot = _Shot(
                        beat_ids=shot.beat_ids + nxt_shot.beat_ids,
                        duration=new_dur,
                        prompt_action=shot.prompt_action,
                        duration_reason=(
                            f"{shot.duration_reason}; "
                            f"{nxt_shot.beat_ids[0]} (short_insert +{nxt_shot.duration}s merged)"
                        ),
                        line_ids=shot.line_ids + nxt_shot.line_ids,
                        is_dialogue=shot.is_dialogue or nxt_shot.is_dialogue,
                        is_transition=shot.is_transition,
                        required_element_ids=_union_elements([shot, nxt_shot]),
                        camera=shot.camera,
                        lighting=shot.lighting,
                        motion=_merge_motion_max([shot, nxt_shot], shot),
                    )
                    j += 1

            result.append(shot)
            i = j

        else:
            if _is_standalone_insert(beat):
                result.append(shot)
                i += 1
                continue

            # Insert beat encountered without a backward-merge host:
            # may_merge_with_next=false on the preceding beat, or at list start.
            # Collect consecutive inserts and merge FORWARD into next regular beat.
            pending: list[_Shot] = [shot]
            j = i + 1
            while j < n:
                nxt_beat, nxt_shot = raw[j]
                if nxt_beat.get("semantic_duration_hint") != "short_insert":
                    break
                if _is_standalone_insert(nxt_beat):
                    break
                pending.append(nxt_shot)
                j += 1

            if j < n:
                # Merge pending inserts into the next regular beat (forward merge)
                nxt_beat, nxt_shot = raw[j]
                extra = sum(s.duration for s in pending)
                merged_dur = min(MAX_CLIP_DURATION, extra + nxt_shot.duration)
                merged_beat_ids = [b for s in pending for b in s.beat_ids] + nxt_shot.beat_ids
                merged_line_ids = [l for s in pending for l in s.line_ids] + nxt_shot.line_ids
                reason_parts = [
                    f"{s.beat_ids[0]} (short_insert merged fwd)" for s in pending
                ]
                reason_parts.append(nxt_shot.duration_reason)
                result.append(_Shot(
                    beat_ids=merged_beat_ids,
                    duration=merged_dur,
                    prompt_action=nxt_shot.prompt_action,
                    duration_reason="; ".join(reason_parts),
                    line_ids=merged_line_ids,
                    is_dialogue=nxt_shot.is_dialogue or any(s.is_dialogue for s in pending),
                    is_transition=nxt_shot.is_transition,
                    required_element_ids=_union_elements(pending + [nxt_shot]),
                    camera=nxt_shot.camera,
                    lighting=nxt_shot.lighting,
                    motion=_merge_motion_max(pending + [nxt_shot], nxt_shot),
                ))
                i = j + 1

            else:
                # No following regular beat: merge pending inserts BACKWARD into last result
                if result:
                    last = result[-1]
                    extra = sum(s.duration for s in pending)
                    new_dur = min(MAX_CLIP_DURATION, last.duration + extra)
                    result[-1] = _Shot(
                        beat_ids=last.beat_ids + [b for s in pending for b in s.beat_ids],
                        duration=new_dur,
                        prompt_action=last.prompt_action,
                        duration_reason=last.duration_reason + "; trailing inserts merged",
                        line_ids=last.line_ids + [l for s in pending for l in s.line_ids],
                        is_dialogue=last.is_dialogue or any(s.is_dialogue for s in pending),
                        is_transition=last.is_transition,
                        required_element_ids=_union_elements([last] + pending),
                        camera=last.camera,
                        lighting=last.lighting,
                        motion=_merge_motion_max([last] + pending, last),
                    )
                i = j  # j == n here

    return result


# ---------------------------------------------------------------------------
# Shot → clip packing
# ---------------------------------------------------------------------------

def _pack_clips(shots: list[_Shot], scene_id: str) -> list[dict[str, Any]]:
    """
    Pack resolved shots into clip dicts with greedy first-fit packing.

    Hard constraint: no clip total > MAX_CLIP_DURATION.
    Soft preference: cut after transition beats when possible.

    Returns list of raw clip dicts (not yet manifest-shaped).
    """
    clips: list[dict[str, Any]] = []
    buf: list[_Shot] = []
    buf_total: int = 0

    def _flush() -> None:
        nonlocal buf, buf_total
        if not buf:
            return
        clip_num = len(clips) + 1
        clip_id = f"CLIP_{scene_id}_{clip_num:02d}"

        shots_out: list[dict[str, Any]] = []
        for si, s in enumerate(buf):
            letter = string.ascii_uppercase[si]
            sd: dict[str, Any] = {
                "shot_id": f"SHOT_{scene_id}_{clip_num:02d}_{letter}",
                "duration_seconds": s.duration,
                "source_beat_ids": s.beat_ids,
                "prompt_action": s.prompt_action,
                "duration_reason": s.duration_reason,
            }
            if s.line_ids:
                sd["dialogue_line_ids"] = s.line_ids
            if s.required_element_ids:
                sd["required_element_ids"] = s.required_element_ids
            if s.camera:
                sd["camera"] = s.camera
            if s.lighting:
                sd["lighting"] = s.lighting
            if s.motion:
                sd["motion"] = s.motion
            shots_out.append(sd)

        dlg_shot_count = sum(1 for s in buf if s.is_dialogue)
        is_heavy = dlg_shot_count * 2 > len(buf)

        clips.append({
            "clip_id": clip_id,
            "total_duration": buf_total,
            "is_dialogue_heavy": is_heavy,
            "shots": shots_out,
            "all_line_ids": [l for s in buf for l in s.line_ids],
        })
        buf = []
        buf_total = 0

    for idx, shot in enumerate(shots):
        if buf_total + shot.duration > MAX_CLIP_DURATION:
            _flush()

        buf.append(shot)
        buf_total += shot.duration

        # Soft preference: cut after transition beats when next shot won't fit anyway
        if shot.is_transition and idx + 1 < len(shots):
            next_shot = shots[idx + 1]
            if buf_total + next_shot.duration > MAX_CLIP_DURATION:
                _flush()

    _flush()
    return clips


# ---------------------------------------------------------------------------
# Output record builders
# ---------------------------------------------------------------------------

def _build_output(
    packed: list[dict[str, Any]],
    scene_id: str,
    sbp_ref: str,
    db_ref: str,
    created_by: str,
    created_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Build omni_clip_plan dict and list of omni_clip_manifest dicts from packed clips.

    Returns:
        (omni_clip_plan, [omni_clip_manifest, ...])
    """
    clip_summaries: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []

    for pc in packed:
        clip_id: str = pc["clip_id"]
        total_dur: int = pc["total_duration"]
        shots: list[dict] = pc["shots"]
        is_heavy: bool = pc["is_dialogue_heavy"]
        all_lines: list[str] = pc["all_line_ids"]

        continuity_mode = "metadata_only" if is_heavy else "frame_input_eligible"

        clip_summaries.append({
            "clip_id": clip_id,
            "clip_manifest_ref": (
                f"planning/scenes/{scene_id}/manifests/{clip_id}_manifest.yaml"
            ),
            "total_duration_seconds": total_dur,
            "source_beat_count": sum(len(s["source_beat_ids"]) for s in shots),
        })

        manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "omni_clip_manifest",
            "scene_id": scene_id,
            "clip_id": clip_id,
            "source_scene_beat_plan_ref": sbp_ref,
            "source_dialogue_beats_ref": db_ref,
            "total_duration_seconds": total_dur,
            "continuity_input_mode": continuity_mode,
            "shots": shots,
            "kling_native_audio": {
                "enabled": False,
                "provider_policy": "kling_native_only",
                "external_tts_allowed": False,
                "adr_vendor_allowed": False,
            },
            "notes": f"Generated by omni_clip_planner packer_version={PACKER_VERSION}",
            "provenance": {
                "created_by": created_by,
                "created_at": created_at,
            },
        }
        if all_lines:
            manifest["dialogue_line_ids"] = all_lines

        # Clip-level union of all shot required_element_ids (order-preserving, deduped)
        seen: dict[str, None] = {}
        for shot in shots:
            for eid in shot.get("required_element_ids") or []:
                seen[eid] = None
        if seen:
            manifest["required_element_ids"] = list(seen)

        manifests.append(manifest)

    clip_plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "omni_clip_plan",
        "scene_id": scene_id,
        "source_scene_beat_plan_ref": sbp_ref,
        "source_dialogue_beats_ref": db_ref,
        "clip_summaries": clip_summaries,
        "packing_strategy": {
            "packer_version": PACKER_VERSION,
            "packing_mode": "rhythm_aware_constrained",
            "cut_point_preference_order": [
                "location_transition",
                "dialogue_exchange_end",
                "object_discovery",
                "beat_boundary",
            ],
        },
        "notes": (
            f"Computed by omni_clip_planner packer_version={PACKER_VERSION}. "
            f"Clip count is derived, not authored. "
            f"Hard constraints: shot [2..15]s integer-only, clip total <=15s, "
            f"standalone short_insert only when explicitly flagged, no unsplittable beat split."
        ),
        "provenance": {
            "created_by": created_by,
            "created_at": created_at,
        },
    }

    return clip_plan, manifests


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plan_omni_clips(
    scene_id: str,
    beat_plan_ref: str,
    dialogue_beats_ref: str,
    repo_root: str | Path,
    created_by: str = "omni_clip_planner",
    created_at: str = "",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Run deterministic rhythm-aware clip packing for a scene.

    Loads source beats and dialogue lines, resolves shot candidates (merging
    short_insert beats), packs shots into clips, and returns structured
    omni_clip_plan and omni_clip_manifest records ready for YAML serialization
    or schema validation.

    Args:
        scene_id:           Scene identifier, e.g. "SC0001".
        beat_plan_ref:      Relative path from repo_root to scene_beat_plan.yaml.
        dialogue_beats_ref: Relative path from repo_root to dialogue_beats.yaml.
        repo_root:          Repository root directory.
        created_by:         Provenance author field.
        created_at:         ISO 8601 timestamp; if empty, derived from the later
                            mtime of beat_plan_ref and dialogue_beats_ref to ensure
                            deterministic output for identical inputs.

    Returns:
        Tuple of (omni_clip_plan dict, list of omni_clip_manifest dicts).
        Clip count is computed by the packer; never hardcoded.
    """
    root = Path(repo_root)
    beats = _load_beats(root / beat_plan_ref)
    db_record = _load_dialogue_record(root / dialogue_beats_ref)

    if not created_at:
        beat_mtime = (root / beat_plan_ref).stat().st_mtime
        dialogue_mtime = (root / dialogue_beats_ref).stat().st_mtime
        source_mtime = max(beat_mtime, dialogue_mtime)
        created_at = datetime.fromtimestamp(source_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dmap = _build_dialogue_map(db_record)

    shots = _resolve_shots(beats, dmap)
    packed = _pack_clips(shots, scene_id)

    return _build_output(packed, scene_id, beat_plan_ref, dialogue_beats_ref, created_by, created_at)
