"""
contact_sheet_planner.py

Generates per-clip contact-sheet prompt records for a scene's Anchor & Animate pipeline.

Each clip gets a ChatGPT Images 2 prompt record (prompt_type: shot_design,
asset_type: image_set) containing:
  - A multi-panel layout instruction for composing a labeled storyboard grid
  - operator_upload_order: ordered list of shot still archive filenames to upload
  - Panel texts describing each shot's timecode + framing

The contact sheet is a storyboard/QC reference for the operator.
It is NOT an identity-lock source for Kling. Kling receives it only if
the operator enables contact_sheet_ref (default off).

Usage as a library:
    from scripts.agents.contact_sheet_planner import ContactSheetPlanner
    planner = ContactSheetPlanner(repo_root=Path("."), scene_id="SC0014")
    records = planner.plan()  # list of prompt record dicts

Usage as CLI:
    python -m scripts.agents.contact_sheet_planner SC0014 [--repo-root .] [--out-dir prompts/draft]
"""

from __future__ import annotations

import argparse
from itertools import groupby
from pathlib import Path
from typing import Any

import yaml

from scripts.agents.model_guidance_resolver import resolve_model_guidance
from scripts.agents.shot_still_resolver import ShotStillEntry, ShotStillResolver

_CHATGPT_TARGET = "chatgpt_image_best_available"


class ContactSheetPlanner:
    def __init__(self, repo_root: Path | str, scene_id: str) -> None:
        self.repo_root = Path(repo_root)
        self.scene_id = scene_id

    def plan(self) -> list[dict[str, Any]]:
        """Return a list of prompt record dicts — one per clip."""
        resolved = resolve_model_guidance(
            repo_root=self.repo_root, internal_model_target=_CHATGPT_TARGET
        )
        resolver = ShotStillResolver(repo_root=self.repo_root, scene_id=self.scene_id)
        entries = resolver.resolve()
        shot_meta = self._build_shot_meta_index(resolver)

        records: list[dict[str, Any]] = []
        for clip_id, group in groupby(entries, key=lambda e: e.clip_id):
            clip_entries = list(group)
            clip_num = int(clip_id.split("_")[-1])
            record = self._build_record(clip_id, clip_num, clip_entries, shot_meta, resolved)
            records.append(record)
        return records

    # ------------------------------------------------------------------
    # Record builder
    # ------------------------------------------------------------------

    def _build_record(
        self,
        clip_id: str,
        clip_num: int,
        entries: list[ShotStillEntry],
        shot_meta: dict,
        resolved: dict,
    ) -> dict[str, Any]:
        slug = f"contact-clip-{clip_num:02d}"
        prompt_id = f"{self.scene_id}__{slug}__v01"
        panel_count = len(entries)
        panel_texts = [_build_panel_text(i + 1, e, shot_meta) for i, e in enumerate(entries)]
        prompt_text = _build_contact_sheet_prompt(clip_id, panel_texts)
        upload_order = [e.archive_filename for e in entries]
        model_name = resolved.get("resolved_model_name", "")
        snapshot_ref = resolved.get("model_guidance_snapshot_ref", "")

        return {
            "prompt_id": prompt_id,
            "scene_id": self.scene_id,
            "prompt_type": "shot_design",
            "lifecycle_stage": "draft",
            "target_models": [model_name],
            "source_refs": {
                "scene_card": f"planning/scenes/{self.scene_id}/scene_card.yaml",
                "scene_excerpt": (
                    f"planning/scenes/{self.scene_id}/manifests/{clip_id}_manifest.yaml"
                ),
            },
            "prompt_text": prompt_text,
            "generation_params": {
                "provider": resolved.get("provider", "openai"),
                "provider_surface": resolved.get("provider_surface", "chatgpt_ui"),
                "model_guidance_snapshot_ref": snapshot_ref,
                "resolved_model_name": model_name,
                "resolved_model_role": "best_for_this_task",
                "constraint_strategy": "embedded_positive_constraints",
                "clip_id": clip_id,
                "panel_count": panel_count,
                "ordered_shot_stills": upload_order,
                "operator_upload_order": upload_order,
                "contact_sheet_for_kling_default": "off",
                "repo_binary_committed": False,
                "external_generation_required": True,
            },
            "expected_output": {
                "asset_type": "image_set",
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

    # ------------------------------------------------------------------
    # Shot metadata index
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
# Panel text builder
# ------------------------------------------------------------------

def _build_panel_text(
    panel_num: int, entry: ShotStillEntry, shot_meta: dict
) -> str:
    shot = shot_meta.get(entry.shot_id, {})
    framing = shot.get("camera", {}).get("framing", "shot")
    coverage = shot.get("coverage_role", "")
    duration = shot.get("duration_seconds", "?")
    label_parts = [f"Shot {panel_num}"]
    if coverage:
        label_parts.append(coverage)
    label_parts.append(f"{duration}s")
    label_parts.append(framing)
    return " | ".join(label_parts)


# ------------------------------------------------------------------
# Contact sheet prompt text builder
# ------------------------------------------------------------------

def _build_contact_sheet_prompt(clip_id: str, panel_texts: list[str]) -> str:
    n = len(panel_texts)
    panels_desc = "; ".join(
        f"Panel {i+1}: {txt}" for i, txt in enumerate(panel_texts)
    )
    return (
        f"Compose a {n}-panel cinematic storyboard contact sheet for clip {clip_id}. "
        f"Arrange the {n} provided shot stills in a single-row or grid layout with clear panel dividers. "
        f"Label each panel at the bottom with its shot number and framing. "
        f"Panel layout: {panels_desc}. "
        f"Style: clean production storyboard, dark background, minimal label text. "
        f"Constraints: No additional narrative content, no extra characters or objects. "
        f"No subtitles, no visible timecode overlay burned into the image panels, no visible grid lines outside panel borders."
    )


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate contact-sheet prompt records for a scene."
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

    planner = ContactSheetPlanner(repo_root=Path(args.repo_root), scene_id=args.scene_id)
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

    print(f"Total: {len(records)} contact-sheet prompt records.")


if __name__ == "__main__":
    _main()
