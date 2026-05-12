from __future__ import annotations

from pathlib import Path

import yaml

from scripts.validators.validate_character_continuity import validate_character_continuity


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _anchor(*, external_ref: str = "pending_external://C01_FRONT_HERO_LOCK_V001") -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "character_identity_anchor",
        "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
        "character_id": "C01",
        "status": "draft",
        "source_reference_strategy": {
            "reference_sheet_allowed_as_identity_source": True,
            "final_hero_lock_requires_single_clean_image": True,
            "contact_sheet_layout_forbidden_as_lock": True,
        },
        "source_reference_sheet_ref": "MJ_ELEMENT_C01_HERO_LOCKED_V001",
        "front_hero_lock_ref": {"pending": True, "external_ref": external_ref},
        "fixed_identity_anchors": ["face"],
        "mutable_appearance_allowed": ["wardrobe"],
        "forbidden_drift": ["new face"],
        "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
    }


def _look(
    *,
    look_id: str = "C01_LOOK_HOME_MORNING_V001",
    start_scene: str = "SC0001",
    end_scene: str = "SC0003",
    inherits: str = "C01_IDENTITY_ANCHOR_V001",
    change_reason: str | None = "opening continuity",
) -> dict:
    payload = {
        "schema_version": "0.x-draft",
        "record_type": "character_look_variant",
        "look_id": look_id,
        "character_id": "C01",
        "inherits_identity_anchor": inherits,
        "status": "draft",
        "look_role": "domestic_morning",
        "wardrobe_refs": {"primary_wardrobe_id": "WD001", "supplementary_wardrobe_ids": []},
        "continuity_scope": {"start_scene": start_scene, "end_scene": end_scene},
        "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
    }
    if change_reason is not None:
        payload["change_reason"] = change_reason
    return payload


def _scene_map(anchor_id: str = "C01_IDENTITY_ANCHOR_V001") -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "scene_character_look_map",
        "scene_id": "SC0001",
        "status": "draft",
        "characters": [
            {
                "character_id": "C01",
                "identity_anchor_id": anchor_id,
                "look_id": "C01_LOOK_HOME_MORNING_V001",
                "required": True,
            }
        ],
        "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
    }


def _kling_look_element(
    *,
    element_id: str = "KLING_ELEM_C01_HOME_MORNING_V001",
    character_id: str = "C01",
    identity_anchor_id: str = "C01_IDENTITY_ANCHOR_V001",
    look_id: str = "C01_LOOK_HOME_MORNING_V001",
    alias: str = "@C01_HOME_MORNING",
    status: str = "draft",
    wardrobe_ids: list[str] | None = None,
    front_hero_lock_ref: str = "pending_external://C01_FRONT_HERO_LOCK_V001",
) -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "kling_character_look_element",
        "kling_character_look_element_id": element_id,
        "character_id": character_id,
        "identity_anchor_id": identity_anchor_id,
        "look_id": look_id,
        "kling_element_alias": alias,
        "display_name": "Test Element",
        "status": status,
        "element_role": "character_look_composite",
        "source_reference_chain": {
            "identity_source_ref": "pending_external://C01_MJ_SHEET_PENDING",
            "front_hero_lock_ref": front_hero_lock_ref,
            "perspective_pack_id": None,
            "wardrobe_ids": wardrobe_ids or ["WD001"],
        },
        "omni_usage_policy": {
            "use_as_primary_character_element": True,
            "do_not_mix_with_other_same_character_look_aliases_in_same_shot": True,
            "wardrobe_is_baked_into_element": True,
            "separate_wardrobe_element_optional": False,
        },
        "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
    }


def test_character_continuity_valid_minimal_passes(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/character_identity_anchor.yaml",
        _anchor(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        _look(),
    )
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/scene_character_look_map.yaml",
        _scene_map(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/wardrobe/WD001/element_view_plan.yaml",
        {"schema_version": "0.x-draft", "record_type": "element_view_plan", "element_id": "WD001", "element_type": "wardrobe", "retrofit_status": "planned", "views": [{"view_id": "main_front", "view_label": "main", "generation_pattern": "anchor_t2i", "anchor_dependency": "none", "status": "not_started"}], "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"}},
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        _kling_look_element(),
    )
    assert validate_character_continuity(tmp_path) == []


