from __future__ import annotations

import sys
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.omni_set_gate import (  # noqa: E402
    audit_omni_set_gate,
    main as omni_set_gate_main,
    write_omni_set_gate_report,
)


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_minimal_scene(
    repo_root: Path,
    *,
    pack_status: str = "locked",
) -> None:
    _write_yaml(
        repo_root / "planning/scenes/SC0001/scene_card.yaml",
        {
            "scene_id": "SC0001",
            "omni_set_ref": "visual_dev/omni_sets/SC0001/",
            "shot_list_omni": [
                {
                    "shot_id": "SC0001_OMNI01",
                    "duration_seconds": 5,
                }
            ],
        },
    )
    _write_yaml(
        repo_root / "visual_dev/omni_sets/SC0001/element_set.yaml",
        {
            "element_set_id": "ES0001",
            "scene_id": "SC0001",
            "status": "draft",
            "canon_lock": False,
            "element_refs": [
                "visual_dev/omni_sets/SC0001/elements_used/C01_nadia.yaml"
            ],
        },
    )
    _write_yaml(
        repo_root / "visual_dev/omni_sets/SC0001/elements_used/C01_nadia.yaml",
        {
            "element_ref": "C01_nadia",
            "pack_path_expected": "visual_dev/elements/characters/C01/",
            "status": "descriptor_only",
        },
    )
    _write_yaml(
        repo_root / "visual_dev/elements/characters/C01/pack_manifest.yaml",
        {
            "element_id": "C01",
            "pack_status": pack_status,
        },
    )


def test_ready_gate_when_scene_metadata_and_packs_are_locked(tmp_path: Path) -> None:
    _write_minimal_scene(tmp_path, pack_status="locked")

    report = audit_omni_set_gate(tmp_path, "SC0001")

    assert report["ready_for_kling_prompt_generation"] is True
    assert report["gate_status"] == "ready_for_kling_prompt_generation"
    assert report["shot_list_gate"]["shot_count"] == 1
    assert report["shot_list_gate"]["total_duration_seconds"] == 5
    assert report["element_pack_gate"]["summary"]["ready_packs"] == 1
    assert report["blocking_reasons"] == []


def test_metadata_only_pack_blocks_without_mutating_pack_manifest(tmp_path: Path) -> None:
    _write_minimal_scene(tmp_path, pack_status="metadata_only")
    pack_manifest = tmp_path / "visual_dev/elements/characters/C01/pack_manifest.yaml"
    before = pack_manifest.read_text(encoding="utf-8")

    report = audit_omni_set_gate(tmp_path, "SC0001")

    assert report["ready_for_kling_prompt_generation"] is False
    assert report["gate_status"] == "blocked_pending_locked_element_packs"
    assert report["element_pack_gate"]["summary"]["metadata_only_packs"] == 1
    assert "pack_status is 'metadata_only'" in report["blocking_reasons"][0]
    assert pack_manifest.read_text(encoding="utf-8") == before


def test_cli_writes_schema_valid_metadata_only_gate_report(tmp_path: Path) -> None:
    _write_minimal_scene(tmp_path, pack_status="metadata_only")

    code = omni_set_gate_main(
        [
            "--repo-root",
            str(tmp_path),
            "--scene-id",
            "SC0001",
        ]
    )
    output_path = tmp_path / "evidence/omni_set_gates/SC0001_gate.yaml"
    report = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert code == 0
    assert report["external_generation_performed"] is False
    assert report["binary_outputs_created"] is False
    assert report["lifecycle_promotion_performed"] is False
    schema = json.loads(
        (REPO_ROOT / "schemas/omni_set_gate.schema.json").read_text(encoding="utf-8")
    )
    errors = list(Draft202012Validator(schema).iter_errors(report))
    assert errors == []


def test_real_sc0001_gate_report_file_is_schema_valid(tmp_path: Path) -> None:
    output_path = tmp_path / "SC0001_gate.yaml"

    write_omni_set_gate_report(
        REPO_ROOT,
        "SC0001",
        output_path=output_path,
        generated_at="2026-05-04T19:30:00Z",
    )
    report = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert report["scene_id"] == "SC0001"
    assert report["storage_policy"] == "no_binary_commits"
    assert report["ready_for_kling_prompt_generation"] is False
    assert not list(tmp_path.rglob("*.mp4"))
    assert not list(tmp_path.rglob("*.mov"))
