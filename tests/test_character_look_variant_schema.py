from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]


def _valid_payload() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "character_look_variant",
        "look_id": "C01_LOOK_HOME_MORNING_V001",
        "character_id": "C01",
        "inherits_identity_anchor": "C01_IDENTITY_ANCHOR_V001",
        "status": "draft",
        "look_role": "domestic_morning",
        "wardrobe_refs": {
            "primary_wardrobe_id": "WD001",
            "supplementary_wardrobe_ids": [],
        },
        "appearance_state": {
            "fatigue_level": "nominal",
            "damage_level": "none",
            "hair_state_within_anchor": "controlled",
        },
        "continuity_scope": {
            "start_scene": "SC0001",
            "end_scene": "SC0003",
        },
        "change_reason": "opening continuity",
        "provenance": {
            "created_by": "tests",
            "created_at": "2026-05-12T00:00:00Z",
        },
    }


def _validator() -> Draft202012Validator:
    schema = json.loads(
        (REPO_ROOT / "schemas/character_look_variant.schema.json").read_text(
            encoding="utf-8"
        )
    )
    return Draft202012Validator(schema)


def test_character_look_variant_schema_valid_payload() -> None:
    assert list(_validator().iter_errors(_valid_payload())) == []


def test_character_look_variant_schema_rejects_bad_look_pattern() -> None:
    payload = _valid_payload()
    payload["look_id"] = "BAD"
    assert list(_validator().iter_errors(payload))


def test_character_look_variant_schema_rejects_bad_status_enum() -> None:
    payload = _valid_payload()
    payload["status"] = "materialized"
    assert list(_validator().iter_errors(payload))


def test_character_look_variant_schema_requires_wardrobe_refs() -> None:
    payload = _valid_payload()
    payload.pop("wardrobe_refs")
    assert list(_validator().iter_errors(payload))