def test_character_continuity_rejects_sheet_as_lock_ref(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/character_identity_anchor.yaml",
        _anchor(external_ref="MJ_ELEMENT_C01_HERO_LOCKED_V001"),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(i.field_path == "front_hero_lock_ref.external_ref" for i in issues)


def test_character_continuity_rejects_missing_identity_anchor_in_scene_map(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/scene_character_look_map.yaml",
        _scene_map(anchor_id="C01_IDENTITY_ANCHOR_V999"),
    )
    issues = validate_character_continuity(tmp_path)
    assert any("identity_anchor_id" in i.field_path for i in issues)


def test_character_continuity_rejects_dangling_look_id_in_scene_map(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/character_identity_anchor.yaml",
        _anchor(),
    )
    payload = _scene_map()
    payload["characters"][0]["look_id"] = "C01_LOOK_MISSING_V001"
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/scene_character_look_map.yaml",
        payload,
    )
    issues = validate_character_continuity(tmp_path)
    assert any(
        i.field_path.endswith("look_id")
        and "must reference an existing character_look_variant" in i.message
        for i in issues
    )


def test_character_continuity_rejects_overlap_scope(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_A_V001.yaml",
        _look(look_id="C01_LOOK_A_V001", start_scene="SC0001", end_scene="SC0003"),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_B_V001.yaml",
        _look(look_id="C01_LOOK_B_V001", start_scene="SC0003", end_scene="SC0005", change_reason="shift"),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(i.field_path == "continuity_scope" for i in issues)


def test_character_continuity_requires_change_reason_on_contiguous_look_change(
    tmp_path: Path,
) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_A_V001.yaml",
        _look(look_id="C01_LOOK_A_V001", start_scene="SC0001", end_scene="SC0002"),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_B_V001.yaml",
        _look(look_id="C01_LOOK_B_V001", start_scene="SC0003", end_scene="SC0004", change_reason=None),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(i.field_path == "change_reason" for i in issues)


def test_character_continuity_rejects_inherits_character_mismatch(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        _look(inherits="C02_IDENTITY_ANCHOR_V001"),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(i.field_path == "inherits_identity_anchor" for i in issues)


def test_character_continuity_accepts_intake_slot_as_provisional_wardrobe_registry(
    tmp_path: Path,
) -> None:
    payload = _look()
    payload["character_id"] = "C04"
    payload["look_id"] = "C04_LOOK_OPERATIONAL_V001"
    payload["inherits_identity_anchor"] = "C04_IDENTITY_ANCHOR_V001"
    payload["wardrobe_refs"]["primary_wardrobe_id"] = "WD005"
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C04/look_variants/C04_LOOK_OPERATIONAL_V001.yaml",
        payload,
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C04/wardrobe/WD005/intake_slot.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "intake_slot",
            "slot_id": "WD005",
            "status": "draft",
            "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
        },
    )
    issues = validate_character_continuity(tmp_path)
    assert not any(
        i.record_type == "character_look_variant"
        and i.field_path == "wardrobe_refs"
        and "WD005" in i.message
        for i in issues
    )


def test_character_continuity_rejects_missing_wardrobe_when_no_plan_or_intake(
    tmp_path: Path,
) -> None:
    payload = _look()
    payload["character_id"] = "C04"
    payload["look_id"] = "C04_LOOK_OPERATIONAL_V001"
    payload["inherits_identity_anchor"] = "C04_IDENTITY_ANCHOR_V001"
    payload["wardrobe_refs"]["primary_wardrobe_id"] = "WD999"
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C04/look_variants/C04_LOOK_OPERATIONAL_V001.yaml",
        payload,
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C04/wardrobe/WD005/intake_slot.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "intake_slot",
            "slot_id": "WD005",
            "status": "draft",
            "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
        },
    )
    issues = validate_character_continuity(tmp_path)
    assert any(
        i.record_type == "character_look_variant"
        and i.field_path == "wardrobe_refs"
        and "WD999" in i.message
        and i.severity == "error"
        for i in issues
    )


