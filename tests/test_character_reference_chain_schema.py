"""
PR-REF-1 tests: character_reference_chain schema (schema_version 0.x-draft).

Covers:
- Schema file exists and is valid JSON with the expected consts.
- A minimal two-stage chain record validates.
- character_id pattern is enforced (C03 ok; Nadia / c03 / CHAR03 rejected).
- Missing required stages/fields are rejected.
- Stage version enums are enforced (stage_1 v8/v8.1, stage_2 v7).
- additionalProperties=false rejects unknown / lifecycle keys.
- FORBIDDEN_LIFECYCLE_KEYS never present in schema properties.
- Any authored reference_chain.yaml records validate against this schema.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "character_reference_chain.schema.json"
RECORDS_GLOB = "visual_dev/elements/characters/**/reference_chain.yaml"

FORBIDDEN_LIFECYCLE_KEYS = {"pack_status", "canon_lock", "approved", "locked", "selected"}


def _load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _minimal_record(overrides: dict | None = None) -> dict:
    base = {
        "schema_version": "0.x-draft",
        "record_type": "character_reference_chain",
        "character_id": "C03",
        "status": "draft",
        "stage_1": {
            "model": "midjourney",
            "version": "v8.1",
            "role": "narrative_identity_reference",
            "prompt_template_ref": "templates/element_reference_prompts/character_mj_v8_narrative_identity.md",
            "output_ref": "pending_external://C03_NARRATIVE_IDENTITY_V001",
            "full_body_required": False,
        },
        "stage_2": {
            "model": "midjourney",
            "version": "v7",
            "role": "omni_reference_identity_refinement",
            "prompt_template_ref": "templates/element_reference_prompts/character_mj_v7_oref_refinement.md",
            "input_ref": "pending_external://C03_NARRATIVE_IDENTITY_V001",
            "output_ref": "pending_external://MJ_OMNI_REF_C03_V001",
            "uses_oref": True,
        },
        "handoff": {
            "to_model": "gpt_images_2",
            "source_reference_id": "MJ_OMNI_REF_C03_V001",
        },
        "provenance": {
            "created_by": "hknbb",
            "created_at": "2026-05-16T00:00:00Z",
        },
    }
    if overrides:
        base.update(overrides)
    return base


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.exists(), f"Schema not found: {SCHEMA_PATH}"


def test_schema_is_valid_json() -> None:
    schema = _load_schema()
    assert schema.get("type") == "object"


def test_schema_consts() -> None:
    schema = _load_schema()
    assert schema["properties"]["schema_version"]["const"] == "0.x-draft"
    assert schema["properties"]["record_type"]["const"] == "character_reference_chain"


def test_schema_has_no_forbidden_lifecycle_keys() -> None:
    schema = _load_schema()
    schema_props = set(schema.get("properties", {}).keys())
    intersection = schema_props & FORBIDDEN_LIFECYCLE_KEYS
    assert not intersection, (
        f"character_reference_chain schema must not contain lifecycle keys: {intersection}"
    )


def test_minimal_record_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(_minimal_record()))
    assert errors == [], "\n".join(e.message for e in errors)


def test_invalid_character_id_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    for bad_id in ("Nadia", "c03", "CHAR03", "C3", "LOC001"):
        record = _minimal_record({"character_id": bad_id})
        errors = list(validator.iter_errors(record))
        assert errors, f"character_id={bad_id!r} should fail pattern validation"


def test_missing_stage_2_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record()
    del record["stage_2"]
    errors = list(validator.iter_errors(record))
    assert errors, "Missing stage_2 must fail"


def test_stage_1_invalid_version_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record()
    record["stage_1"] = copy.deepcopy(record["stage_1"])
    record["stage_1"]["version"] = "v7"
    errors = list(validator.iter_errors(record))
    assert errors, "stage_1 version 'v7' must fail (enum is v8/v8.1)"


def test_stage_2_must_be_v7() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record()
    record["stage_2"] = copy.deepcopy(record["stage_2"])
    record["stage_2"]["version"] = "v8.1"
    errors = list(validator.iter_errors(record))
    assert errors, "stage_2 version 'v8.1' must fail (const is v7)"


def test_unknown_top_level_key_rejected() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record({"locked": True})
    errors = list(validator.iter_errors(record))
    assert errors, "additionalProperties: false must reject unknown/lifecycle keys"


def test_missing_handoff_source_reference_id_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _minimal_record()
    record["handoff"] = {"to_model": "gpt_images_2"}
    errors = list(validator.iter_errors(record))
    assert errors, "handoff without source_reference_id must fail"


def test_all_authored_reference_chain_records_pass_schema() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    for record_path in sorted(REPO_ROOT.glob(RECORDS_GLOB)):
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        assert errors == [], (
            f"{record_path.relative_to(REPO_ROOT).as_posix()} failed schema:\n"
            + "\n".join(f"  {e.json_path}: {e.message}" for e in errors)
        )
