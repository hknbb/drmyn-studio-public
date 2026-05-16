import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import validate_prompt_records


@pytest.fixture
def mock_repo(tmp_path):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir(parents=True)
    schema_src = REPO_ROOT / "schemas" / "prompt_record.schema.json"
    
    if schema_src.exists():
        (schema_dir / "prompt_record.schema.json").write_text(
            schema_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    
    return tmp_path


def write_prompt(repo_root, stage, filename, payload):
    d = repo_root / "prompts" / stage
    d.mkdir(parents=True, exist_ok=True)
    with open(d / filename, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def get_valid_prompt():
    return {
        "prompt_id": "SC0001__t2i-char-midjourney__v01",
        "scene_id": "SC0001",
        "prompt_type": "t2i_character_element",
        "lifecycle_stage": "draft",
        "target_models": ["midjourney"],
        "source_refs": {
            "scene_card": "planning/scenes/SC0001/scene_card.yaml",
            "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md"
        },
        "prompt_text": "A highly detailed portrait of Nadia...",
        "status": "active",
        "canon_lock": False
    }


def get_valid_kling_prompt():
    return {
        "prompt_id": "SC0001__omni-kling-alias-taxonomy__v01",
        "scene_id": "SC0001",
        "prompt_type": "omni_instruction",
        "lifecycle_stage": "draft",
        "target_models": ["kling_omni"],
        "source_refs": {
            "scene_card": "planning/scenes/SC0001/scene_card.yaml",
            "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md",
        },
        "prompt_text": (
            "Create one Kling Omni element-based video clip with active elements: "
            "@Nadia."
        ),
        "generation_params": {
            "required_element_aliases": ["@Nadia"],
            "repo_canonical_aliases": ["@C01_HOME_MORNING"],
            "alias_resolution": {"@C01_HOME_MORNING": "@Nadia"},
            "attached_element_refs": [
                {
                    "element_id": "C01",
                    "element_type": "character_look",
                    "repo_alias": "@C01_HOME_MORNING",
                    "platform_alias": "@Nadia",
                    "platform_binding_required": True,
                    "readiness": "draft_reference_ready",
                }
            ],
        },
        "status": "active",
        "canon_lock": False,
    }


def write_kling_character_look_element(repo_root, alias="@C01_HOME_MORNING"):
    d = repo_root / "visual_dev" / "elements" / "characters" / "C01" / "kling_elements"
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.x-draft",
        "record_type": "kling_character_look_element",
        "kling_character_look_element_id": "KLING_ELEM_C01_HOME_MORNING_V001",
        "character_id": "C01",
        "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
        "look_id": "C01_LOOK_HOME_MORNING_V001",
        "kling_element_alias": alias,
        "display_name": "C01 Home Morning",
        "status": "draft",
        "element_role": "character_look_composite",
        "source_reference_chain": {
            "identity_source_ref": "MJ_ELEMENT_C01_HERO_LOCKED_V001",
            "front_hero_lock_ref": "external://local_manual/c01.png",
            "perspective_pack_id": "GPTIMG2_C01_PERSPECTIVE_PACK_V001",
            "wardrobe_ids": ["WD001"],
        },
        "omni_usage_policy": {
            "use_as_primary_character_element": True,
            "do_not_mix_with_other_same_character_look_aliases_in_same_shot": True,
            "wardrobe_is_baked_into_element": True,
            "separate_wardrobe_element_optional": False,
        },
        "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
    }
    with open(d / "KLING_ELEM_C01_HOME_MORNING_V001.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def write_element_bindings(repo_root):
    d = repo_root / "visual_dev" / "omni_sets" / "SC0001"
    d.mkdir(parents=True, exist_ok=True)
    docs = [
        {
            "schema_version": "0.x-draft",
            "record_type": "element_binding",
            "element_id": "C01",
            "element_type": "character",
            "kling_alias": "@Nadia",
            "binding_status": "created",
        },
        {
            "schema_version": "0.x-draft",
            "record_type": "element_binding",
            "element_id": "LOC001",
            "element_type": "location_sub_area",
            "kling_alias": "@ValeResidenceKitchenPassage",
            "binding_status": "created",
        },
    ]
    with open(d / "element_bindings.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump_all(docs, f, sort_keys=False)


def write_ready_shot_element_manifest(repo_root, *, binding_status="created", gate_status="all_elements_ready"):
    schema_src = REPO_ROOT / "schemas" / "shot_element_manifest.schema.json"
    (repo_root / "schemas" / "shot_element_manifest.schema.json").write_text(
        schema_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    manifest_path = (
        repo_root
        / "visual_dev"
        / "omni_sets"
        / "SC0001"
        / "shot_element_manifests"
        / "SH001.yaml"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "0.x-draft",
        "record_type": "shot_element_manifest",
        "manifest_id": "MANIFEST_SC0001_SH001_V001",
        "scene_id": "SC0001",
        "shot_id": "SH001",
        "required_elements": [
            {
                "element_id": "C01",
                "element_type": "character",
                "role": "primary_subject",
                "registration_state_required": "created",
            }
        ],
        "environmental_only_allowed_ids": [],
        "gate_status": gate_status,
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    write_element_bindings(repo_root)
    bindings_path = repo_root / "visual_dev" / "omni_sets" / "SC0001" / "element_bindings.yaml"
    docs = list(yaml.safe_load_all(bindings_path.read_text(encoding="utf-8")))
    docs[0]["binding_status"] = binding_status
    bindings_path.write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")

    element_root = repo_root / "visual_dev" / "elements" / "characters" / "C01"
    element_root.mkdir(parents=True, exist_ok=True)
    (element_root / "pack_manifest.yaml").write_text(
        yaml.safe_dump({"element_id": "C01"}, sort_keys=False),
        encoding="utf-8",
    )
    gpt_pack = {
        "schema_version": "0.x-draft",
        "record_type": "gpt_images_perspective_pack",
        "prompt_pack_id": "GPTIMG2_C01_PERSPECTIVE_PACK_V002",
        "status": "review",
        "source_reference_id": "MJ_ELEMENT_C01_HERO_LOCKED_V002",
        "target_model": "gpt_images_2",
        "target_role": "multi_perspective_element_expander",
        "element_id": "C01",
        "element_type": "character",
        "shared_preservation_instruction": "Preserve identity.",
        "perspective_policy": "three_view_no_rear",
        "prompts": [
            {
                "prompt_id": "GPTIMG2_C01_FRONT_REFERENCE_V002",
                "perspective": "front_reference",
                "prompt_text": "Front full-body studio reference.",
                "constraints": ["single character only"],
                "expected_output": {"asset_type": "still"},
            },
            {
                "prompt_id": "GPTIMG2_C01_LEFT_REFERENCE_V002",
                "perspective": "left_reference",
                "prompt_text": "Left profile studio reference.",
                "constraints": ["single character only"],
                "expected_output": {"asset_type": "still"},
            },
            {
                "prompt_id": "GPTIMG2_C01_RIGHT_REFERENCE_V002",
                "perspective": "right_reference",
                "prompt_text": "Right profile studio reference.",
                "constraints": ["single character only"],
                "expected_output": {"asset_type": "still"},
            },
        ],
        "qc_gate": {
            "minimum_score": 85,
            "all_perspectives_required": True,
            "failed_perspective_revision_only": True,
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }
    (element_root / "gpt_images_perspective_pack.yaml").write_text(
        yaml.safe_dump(gpt_pack, sort_keys=False),
        encoding="utf-8",
    )
    kling_ref = {
        "schema_version": "0.x-draft",
        "record_type": "kling_element_reference_record",
        "kling_element_reference_id": "KLING_REF_C01_V001",
        "status": "review",
        "element_id": "C01",
        "element_type": "character",
        "source_midjourney_reference": {
            "reference_id": "MJ_ELEMENT_C01_HERO_LOCKED_V001",
            "prompt_id": "MJ_PROMPT_C01_HERO_LOCKED_V001",
        },
        "gpt_images_2_perspectives": {
            "front_reference": "GPTIMG2_C01_FRONT_REFERENCE_V002",
            "left_reference": "GPTIMG2_C01_LEFT_REFERENCE_V002",
            "right_reference": "GPTIMG2_C01_RIGHT_REFERENCE_V002",
        },
        "continuity_anchors": ["identity", "wardrobe"],
        "approval_gate": {
            "all_perspectives_score_85_plus": True,
            "operator_approved": True,
            "operator_session_ref": "OP-TEST",
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }
    (element_root / "kling_element_reference.yaml").write_text(
        yaml.safe_dump(kling_ref, sort_keys=False), encoding="utf-8"
    )
    return "visual_dev/omni_sets/SC0001/shot_element_manifests/SH001.yaml"


class DummyArgs:
    def __init__(self, repo_root, report_json):
        self.repo_root = repo_root
        self.report_json = report_json


def test_empty_directory_exits_0(mock_repo, capsys):
    args = DummyArgs(mock_repo, mock_repo / "report.json")
    assert validate_prompt_records.main(args) == 0
    assert "0 files validated" in capsys.readouterr().out


def test_valid_minimal_record_passes(mock_repo, capsys):
    write_prompt(mock_repo, "draft", "test_prompt.yaml", get_valid_prompt())
    args = DummyArgs(mock_repo, mock_repo / "report.json")
    assert validate_prompt_records.main(args) == 0
    assert "1 files validated successfully" in capsys.readouterr().out


def test_missing_prompt_text_fails(mock_repo):
    payload = get_valid_prompt()
    del payload["prompt_text"]
    write_prompt(mock_repo, "draft", "test_prompt.yaml", payload)
    args = DummyArgs(mock_repo, mock_repo / "report.json")
    assert validate_prompt_records.main(args) == 1
    
    report = json.loads((mock_repo / "report.json").read_text())
    assert report["files_with_errors"] == 1


def test_invalid_prompt_id_pattern_fails(mock_repo):
    payload = get_valid_prompt()
    payload["prompt_id"] = "INVALID_ID_FORMAT"
    write_prompt(mock_repo, "draft", "test_prompt.yaml", payload)
    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1


def test_lifecycle_stage_production_fails(mock_repo):
    payload = get_valid_prompt()
    payload["lifecycle_stage"] = "production"
    write_prompt(mock_repo, "draft", "test_prompt.yaml", payload)
    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1


def test_active_kling_prompt_without_manifest_ref_fails(mock_repo):
    write_kling_character_look_element(mock_repo)
    write_element_bindings(mock_repo)
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", get_valid_kling_prompt())

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("shot_element_manifest_ref is required" in error for error in errors)


def test_kling_unresolved_required_alias_fails(mock_repo):
    write_kling_character_look_element(mock_repo)
    write_element_bindings(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["required_element_aliases"] = ["@MissingAlias"]
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("@MissingAlias" in error and "unresolved alias" in error for error in errors)


def test_kling_required_alias_conflicting_with_not_attached_fails(mock_repo):
    write_kling_character_look_element(mock_repo)
    write_element_bindings(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["not_attached_as_kling_elements"] = [
        "@ValeResidenceKitchenPassage"
    ]
    payload["generation_params"]["required_element_aliases"] = [
        "@Nadia",
        "@ValeResidenceKitchenPassage",
    ]
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("not_attached_as_kling_elements" in error for error in errors)


def test_kling_attached_repo_alias_must_resolve_to_character_look_record(mock_repo):
    write_element_bindings(mock_repo)
    manifest_ref = write_ready_shot_element_manifest(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["shot_element_manifest_ref"] = manifest_ref
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("repo_alias" in error and "@C01_HOME_MORNING" in error for error in errors)


def test_kling_prompt_with_ready_shot_manifest_passes(mock_repo, capsys):
    write_kling_character_look_element(mock_repo)
    manifest_ref = write_ready_shot_element_manifest(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["shot_element_manifest_ref"] = manifest_ref
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 0
    assert "1 files validated successfully" in capsys.readouterr().out


def test_kling_prompt_manifest_ref_missing_fails(mock_repo):
    write_kling_character_look_element(mock_repo)
    write_element_bindings(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["shot_element_manifest_ref"] = (
        "visual_dev/omni_sets/SC0001/shot_element_manifests/MISSING.yaml"
    )
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("shot_element_manifest_ref not found" in error for error in errors)


def test_kling_prompt_with_planned_binding_manifest_fails(mock_repo):
    write_kling_character_look_element(mock_repo)
    manifest_ref = write_ready_shot_element_manifest(
        mock_repo,
        binding_status="planned",
        gate_status="blocked",
    )
    payload = get_valid_kling_prompt()
    payload["generation_params"]["shot_element_manifest_ref"] = manifest_ref
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("binding_status is 'planned'" in error for error in errors)


def test_kling_prompt_manifest_rejects_not_attached_escape_hatch(mock_repo):
    write_kling_character_look_element(mock_repo)
    manifest_ref = write_ready_shot_element_manifest(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["shot_element_manifest_ref"] = manifest_ref
    payload["generation_params"]["not_attached_as_kling_elements"] = ["@ValeResidenceKitchenPassage"]
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("not_attached_as_kling_elements is not allowed" in error for error in errors)


def test_kling_prompt_raw_name_leak_fails(mock_repo):
    write_kling_character_look_element(mock_repo)
    manifest_ref = write_ready_shot_element_manifest(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["shot_element_manifest_ref"] = manifest_ref
    payload["prompt_text"] = "Create a shot where Nadia enters."
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("raw element names" in error and "Nadia" in error for error in errors)


def test_kling_prompt_canonical_id_leak_fails(mock_repo):
    write_kling_character_look_element(mock_repo)
    manifest_ref = write_ready_shot_element_manifest(mock_repo)
    payload = get_valid_kling_prompt()
    payload["generation_params"]["shot_element_manifest_ref"] = manifest_ref
    payload["prompt_text"] = "Create a shot with @Nadia and C01."
    write_prompt(mock_repo, "draft", "kling_prompt.yaml", payload)

    assert validate_prompt_records.main(DummyArgs(mock_repo, mock_repo / "report.json")) == 1
    report = json.loads((mock_repo / "report.json").read_text())
    errors = report["errors"]["prompts/draft/kling_prompt.yaml"]
    assert any("repo-canonical element ids" in error and "C01" in error for error in errors)
