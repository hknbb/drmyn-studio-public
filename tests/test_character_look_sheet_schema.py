from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_production_records import run_validation  # noqa: E402


def _copy_schemas(repo_root: Path) -> None:
    (repo_root / "schemas").mkdir(parents=True, exist_ok=True)
    for schema in (REPO_ROOT / "schemas").glob("*.schema.json"):
        (repo_root / "schemas" / schema.name).write_text(
            schema.read_text(encoding="utf-8"), encoding="utf-8"
        )


def _valid() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "character_look_sheet",
        "look_sheet_id": "LOOKSHEET_C01_HOME_EVENING_V001",
        "character_id": "C01",
        "look_id": "C01_LOOK_HOME_EVENING_V001",
        "scene_refs": ["SC0014"],
        "physical": {
            "build": "lean, upright",
            "height": "approx 170cm",
            "hair": "dark, pulled back",
            "skin_tone": "neutral",
            "physical_features": "early-30s lean face, dark eyes",
        },
        "wardrobe": {
            "primary_wardrobe_id": "WD010",
            "garment_top": "soft grey-blue domestic knit",
            "garment_bottom": "dark plain trousers",
            "footwear": "barefoot / soft house socks",
            "accessories": [],
        },
        "palette": "muted cream and pale-blue domestic neutrals",
        "status": "review",
        "provenance": {"created_by": "t", "created_at": "2026-06-03T00:00:00Z"},
    }


def _write(repo_root: Path, payload: dict, cid: str = "C01") -> None:
    path = (
        repo_root / "visual_dev" / "elements" / "characters" / cid / "look_sheets"
        / f"{payload['look_sheet_id']}.yaml"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_valid_look_sheet_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write(tmp_path, _valid())
    report = run_validation(tmp_path)
    assert report.by_record_type["character_look_sheet"] == 1
    assert [i for i in report.issues if i.record_type == "character_look_sheet"] == []


def test_missing_wardrobe_bottom_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    rec = _valid()
    del rec["wardrobe"]["garment_bottom"]
    _write(tmp_path, rec)
    report = run_validation(tmp_path)
    assert report.invalid_files >= 1
    msgs = " ".join(i.message for i in report.issues if i.record_type == "character_look_sheet")
    assert "garment_bottom" in msgs


def test_bad_look_sheet_id_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    rec = _valid()
    rec["look_sheet_id"] = "C01_looksheet"
    _write(tmp_path, rec)
    report = run_validation(tmp_path)
    assert report.invalid_files >= 1


def test_forbidden_lifecycle_key_rejected(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    rec = _valid()
    rec["canon_lock"] = True
    _write(tmp_path, rec)
    report = run_validation(tmp_path)
    msgs = " ".join(i.message for i in report.issues if i.record_type == "character_look_sheet")
    assert "Lifecycle" in msgs or "canon_lock" in msgs
