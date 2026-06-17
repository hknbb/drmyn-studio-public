"""
shot_still_planner.py

Generates per-shot still_generation prompt records for a scene's Anchor & Animate pipeline.

Each shot gets a ChatGPT Images 2 prompt record (prompt_type: still_generation,
asset_type: still) containing:
  - A natural-language still photography instruction derived from the manifest shot
  - input_reference_images: the element perspective-view local_paths the operator uploads
  - archive_filename: the scene-globally-ordered output filename
  - protected_subject_flags for C08-containing shots

Usage as a library:
    from scripts.agents.shot_still_planner import ShotStillPlanner
    planner = ShotStillPlanner(repo_root=Path("."), scene_id="SC0014")
    records = planner.plan()  # list of prompt record dicts

Usage as CLI:
    python -m scripts.agents.shot_still_planner SC0014 [--repo-root .] [--out-dir prompts/draft]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

from scripts.agents.model_guidance_resolver import resolve_model_guidance
from scripts.agents.shot_still_resolver import ElementRef, ShotStillEntry, ShotStillResolver

_CHATGPT_TARGET = "chatgpt_image_best_available"

# Priority view keys for reference image selection (most to least identity-dense)
_CHAR_VIEW_PRIORITY = [
    "full_body_front", "front_hero", "close_portrait_front", "front_reference",
    "three_quarter_waist", "three_quarter_left", "three_quarter_medium_reference",
]
_LOC_VIEW_PRIORITY = [
    "front_reference", "three_quarter_medium_reference", "three_quarter_close_reference",
]
_PROP_VIEW_PRIORITY = [
    "front_reference", "three_quarter_medium_reference", "three_quarter_close_reference",
]

# Max GPT Image 2 input images per call
_MAX_INPUT_IMAGES = 16


class ShotStillPlanner:
    def __init__(self, repo_root: Path | str, scene_id: str) -> None:
        self.repo_root = Path(repo_root)
        self.scene_id = scene_id

    def plan(self) -> list[dict[str, Any]]:
        """Return a list of prompt record dicts — one per shot."""
        resolved = resolve_model_guidance(
            repo_root=self.repo_root, internal_model_target=_CHATGPT_TARGET
        )
        resolver = ShotStillResolver(repo_root=self.repo_root, scene_id=self.scene_id)
        entries = resolver.resolve()
        shot_meta = self._build_shot_meta_index(resolver)

        records: list[dict[str, Any]] = []
        for entry in entries:
            shot_data = shot_meta.get(entry.shot_id, {})
            records.append(self._build_record(entry, shot_data, resolved))
        return records

    # ------------------------------------------------------------------
    # Record builder
    # ------------------------------------------------------------------

    def _build_record(
        self, entry: ShotStillEntry, shot_data: dict, resolved: dict
    ) -> dict[str, Any]:
        slug = f"still-{entry.global_index:02d}"
        prompt_id = f"{self.scene_id}__{slug}__v01"
        input_refs = _select_input_references(entry.element_refs)
        protected_flags = _collect_protected_flags(entry.element_refs)
        prompt_text = _build_still_prompt_text(entry, shot_data, input_refs)
        model_name = resolved.get("resolved_model_name", "")
        snapshot_ref = resolved.get("model_guidance_snapshot_ref", "")

        record: dict[str, Any] = {
            "prompt_id": prompt_id,
            "scene_id": self.scene_id,
            "prompt_type": "still_generation",
            "lifecycle_stage": "draft",
            "target_models": [model_name],
            "source_refs": {
                "scene_card": f"planning/scenes/{self.scene_id}/scene_card.yaml",
                "scene_excerpt": f"planning/scenes/{self.scene_id}/manifests/{entry.clip_id}_manifest.yaml",
            },
            "prompt_text": prompt_text,
            "generation_params": {
                "provider": resolved.get("provider", "openai"),
                "provider_surface": resolved.get("provider_surface", "chatgpt_ui"),
                "model_guidance_snapshot_ref": snapshot_ref,
                "resolved_model_name": model_name,
                "resolved_model_role": "best_for_this_task",
                "constraint_strategy": "embedded_positive_constraints",
                "clip_id": entry.clip_id,
                "shot_id": entry.shot_id,
                "shot_order_index": entry.global_index,
                "archive_filename": entry.archive_filename,
                "input_reference_images": list(input_refs),
                "protected_subject_flags": protected_flags,
                "repo_binary_committed": False,
                "external_generation_required": True,
            },
            "expected_output": {
                "asset_type": "still",
                "aspect_ratio": "16:9",
                "variation_count": 1,
            },
            "status": "active",
            "canon_lock": False,
            "provenance": {
                "created_by": "claude_code",
                "created_at": "2026-06-15T00:00:00Z",
            },
        }
        return record

    # ------------------------------------------------------------------
    # Shot metadata index: shot_id → manifest shot dict
    # ------------------------------------------------------------------

    def _build_shot_meta_index(
        self, resolver: ShotStillResolver
    ) -> dict[str, dict]:
        index: dict[str, dict] = {}
        for manifest_path in resolver._discover_manifests():
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = yaml.safe_load(fh)
            for shot in manifest.get("shots", []):
                index[shot["shot_id"]] = shot
        return index


# ------------------------------------------------------------------
# Prompt text builder
# ------------------------------------------------------------------

_CANONICAL_ID_RE = re.compile(
    r"\b(C\d{2}|LOC\d{3}|PROP\d{3}|WD\d{3}|SC\d{4}|KER_\w+|PPACK_\w+)\b"
)


def _strip_canonical_ids(text: str) -> str:
    """Remove canonical planning IDs from text (C01, LOC001, PROP003, SC0014, etc.)."""
    return _CANONICAL_ID_RE.sub("", text)


def _build_still_prompt_text(
    entry: ShotStillEntry, shot: dict, input_refs: list[str]
) -> str:
    framing = shot.get("camera", {}).get("framing", "medium")
    angle = shot.get("camera", {}).get("angle", "eye_level")
    lens = shot.get("camera", {}).get("lens_bias", "")
    lighting_src = shot.get("lighting", {}).get("source", "practical")
    lighting_q = shot.get("lighting", {}).get("quality", "soft")
    lighting_ct = shot.get("lighting", {}).get("color_temp", "warm")
    coverage = shot.get("coverage_role", "")
    action = re.sub(r"@\w+", "", shot.get("prompt_action", "")).strip()
    action = _strip_canonical_ids(action)
    entry_summary = _strip_canonical_ids((shot.get("entry_state") or {}).get("summary", ""))

    anchor_lines: list[str] = []
    for ref in entry.element_refs:
        if ref.continuity_anchors:
            clean = _strip_canonical_ids(ref.continuity_anchors[0])
            anchor_lines.append(clean[:200])

    framing_desc = f"{framing} shot, {angle} angle"
    if lens:
        framing_desc += f" ({lens})"

    parts: list[str] = [
        f"Generate a cinematic still photograph for a {coverage or 'scene'} shot.",
        f"Framing: {framing_desc}.",
    ]
    if entry_summary:
        parts.append(f"Scene state: {entry_summary}.")
    parts.append(f"Action/subject: {action}")
    parts.append(
        f"Lighting: {lighting_src} source, {lighting_q} quality, {lighting_ct} tone."
    )
    if anchor_lines:
        parts.append("Visual anchors (identity reference): " + " | ".join(anchor_lines[:4]) + ".")
    parts += [
        "Style: grounded dramatic realism, photorealistic, warm practical lighting, subtle film grain.",
        "Constraints: No text overlay, no watermarks, no subtitles, no timecode, no additional people or figures not described in the action.",
    ]
    if any("C08" in (ref.element_id or "") for ref in entry.element_refs
           if ref.protected_subject_flags):
        parts.append(
            "Protected subject: The infant must be calm, fully supported, safe. No distress, no unsupported posture, no contact with non-caregiver adults."
        )
    return " ".join(parts)


# ------------------------------------------------------------------
# Reference image selection
# ------------------------------------------------------------------

def _select_input_references(element_refs: list[ElementRef]) -> list[str]:
    """Select one or two reference image local_paths per element, budget ≤16 total."""
    selected: list[str] = []
    for ref in element_refs:
        etype = ref.element_type
        if etype == "character":
            priority = _CHAR_VIEW_PRIORITY
            max_views = 2
        elif etype == "location":
            priority = _LOC_VIEW_PRIORITY
            max_views = 1
        else:
            priority = _PROP_VIEW_PRIORITY
            max_views = 1
        added = _pick_views(ref.perspective_paths, priority, max_views)
        selected.extend(added)
        if len(selected) >= _MAX_INPUT_IMAGES:
            break
    return selected[:_MAX_INPUT_IMAGES]


def _pick_views(
    paths: list,
    priority: list[str],
    max_views: int,
) -> list[str]:
    """Pick up to max_views local_paths from a perspective pack, in priority order."""
    view_map: dict[str, str] = {}
    for pv in paths:
        # view_id is like PPACK_C01_NURSERY_EVENING_V001__full_body_front
        # Extract the suffix after the last __
        parts = pv.view_id.rsplit("__", 1)
        key = parts[-1] if len(parts) == 2 else pv.view_id
        view_map[key] = pv.local_path

    result: list[str] = []
    for key in priority:
        if key in view_map and view_map[key]:
            result.append(view_map[key])
            if len(result) >= max_views:
                break

    if not result and view_map:
        result.append(next(iter(view_map.values())))
    return result


def _collect_protected_flags(element_refs: list[ElementRef]) -> list[str]:
    flags: list[str] = []
    for ref in element_refs:
        for f in ref.protected_subject_flags:
            if f not in flags:
                flags.append(f)
    return flags


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate shot still prompt records for a scene."
    )
    parser.add_argument("scene_id", help="Scene ID (e.g. SC0014)")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument(
        "--out-dir",
        default="prompts/draft",
        help="Output directory (default: prompts/draft)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print records to stdout without writing files",
    )
    args = parser.parse_args()

    planner = ShotStillPlanner(repo_root=Path(args.repo_root), scene_id=args.scene_id)
    records = planner.plan()

    out_dir = Path(args.repo_root) / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for record in records:
        prompt_id: str = record["prompt_id"]
        filename = f"{prompt_id}.yaml"
        content = yaml.dump(record, allow_unicode=True, sort_keys=False, width=120)
        if args.dry_run:
            print(f"# {filename}")
            print(content)
            print()
        else:
            (out_dir / filename).write_text(content, encoding="utf-8")
            print(f"Written: {out_dir / filename}")

    print(f"Total: {len(records)} still prompt records.")


if __name__ == "__main__":
    _main()
