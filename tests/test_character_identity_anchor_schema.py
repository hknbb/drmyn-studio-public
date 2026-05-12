from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]


def _valid_payload() -> dict:
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
        "front_hero_lock_ref": {
            "pending": True,
            "external_ref": "pending_external://C01_FRONT_HERO_LOCK_V001",
        },
        "fixed_identity_anchors": ["facial topology"],
        "mutable_appearance_allowed": ["wardrobe"],
        "forbidden_drift": ["new face"],
        "provenance": {
            "created_by": "tests",
            "created_at": "2026-05-12T00:00:00Z",
        },
    }


def _validator() -> Draft202012Validator:
    schema = json.loads(
        (REPO_ROOT / "schemas/character_identity_anchor.schema.json").read_text(
            encoding="utf-8"
        )
    )
    return Draft202012Validator(schema)


def test_character_identity_anchor_schema_valid_payload() -> None:
    errors = list(_validator().iter_errors(_valid_payload()))
    assert errors == []


def test_character_identity_anchor_schema_rejects_bad_id_pattern() -> None:
    payload = _valid_payload()
    payload["identity_anchor_id"] = "BAD_ANCHOR"
    errors = list(_validator().iter_errors(payload))
    assert errors


def test_character_identity_anchor_schema_locked_requires_non_pending_lock_ref() -> None:
    payload = _valid_payload()
    payload["status"] = "locked"
    payload["front_hero_lock_ref"]["pending"] = True
    errors = list(_validator().iter_errors(payload))
    assert errors


def test_character_identity_anchor_schema_missing_required_field_fails() -> None:
    payload = _valid_payload()
    payload.pop("source_reference_sheet_ref")
    errors = list(_validator().iter_errors(payload))
    assert errors
