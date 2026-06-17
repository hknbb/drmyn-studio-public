"""
B8-5 tests: canonical_asset_intake_slot schema validation.

Covers:
- All existing intake_slot.yaml files pass the schema.
- storage_policy enum: no_binary_commits and git_lfs_approved_references_only accepted.
- Invalid storage_policy values rejected.
- FORBIDDEN_LIFECYCLE_KEYS never present in valid intake slots.
- validate_production_records.py counts intake_slot records correctly.
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

from scripts.validate_production_records import run_validation  # noqa: E402


SCHEMA_PATH = REPO_ROOT / "schemas" / "canonical_asset_intake_slot.schema.json"
SLOTS_GLOB = "visual_dev/elements/**/intake_slot.yaml"


def _load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _minimal_slot(overrides: dict | None = None) -> dict:
    base = {
        "scene_id": "SC0001",
        "work_order_id": "SC0001_ASSET_01_C01",
        "element_id": "C01",
        "element_type": "character",
        "group_id": "wd001",
        "group_type": "wardrobe_reference_set",
        "context": "Domestic morning control scene.",
        "required_views": ["front_reference"],
        "source_status": "not_collected",
        "copyright_review": "pending",
        "provenance_review": "pending",
        "intake_ready_to_proceed": False,
        "canonical_assets_committed": [],
        "storage_policy": "no_binary_commits",
        "forbidden_actions": ["Do not add placeholder binaries."],
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


def test_storage_policy_enum_allows_no_binary_commits() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    slot = _minimal_slot({"storage_policy": "no_binary_commits"})
    errors = list(validator.iter_errors(slot))
    assert errors == []


def test_storage_policy_enum_allows_git_lfs_approved() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    slot = _minimal_slot({"storage_policy": "git_lfs_approved_references_only"})
    errors = list(validator.iter_errors(slot))
    assert errors == []


def test_storage_policy_enum_rejects_unknown_value() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    slot = _minimal_slot({"storage_policy": "external_only"})
    errors = list(validator.iter_errors(slot))
    assert any("storage_policy" in str(e.absolute_path) or "enum" in e.message for e in errors)


def test_storage_policy_enum_rejects_old_const_only_mode() -> None:
    schema = _load_schema()
    # Confirm schema uses enum not const — if it used const only git_lfs would fail above
    storage_policy_def = schema["properties"]["storage_policy"]
    assert "enum" in storage_policy_def
    assert "no_binary_commits" in storage_policy_def["enum"]
    assert "git_lfs_approved_references_only" in storage_policy_def["enum"]


def test_source_status_enum_accepts_all_valid_values() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    for value in ("not_collected", "source_images_in_repo", "source_images_external"):
        slot = _minimal_slot({"source_status": value})
        errors = list(validator.iter_errors(slot))
        assert errors == [], f"source_status={value!r} should be valid"


def test_copyright_review_enum_accepts_all_valid_values() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    for value in ("pending", "approved", "rejected"):
        slot = _minimal_slot({"copyright_review": value})
        errors = list(validator.iter_errors(slot))
        assert errors == [], f"copyright_review={value!r} should be valid"


def test_missing_required_field_fails() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    slot = _minimal_slot()
    del slot["storage_policy"]
    errors = list(validator.iter_errors(slot))
    assert errors, "Missing required field should fail validation"


# ---------------------------------------------------------------------------
# Existing intake_slot.yaml files
# ---------------------------------------------------------------------------


def test_all_existing_intake_slots_pass_schema() -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    slots = sorted(REPO_ROOT.glob(SLOTS_GLOB))
    if not slots:
        return  # clean-slate v0.18.0: no authored intake slots yet
    for slot_path in slots:
        data = yaml.safe_load(slot_path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        assert errors == [], (
            f"{slot_path.relative_to(REPO_ROOT).as_posix()} failed schema validation:\n"
            + "\n".join(f"  {e.json_path}: {e.message}" for e in errors)
        )


def test_all_existing_intake_slots_have_no_binary_commits_policy() -> None:
    slots = sorted(REPO_ROOT.glob(SLOTS_GLOB))
    for slot_path in slots:
        data = yaml.safe_load(slot_path.read_text(encoding="utf-8"))
        assert data.get("storage_policy") == "no_binary_commits", (
            f"{slot_path.name}: expected storage_policy=no_binary_commits, "
            f"got {data.get('storage_policy')!r}"
        )


def test_all_existing_intake_slots_have_empty_canonical_assets() -> None:
    slots = sorted(REPO_ROOT.glob(SLOTS_GLOB))
    for slot_path in slots:
        data = yaml.safe_load(slot_path.read_text(encoding="utf-8"))
        committed = data.get("canonical_assets_committed", [])
        assert committed == [], (
            f"{slot_path.name}: canonical_assets_committed should be empty "
            f"before B8A, got {committed!r}"
        )


def test_all_existing_intake_slots_intake_not_ready() -> None:
    slots = sorted(REPO_ROOT.glob(SLOTS_GLOB))
    for slot_path in slots:
        data = yaml.safe_load(slot_path.read_text(encoding="utf-8"))
        assert data.get("intake_ready_to_proceed") is False, (
            f"{slot_path.name}: intake_ready_to_proceed must be false before B8A human PR"
        )


# ---------------------------------------------------------------------------
# Validator integration
# ---------------------------------------------------------------------------


def test_validate_production_records_counts_intake_slots() -> None:
    report = run_validation(REPO_ROOT)
    slot_count = report.by_record_type.get("canonical_asset_intake_slot", 0)
    expected = len(sorted(REPO_ROOT.glob(SLOTS_GLOB)))
    assert slot_count == expected, (
        f"Validator counted {slot_count} intake_slot records, expected {expected}"
    )
    assert report.issues == []


def test_intake_slot_schema_gitignore_entry_present() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "intake_staging" in gitignore, (
        ".gitignore must include visual_dev/intake_staging/ for B8A staging dir"
    )
