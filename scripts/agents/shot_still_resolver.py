"""
shot_still_resolver.py

Resolves all shots in a scene to:
  - A globally-ordered 1-based index (for scene-wide archive filenames)
  - The designed-still archive filename (SC0014_01_clip-sc0014-01_shot-sc0014-01-a.png)
  - Per-shot element references: element_id → KER record → perspective view local_paths

Usage as a library:
    from scripts.agents.shot_still_resolver import ShotStillResolver
    resolver = ShotStillResolver(repo_root=Path("."), scene_id="SC0014")
    entries = resolver.resolve()

Usage as CLI:
    python -m scripts.agents.shot_still_resolver SC0014 [--repo-root .]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Element IDs that require protected-subject constraints in still prompts
_PROTECTED_SUBJECT_IDS = {"C08"}


@dataclass
class PerspectivePath:
    view_id: str
    local_path: str
    external_storage_ref: str | None = None


@dataclass
class ElementRef:
    element_id: str
    ker_id: str
    ker_path: str
    element_type: str = ""
    continuity_anchors: list[str] = field(default_factory=list)
    perspective_paths: list[PerspectivePath] = field(default_factory=list)
    protected_subject_flags: list[str] = field(default_factory=list)


@dataclass
class ShotStillEntry:
    global_index: int
    clip_id: str
    shot_id: str
    archive_filename: str
    required_element_ids: list[str]
    element_refs: list[ElementRef] = field(default_factory=list)


class ShotStillResolver:
    def __init__(self, repo_root: Path | str, scene_id: str) -> None:
        self.repo_root = Path(repo_root)
        self.scene_id = scene_id
        self._ker_index: dict[str, list[dict]] | None = None
        self._lmi_index: dict[str, dict] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self) -> list[ShotStillEntry]:
        """Return ordered ShotStillEntry list for all shots in the scene."""
        manifest_paths = self._discover_manifests()
        ker_index = self._build_ker_index()
        lmi_index = self._build_lmi_index()

        entries: list[ShotStillEntry] = []
        global_idx = 0

        for manifest_path in manifest_paths:
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = yaml.safe_load(fh)
            clip_id: str = manifest["clip_id"]
            for shot in manifest.get("shots", []):
                global_idx += 1
                shot_id: str = shot["shot_id"]
                element_ids: list[str] = shot.get("required_element_ids", [])
                archive_fn = _build_archive_filename(
                    self.scene_id, global_idx, clip_id, shot_id
                )
                element_refs = self._resolve_element_refs(
                    element_ids, ker_index, lmi_index
                )
                entries.append(
                    ShotStillEntry(
                        global_index=global_idx,
                        clip_id=clip_id,
                        shot_id=shot_id,
                        archive_filename=archive_fn,
                        required_element_ids=element_ids,
                        element_refs=element_refs,
                    )
                )

        return entries

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def _discover_manifests(self) -> list[Path]:
        pattern = str(
            self.repo_root
            / "planning"
            / "scenes"
            / self.scene_id
            / "manifests"
            / "CLIP_*.yaml"
        )
        paths = sorted(glob.glob(pattern))
        if not paths:
            raise FileNotFoundError(
                f"No clip manifests found for {self.scene_id} at {pattern}"
            )
        return [Path(p) for p in paths]

    # ------------------------------------------------------------------
    # KER index: element_id → list of KER dicts (may have >1 per element_id)
    # ------------------------------------------------------------------

    def _build_ker_index(self) -> dict[str, list[dict]]:
        if self._ker_index is not None:
            return self._ker_index
        index: dict[str, list[dict]] = {}
        pattern = str(self.repo_root / "visual_dev" / "elements" / "**" / "kling_element_reference_*.yaml")
        for ker_path in glob.glob(pattern, recursive=True):
            with open(ker_path, encoding="utf-8") as fh:
                ker = yaml.safe_load(fh)
            if ker.get("record_type") != "kling_element_reference_record":
                continue
            eid = ker.get("element_id", "")
            if eid not in index:
                index[eid] = []
            index[eid].append({"data": ker, "path": ker_path})
        self._ker_index = index
        return index

    # ------------------------------------------------------------------
    # Local media index: view_id → entry dict
    # ------------------------------------------------------------------

    def _build_lmi_index(self) -> dict[str, dict]:
        if self._lmi_index is not None:
            return self._lmi_index
        lmi_index: dict[str, dict] = {}
        lmi_dir = self.repo_root / "evidence" / "local_media_indices"
        for lmi_path in lmi_dir.glob("*.yaml"):
            with open(lmi_path, encoding="utf-8") as fh:
                lmi = yaml.safe_load(fh)
            for entry in lmi.get("entries", []):
                eid_or_tid = entry.get("element_id_or_take_id", "")
                if eid_or_tid:
                    lmi_index[eid_or_tid] = entry
        self._lmi_index = lmi_index
        return lmi_index

    # ------------------------------------------------------------------
    # Element ref resolution
    # ------------------------------------------------------------------

    def _resolve_element_refs(
        self,
        element_ids: list[str],
        ker_index: dict[str, list[dict]],
        lmi_index: dict[str, dict],
    ) -> list[ElementRef]:
        refs: list[ElementRef] = []
        for eid in element_ids:
            kers = ker_index.get(eid, [])
            for ker_record in kers:
                ker_data = ker_record["data"]
                ker_path = ker_record["path"]
                ker_id = ker_data.get("kling_element_reference_id", "")
                perspectives = ker_data.get("gpt_images_2_perspectives", {})
                pv_paths: list[PerspectivePath] = []
                for _view_name, view_id in perspectives.items():
                    entry = lmi_index.get(view_id)
                    if entry:
                        pv_paths.append(
                            PerspectivePath(
                                view_id=view_id,
                                local_path=entry.get("local_path", ""),
                                external_storage_ref=entry.get("external_storage_ref"),
                            )
                        )
                flags: list[str] = []
                if eid in _PROTECTED_SUBJECT_IDS:
                    flags = ["C08_NO_CONTACT", "C08_DISTRESS_OFF_FRAME"]
                refs.append(
                    ElementRef(
                        element_id=eid,
                        ker_id=ker_id,
                        ker_path=os.path.relpath(ker_path, self.repo_root),
                        element_type=ker_data.get("element_type", ""),
                        continuity_anchors=ker_data.get("continuity_anchors", []),
                        perspective_paths=pv_paths,
                        protected_subject_flags=flags,
                    )
                )
        return refs


# ------------------------------------------------------------------
# Archive filename helper
# ------------------------------------------------------------------

def _build_archive_filename(
    scene_id: str, global_index: int, clip_id: str, shot_id: str
) -> str:
    """
    Build the scene-globally-ordered archive filename for a designed shot still.

    Pattern: {scene_id}_{NN:02d}_{clip_slug}_{shot_slug}.png
    Example: SC0014_01_clip-sc0014-01_shot-sc0014-01-a.png
    """
    clip_slug = clip_id.lower().replace("_", "-")
    shot_slug = shot_id.lower().replace("_", "-")
    return f"{scene_id}_{global_index:02d}_{clip_slug}_{shot_slug}.png"


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(description="Resolve shot stills for a scene.")
    parser.add_argument("scene_id", help="Scene ID (e.g. SC0014)")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    resolver = ShotStillResolver(repo_root=Path(args.repo_root), scene_id=args.scene_id)
    entries = resolver.resolve()

    if args.format == "json":
        output = []
        for e in entries:
            output.append(
                {
                    "global_index": e.global_index,
                    "clip_id": e.clip_id,
                    "shot_id": e.shot_id,
                    "archive_filename": e.archive_filename,
                    "required_element_ids": e.required_element_ids,
                    "element_refs": [
                        {
                            "element_id": r.element_id,
                            "ker_id": r.ker_id,
                            "perspective_paths": [
                                {"view_id": p.view_id, "local_path": p.local_path}
                                for p in r.perspective_paths
                            ],
                            "protected_subject_flags": r.protected_subject_flags,
                        }
                        for r in e.element_refs
                    ],
                }
            )
        print(json.dumps(output, indent=2))
    else:
        col_w = [6, 22, 28, 52]
        hdr = (
            f"{'#':>{col_w[0]}}  {'clip':<{col_w[1]}}  {'shot':<{col_w[2]}}  "
            f"{'archive_filename':<{col_w[3]}}"
        )
        print(hdr)
        print("-" * sum(col_w + [len(col_w) * 2]))
        for e in entries:
            ker_ids = ", ".join(r.ker_id for r in e.element_refs) or "—"
            print(
                f"{e.global_index:>{col_w[0]}}  {e.clip_id:<{col_w[1]}}  "
                f"{e.shot_id:<{col_w[2]}}  {e.archive_filename:<{col_w[3]}}"
            )
        print(f"\nTotal: {len(entries)} shots")


if __name__ == "__main__":
    _main()
