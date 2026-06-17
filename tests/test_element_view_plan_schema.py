"""
A1 tests: element_view_plan schema validation (schema_version 0.x-draft).

Covers:
- Schema file exists and is valid JSON with required structure.
- Minimal valid records pass for each element_type.
- retrofit_status enum validated (historical, planned, active).
- generation_pattern enum validated (anchor_t2i, anchor_refine_img2img, independent_t2i).
- anchor_dependency enum validated.
- view status enum validated.
- additionalProperties=false rejects Kling-binding fields (kling_alias, speaker_mapping).
- FORBIDDEN_LIFECYCLE_KEYS never present in schema properties.
- Missing required fields are rejected.
- All B0 retrofit draft records validate against this schema.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SCHEMA_PATH = REPO_ROOT / "schemas" / "element_view_plan.schema.json"
B0_RECORDS_GLOB = "visual_dev/elements/**/element_view_plan.yaml"

FORBIDDEN_LIFECYCLE_KEYS = {"pack_status", "canon_lock", "approved", "locked", "selected"}


def _load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _minimal_record(overrides: dict | None = None) -> dict:
    base = {
        "schema_version": "0.x-draft",
        "record_type": "element_view_plan",
        "element_id": "C01",
        "element_type": "character",
        "retrofit_status": "historical",
        "views": [
            {
                "view_id": "main_front",
                "view_label": "Front reference",
                "generation_pattern": "independent_t2i",
                "anchor_dependency": "none",
                "status": "complete",
            }
        ],
        "provenance": {
            "created_by": "hknbb",
            "created_at": "2026-05-08T00:00:00Z",
        },
    }
    if overrides:
        base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Schema structural tests
# ---------------------------------------------------------------------------


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.exists(), f"Schema not found: {SCHEMA_PATH}"


def test_schema_is_valid_json() -> None:
    schema = _load_schema()
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"


def test_schema_version_const_is_draft() -> None:
    schema = _load_schema()
    assert schema["properties"]["schema_version"]["const"] == "0.x-draft"


def test_schema_record_type_const() -> None:
    schema = _load_schema()
    assert schema["properties"]["record_type"]["const"] == "element_view_plan"


def test_schema_has_no_forbidden_lifecycle_keys() -> None:
    schema = _load_schema()
    schema_props = set(schema.get("properties", {}).keys())
    intersection = schema_props & FORBIDDEN_LIFECYCLE_KEYS
    assert not intersection, (
        f"element_view_plan schema must not contain lifecycle keys: {intersection}"
    )


def test_schema_rejects_kling_binding_fields() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"kling_alias": "@Nadia"})
    errors = list(validator.iter_errors(record))
    assert errors, "kling_alias must be rejected by additionalProperties: false"


def test_schema_rejects_speaker_mapping() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"speaker_mapping": {"C01": "@Nadia"}})
    errors = list(validator.iter_errors(record))
    assert errors, "speaker_mapping must be rejected (belongs in element_binding schema)"


# ---------------------------------------------------------------------------
# Valid record tests
# ---------------------------------------------------------------------------


def test_minimal_character_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(_minimal_record()))
    assert errors == [], "\n".join(e.message for e in errors)


def test_minimal_wardrobe_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "element_id": "WD001",
        "element_type": "wardrobe",
        "element_subtype": "WD001",
    })
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


def test_minimal_prop_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "element_id": "PROP003",
        "element_type": "prop",
    })
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


def test_minimal_location_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "element_id": "LOC001",
        "element_type": "location",
        "element_subtype": "kitchen_passage",
    })
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


def test_planned_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "retrofit_status": "planned",
        "views": [
            {
                "view_id": "main_front",
                "view_label": "Front reference",
                "generation_pattern": "anchor_t2i",
                "anchor_dependency": "none",
                "status": "not_started",
            }
        ],
    })
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


def test_active_anchor_refine_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "retrofit_status": "active",
        "anchor_view": "main_front",
        "views": [
            {
                "view_id": "main_front",
                "view_label": "Front reference (anchor)",
                "generation_pattern": "anchor_t2i",
                "anchor_dependency": "none",
                "status": "complete",
                "canonical_asset_path": "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_front.png",
            },
            {
                "view_id": "three_quarter_left",
                "view_label": "Three-quarter left",
                "generation_pattern": "anchor_refine_img2img",
                "anchor_dependency": "required",
                "status": "not_started",
                "model_adapter_target": "nano_banana_best_available",
            },
        ],
    })
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


def test_full_four_view_historical_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = {
        "schema_version": "0.x-draft",
        "record_type": "element_view_plan",
        "element_id": "WD001",
        "element_type": "wardrobe",
        "element_subtype": "WD001",
        "element_context": "Early-morning domestic control (SC0001, SC0003).",
        "retrofit_status": "historical",
        "anchor_view": "front_reference",
        "views": [
            {
                "view_id": "front_reference",
                "view_label": "Front reference (anchor)",
                "generation_pattern": "independent_t2i",
                "anchor_dependency": "none",
                "model_adapter_target": "midjourney_image_best_available",
                "status": "complete",
                "canonical_asset_path": "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_front.png",
                "generation_notes": "Midjourney v8.1 output. Selected as front_reference (Path B, 2026-05-07).",
            },
            {
                "view_id": "three_quarter_reference",
                "view_label": "Three-quarter reference",
                "generation_pattern": "independent_t2i",
                "anchor_dependency": "none",
                "model_adapter_target": "chatgpt_image_best_available",
                "status": "complete",
                "canonical_asset_path": "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_three_quarter.png",
            },
            {
                "view_id": "back_reference",
                "view_label": "Back reference",
                "generation_pattern": "independent_t2i",
                "anchor_dependency": "none",
                "model_adapter_target": "chatgpt_image_best_available",
                "status": "complete",
                "canonical_asset_path": "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_back.png",
            },
            {
                "view_id": "context_reference",
                "view_label": "Context reference (in-setting)",
                "generation_pattern": "independent_t2i",
                "anchor_dependency": "none",
                "model_adapter_target": "chatgpt_image_best_available",
                "status": "complete",
                "canonical_asset_path": "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_context.png",
            },
        ],
        "original_locked_at": "2026-05-07T19:11:00Z",
        "original_method_summary": "1 Midjourney + 3 ChatGPT Image, all independent_t2i. No anchor-then-refine applied.",
        "evidence_refs": [
            "visual_dev/elements/characters/C01/wardrobe/WD001/intake_slot.yaml",
            "visual_dev/elements/characters/C01/image_selection.yaml",
        ],
        "provenance": {
            "created_by": "hknbb",
            "created_at": "2026-05-08T00:00:00Z",
        },
    }
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


# ---------------------------------------------------------------------------
# Invalid record tests
# ---------------------------------------------------------------------------


def test_missing_schema_version_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record()
    del record["schema_version"]
    errors = list(validator.iter_errors(record))
    assert errors, "Missing schema_version must fail"


def test_wrong_schema_version_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"schema_version": "1.0"})
    errors = list(validator.iter_errors(record))
    assert errors, "schema_version '1.0' must fail (const is 0.x-draft)"


def test_missing_record_type_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record()
    del record["record_type"]
    errors = list(validator.iter_errors(record))
    assert errors, "Missing record_type must fail"


def test_wrong_record_type_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"record_type": "element_binding"})
    errors = list(validator.iter_errors(record))
    assert errors, "Incorrect record_type must fail"


def test_invalid_element_id_pattern_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    for bad_id in ("Nadia", "c01", "CHAR01", "LOC1"):
        record = _minimal_record({"element_id": bad_id})
        errors = list(validator.iter_errors(record))
        assert errors, f"element_id={bad_id!r} should fail pattern validation"


def test_invalid_element_type_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"element_type": "scene"})
    errors = list(validator.iter_errors(record))
    assert errors, "element_type 'scene' must fail"


def test_invalid_retrofit_status_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"retrofit_status": "complete"})
    errors = list(validator.iter_errors(record))
    assert errors, "retrofit_status 'complete' must fail"


def test_empty_views_array_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"views": []})
    errors = list(validator.iter_errors(record))
    assert errors, "Empty views array must fail (minItems: 1)"


def test_invalid_generation_pattern_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "views": [
            {
                "view_id": "main_front",
                "view_label": "Front",
                "generation_pattern": "legacy_t2i",
                "anchor_dependency": "none",
                "status": "complete",
            }
        ]
    })
    errors = list(validator.iter_errors(record))
    assert errors, "generation_pattern 'legacy_t2i' must fail"


def test_invalid_view_status_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "views": [
            {
                "view_id": "main_front",
                "view_label": "Front",
                "generation_pattern": "independent_t2i",
                "anchor_dependency": "none",
                "status": "done",
            }
        ]
    })
    errors = list(validator.iter_errors(record))
    assert errors, "status 'done' must fail"


def test_view_with_hardcoded_provider_version_in_model_adapter_target_is_not_blocked_by_schema() -> None:
    """Schema does not enforce no-hardcoding; that's a Python/CI grep-test concern.
    This test documents that the schema allows any string in model_adapter_target —
    the hardcoding policy is enforced by the CI allowlist check, not JSON Schema.
    """
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({
        "views": [
            {
                "view_id": "main_front",
                "view_label": "Front",
                "generation_pattern": "independent_t2i",
                "anchor_dependency": "none",
                "status": "complete",
                "model_adapter_target": "midjourney_image_best_available",
            }
        ]
    })
    errors = list(validator.iter_errors(record))
    assert errors == [], "Valid stable internal ID must pass schema"


# ---------------------------------------------------------------------------
# B0 retrofit record validation
# ---------------------------------------------------------------------------


def test_all_b0_element_view_plan_records_pass_schema() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    records = sorted(REPO_ROOT.glob(B0_RECORDS_GLOB))
    if not records:
        return  # clean-slate v0.18.0: no authored records yet
    for record_path in records:
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        assert errors == [], (
            f"{record_path.relative_to(REPO_ROOT).as_posix()} failed schema validation:\n"
            + "\n".join(f"  {e.json_path}: {e.message}" for e in errors)
        )


def test_b0_records_contain_no_forbidden_lifecycle_keys() -> None:
    records = sorted(REPO_ROOT.glob(B0_RECORDS_GLOB))
    for record_path in records:
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        found = set(data.keys()) & FORBIDDEN_LIFECYCLE_KEYS
        assert not found, (
            f"{record_path.name} contains forbidden lifecycle keys: {found}"
        )


def test_b0_historical_records_have_original_locked_at() -> None:
    records = sorted(REPO_ROOT.glob(B0_RECORDS_GLOB))
    for record_path in records:
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        if data.get("retrofit_status") == "historical":
            assert data.get("original_locked_at") is not None, (
                f"{record_path.name}: historical record must have original_locked_at"
            )


def test_b0_historical_records_have_evidence_refs() -> None:
    records = sorted(REPO_ROOT.glob(B0_RECORDS_GLOB))
    for record_path in records:
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        if data.get("retrofit_status") == "historical":
            refs = data.get("evidence_refs", [])
            assert refs, (
                f"{record_path.name}: historical record must have at least one evidence_ref"
            )


def test_b0_records_have_correct_schema_version() -> None:
    records = sorted(REPO_ROOT.glob(B0_RECORDS_GLOB))
    for record_path in records:
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        assert data.get("schema_version") == "0.x-draft", (
            f"{record_path.name}: schema_version must be '0.x-draft'"
        )
