"""
Dialogue coverage validator ("no dropped dialogue").

A scene's verbatim spoken lines are the soul of the scene; the prompt renderer
now carries each line inline as alias-tagged on-screen text in the speaking shot.
For that to hold, every load-bearing dialogue line must actually be ASSIGNED to a
shot. This validator guards against the line silently vanishing (the failure mode
where a whole scene's dialogue disappeared from the prompt because it was never
assigned to a shot, or was gated out).

Rule (hard failure), per scene:
  Every dialogue line with ``dialogue_required: true`` and ``line_type != implied``
  whose ``target_beat_id`` is covered by at least one clip manifest MUST appear in
  exactly one shot's ``dialogue_line_ids`` across the scene's manifests.

  - DIALOGUE_LINE_DROPPED   - a required, non-implied line whose beat is covered is
                              not assigned to any shot.
  - DIALOGUE_LINE_DUPLICATED - the same line_id is assigned to more than one shot.

Read-only. Operates on already-parsed records so it is reusable from the
production validator and from tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DialogueCoverageError(ValueError):
    scene_id: str
    error_code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.scene_id}] {self.error_code}: {self.message}"


def validate_dialogue_coverage(
    scene_id: str,
    dialogue_lines: list[dict[str, Any]],
    manifests: list[dict[str, Any]],
) -> list[DialogueCoverageError]:
    """Validate that every required, non-implied dialogue line is assigned to a shot.

    Args:
        scene_id: scene identifier (e.g. SC0014)
        dialogue_lines: the dialogue_beats.yaml ``dialogue_lines`` list
        manifests: the scene's omni_clip_manifest dicts

    Returns:
        list of DialogueCoverageError (empty when the scene is clean)
    """
    errors: list[DialogueCoverageError] = []

    # Beats covered by any shot, and where each dialogue line_id is assigned.
    covered_beats: set[str] = set()
    line_to_shots: dict[str, list[str]] = {}
    for manifest in manifests:
        if not isinstance(manifest, dict):
            continue
        for shot in manifest.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            shot_id = shot.get("shot_id", "?")
            for bid in shot.get("source_beat_ids") or []:
                if isinstance(bid, str):
                    covered_beats.add(bid)
            for lid in shot.get("dialogue_line_ids") or []:
                if isinstance(lid, str):
                    line_to_shots.setdefault(lid, []).append(shot_id)

    # Duplicate assignment across shots.
    for lid, shots in sorted(line_to_shots.items()):
        if len(shots) > 1:
            errors.append(
                DialogueCoverageError(
                    scene_id,
                    "DIALOGUE_LINE_DUPLICATED",
                    f"dialogue line {lid} is assigned to {len(shots)} shots "
                    f"({', '.join(shots)}); each line belongs to exactly one shot.",
                )
            )

    # Required, non-implied lines whose beat is covered must be assigned.
    for line in dialogue_lines:
        if not isinstance(line, dict):
            continue
        if not line.get("dialogue_required"):
            continue
        if line.get("line_type") == "implied":
            continue
        target = line.get("target_beat_id")
        if not isinstance(target, str) or target not in covered_beats:
            continue
        lid = line.get("line_id")
        if not isinstance(lid, str) or lid not in line_to_shots:
            errors.append(
                DialogueCoverageError(
                    scene_id,
                    "DIALOGUE_LINE_DROPPED",
                    f"required dialogue line {lid!r} (beat {target}) is covered by the "
                    "clip plan but is not assigned to any shot's dialogue_line_ids; it "
                    "would never reach the prompt.",
                )
            )

    return errors


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def validate_scene_dialogue_coverage(
    repo_root: str | Path, scene_id: str
) -> list[DialogueCoverageError]:
    """Load a scene's dialogue_beats + omni_clip_manifests and validate coverage."""
    repo_root = Path(repo_root)
    scene_dir = repo_root / "planning" / "scenes" / scene_id
    dialogue = _load_yaml(scene_dir / "dialogue_beats.yaml")
    dialogue_lines = dialogue.get("dialogue_lines")
    if not isinstance(dialogue_lines, list):
        dialogue_lines = []

    manifests: list[dict[str, Any]] = []
    for mpath in sorted((scene_dir / "manifests").glob("*.yaml")):
        doc = _load_yaml(mpath)
        if doc.get("record_type") == "omni_clip_manifest":
            manifests.append(doc)

    return validate_dialogue_coverage(scene_id, dialogue_lines, manifests)
