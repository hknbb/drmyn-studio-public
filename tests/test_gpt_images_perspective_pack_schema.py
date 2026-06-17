"""
PR-REF-0 tests: gpt_images_perspective_pack schema (schema_version 0.x-draft).

Covers:
- Schema file exists and is valid JSON.
- perspective_policy enum includes the additive v2 value.
- A three_view_scale_angle_v2 prompts array (front / three_quarter_medium /
  three_quarter_close) validates.
- A v2 array missing one required view is rejected.
- A v2 array with a legacy directional perspective (left_reference) is rejected.
- The legacy directional three-view array still validates (grandfather).
- All authored gpt_images_perspective_pack.yaml records pass schema.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "gpt_images_perspective_pack.schema.json"
RECORDS_GLOB = "visual_dev/elements/**/gpt_images_perspective_pack.yaml"


def _load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _prompt(prompt_id: str, perspective: str) -> dict:
    return {
        "prompt_id": prompt_id,
        "perspective": perspective,
        "prompt_text": f"Generate the {perspective} view of the element.",
        "constraints": ["preserve identity"],
        "expected_output": {"asset_type": "still", "aspect_ratio": "2:3"},
    }


def _base_record(prompts: list[dict]) -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "gpt_images_perspective_pack",
        "prompt_pack_id": "GPTIMG2_TEST_PERSPECTIVE_PACK_V001",
        "status": "draft",
        "source_reference_id": "CHATGPTIMG_ELEMENT_TEST_V001",
        "target_model": "gpt_images_2",
        "target_role": "multi_perspective_element_expander",
        "element_id": "C03",
        "element_type": "character",
        "shared_preservation_instruction": "Preserve identity; change only perspective.",
        "prompts": prompts,
        "qc_gate": {
            "minimum_score": 85,
            "all_perspectives_required": True,
            "failed_perspective_revision_only": True,
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }


_V2_PROMPTS = [
    _prompt("GPTIMG2_TEST_P01_FRONT_V001", "front_reference"),
    _prompt("GPTIMG2_TEST_P02_TQM_V001", "three_quarter_medium_reference"),
    _prompt("GPTIMG2_TEST_P03_TQC_V001", "three_quarter_close_reference"),
]

_LEGACY_DIRECTIONAL_PROMPTS = [
    _prompt("GPTIMG2_TEST_P01_FRONT_V001", "front_reference"),
    _prompt("GPTIMG2_TEST_P02_LEFT_V001", "left_reference"),
    _prompt("GPTIMG2_TEST_P03_RIGHT_V001", "right_reference"),
]


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.exists(), f"Schema not found: {SCHEMA_PATH}"


def test_schema_is_valid_json() -> None:
    schema = _load_schema()
    assert schema.get("type") == "object"


def test_perspective_policy_enum_includes_v2() -> None:
    schema = _load_schema()
    enum = schema["properties"]["perspective_policy"]["enum"]
    assert "three_view_scale_angle_v2" in enum
    # Legacy values remain for grandfathered records.
    assert "legacy_four_view" in enum
    assert "three_view_no_rear" in enum


def test_v2_scale_angle_three_view_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _base_record(copy.deepcopy(_V2_PROMPTS))
    record["perspective_policy"] = "three_view_scale_angle_v2"
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


def test_v2_missing_required_view_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    prompts = copy.deepcopy(_V2_PROMPTS)
    # Duplicate front_reference -> missing three_quarter_close_reference.
    prompts[2]["perspective"] = "front_reference"
    record = _base_record(prompts)
    record["perspective_policy"] = "three_view_scale_angle_v2"
    errors = list(validator.iter_errors(record))
    assert errors, "v2 array missing three_quarter_close_reference must fail"


def test_v2_rejects_legacy_directional_perspective() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    prompts = copy.deepcopy(_V2_PROMPTS)
    prompts[1]["perspective"] = "left_reference"
    record = _base_record(prompts)
    record["perspective_policy"] = "three_view_scale_angle_v2"
    errors = list(validator.iter_errors(record))
    assert errors, "mixing left_reference into a v2 array must fail"


def test_legacy_directional_three_view_still_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    record = _base_record(copy.deepcopy(_LEGACY_DIRECTIONAL_PROMPTS))
    record["perspective_policy"] = "three_view_no_rear"
    errors = list(validator.iter_errors(record))
    assert errors == [], "\n".join(e.message for e in errors)


def test_all_authored_records_pass_schema() -> None:
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
