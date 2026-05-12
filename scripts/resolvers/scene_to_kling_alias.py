from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

ALIAS_RE = re.compile(r"^@C\d{2}_[A-Z0-9_]+$")


class SceneAliasResolverError(RuntimeError):
    pass


@dataclass
class SceneAliasRow:
    scene_id: str
    character_id: str
    identity_anchor_id: str
    look_id: str
    kling_element_alias: str
    kling_character_look_element_id: str
    element_record_path: str
    continuity_note: str | None



def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SceneAliasResolverError(f"failed to read YAML: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise SceneAliasResolverError(f"expected mapping YAML: {path}")
    return data



def _scene_id_num(scene_id: str) -> int:
    if not scene_id.startswith("SC") or not scene_id[2:].isdigit():
        raise SceneAliasResolverError(f"invalid scene id: {scene_id}")
    return int(scene_id[2:])



def _scene_map_path(repo_root: Path, scene_id: str) -> Path:
    return repo_root / "visual_dev" / "omni_sets" / scene_id / "scene_character_look_map.yaml"



def load_active_kling_alias_index(repo_root: Path) -> dict[str, dict[str, Any]]:
    by_look_id: dict[str, dict[str, Any]] = {}
    for path in sorted(repo_root.glob("visual_dev/elements/characters/*/kling_elements/*.yaml")):
        data = _load_yaml_mapping(path)
        status = data.get("status")
        if status in {"blocked", "rejected"}:
            continue

        look_id = data.get("look_id")
        alias = data.get("kling_element_alias")
        char_id = data.get("character_id")
        elem_id = data.get("kling_character_look_element_id")

        if not isinstance(look_id, str) or not look_id:
            raise SceneAliasResolverError(f"missing/invalid look_id in {path}")
        if not isinstance(alias, str) or not alias:
            raise SceneAliasResolverError(f"missing/invalid kling_element_alias in {path}")
        if not ALIAS_RE.match(alias):
            raise SceneAliasResolverError(
                f"invalid alias pattern for {look_id}: {alias} in {path}"
            )
        if look_id in by_look_id:
            other = by_look_id[look_id]["path"]
            raise SceneAliasResolverError(
                f"ambiguous active alias for {look_id}: {other} and {path}"
            )

        by_look_id[look_id] = {
            "data": data,
            "path": path,
            "character_id": char_id,
            "kling_element_alias": alias,
            "kling_character_look_element_id": elem_id,
        }

    return by_look_id



def resolve_scene_aliases(repo_root: Path, scene_id: str) -> list[SceneAliasRow]:
    scene_map = _scene_map_path(repo_root, scene_id)
    if not scene_map.exists():
        raise SceneAliasResolverError(f"scene map not found: {scene_map}")

    map_data = _load_yaml_mapping(scene_map)
    characters = map_data.get("characters")
    if not isinstance(characters, list):
        raise SceneAliasResolverError(f"scene map characters must be a list: {scene_map}")

    active_by_look = load_active_kling_alias_index(repo_root)

    rows: list[SceneAliasRow] = []
    for idx, entry in enumerate(characters):
        if not isinstance(entry, dict):
            raise SceneAliasResolverError(f"scene map entry must be object: {scene_map}#{idx}")
        look_id = entry.get("look_id")
        character_id = entry.get("character_id")
        identity_anchor_id = entry.get("identity_anchor_id")
        continuity_note = entry.get("continuity_note")

        if not isinstance(look_id, str) or not look_id:
            raise SceneAliasResolverError(f"missing look_id: {scene_map}#{idx}")
        if not isinstance(character_id, str) or not character_id:
            raise SceneAliasResolverError(f"missing character_id: {scene_map}#{idx}")
        if not isinstance(identity_anchor_id, str) or not identity_anchor_id:
            raise SceneAliasResolverError(f"missing identity_anchor_id: {scene_map}#{idx}")

        resolved = active_by_look.get(look_id)
        if resolved is None:
            raise SceneAliasResolverError(
                f"no active kling alias record for look_id {look_id} in {scene_id}"
            )

        resolved_char = resolved.get("character_id")
        if resolved_char != character_id:
            raise SceneAliasResolverError(
                f"character mismatch for look_id {look_id} in {scene_id}: "
                f"map has {character_id}, alias record has {resolved_char}"
            )

        rows.append(
            SceneAliasRow(
                scene_id=scene_id,
                character_id=character_id,
                identity_anchor_id=identity_anchor_id,
                look_id=look_id,
                kling_element_alias=resolved["kling_element_alias"],
                kling_character_look_element_id=resolved["kling_character_look_element_id"],
                element_record_path=resolved["path"].relative_to(repo_root).as_posix(),
                continuity_note=continuity_note if isinstance(continuity_note, str) else None,
            )
        )

    rows.sort(key=lambda row: row.character_id)
    return rows



def resolve_known_pilot_scenes(repo_root: Path) -> list[SceneAliasRow]:
    rows: list[SceneAliasRow] = []
    for scene_num in range(1, 10):
        scene_id = f"SC{scene_num:04d}"
        rows.extend(resolve_scene_aliases(repo_root, scene_id))
    return rows



def _print_rows(rows: list[SceneAliasRow]) -> None:
    if not rows:
        print("No alias rows resolved.")
        return
    current_scene = None
    for row in rows:
        if row.scene_id != current_scene:
            current_scene = row.scene_id
            print(f"{current_scene}:")
        print(
            f"  - character_id: {row.character_id}\n"
            f"    look_id: {row.look_id}\n"
            f"    kling_element_alias: {row.kling_element_alias}\n"
            f"    kling_character_look_element_id: {row.kling_character_look_element_id}\n"
            f"    element_record_path: {row.element_record_path}\n"
            f"    continuity_note: {row.continuity_note or ''}"
        )



def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve scene look IDs to Kling aliases")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--scene-id", help="Scene ID (e.g. SC0001)")
    parser.add_argument(
        "--all-known-pilot",
        action="store_true",
        help="Resolve SC0001-SC0009",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    if bool(args.scene_id) == bool(args.all_known_pilot):
        parser.error("Provide exactly one of --scene-id or --all-known-pilot")

    try:
        if args.scene_id:
            _scene_id_num(args.scene_id)
            rows = resolve_scene_aliases(repo_root, args.scene_id)
        else:
            rows = resolve_known_pilot_scenes(repo_root)
        _print_rows(rows)
    except SceneAliasResolverError as exc:
        print(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
