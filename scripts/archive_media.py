"""
archive_media.py

File an externally-produced image/video binary into a standardized, LOCAL-ONLY
archive tree and register it in a metadata-only ``local_media_index`` record.

The archive tree is git-ignored (see ``.gitignore`` -> ``archive/``); only the
metadata index under ``evidence/local_media_indices/`` is committed. No media
binary is ever committed to the repository (``repo_binary_committed: false``).

Standard layout::

    archive/<PROJECT>/<SCENE>/<ELEMENT>/stage<N>/<images|video>/<filename>

where ``<SCENE>`` is ``SCdddd`` or ``_elements``.

Usage::

    python scripts/archive_media.py \
        --src "C:/path/to/ChatGPT Image ... .png" \
        --scene _elements --element C10 --stage 3 \
        --kind gpt_images_2_perspective_output \
        --id GPTIMG2_C10_P01_FRONT_V001 \
        --notes "Stage-3 front_reference."

This script is metadata-only with respect to the repo: it copies (or moves) the
binary into the git-ignored archive and writes/updates a YAML index. It never
mutates lifecycle/pack state, prompts, or element records.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROJECT = "nexuszero"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
SCENE_RE = re.compile(r"^(SC\d{4}|_elements)$")
INDEX_DIR = Path("evidence/local_media_indices")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def infer_media_type(src: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    ext = src.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    raise ValueError(
        f"Cannot infer media type from extension {ext!r}; pass --media-type image|video."
    )


def dest_relpath(
    *, project: str, scene: str, element: str, stage: int, media_type: str, filename: str
) -> Path:
    bucket = "images" if media_type == "image" else "video"
    return Path("archive") / project / scene / element / f"stage{stage}" / bucket / filename


def dest_relpath_subdir(
    *, project: str, scene: str, subdir: str, filename: str
) -> Path:
    """Scene-level subcategory path (K4 convention): no element or stage component."""
    return Path("archive") / project / scene / subdir / filename


def index_path_for(scene: str) -> Path:
    return INDEX_DIR / f"LOCAL_MEDIA_INDEX_{scene}_ARCHIVE_V001.yaml"


def _compute_storage_policy(entries: list[dict[str, Any]]) -> str:
    kinds = set()
    for entry in entries:
        local = str(entry.get("local_path", ""))
        if "/images/" in local:
            kinds.add("image")
        elif "/video/" in local:
            kinds.add("video")
    if kinds == {"image"}:
        return "external_image_only"
    if kinds == {"video"}:
        return "external_video_only"
    return "mixed_external"


def load_index(path: Path, scene: str) -> dict[str, Any]:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Existing index {path} is not a mapping.")
        data.setdefault("scene_id", scene)
        data.setdefault("entries", [])
        return data
    return {
        "scene_id": scene,
        "created_at": _utc_now(),
        "storage_policy": "external_image_only",
        "entries": [],
    }


def archive_one(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    src = Path(args.src)
    if not src.is_absolute():
        src = (Path.cwd() / src).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")

    if not SCENE_RE.match(args.scene):
        raise ValueError(f"--scene must be SCdddd or _elements, got {args.scene!r}")

    subdir = getattr(args, "subdir", None)
    if subdir:
        if not args.element:
            # subdir mode: no element/stage required
            pass
        # element is ignored when subdir is set
    else:
        if not args.element:
            raise ValueError("--element is required unless --subdir is set.")

    media_type = infer_media_type(src, args.media_type)
    if subdir:
        rel = dest_relpath_subdir(
            project=args.project,
            scene=args.scene,
            subdir=subdir,
            filename=src.name,
        )
    else:
        rel = dest_relpath(
            project=args.project,
            scene=args.scene,
            element=args.element,
            stage=args.stage,
            media_type=media_type,
            filename=src.name,
        )
    dest = repo_root / rel

    if args.dry_run:
        print(f"[dry-run] would copy {src} -> {dest}")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if args.move:
            shutil.move(str(src), str(dest))
        else:
            shutil.copy2(str(src), str(dest))

    digest = None if args.dry_run else _sha256(dest)
    size = None if args.dry_run else dest.stat().st_size
    rel_posix = rel.as_posix()

    entry: dict[str, Any] = {
        "kind": args.kind,
        "element_id_or_take_id": args.id or args.element,
        "storage_backend": "local_manual",
        "last_seen_at": _utc_now(),
        "repo_binary_committed": False,
        "local_path": rel_posix,
        "external_storage_ref": f"external://local_manual/{rel_posix}",
    }
    if digest:
        entry["sha256"] = digest
    if size is not None:
        entry["size_bytes"] = size
    if subdir:
        default_note = f"Archived {media_type} for scene {args.scene}/{subdir}."
    else:
        default_note = f"Archived {media_type} for {args.element} (stage {args.stage})."
    note = args.notes or default_note
    note += f" Source: {src}." if not args.notes else ""
    entry["notes"] = note

    index_file = (
        Path(args.index) if args.index else repo_root / index_path_for(args.scene)
    )
    if not index_file.is_absolute():
        index_file = repo_root / index_file
    index = load_index(index_file, args.scene)

    # Replace any existing entry with the same local_path (idempotent re-archive).
    index["entries"] = [
        e for e in index["entries"] if e.get("local_path") != rel_posix
    ]
    index["entries"].append(entry)
    index["storage_policy"] = _compute_storage_policy(index["entries"])

    if args.dry_run:
        print(f"[dry-run] would write index {index_file} (+1 entry)")
    else:
        index_file.parent.mkdir(parents=True, exist_ok=True)
        with index_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(index, f, sort_keys=False, allow_unicode=True)
        print(f"archived: {rel_posix}")
        print(f"index:    {index_file.relative_to(repo_root).as_posix()}")
    return entry


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", required=True, help="Path to the source media file.")
    p.add_argument("--scene", required=True, help="SCdddd or _elements.")
    p.add_argument("--element", default=None, help="Element/character id (e.g. C10, LOC001). Required unless --subdir is set.")
    p.add_argument("--stage", type=int, default=3, choices=[1, 2, 3], help="Pipeline stage.")
    p.add_argument("--subdir", choices=["shots", "contact_sheets", "clips"], default=None,
                   help="Scene-level subcategory (shots|contact_sheets|clips). When set, --element and --stage are ignored.")
    p.add_argument("--media-type", choices=["image", "video"], default=None)
    p.add_argument("--kind", default="archived_media", help="Semantic kind label for the index entry.")
    p.add_argument("--id", default=None, help="element_id_or_take_id (defaults to --element).")
    p.add_argument("--project", default=DEFAULT_PROJECT)
    p.add_argument("--notes", default=None)
    p.add_argument("--index", default=None, help="Override index YAML path.")
    p.add_argument("--repo-root", default=str(REPO_ROOT))
    p.add_argument("--move", action="store_true", help="Move instead of copy.")
    p.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        archive_one(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
