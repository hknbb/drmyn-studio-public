"""
PR-REF-3 tests: perspective_qc_report schema (schema_version 0.x-draft).

Covers:
- Schema file exists and is valid JSON.
- perspective enum includes the additive v2 scale-angle views.
- A v2 scale-angle QC report (front / three_quarter_medium / three_quarter_close)
  with optional v2 criteria fields validates.
- Legacy directional QC reports still validate (grandfather).
- Unknown perspective-score fields are rejected (additionalProperties: false).
- All authored perspective_qc records validate against this schema.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "perspective_qc_report.schema.json"
RECORDS_GLOB = "evidence/perspective_qc/*.yaml"


def _load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _score(prompt_id: str, perspective: str, extra: dict | None = None) -> dict:
    s = {
        "prompt_id": prompt_id,
        "perspective": perspective,
        "identity_preservation": 90,
        "perspective_usefulness": 90,
        "material_palette_continuity": 90,
        "production_reference_cleanliness": 90,
        "hallucination_absence": 90,
        "total_score": 90,
        "decision": "pass",
    }
    if extra:
        s.update(extra)
    return s


def _base_record(scores: list[dict]) -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "perspective_qc_report",
        "perspective_qc_id": "PQC_TEST_PERSPECTIVE_PACK_V001",
        "status": "draft",
        "scene_id": "SC0001",
        "element_id": "C03",
        "prompt_pack_id": "GPTIMG2_TEST_PERSPECTIVE_PACK_V001",
        "operator_session_ref": "OP-TEST-2026-05-16",
        "perspective_scores": scores,
        "gate": {"minimum_score": 85, "can_advance_to_kling_reference": False},
        "notes": "v2 scale-angle QC test record.",
    }


def test_schema_file_exists_and_valid_json() -> None:
    schema = _load_schema()
    assert schema.get("type") == "object"


def test_perspective_enum_includes_v2_scale_angle_views() -> None:
    schema = _load_schema()
    enum = schema["properties"]["perspective_scores"]["items"]["properties"]["perspective"]["enum"]
    assert "three_quarter_medium_reference" in enum
    assert "three_quarter_close_reference" in enum
    # Legacy values retained for grandfathered records.
    assert "left_reference" in enum
    assert "front_hero" in enum


def test_v2_scale_angle_report_with_optional_criteria_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    v2_criteria = {
        "character_description_strength": 88,
        "identity_readability": 91,
        "silhouette_readability": 89,
        "wardrobe_world_fit": 90,
        "expression_performance_readability": 87,
        "view_distinction": 92,
        "scale_distinction": 90,
        "no_directional_confusion": 95,
    }
    scores = [
        _score("GPTIMG2_TEST_P01_FRONT_V001", "front_reference", v2_criteria),
        _score("GPTIMG2_TEST_P02_TQM_V001", "three_quarter_medium_reference"),
        _score("GPTIMG2_TEST_P03_TQC_V001", "three_quarter_close_reference"),
    ]
    errors = list(validator.iter_errors(_base_record(scores)))
    assert errors == [], "\n".join(e.message for e in errors)


def test_legacy_directional_report_still_passes() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    scores = [
        _score("P01", "front_reference"),
        _score("P02", "left_reference"),
        _score("P03", "right_reference"),
    ]
    errors = list(validator.iter_errors(_base_record(scores)))
    assert errors == [], "\n".join(e.message for e in errors)


def test_unknown_score_field_rejected() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    bad = _score("P01", "front_reference", {"full_body_score": 80})
    scores = [
        bad,
        _score("P02", "three_quarter_medium_reference"),
        _score("P03", "three_quarter_close_reference"),
    ]
    errors = list(validator.iter_errors(_base_record(scores)))
    assert errors, "additionalProperties: false must reject unknown score fields"


def test_all_authored_perspective_qc_records_pass_schema() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    records = sorted(REPO_ROOT.glob(RECORDS_GLOB))
    assert records, f"No perspective_qc records found under {RECORDS_GLOB}"
    for record_path in records:
        data = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        assert errors == [], (
            f"{record_path.relative_to(REPO_ROOT).as_posix()} failed schema:\n"
            + "\n".join(f"  {e.json_path}: {e.message}" for e in errors)
        )
