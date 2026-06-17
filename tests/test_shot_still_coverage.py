"""
Tests for scripts/validators/validate_shot_still_coverage.py

Error codes validated:
  STILL_MISSING
  CONTACT_SHEET_MISSING
  CONTACT_SHEET_ORDER_MISMATCH
  ARCHIVE_FILENAME_DUPLICATE
  VISUAL_BUDGET_EXCEEDED
  PROTECTED_FLAGS_MISSING
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from scripts.validators.validate_shot_still_coverage import validate_shot_still_coverage

SCENE_ID = "SC9999"


# ------------------------------------------------------------------
# Helpers to build minimal temp repo structures
# ------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


def _manifest(
    tmpdir: Path,
    clip_id: str,
    shots: list[dict],
) -> None:
    data = {
        "schema_version": "0.x-draft",
        "record_type": "omni_clip_manifest",
        "scene_id": SCENE_ID,
        "clip_id": clip_id,
        "source_scene_beat_plan_ref": f"planning/scenes/{SCENE_ID}/scene_beat_plan.yaml",
        "source_dialogue_beats_ref": "",
        "total_duration_seconds": sum(s["duration_seconds"] for s in shots),
        "continuity_input_mode": "frame_input_active",
        "shots": shots,
        "kling_native_audio": {
            "enabled": False,
            "provider_policy": "kling_native_only",
            "external_tts_allowed": False,
            "adr_vendor_allowed": False,
        },
        "provenance": {"created_by": "test", "created_at": "2026-06-15T00:00:00Z"},
    }
    _write_yaml(
        tmpdir / "planning" / "scenes" / SCENE_ID / "manifests" / f"{clip_id}_manifest.yaml",
        data,
    )


def _still_prompt(
    tmpdir: Path,
    shot_id: str,
    clip_id: str,
    archive_filename: str,
    global_index: int = 1,
    protected_flags: list[str] | None = None,
) -> None:
    data = {
        "prompt_id": f"{SCENE_ID}__still-{global_index:02d}__v01",
        "scene_id": SCENE_ID,
        "prompt_type": "still_generation",
        "lifecycle_stage": "draft",
        "target_models": ["gpt-image-2"],
        "prompt_text": "Generate a cinematic still.",
        "generation_params": {
            "clip_id": clip_id,
            "shot_id": shot_id,
            "shot_order_index": global_index,
            "archive_filename": archive_filename,
            "input_reference_images": [],
            "protected_subject_flags": protected_flags or [],
        },
        "expected_output": {"asset_type": "still", "aspect_ratio": "16:9", "variation_count": 1},
        "status": "active",
        "canon_lock": False,
        "provenance": {"created_by": "test", "created_at": "2026-06-15T00:00:00Z"},
    }
    _write_yaml(
        tmpdir / "prompts" / "draft" / f"{SCENE_ID}__still-{global_index:02d}__v01.yaml",
        data,
    )


def _contact_sheet_prompt(
    tmpdir: Path,
    clip_id: str,
    clip_num: int,
    upload_order: list[str],
) -> None:
    data = {
        "prompt_id": f"{SCENE_ID}__contact-clip-{clip_num:02d}__v01",
        "scene_id": SCENE_ID,
        "prompt_type": "shot_design",
        "lifecycle_stage": "draft",
        "target_models": ["gpt-image-2"],
        "prompt_text": "Compose contact sheet.",
        "generation_params": {
            "clip_id": clip_id,
            "panel_count": len(upload_order),
            "operator_upload_order": upload_order,
            "contact_sheet_for_kling_default": "off",
        },
        "expected_output": {"asset_type": "image_set", "aspect_ratio": "16:9", "variation_count": 1},
        "status": "active",
        "canon_lock": False,
        "provenance": {"created_by": "test", "created_at": "2026-06-15T00:00:00Z"},
    }
    _write_yaml(
        tmpdir / "prompts" / "draft" / f"{SCENE_ID}__contact-clip-{clip_num:02d}__v01.yaml",
        data,
    )


def _kling_prompt(
    tmpdir: Path,
    clip_id: str,
    clip_num: int,
    input_mode: str = "text_only",
    visual_budget: dict | None = None,
) -> None:
    gp: dict = {
        "clip_id": clip_id,
        "total_duration_seconds": 10,
    }
    if input_mode == "anchored_i2v":
        gp["input_mode"] = "anchored_i2v"
        gp["visual_input_budget"] = visual_budget or {"total": 7, "start_frame": 1, "element_slots": 6}
    data = {
        "prompt_id": f"{SCENE_ID}__omni-kling-omni-clip-{clip_id.lower().replace('_', '-')}-safe__v01",
        "scene_id": SCENE_ID,
        "prompt_type": "omni_instruction",
        "lifecycle_stage": "draft",
        "target_models": ["kling-v3"],
        "prompt_text": "Motion direction.",
        "generation_params": gp,
        "expected_output": {"asset_type": "clip", "duration_seconds": 10},
        "status": "active",
        "canon_lock": False,
        "provenance": {"created_by": "test", "created_at": "2026-06-15T00:00:00Z"},
    }
    slug = clip_id.lower().replace("_", "-")
    _write_yaml(
        tmpdir / "prompts" / "draft" / f"{SCENE_ID}__omni-kling-{clip_num:02d}-safe__v01.yaml",
        data,
    )


def _two_clip_setup(
    tmpdir: Path,
    *,
    include_stills: bool = True,
    include_contact_sheets: bool = True,
) -> None:
    """Minimal two-clip, four-shot setup with full coverage."""
    shots_c1 = [
        {"shot_id": "SHOT_SC9999_01_A", "duration_seconds": 4, "source_beat_ids": ["B1"],
         "prompt_action": "action a", "duration_reason": "r", "required_element_ids": ["C01"]},
        {"shot_id": "SHOT_SC9999_01_B", "duration_seconds": 4, "source_beat_ids": ["B2"],
         "prompt_action": "action b", "duration_reason": "r", "required_element_ids": ["C01"]},
    ]
    shots_c2 = [
        {"shot_id": "SHOT_SC9999_02_A", "duration_seconds": 4, "source_beat_ids": ["B3"],
         "prompt_action": "action c", "duration_reason": "r", "required_element_ids": ["C01"]},
        {"shot_id": "SHOT_SC9999_02_B", "duration_seconds": 4, "source_beat_ids": ["B4"],
         "prompt_action": "action d", "duration_reason": "r", "required_element_ids": ["C01"]},
    ]
    _manifest(tmpdir, "CLIP_SC9999_01", shots_c1)
    _manifest(tmpdir, "CLIP_SC9999_02", shots_c2)

    fns = [
        f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png",
        f"{SCENE_ID}_02_clip-sc9999-01_shot-sc9999-01-b.png",
        f"{SCENE_ID}_03_clip-sc9999-02_shot-sc9999-02-a.png",
        f"{SCENE_ID}_04_clip-sc9999-02_shot-sc9999-02-b.png",
    ]
    shots_flat = [
        ("SHOT_SC9999_01_A", "CLIP_SC9999_01", fns[0], 1),
        ("SHOT_SC9999_01_B", "CLIP_SC9999_01", fns[1], 2),
        ("SHOT_SC9999_02_A", "CLIP_SC9999_02", fns[2], 3),
        ("SHOT_SC9999_02_B", "CLIP_SC9999_02", fns[3], 4),
    ]
    if include_stills:
        for sid, cid, fn, idx in shots_flat:
            _still_prompt(tmpdir, sid, cid, fn, idx)

    if include_contact_sheets:
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_01", 1, [fns[0], fns[1]])
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_02", 2, [fns[2], fns[3]])


# ------------------------------------------------------------------
# Tests: no manifests / no prompts → silent
# ------------------------------------------------------------------

def test_no_manifests_returns_empty():
    with tempfile.TemporaryDirectory() as td:
        issues = validate_shot_still_coverage(Path(td), SCENE_ID)
    assert issues == []


def test_manifests_but_no_prompts_skips():
    """If no still/contact-sheet prompts exist yet, validator is silent."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _manifest(tmpdir, "CLIP_SC9999_01", [
            {"shot_id": "SHOT_SC9999_01_A", "duration_seconds": 4, "source_beat_ids": ["B1"],
             "prompt_action": "a", "duration_reason": "r"},
        ])
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    assert issues == []


