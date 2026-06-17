"""
Tests for scripts/agents/shot_still_planner.py and contact_sheet_planner.py

Validates:
1. ShotStillPlanner generates 22 prompt records for SC0014
2. Each record has prompt_type: still_generation, asset_type: still
3. prompt_id matches pattern SC0014__still-NN__v01
4. generation_params contains clip_id, shot_id, archive_filename, input_reference_images
5. C08 shots carry protected_subject_flags
6. ContactSheetPlanner generates 8 prompt records for SC0014
7. Each contact sheet record has prompt_type: shot_design, asset_type: image_set
8. operator_upload_order is ordered list of archive filenames
9. prompt_id matches pattern SC0014__contact-clip-NN__v01
10. panel_count matches actual shots in each clip
11. Kling contact_sheet default is off in generation_params
12. No canonical IDs (C01, LOC001, etc.) leak into prompt_text
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.agents.shot_still_planner import ShotStillPlanner
from scripts.agents.contact_sheet_planner import ContactSheetPlanner

REPO_ROOT = Path(__file__).parent.parent.parent
PROMPT_ID_STILL = re.compile(r"^SC\d{4}__still-\d{2}__v\d{2}$")
PROMPT_ID_CONTACT = re.compile(r"^SC\d{4}__contact-clip-\d{2}__v\d{2}$")
CANONICAL_ID_PATTERN = re.compile(r"\b(C\d{2}|LOC\d{3}|PROP\d{3}|WD\d{3}|SC\d{4})\b")


@pytest.fixture(scope="module")
def still_records():
    planner = ShotStillPlanner(repo_root=REPO_ROOT, scene_id="SC0014")
    return planner.plan()


@pytest.fixture(scope="module")
def contact_records():
    planner = ContactSheetPlanner(repo_root=REPO_ROOT, scene_id="SC0014")
    return planner.plan()


# -------------------------------------------------------------------------
# ShotStillPlanner
# -------------------------------------------------------------------------

def test_still_planner_count(still_records):
    assert len(still_records) == 22


def test_still_planner_prompt_type(still_records):
    for r in still_records:
        assert r["prompt_type"] == "still_generation"


def test_still_planner_asset_type(still_records):
    for r in still_records:
        assert r["expected_output"]["asset_type"] == "still"


def test_still_planner_prompt_id_pattern(still_records):
    for r in still_records:
        assert PROMPT_ID_STILL.match(r["prompt_id"]), (
            f"Unexpected prompt_id: {r['prompt_id']}"
        )


def test_still_planner_prompt_ids_unique(still_records):
    ids = [r["prompt_id"] for r in still_records]
    assert len(ids) == len(set(ids))


def test_still_planner_generation_params_clip_shot(still_records):
    for r in still_records:
        gp = r["generation_params"]
        assert "clip_id" in gp
        assert "shot_id" in gp
        assert "archive_filename" in gp
        assert "shot_order_index" in gp


def test_still_planner_archive_filename_matches_index(still_records):
    for r in still_records:
        gp = r["generation_params"]
        idx = gp["shot_order_index"]
        fn = gp["archive_filename"]
        expected_prefix = f"SC0014_{idx:02d}_"
        assert fn.startswith(expected_prefix), (
            f"archive_filename {fn!r} doesn't start with {expected_prefix!r}"
        )


def test_still_planner_c08_shots_have_protected_flags(still_records):
    c08_records = [
        r for r in still_records
        if r["generation_params"].get("protected_subject_flags")
    ]
    assert c08_records, "Expected some records with protected_subject_flags"
    for r in c08_records:
        flags = r["generation_params"]["protected_subject_flags"]
        assert "C08_NO_CONTACT" in flags
        assert "C08_DISTRESS_OFF_FRAME" in flags


def test_still_planner_prompt_text_non_empty(still_records):
    for r in still_records:
        assert len(r["prompt_text"].strip()) > 50


def test_still_planner_no_canonical_ids_in_prompt_text(still_records):
    for r in still_records:
        text = r["prompt_text"]
        matches = CANONICAL_ID_PATTERN.findall(text)
        assert not matches, (
            f"Canonical IDs {matches} found in prompt_text for {r['prompt_id']}"
        )


def test_still_planner_provider_is_openai(still_records):
    for r in still_records:
        assert r["generation_params"]["provider"] == "openai"


def test_still_planner_target_model_is_gpt_image_2(still_records):
    for r in still_records:
        assert "gpt-image-2" in r["target_models"]


def test_still_planner_input_reference_images_present(still_records):
    records_with_refs = [
        r for r in still_records
        if r["generation_params"]["input_reference_images"]
    ]
    assert records_with_refs, "Expected at least some records with input_reference_images"


# -------------------------------------------------------------------------
# ContactSheetPlanner
# -------------------------------------------------------------------------

def test_contact_planner_count(contact_records):
    assert len(contact_records) == 8


def test_contact_planner_prompt_type(contact_records):
    for r in contact_records:
        assert r["prompt_type"] == "shot_design"


def test_contact_planner_asset_type(contact_records):
    for r in contact_records:
        assert r["expected_output"]["asset_type"] == "image_set"


def test_contact_planner_prompt_id_pattern(contact_records):
    for r in contact_records:
        assert PROMPT_ID_CONTACT.match(r["prompt_id"]), (
            f"Unexpected prompt_id: {r['prompt_id']}"
        )


def test_contact_planner_prompt_ids_unique(contact_records):
    ids = [r["prompt_id"] for r in contact_records]
    assert len(ids) == len(set(ids))


def test_contact_planner_has_operator_upload_order(contact_records):
    for r in contact_records:
        gp = r["generation_params"]
        assert "operator_upload_order" in gp
        assert len(gp["operator_upload_order"]) > 0


def test_contact_planner_upload_order_matches_panel_count(contact_records):
    for r in contact_records:
        gp = r["generation_params"]
        assert len(gp["operator_upload_order"]) == gp["panel_count"]


def test_contact_planner_upload_order_all_png(contact_records):
    for r in contact_records:
        for fn in r["generation_params"]["operator_upload_order"]:
            assert fn.endswith(".png"), f"Non-PNG archive filename: {fn}"


def test_contact_planner_kling_contact_sheet_default_off(contact_records):
    for r in contact_records:
        assert r["generation_params"]["contact_sheet_for_kling_default"] == "off"


def test_contact_planner_total_panels_equals_22(contact_records):
    total = sum(r["generation_params"]["panel_count"] for r in contact_records)
    assert total == 22


def test_contact_planner_prompt_text_contains_clip_id(contact_records):
    for r in contact_records:
        clip_id = r["generation_params"]["clip_id"]
        assert clip_id in r["prompt_text"]


def test_contact_planner_provider_is_openai(contact_records):
    for r in contact_records:
        assert r["generation_params"]["provider"] == "openai"