def test_character_continuity_existing_element_view_plan_registry_still_passes(
    tmp_path: Path,
) -> None:
    payload = _look()
    payload["character_id"] = "C02"
    payload["look_id"] = "C02_LOOK_CORPORATE_CONTROL_V001"
    payload["inherits_identity_anchor"] = "C02_IDENTITY_ANCHOR_V001"
    payload["wardrobe_refs"]["primary_wardrobe_id"] = "WD003"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C02/look_variants/C02_LOOK_CORPORATE_CONTROL_V001.yaml",
        payload,
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C02/wardrobe/WD003/element_view_plan.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "element_view_plan",
            "element_id": "WD003",
            "element_type": "wardrobe",
            "retrofit_status": "planned",
            "views": [
                {
                    "view_id": "main_front",
                    "view_label": "main",
                    "generation_pattern": "anchor_t2i",
                    "anchor_dependency": "none",
                    "status": "not_started",
                }
            ],
            "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
        },
    )
    issues = validate_character_continuity(tmp_path)
    assert not any(
        i.record_type == "character_look_variant"
        and i.field_path == "wardrobe_refs"
        and "WD003" in i.message
        for i in issues
    )


def test_character_continuity_rejects_missing_kling_alias_for_scene_look_id(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/character_identity_anchor.yaml",
        _anchor(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        _look(),
    )
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/scene_character_look_map.yaml",
        _scene_map(),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(
        i.record_type == "scene_character_look_map"
        and "active kling_character_look_element alias" in i.message
        for i in issues
    )


def test_character_continuity_rejects_duplicate_kling_alias(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        _look(),
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        _kling_look_element(
            element_id="KLING_ELEM_C01_HOME_MORNING_V001",
            alias="@C01_HOME_MORNING",
        ),
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C02/kling_elements/KLING_ELEM_C02_CORP_V001.yaml",
        _kling_look_element(
            element_id="KLING_ELEM_C02_CORP_V001",
            character_id="C02",
            identity_anchor_id="C02_IDENTITY_ANCHOR_V001",
            look_id="C01_LOOK_HOME_MORNING_V001",
            alias="@C01_HOME_MORNING",
        ),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(
        i.record_type == "kling_character_look_element"
        and i.field_path == "kling_element_alias"
        and "globally unique" in i.message
        for i in issues
    )


def test_character_continuity_rejects_duplicate_active_character_look_element(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        _look(),
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        _kling_look_element(element_id="KLING_ELEM_C01_HOME_MORNING_V001"),
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V002.yaml",
        _kling_look_element(
            element_id="KLING_ELEM_C01_HOME_MORNING_V002",
            alias="@C01_HOME_MORNING_ALT",
        ),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(
        i.record_type == "kling_character_look_element"
        and "(character_id, look_id)" in i.message
        for i in issues
    )


def test_character_continuity_rejects_mismatched_kling_identity_anchor(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        _look(),
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        _kling_look_element(identity_anchor_id="C99_IDENTITY_ANCHOR_V001"),
    )
    issues = validate_character_continuity(tmp_path)
    assert any(
        i.record_type == "kling_character_look_element"
        and i.field_path == "identity_anchor_id"
        and "look_variant.inherits_identity_anchor" in i.message
        for i in issues
    )


def test_character_continuity_allows_blocked_duplicate_character_look_element(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        _look(),
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        _kling_look_element(element_id="KLING_ELEM_C01_HOME_MORNING_V001", alias="@C01_HOME_MORNING"),
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V002.yaml",
        _kling_look_element(
            element_id="KLING_ELEM_C01_HOME_MORNING_V002",
            alias="@C01_HOME_MORNING_ALT",
            status="blocked",
        ),
    )
    issues = validate_character_continuity(tmp_path)
    assert not any(
        i.record_type == "kling_character_look_element"
        and "(character_id, look_id)" in i.message
        for i in issues
    )