# ------------------------------------------------------------------
# Tests: full coverage → no issues
# ------------------------------------------------------------------

def test_full_coverage_no_issues():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir)
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    assert issues == [], [i.error_code + ": " + i.message for i in issues]


# ------------------------------------------------------------------
# Tests: STILL_MISSING
# ------------------------------------------------------------------

def test_still_missing_reported():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir, include_stills=False)
        # Add only the contact sheets (no stills) to trigger validation
        fns = [
            f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png",
            f"{SCENE_ID}_02_clip-sc9999-01_shot-sc9999-01-b.png",
            f"{SCENE_ID}_03_clip-sc9999-02_shot-sc9999-02-a.png",
            f"{SCENE_ID}_04_clip-sc9999-02_shot-sc9999-02-b.png",
        ]
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_01", 1, [fns[0], fns[1]])
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "STILL_MISSING" in codes


def test_still_missing_one_shot():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir, include_stills=False)
        # Only add still for first shot, not second
        _still_prompt(tmpdir, "SHOT_SC9999_01_A", "CLIP_SC9999_01",
                      f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png", 1)
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_01", 1,
                              [f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png"])
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    missing = [i for i in issues if i.error_code == "STILL_MISSING"]
    assert any(i.shot_id == "SHOT_SC9999_01_B" for i in missing)


# ------------------------------------------------------------------
# Tests: CONTACT_SHEET_MISSING
# ------------------------------------------------------------------

def test_contact_sheet_missing():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir, include_contact_sheets=False)
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "CONTACT_SHEET_MISSING" in codes


def test_contact_sheet_missing_only_one_clip():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir, include_contact_sheets=False)
        fns = [
            f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png",
            f"{SCENE_ID}_02_clip-sc9999-01_shot-sc9999-01-b.png",
        ]
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_01", 1, fns)
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    missing = [i for i in issues if i.error_code == "CONTACT_SHEET_MISSING"]
    assert len(missing) == 1
    assert missing[0].clip_id == "CLIP_SC9999_02"


