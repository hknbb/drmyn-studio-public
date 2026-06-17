"""Continuity-presence validation across scene_beat_plan and omni_clip_manifest.

The schema validates structure; the omni_clip_manifest validator checks that
source_beat_ids exist. Neither checks that a subject who is physically continuous
in the action stays attached as an element through the sequence. A subject that is
present before and after a beat but silently dropped in between (the "continuity
presence gap") drifts out of the element-attach list, so a downstream Kling prompt
never attaches it and the model is free to hallucinate or omit it. For a protected
subject (e.g. an infant) this is a safety-relevant omission.

Two checks:

Control A — beat -> manifest superset (deterministic, hard):
    Every figure's base_element_id in a shot must also appear in that shot's
    required_element_ids, and every element/figure declared by a shot's source
    beats must be carried forward into that shot. The packer copies beat data
    verbatim; this catches packer or hand-edit drift.

Control B — scene presence gap (hard, with opt-out):
    Within an ordered scene_beat_plan, a character/prop element present in beat i
    and beat k (i < k) but absent from an intermediate beat j is flagged, unless
    that element id is listed in beat j's ``subjects_off_frame`` (the explicit,
    human-authored acknowledgement that the subject is intentionally out of frame).
    Locations (LOC*) are excluded: their attach is driven by framing, not subject
    continuity, so they legitimately drop out of tight inserts.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Subjects whose continuity we track: characters (C01) and props (PROP001).
# Locations (LOC001) are excluded — see module docstring.
_SUBJECT_RE = re.compile(r"^(C\d+|PROP\d+)$")


@dataclass(frozen=True)
class ContinuityPresenceIssue:
    file: str
    field_path: str
    error_code: str
    message: str


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_yaml_documents(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    return [d for d in docs if isinstance(d, dict)]


def _is_subject(element_id: str) -> bool:
    return bool(_SUBJECT_RE.match(element_id))


def _figure_element_ids(container: dict[str, Any]) -> set[str]:
    """base_element_id of every figure entry in a beat or shot."""
    ids: set[str] = set()
    for fig in container.get("figures") or []:
        if isinstance(fig, dict):
            base = fig.get("base_element_id")
            if isinstance(base, str) and base:
                ids.add(base)
    return ids


def _element_ids(container: dict[str, Any]) -> set[str]:
    """Union of required_element_ids and figures[].base_element_id."""
    ids: set[str] = set()
    for eid in container.get("required_element_ids") or []:
        if isinstance(eid, str) and eid:
            ids.add(eid)
    return ids | _figure_element_ids(container)


def _beats_by_id(beat_plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    beats: dict[str, dict[str, Any]] = {}
    for beat in beat_plan.get("source_beats") or []:
        if isinstance(beat, dict):
            beat_id = beat.get("beat_id")
            if isinstance(beat_id, str) and beat_id:
                beats[beat_id] = beat
    return beats


# --------------------------------------------------------------------------- #
# Control B — scene presence gap
# --------------------------------------------------------------------------- #
def validate_presence_gap(
    beat_plan: dict[str, Any], rel_file: str
) -> list[ContinuityPresenceIssue]:
    issues: list[ContinuityPresenceIssue] = []
    ordered_beats = [
        b for b in (beat_plan.get("source_beats") or []) if isinstance(b, dict)
    ]
    if not ordered_beats:
        return issues

    # Per-beat tracked-subject sets and off-frame acknowledgements.
    present: list[set[str]] = []
    off_frame: list[set[str]] = []
    for beat in ordered_beats:
        subjects = {e for e in _element_ids(beat) if _is_subject(e)}
        acks = {
            e
            for e in (beat.get("subjects_off_frame") or [])
            if isinstance(e, str) and _is_subject(e)
        }
        present.append(subjects)
        off_frame.append(acks)

    all_subjects = sorted(set().union(*present)) if present else []
    for subject in all_subjects:
        indices = [i for i, s in enumerate(present) if subject in s]
        if len(indices) < 2:
            continue
        first, last = indices[0], indices[-1]
        for j in range(first + 1, last):
            if subject in present[j] or subject in off_frame[j]:
                continue
            beat = ordered_beats[j]
            beat_id = beat.get("beat_id", f"[index {j}]")
            issues.append(
                ContinuityPresenceIssue(
                    file=rel_file,
                    field_path=f"source_beats[{j}].{beat_id}",
                    error_code="CONTINUITY_PRESENCE_GAP",
                    message=(
                        f"{subject} is present before (beat "
                        f"{ordered_beats[first].get('beat_id')}) and after (beat "
                        f"{ordered_beats[last].get('beat_id')}) but is missing from "
                        f"beat {beat_id!r}. Add {subject} to required_element_ids/"
                        f"figures if it is on-frame, or to subjects_off_frame to "
                        f"acknowledge it is intentionally out of frame."
                    ),
                )
            )
    return issues


# --------------------------------------------------------------------------- #
# Control A — beat -> manifest superset
# --------------------------------------------------------------------------- #
def validate_manifest_superset(
    manifest: dict[str, Any],
    beats_by_id: dict[str, dict[str, Any]],
    rel_file: str,
) -> list[ContinuityPresenceIssue]:
    issues: list[ContinuityPresenceIssue] = []
    clip_id = manifest.get("clip_id", "UNKNOWN")
    shots = manifest.get("shots") or []

    for idx, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id", f"[index {idx}]")
        required = {
            e for e in (shot.get("required_element_ids") or []) if isinstance(e, str)
        }
        figure_ids = _figure_element_ids(shot)

        # A1: every figure must be attached as a required element.
        for base in sorted(figure_ids - required):
            issues.append(
                ContinuityPresenceIssue(
                    file=rel_file,
                    field_path=f"shots[{idx}].{shot_id}.required_element_ids",
                    error_code="FIGURE_NOT_ATTACHED",
                    message=(
                        f"[{clip_id}] shot {shot_id!r} has a figure with "
                        f"base_element_id {base} but {base} is not in "
                        f"required_element_ids."
                    ),
                )
            )

        # A2: every element/figure declared by the shot's source beats must be
        # carried forward into the shot.
        shot_elements = required | figure_ids
        for beat_id in shot.get("source_beat_ids") or []:
            beat = beats_by_id.get(beat_id)
            if beat is None:
                continue  # unknown beat id is reported by validate_omni_clip_manifest
            for missing in sorted(_element_ids(beat) - shot_elements):
                issues.append(
                    ContinuityPresenceIssue(
                        file=rel_file,
                        field_path=f"shots[{idx}].{shot_id}.required_element_ids",
                        error_code="BEAT_ELEMENT_DROPPED",
                        message=(
                            f"[{clip_id}] shot {shot_id!r} maps source beat "
                            f"{beat_id!r} which declares {missing}, but {missing} "
                            f"is absent from the shot's required_element_ids/figures."
                        ),
                    )
                )
    return issues


# --------------------------------------------------------------------------- #
# Scene-level entry point (used by validate_production_records)
# --------------------------------------------------------------------------- #
def validate_scene_continuity_presence(
    repo_root: str | Path, scene_id: str
) -> list[ContinuityPresenceIssue]:
    repo_root = Path(repo_root)
    issues: list[ContinuityPresenceIssue] = []

    beat_plan_path = repo_root / "planning" / "scenes" / scene_id / "scene_beat_plan.yaml"
    beat_docs = _load_yaml_documents(beat_plan_path)
    beat_plan = beat_docs[0] if beat_docs else {}
    if beat_plan:
        issues.extend(
            validate_presence_gap(beat_plan, _relative(beat_plan_path, repo_root))
        )

    beats_by_id = _beats_by_id(beat_plan)
    manifest_dir = repo_root / "planning" / "scenes" / scene_id / "manifests"
    for manifest_path in sorted(manifest_dir.glob("CLIP_*.yaml")):
        for manifest in _load_yaml_documents(manifest_path):
            issues.extend(
                validate_manifest_superset(
                    manifest, beats_by_id, _relative(manifest_path, repo_root)
                )
            )
    return issues


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _validate_path(path: Path, repo_root: Path) -> list[ContinuityPresenceIssue]:
    rel = _relative(path, repo_root)
    docs = _load_yaml_documents(path)
    issues: list[ContinuityPresenceIssue] = []
    for doc in docs:
        record_type = doc.get("record_type")
        if record_type == "scene_beat_plan":
            issues.extend(validate_presence_gap(doc, rel))
        elif record_type == "omni_clip_manifest":
            ref = doc.get("source_scene_beat_plan_ref")
            beats_by_id: dict[str, dict[str, Any]] = {}
            if isinstance(ref, str) and ref:
                beat_docs = _load_yaml_documents(repo_root / ref)
                if beat_docs:
                    beats_by_id = _beats_by_id(beat_docs[0])
            issues.extend(validate_manifest_superset(doc, beats_by_id, rel))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate continuity-presence across beat plans and clip manifests."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    all_issues: list[ContinuityPresenceIssue] = []
    for raw_path in args.paths:
        path = raw_path if raw_path.is_absolute() else repo_root / raw_path
        all_issues.extend(_validate_path(path, repo_root))

    for issue in all_issues:
        print(f"{issue.file}:{issue.field_path}: {issue.error_code}: {issue.message}")
    return 1 if all_issues else 0


if __name__ == "__main__":
    sys.exit(main())
