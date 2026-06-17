from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.pack_lock_readiness import (  # noqa: E402
    audit_pack_lock_readiness,
    main as pack_lock_readiness_main,
    write_pack_lock_readiness_report,
)


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_gitattributes(repo_root: Path) -> None:
    (repo_root / ".gitattributes").write_text(
        "\n".join(
            [
                "visual_dev/elements/**/*.png  filter=lfs diff=lfs merge=lfs -text",
                "visual_dev/elements/**/*.jpg  filter=lfs diff=lfs merge=lfs -text",
                "visual_dev/elements/**/*.jpeg filter=lfs diff=lfs merge=lfs -text",
                "visual_dev/elements/**/*.webp filter=lfs diff=lfs merge=lfs -text",
            ]
        ),
        encoding="utf-8",
    )


def _write_gate(repo_root: Path, scene_id: str = "SC0001") -> None:
    _write_yaml(
        repo_root / "evidence/omni_set_gates" / f"{scene_id}_gate.yaml",
        {
            "scene_id": scene_id,
            "element_pack_gate": {
                "elements": [
                    {
                        "element_ref": "visual_dev/omni_sets/SC0001/elements_used/C01.yaml",
                        "pack_path_expected": "visual_dev/elements/characters/C01/",
                    }
                ]
            },
        },
    )


def _write_pack(
    repo_root: Path,
    *,
    with_asset: bool,
    intake_ready: bool,
) -> Path:
    pack_dir = repo_root / "visual_dev/elements/characters/C01"
    _write_yaml(
        pack_dir / "pack_manifest.yaml",
        {
            "element_id": "C01",
            "pack_status": "metadata_only",
            "text_assets": ["pack_manifest.yaml", "source_notes.md"],
        },
    )
    _write_yaml(
        pack_dir / "image_intake_manifest.yaml",
        {
            "element_id": "C01",
            "source_status": (
                "source_images_in_repo" if with_asset else "no_source_images_in_repo"
            ),
            "copyright_review": "complete" if intake_ready else "pending",
            "provenance_review": "complete" if intake_ready else "pending",
            "intake_ready_to_proceed": intake_ready,
            "open_blockers": [] if intake_ready else ["No source images available in repo."],
        },
    )
    (pack_dir / "source_notes.md").write_text("Grounded source notes.\n", encoding="utf-8")
    if with_asset:
        (pack_dir / "canonical_reference.png").write_bytes(b"not-a-real-image-for-temp-test")
    return pack_dir / "pack_manifest.yaml"


def test_ready_pack_reports_ready_for_human_lock_review(tmp_path: Path) -> None:
    _write_gitattributes(tmp_path)
    _write_gate(tmp_path)
    _write_pack(tmp_path, with_asset=True, intake_ready=True)

    report = audit_pack_lock_readiness(tmp_path, "SC0001")

    assert report["report_status"] == "ready_for_human_lock_review"
    assert report["ready_for_human_lock_review"] is True
    assert report["summary"]["ready_for_lock_review"] == 1
    assert report["summary"]["packs_with_canonical_assets"] == 1
    assert report["packs"][0]["ready_for_lock_review"] is True
    assert report["packs"][0]["missing_requirements"] == []
    assert report["lock_action_performed"] is False


def test_metadata_only_missing_assets_report_blocks_without_mutation(tmp_path: Path) -> None:
    _write_gitattributes(tmp_path)
    _write_gate(tmp_path)
    pack_manifest = _write_pack(tmp_path, with_asset=False, intake_ready=False)
    before = pack_manifest.read_text(encoding="utf-8")

    report = audit_pack_lock_readiness(tmp_path, "SC0001")

    assert report["report_status"] == "blocked_missing_canonical_assets"
    assert report["ready_for_human_lock_review"] is False
    assert report["summary"]["blocked_packs"] == 1
    assert report["summary"]["packs_missing_canonical_assets"] == 1
    assert "no canonical image assets found in pack" in report["packs"][0]["missing_requirements"]
    assert "source images are not present in repo" in report["packs"][0]["missing_requirements"]
    assert pack_manifest.read_text(encoding="utf-8") == before


def test_cli_writes_schema_valid_report(tmp_path: Path) -> None:
    _write_gitattributes(tmp_path)
    _write_gate(tmp_path)
    _write_pack(tmp_path, with_asset=False, intake_ready=False)

    code = pack_lock_readiness_main(
        [
            "--repo-root",
            str(tmp_path),
            "--scene-id",
            "SC0001",
        ]
    )
    report_path = tmp_path / "evidence/pack_lock_readiness/SC0001_pack_lock_readiness.yaml"
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/pack_lock_readiness.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert code == 0
    assert report["lock_action_performed"] is False
    assert report["canonical_assets_created"] is False
    assert list(Draft202012Validator(schema).iter_errors(report)) == []