# ------------------------------------------------------------------
# Tests: CONTACT_SHEET_ORDER_MISMATCH
# ------------------------------------------------------------------

def test_contact_sheet_order_mismatch():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir, include_contact_sheets=False)
        fns = [
            f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png",
            f"{SCENE_ID}_02_clip-sc9999-01_shot-sc9999-01-b.png",
        ]
        # Reversed order — should trigger mismatch
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_01", 1, [fns[1], fns[0]])
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_02", 2, [
            f"{SCENE_ID}_03_clip-sc9999-02_shot-sc9999-02-a.png",
            f"{SCENE_ID}_04_clip-sc9999-02_shot-sc9999-02-b.png",
        ])
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "CONTACT_SHEET_ORDER_MISMATCH" in codes


def test_correct_order_no_mismatch():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir)
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "CONTACT_SHEET_ORDER_MISMATCH" not in codes


# ------------------------------------------------------------------
# Tests: ARCHIVE_FILENAME_DUPLICATE
# ------------------------------------------------------------------

def test_archive_filename_duplicate():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir, include_stills=False, include_contact_sheets=False)
        same_fn = f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png"
        # Two stills with same archive filename
        _still_prompt(tmpdir, "SHOT_SC9999_01_A", "CLIP_SC9999_01", same_fn, 1)
        # Write a second still with same fn but different shot/index
        data = {
            "prompt_id": f"{SCENE_ID}__still-02__v01",
            "scene_id": SCENE_ID,
            "prompt_type": "still_generation",
            "lifecycle_stage": "draft",
            "target_models": ["gpt-image-2"],
            "prompt_text": "Generate another still.",
            "generation_params": {
                "clip_id": "CLIP_SC9999_01",
                "shot_id": "SHOT_SC9999_01_B",
                "shot_order_index": 2,
                "archive_filename": same_fn,  # duplicate!
                "input_reference_images": [],
                "protected_subject_flags": [],
            },
            "expected_output": {"asset_type": "still", "aspect_ratio": "16:9", "variation_count": 1},
            "status": "active",
            "canon_lock": False,
            "provenance": {"created_by": "test", "created_at": "2026-06-15T00:00:00Z"},
        }
        import yaml
        (tmpdir / "prompts" / "draft" / f"{SCENE_ID}__still-02__v01.yaml").write_text(
            yaml.dump(data), encoding="utf-8"
        )
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "ARCHIVE_FILENAME_DUPLICATE" in codes


