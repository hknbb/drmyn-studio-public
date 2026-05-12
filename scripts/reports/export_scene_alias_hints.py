from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.resolvers.scene_to_kling_alias import resolve_scene_aliases



def _scene_num(scene_id: str) -> int:
    if not scene_id.startswith("SC") or not scene_id[2:].isdigit():
        raise ValueError(f"invalid scene id: {scene_id}")
    return int(scene_id[2:])



def _prompt_hint(alias: str, character_id: str) -> str:
    return f"Use element {alias} as {character_id}."



def _constraint_hint(character_id: str, look_id: str) -> str:
    suffix = look_id.split("_LOOK_", 1)[1].rsplit("_V", 1)[0] if "_LOOK_" in look_id else look_id
    return f"Do not switch {character_id} away from {suffix} wardrobe state in this shot."



def build_report(repo_root: Path, scene_start: str, scene_end: str) -> dict[str, Any]:
    start_n = _scene_num(scene_start)
    end_n = _scene_num(scene_end)
    if start_n > end_n:
        raise ValueError("scene-start must be <= scene-end")

    scenes: list[dict[str, Any]] = []
    for n in range(start_n, end_n + 1):
        scene_id = f"SC{n:04d}"
        rows = resolve_scene_aliases(repo_root, scene_id)
        aliases = []
        for row in rows:
            aliases.append(
                {
                    "character_id": row.character_id,
                    "look_id": row.look_id,
                    "kling_element_alias": row.kling_element_alias,
                    "element_record_path": row.element_record_path,
                    "prompt_hint": _prompt_hint(row.kling_element_alias, row.character_id),
                    "constraint_hint": _constraint_hint(row.character_id, row.look_id),
                }
            )
        aliases.sort(key=lambda x: x["character_id"])
        scenes.append({"scene_id": scene_id, "aliases": aliases})

    scenes.sort(key=lambda x: x["scene_id"])

    return {
        "report_id": f"SCENE_ALIAS_HINTS_{scene_start}_{scene_end}_V001",
        "scope": {"scene_start": scene_start, "scene_end": scene_end},
        "generated_by": "codex",
        "generated_at": datetime(2026, 5, 12, 0, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "scenes": scenes,
    }



def main() -> int:
    parser = argparse.ArgumentParser(description="Export scene -> Kling alias hint report")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--scene-start", required=True, help="Start scene id (e.g. SC0001)")
    parser.add_argument("--scene-end", required=True, help="End scene id (e.g. SC0009)")
    parser.add_argument("--output", help="Optional output YAML path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    report = build_report(repo_root, args.scene_start, args.scene_end)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(yaml.safe_dump(report, sort_keys=False), encoding="utf-8")
        print(f"Wrote: {out_path.as_posix()}")
    else:
        print(yaml.safe_dump(report, sort_keys=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
