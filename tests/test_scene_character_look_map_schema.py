from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]


def _valid_payload() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "scene_character_look_map",
        "scene_id": "SC0001",
        "status": "draft",
        "characters": [
            {
                "character_id": "C01",
                "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
                "look_id": "C01_LOOK_HOME_MORNING_V001",
                "required": True,
                "continuity_note": "opening continuity",
            }
        ],
        "provenance": {
            "created_by": "tests",
            "created_at": "2026-05-12T00:00:00Z",
        },
    }


def _validator() -> Draft202012Validator:
    schema = json.loads(
        (REPO_ROOT / "schemas/scene_character_look_map.schema.json").read_text(
            encoding="utf-8"
        )
    )
    return Draft202012Validator(schema)


def test_scene_character_look_map_schema_valid_payload() -> None:
    assert list(_validator().iter_errors(_valid_payload())) == []


def test_scene_character_look_map_schema_rejects_bad_scene_id() -> None:
    payload = _valid_payload()
    payload["scene_id"] = "S1"
    assert list(_validator().iter_errors(payload))


def test_scene_character_look_map_schema_rejects_bad_character_look_pattern() -> None:
    payload = _valid_payload()
    payload["characters"][0]["look_id"] = "BAD"
    assert list(_validator().iter_errors(payload))


def test_scene_character_look_map_schema_requires_character_entries() -> None:
    payload = _valid_payload()
    payload["characters"] = []
    assert list(_validator().iter_errors(payload))