# ------------------------------------------------------------------
# Tests: PROTECTED_FLAGS_MISSING
# ------------------------------------------------------------------

def test_c08_shot_without_protected_flags():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        shots_c1 = [
            {"shot_id": "SHOT_SC9999_01_A", "duration_seconds": 5, "source_beat_ids": ["B1"],
             "prompt_action": "Nadia holds Jin.", "duration_reason": "r",
             "required_element_ids": ["C01", "C08"]},  # C08 present
        ]
        _manifest(tmpdir, "CLIP_SC9999_01", shots_c1)
        fn = f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png"
        # Still without protected flags
        _still_prompt(tmpdir, "SHOT_SC9999_01_A", "CLIP_SC9999_01", fn, 1, protected_flags=[])
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_01", 1, [fn])
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "PROTECTED_FLAGS_MISSING" in codes


def test_c08_shot_with_correct_flags_passes():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        shots_c1 = [
            {"shot_id": "SHOT_SC9999_01_A", "duration_seconds": 5, "source_beat_ids": ["B1"],
             "prompt_action": "Nadia holds Jin.", "duration_reason": "r",
             "required_element_ids": ["C01", "C08"]},
        ]
        _manifest(tmpdir, "CLIP_SC9999_01", shots_c1)
        fn = f"{SCENE_ID}_01_clip-sc9999-01_shot-sc9999-01-a.png"
        _still_prompt(tmpdir, "SHOT_SC9999_01_A", "CLIP_SC9999_01", fn, 1,
                      protected_flags=["C08_NO_CONTACT", "C08_DISTRESS_OFF_FRAME"])
        _contact_sheet_prompt(tmpdir, "CLIP_SC9999_01", 1, [fn])
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "PROTECTED_FLAGS_MISSING" not in codes


def test_non_c08_shot_no_flag_required():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir)
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "PROTECTED_FLAGS_MISSING" not in codes


# ------------------------------------------------------------------
# Tests: VISUAL_BUDGET_EXCEEDED
# ------------------------------------------------------------------

def test_visual_budget_ok_not_exceeded():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir)
        _kling_prompt(tmpdir, "CLIP_SC9999_01", 1, "anchored_i2v",
                      {"total": 7, "start_frame": 1, "element_slots": 6})
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "VISUAL_BUDGET_EXCEEDED" not in codes


def test_visual_budget_exceeded():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir)
        _kling_prompt(tmpdir, "CLIP_SC9999_01", 1, "anchored_i2v",
                      {"total": 8, "start_frame": 1, "element_slots": 7})  # total=8 > 7
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "VISUAL_BUDGET_EXCEEDED" in codes


def test_text_only_kling_prompt_ignores_budget():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir)
        _kling_prompt(tmpdir, "CLIP_SC9999_01", 1, "text_only")  # no budget check
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "VISUAL_BUDGET_EXCEEDED" not in codes


def test_visual_budget_with_contact_sheet_5_slots_ok():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _two_clip_setup(tmpdir)
        _kling_prompt(tmpdir, "CLIP_SC9999_01", 1, "anchored_i2v",
                      {"total": 7, "start_frame": 1, "contact_sheet": 1, "element_slots": 5})
        issues = validate_shot_still_coverage(tmpdir, SCENE_ID)
    codes = [i.error_code for i in issues]
    assert "VISUAL_BUDGET_EXCEEDED" not in codes
