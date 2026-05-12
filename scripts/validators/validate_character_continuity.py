from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


@dataclass
class CharacterContinuityIssue:
    file: str
    record_type: str
    field_path: str
    message: str
    severity: str = "error"


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _scene_num(scene_id: str) -> int | None:
    if not isinstance(scene_id, str) or not scene_id.startswith("SC"):
        return None
    digits = scene_id[2:]
    if not digits.isdigit():
        return None
    return int(digits)


def validate_character_continuity(repo_root: Path) -> list[CharacterContinuityIssue]:
    issues: list[CharacterContinuityIssue] = []
    kling_alias_re = re.compile(r"^@C\d{2}_[A-Z0-9_]+$")

    anchor_paths = sorted(
        repo_root.glob("visual_dev/elements/characters/*/character_identity_anchor.yaml")
    )
    look_paths = sorted(
        repo_root.glob("visual_dev/elements/characters/*/look_variants/*.yaml")
    )
    map_paths = sorted(repo_root.glob("visual_dev/omni_sets/SC*/scene_character_look_map.yaml"))
    kling_look_element_paths = sorted(
        repo_root.glob("visual_dev/elements/characters/*/kling_elements/*.yaml")
    )
    wardrobe_plan_paths = list(
        repo_root.glob("visual_dev/elements/characters/*/wardrobe/WD*/element_view_plan.yaml")
    )
    wardrobe_intake_paths = list(
        repo_root.glob("visual_dev/elements/characters/*/wardrobe/WD*/intake_slot.yaml")
    )
    wardrobe_registry_available = len(wardrobe_plan_paths) > 0 or len(wardrobe_intake_paths) > 0
    known_wardrobe_ids = {p.parent.name for p in wardrobe_plan_paths}
    known_wardrobe_ids.update({p.parent.name for p in wardrobe_intake_paths})

    anchor_by_id: dict[str, dict[str, Any]] = {}
    for path in anchor_paths:
        data = _load_yaml_mapping(path)
        if not data:
            continue
        anchor_id = data.get("identity_anchor_id")
        if isinstance(anchor_id, str) and anchor_id:
            anchor_by_id[anchor_id] = {"data": data, "path": path}
            source_ref = data.get("source_reference_sheet_ref")
            lock_ref = data.get("front_hero_lock_ref")
            if isinstance(lock_ref, dict):
                external_ref = lock_ref.get("external_ref")
                if isinstance(source_ref, str) and isinstance(external_ref, str):
                    if source_ref == external_ref:
                        issues.append(
                            CharacterContinuityIssue(
                                file=path.relative_to(repo_root).as_posix(),
                                record_type="character_identity_anchor",
                                field_path="front_hero_lock_ref.external_ref",
                                message=(
                                    "front_hero_lock_ref.external_ref must not equal "
                                    "source_reference_sheet_ref"
                                ),
                            )
                        )

    look_by_id: dict[str, dict[str, Any]] = {}
    looks_by_character: dict[str, list[dict[str, Any]]] = {}
    for path in look_paths:
        data = _load_yaml_mapping(path)
        if not data:
            continue
        look_id = data.get("look_id")
        character_id = data.get("character_id")
        anchor_id = data.get("inherits_identity_anchor")
        if isinstance(look_id, str) and look_id:
            look_by_id[look_id] = {"data": data, "path": path}
        if isinstance(character_id, str):
            looks_by_character.setdefault(character_id, []).append({"data": data, "path": path})

        # HARD: look variant inherits same character
        if isinstance(anchor_id, str) and isinstance(character_id, str):
            anchor_char = anchor_id.split("_", 1)[0] if "_" in anchor_id else ""
            if anchor_char != character_id:
                issues.append(
                    CharacterContinuityIssue(
                        file=path.relative_to(repo_root).as_posix(),
                        record_type="character_look_variant",
                        field_path="inherits_identity_anchor",
                        message="inherits_identity_anchor must match look variant character_id",
                    )
                )

    kling_look_elements: list[dict[str, Any]] = []
    active_kling_by_look_id: dict[str, list[dict[str, Any]]] = {}
    active_char_look_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    kling_alias_seen: dict[str, dict[str, Any]] = {}

    for path in kling_look_element_paths:
        data = _load_yaml_mapping(path)
        if not data:
            continue
        rel = path.relative_to(repo_root).as_posix()
        kling_look_elements.append({"data": data, "path": path})

        look_id = data.get("look_id")
        character_id = data.get("character_id")
        identity_anchor_id = data.get("identity_anchor_id")
        alias = data.get("kling_element_alias")
        status = data.get("status")
        source_chain = data.get("source_reference_chain")

        if isinstance(alias, str) and alias:
            if not kling_alias_re.match(alias):
                issues.append(
                    CharacterContinuityIssue(
                        file=rel,
                        record_type="kling_character_look_element",
                        field_path="kling_element_alias",
                        message="kling_element_alias must match ^@C\\d{2}_[A-Z0-9_]+$",
                    )
                )
            prev = kling_alias_seen.get(alias)
            if prev is not None:
                issues.append(
                    CharacterContinuityIssue(
                        file=rel,
                        record_type="kling_character_look_element",
                        field_path="kling_element_alias",
                        message="kling_element_alias must be globally unique",
                    )
                )
            else:
                kling_alias_seen[alias] = {"path": path}

        if status == "locked" and isinstance(source_chain, dict):
            lock_ref = source_chain.get("front_hero_lock_ref")
            if isinstance(lock_ref, str) and lock_ref.startswith("pending_external://"):
                issues.append(
                    CharacterContinuityIssue(
                        file=rel,
                        record_type="kling_character_look_element",
                        field_path="source_reference_chain.front_hero_lock_ref",
                        message=(
                            "locked kling_character_look_element cannot use pending_external:// "
                            "front_hero_lock_ref"
                        ),
                    )
                )

        look_entry = look_by_id.get(look_id) if isinstance(look_id, str) else None
        if isinstance(look_id, str) and look_id and look_entry is None:
            issues.append(
                CharacterContinuityIssue(
                    file=rel,
                    record_type="kling_character_look_element",
                    field_path="look_id",
                    message="look_id must reference an existing character_look_variant",
                )
            )

        if (
            isinstance(look_id, str)
            and isinstance(character_id, str)
            and not look_id.startswith(f"{character_id}_LOOK_")
        ):
            issues.append(
                CharacterContinuityIssue(
                    file=rel,
                    record_type="kling_character_look_element",
                    field_path="character_id",
                    message="character_id must match look_id prefix",
                )
            )

        if look_entry and isinstance(identity_anchor_id, str):
            expected_anchor = look_entry["data"].get("inherits_identity_anchor")
            if expected_anchor != identity_anchor_id:
                issues.append(
                    CharacterContinuityIssue(
                        file=rel,
                        record_type="kling_character_look_element",
                        field_path="identity_anchor_id",
                        message="identity_anchor_id must match look_variant.inherits_identity_anchor",
                    )
                )

        if isinstance(source_chain, dict):
            wardrobe_ids = source_chain.get("wardrobe_ids")
            if isinstance(wardrobe_ids, list):
                for idx, wd in enumerate(wardrobe_ids):
                    if isinstance(wd, str) and wd in known_wardrobe_ids:
                        continue
                    severity = "error" if wardrobe_registry_available else "warning"
                    issues.append(
                        CharacterContinuityIssue(
                            file=rel,
                            record_type="kling_character_look_element",
                            field_path=f"source_reference_chain.wardrobe_ids.{idx}",
                            message=f"wardrobe reference not found in registry: {wd}",
                            severity=severity,
                        )
                    )

        if status not in {"blocked", "rejected"}:
            if isinstance(look_id, str):
                active_kling_by_look_id.setdefault(look_id, []).append({"path": path, "data": data})
            if isinstance(character_id, str) and isinstance(look_id, str):
                active_char_look_pair.setdefault((character_id, look_id), []).append(
                    {"path": path, "data": data}
                )

    # HARD: look_id continuity overlap and change_reason requirement
    for character_id, look_entries in looks_by_character.items():
        parsed: list[dict[str, Any]] = []
        for item in look_entries:
            data = item["data"]
            path = item["path"]
            scope = data.get("continuity_scope")
            if not isinstance(scope, dict):
                continue
            start_scene = scope.get("start_scene")
            end_scene = scope.get("end_scene")
            start_num = _scene_num(start_scene)
            end_num = _scene_num(end_scene)
            if start_num is None or end_num is None:
                continue
            parsed.append(
                {
                    "path": path,
                    "data": data,
                    "start_scene": start_scene,
                    "end_scene": end_scene,
                    "start_num": start_num,
                    "end_num": end_num,
                }
            )

        parsed.sort(key=lambda x: x["start_num"])
        for idx in range(len(parsed)):
            a = parsed[idx]
            for jdx in range(idx + 1, len(parsed)):
                b = parsed[jdx]
                if b["start_num"] > a["end_num"]:
                    break
                # overlap
                if b["start_num"] <= a["end_num"] and b["end_num"] >= a["start_num"]:
                    issues.append(
                        CharacterContinuityIssue(
                            file=b["path"].relative_to(repo_root).as_posix(),
                            record_type="character_look_variant",
                            field_path="continuity_scope",
                            message=(
                                "continuity_scope overlaps another look variant for the same character"
                            ),
                        )
                    )

        for idx in range(1, len(parsed)):
            prev = parsed[idx - 1]
            curr = parsed[idx]
            prev_look = prev["data"].get("look_id")
            curr_look = curr["data"].get("look_id")
            if prev_look != curr_look:
                if prev["end_num"] + 1 == curr["start_num"]:
                    change_reason = curr["data"].get("change_reason")
                    if not isinstance(change_reason, str) or not change_reason.strip():
                        issues.append(
                            CharacterContinuityIssue(
                                file=curr["path"].relative_to(repo_root).as_posix(),
                                record_type="character_look_variant",
                                field_path="change_reason",
                                message="change_reason is required when look changes across contiguous scope",
                            )
                        )

    for (character_id, look_id), entries in active_char_look_pair.items():
        if len(entries) > 1:
            for entry in entries[1:]:
                issues.append(
                    CharacterContinuityIssue(
                        file=entry["path"].relative_to(repo_root).as_posix(),
                        record_type="kling_character_look_element",
                        field_path="status",
                        message=(
                            "only one active kling_character_look_element is allowed per "
                            "(character_id, look_id)"
                        ),
                    )
                )

    # scene map checks
    for path in map_paths:
        data = _load_yaml_mapping(path)
        if not data:
            continue
        characters = data.get("characters")
        if not isinstance(characters, list):
            continue
        for idx, entry in enumerate(characters):
            if not isinstance(entry, dict):
                continue
            anchor_id = entry.get("identity_anchor_id")
            look_id = entry.get("look_id")
            char_id = entry.get("character_id")
            # HARD: map anchor exists
            if isinstance(anchor_id, str) and anchor_id and anchor_id not in anchor_by_id:
                issues.append(
                    CharacterContinuityIssue(
                        file=path.relative_to(repo_root).as_posix(),
                        record_type="scene_character_look_map",
                        field_path=f"characters.{idx}.identity_anchor_id",
                        message="identity_anchor_id must reference an existing character_identity_anchor",
                    )
                )
            look_entry = look_by_id.get(look_id) if isinstance(look_id, str) else None
            if isinstance(look_id, str) and look_id and look_entry is None:
                issues.append(
                    CharacterContinuityIssue(
                        file=path.relative_to(repo_root).as_posix(),
                        record_type="scene_character_look_map",
                        field_path=f"characters.{idx}.look_id",
                        message="look_id must reference an existing character_look_variant",
                    )
                )
            if look_entry and isinstance(char_id, str):
                if look_entry["data"].get("character_id") != char_id:
                    issues.append(
                        CharacterContinuityIssue(
                            file=path.relative_to(repo_root).as_posix(),
                            record_type="scene_character_look_map",
                            field_path=f"characters.{idx}.look_id",
                        message="look_id must match scene map character_id",
                    )
                )
            if isinstance(look_id, str) and look_id and look_id not in active_kling_by_look_id:
                issues.append(
                    CharacterContinuityIssue(
                        file=path.relative_to(repo_root).as_posix(),
                        record_type="scene_character_look_map",
                        field_path=f"characters.{idx}.look_id",
                        message=(
                            "look_id must resolve to an active kling_character_look_element alias"
                        ),
                    )
                )

    # SOFT/HARD wardrobe existence gate
    # Accept both full wardrobe plans and provisional intake slots as registry entries.
    for path in look_paths:
        data = _load_yaml_mapping(path)
        if not data:
            continue
        refs = data.get("wardrobe_refs")
        if not isinstance(refs, dict):
            continue
        wardrobe_ids: list[str] = []
        primary = refs.get("primary_wardrobe_id")
        if isinstance(primary, str):
            wardrobe_ids.append(primary)
        supplementary = refs.get("supplementary_wardrobe_ids")
        if isinstance(supplementary, list):
            for wd in supplementary:
                if isinstance(wd, str):
                    wardrobe_ids.append(wd)
        for wd in wardrobe_ids:
            if wd in known_wardrobe_ids:
                continue
            severity = "error" if wardrobe_registry_available else "warning"
            issues.append(
                CharacterContinuityIssue(
                    file=path.relative_to(repo_root).as_posix(),
                    record_type="character_look_variant",
                    field_path="wardrobe_refs",
                    message=f"wardrobe reference not found in registry: {wd}",
                    severity=severity,
                )
            )

    # SOFT/HARD: FRONT HERO LOCK -> perspective pack advance.
    # If a pack does not expose an advance field, this check is skipped (soft).
    pack_paths = sorted(repo_root.glob("visual_dev/elements/**/gpt_images_perspective_pack.yaml"))
    anchor_by_character: dict[str, dict[str, Any]] = {}
    for anchor_id, anchor_entry in anchor_by_id.items():
        anchor_data = anchor_entry.get("data", {})
        character_id = anchor_data.get("character_id")
        if isinstance(character_id, str):
            anchor_by_character[character_id] = anchor_entry

    for path in pack_paths:
        data = _load_yaml_mapping(path)
        if not data:
            continue
        advance_flag = None
        if isinstance(data.get("can_advance_to_kling_reference"), bool):
            advance_flag = data.get("can_advance_to_kling_reference")
        elif isinstance(data.get("qc_gate"), dict) and isinstance(
            data.get("qc_gate", {}).get("can_advance_to_kling_reference"), bool
        ):
            advance_flag = data.get("qc_gate", {}).get("can_advance_to_kling_reference")
        if advance_flag is not True:
            continue
        element_id = data.get("element_id")
        anchor_entry = anchor_by_character.get(element_id) if isinstance(element_id, str) else None
        if not anchor_entry:
            continue
        anchor_data = anchor_entry.get("data", {})
        lock_ref = anchor_data.get("front_hero_lock_ref")
        if (
            anchor_data.get("status") != "locked"
            or not isinstance(lock_ref, dict)
            or lock_ref.get("pending") is not False
        ):
            issues.append(
                CharacterContinuityIssue(
                    file=path.relative_to(repo_root).as_posix(),
                    record_type="gpt_images_perspective_pack",
                    field_path="can_advance_to_kling_reference",
                    message=(
                        "perspective pack cannot advance before identity anchor is locked and "
                        "front_hero_lock_ref.pending is false"
                    ),
                )
            )

    return issues
