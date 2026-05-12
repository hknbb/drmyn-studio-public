from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def _load_validator(repo_root: Path) -> Draft202012Validator:
    schema_path = repo_root / "schemas" / "kling_character_look_element.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _base_record() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "kling_character_look_element",
        "kling_character_look_element_id": "KLING_ELEM_C01_HOME_MORNING_V001",
        "character_id": "C01",
        "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
        "look_id": "C01_LOOK_HOME_MORNING_V001",
        "kling_element_alias": "@C01_HOME_MORNING",
        "display_name": "C01 Home Morning",
        "status": "draft",
        "element_role": "character_look_composite",
        "source_reference_chain": {
            "identity_source_ref": "pending_external://C01_MJ_SHEET_PENDING",
            "front_hero_lock_ref": "pending_external://C01_FRONT_HERO_LOCK_V001",
            "perspective_pack_id": None,
            "wardrobe_ids": ["WD001"],
        },
        "omni_usage_policy": {
            "use_as_primary_character_element": True,
            "do_not_mix_with_other_same_character_look_aliases_in_same_shot": True,
            "wardrobe_is_baked_into_element": True,
            "separate_wardrobe_element_optional": False,
        },
        "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
    }


def test_kling_character_look_element_valid_minimal_draft_passes() -> None:
    validator = _load_validator(Path.cwd())
    errors = list(validator.iter_errors(_base_record()))
    assert errors == []


def test_kling_character_look_element_invalid_alias_pattern_fails() -> None:
    validator = _load_validator(Path.cwd())
    record = _base_record()
    record["kling_element_alias"] = "@Nadia"
    errors = list(validator.iter_errors(record))
    assert any("kling_element_alias" in "/".join(str(p) for p in err.absolute_path) for err in errors)


def test_kling_character_look_element_locked_pending_external_fails() -> None:
    validator = _load_validator(Path.cwd())
    record = _base_record()
    record["status"] = "locked"
    errors = list(validator.iter_errors(record))
    assert any(
        "front_hero_lock_ref" in "/".join(str(p) for p in err.absolute_path) or "should not be valid" in err.message
        for err in errors
    )


def test_kling_character_look_element_missing_required_field_fails() -> None:
    validator = _load_validator(Path.cwd())
    record = _base_record()
    record.pop("display_name")
    errors = list(validator.iter_errors(record))
    assert any("display_name" in err.message for err in errors)

