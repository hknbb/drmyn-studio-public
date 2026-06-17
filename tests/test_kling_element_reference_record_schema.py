"""
PR-REF-4 tests: kling_element_reference_record schema (schema_version 0.x-draft).

Covers:
- Schema file exists and is valid JSON.
- A v2 scale-angle gpt_images_2_perspectives mapping (front / three_quarter_medium
  / three_quarter_close) validates against the new oneOf branch.
- Legacy directional and four-view perspective mappings still validate.
- A v2 mapping missing a required view is rejected.
- Mixing a v2 key into a legacy mapping is rejected (additionalProperties: false).
- All authored kling_element_reference records validate against this schema.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "kling_element_reference_record.schema.json"
RECORDS_GLOB = "visual_dev/elements/**/kling_element_reference.yaml"


def _load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _base_record(perspectives: dict) -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "kling_element_reference_record",
        "kling_element_reference_id": "KLING_REF_TEST_V001",
        "status": "draft",
        "element_id": "C03",
        "element_type": "character",
        "source_midjourney_reference": {
            "reference_id": "MJ_OMNI_REF_C03_V001",
            "prompt_id": "MJ_PROMPT_C03_V001",
        },
        "gpt_images_2_perspectives": perspectives,
        "continuity_anchors": ["fixed hair shape"],
        "approval_gate": {
            "all_perspectives_score_85_plus": False,
            "operator_approved": False,
            "operator_session_ref": "OP-TEST-2026-05-16",
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }


_V2 = {
    "front_reference": "GPTIMG2_C03_P01_FRONT_V001",
    "three_quarter_medium_reference": "GPTIMG2_C03_P02_TQM_V001",
    "three_quarter_close_reference": "GPTIMG2_C03_P03_TQC_V001",
}

_LEGACY_DIRECTIONAL = {
    "front_reference": "GPTIMG2_C03_P01_FRONT_V001",
    "left_reference": "GPTIMG2_C03_P02_LEFT_V001",
    "right_reference": "GPTIMG2_C03_P03_RIGHT_V001",
}

_LEGACY_FOUR_VIEW = {
    "front_hero": "GPTIMG2_C03_P01_FRONT_V001",
    "three_quarter_left": "GPTIMG2_C03_P02_TQL_V001",
    "three_quarter_right": "GPTIMG2_C03_P03_TQR_V001",
    "rear_or_side": "GPTIMG2_C03_P04_REAR_V001",
}


def test_schema_file_exists_and_valid_json() -> None:
    schema = _load_schema()
    assert schema.get("type") == "object"


def test_v2_scale_angle_perspectives_pass() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(_base_record(copy.deepcopy(_V2))))
    assert errors == [], "\n".join(e.message for e in errors)


def test_legacy_directional_perspectives_still_pass() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(_base_record(copy.deepcopy(_LEGACY_DIRECTIONAL))))
    assert errors == [], "\n".join(e.message for e in errors)


def test_legacy_four_view_perspectives_still_pass() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(_base_record(copy.deepcopy(_LEGACY_FOUR_VIEW))))
    assert errors == [], "\n".join(e.message for e in errors)


def test_v2_missing_required_view_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    perspectives = copy.deepcopy(_V2)
    del perspectives["three_quarter_close_reference"]
    errors = list(validator.iter_errors(_base_record(perspectives)))
    assert errors, "v2 mapping missing three_quarter_close_reference must fail"


def test_mixed_v2_and_legacy_keys_fail() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    perspectives = copy.deepcopy(_V2)
    perspectives["left_reference"] = "GPTIMG2_C03_PX_LEFT_V001"
    errors = list(validator.iter_errors(_base_record(perspectives)))
    assert errors, "mixing a legacy directional key into a v2 mapping must fail"


def test_all_authored_kling_element_reference_records_pass_schema() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    records = sorted(REPO_ROOT.glob(RECORDS_GLOB))
    if not records:
        return  # clean-slate v0.18.0: no authored records yet
    for record_path in records:
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        assert errors == [], (
            f"{record_path.relative_to(REPO_ROOT).as_posix()} failed schema:\n"
            + "\n".join(f"  {e.json_path}: {e.message}" for e in errors)
        )
