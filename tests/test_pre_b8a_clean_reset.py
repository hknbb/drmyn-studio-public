from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.pre_b8a_clean_reset import (  # noqa: E402
    build_pre_b8a_clean_reset,
    main as pre_b8a_clean_reset_main,
    write_pre_b8a_clean_reset,
)
from scripts.validate_production_records import run_validation  # noqa: E402


def _load_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/pre_b8a_clean_reset.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_validator_schemas(repo_root: Path) -> None:
    schemas_dir = repo_root / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "image_selection.schema.json",
        "asset_clearance.schema.json",
        "video_take.schema.json",
        "video_review.schema.json",
        "selected_take.schema.json",
        "batch_job.schema.json",
        "operator_session.schema.json",
        "canonical_asset_intake_slot.schema.json",
        "pre_b8a_clean_reset.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _minimal_slot(
    *,
    source_status: str = "not_collected",
    storage_policy: str = "no_binary_commits",
    canonical_assets_committed: list[str] | None = None,
    intake_ready_to_proceed: bool = False,
) -> dict:
    return {
        "scene_id": "SC0001",
        "work_order_id": "SC0001_ASSET_01_C01",
        "element_id": "C01",
        "element_type": "character",
        "group_id": "wd001",
        "group_type": "wardrobe_reference_set",
        "context": "test context",
        "required_views": [
            "front_reference",
            "three_quarter_reference",
            "context_reference",
        ],
        "source_status": source_status,
        "copyright_review": "pending",
        "provenance_review": "pending",
        "intake_ready_to_proceed": intake_ready_to_proceed,
        "canonical_assets_committed": canonical_assets_committed or [],
        "storage_policy": storage_policy,
        "forbidden_actions": [
            "Do not add placeholder binaries.",
            "Do not mark copyright_review complete without reviewed evidence.",
        ],
    }


def _seed_base_repo(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/wardrobe/WD001/intake_slot.yaml",
        _minimal_slot(),
    )
    (tmp_path / "visual_dev/elements/characters/C01/wardrobe/WD001/.gitkeep").parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    (tmp_path / "visual_dev/elements/characters/C01/wardrobe/WD001/.gitkeep").write_text(
        "",
        encoding="utf-8",
    )
    (tmp_path / "visual_dev/elements/characters/C01/wardrobe/WD001/README.md").write_text(
        "placeholder\n",
        encoding="utf-8",
    )


def _stage_file(
    tmp_path: Path,
    name: str,
    *,
    sidecar: bool = True,
    view_role: str = "front_reference",
    target_slot_ref: str = "visual_dev/elements/characters/C01/wardrobe/WD001/intake_slot.yaml",
    staging_dir: str = "visual_dev/intake_staging/C01_WD001",
) -> None:
    staged_path = tmp_path / staging_dir / name
    staged_path.parent.mkdir(parents=True, exist_ok=True)
    staged_path.write_bytes(b"img")
    if not sidecar:
        return
    sidecar_path = staged_path.parent / f"{staged_path.name}.sidecar.yaml"
    _write_yaml(
        sidecar_path,
        {
            "target_slot_ref": target_slot_ref,
            "element_id": "C01",
            "group_id": "WD001",
            "view_role": view_role,
            "original_filename": name,
            "staged_path": staged_path.relative_to(tmp_path).as_posix(),
            "source_type": "human_uploaded_reference",
            "copyright_review": "pending",
            "provenance_review": "pending",
        },
    )


def test_real_pre_b8a_clean_reset_record_is_schema_valid() -> None:
    payload = yaml.safe_load(
        (
            REPO_ROOT
            / "evidence/pre_b8a_clean_resets/SC0001_pre_b8a_clean_reset.yaml"
        ).read_text(encoding="utf-8")
    )

    assert list(Draft202012Validator(_load_schema()).iter_errors(payload)) == []


def test_clean_empty_staging_returns_clean_for_b8a_start(tmp_path: Path) -> None:
    _seed_base_repo(tmp_path)

    audit = build_pre_b8a_clean_reset(tmp_path)

    assert audit["reset_status"] == "clean_for_b8a_start"
    assert audit["ready_for_b8a_clean_branch"] is True
    assert audit["staged_files_count"] == 0
    assert audit["sidecar_files_count"] == 0
    assert audit["unexpected_canonical_files"] == []


def test_staged_file_without_sidecar_returns_cleanup_required_before_b8a(
    tmp_path: Path,
) -> None:
    _seed_base_repo(tmp_path)
    _stage_file(tmp_path, "front.jpg", sidecar=False)

    audit = build_pre_b8a_clean_reset(tmp_path)

    assert audit["reset_status"] == "cleanup_required_before_b8a"
    assert audit["staged_images_without_sidecars"] == [
        "visual_dev/intake_staging/C01_WD001/front.jpg"
    ]


def test_orphan_sidecar_returns_cleanup_required_before_b8a(tmp_path: Path) -> None:
    _seed_base_repo(tmp_path)
    sidecar_path = (
        tmp_path
        / "visual_dev/intake_staging/C01_WD001/front.jpg.sidecar.yaml"
    )
    _write_yaml(
        sidecar_path,
        {
            "target_slot_ref": "visual_dev/elements/characters/C01/wardrobe/WD001/intake_slot.yaml",
            "element_id": "C01",
            "group_id": "WD001",
            "view_role": "front_reference",
            "original_filename": "front.jpg",
            "staged_path": "visual_dev/intake_staging/C01_WD001/front.jpg",
        },
    )

    audit = build_pre_b8a_clean_reset(tmp_path)

    assert audit["reset_status"] == "cleanup_required_before_b8a"
    assert audit["orphan_sidecars"] == [
        "visual_dev/intake_staging/C01_WD001/front.jpg.sidecar.yaml"
    ]


def test_duplicate_target_returns_cleanup_required_before_b8a(tmp_path: Path) -> None:
    _seed_base_repo(tmp_path)
    _stage_file(tmp_path, "front_a.jpg", view_role="front_reference")
    _stage_file(tmp_path, "front_b.jpg", view_role="front_reference")

    audit = build_pre_b8a_clean_reset(tmp_path)

    assert audit["reset_status"] == "cleanup_required_before_b8a"
    assert audit["duplicate_target_canonical_paths"] == [
        "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_front.jpg"
    ]


def test_staged_file_outside_c01_wd001_returns_cleanup_required_before_b8a(
    tmp_path: Path,
) -> None:
    _seed_base_repo(tmp_path)
    _stage_file(
        tmp_path,
        "rogue.jpg",
        sidecar=False,
        staging_dir="visual_dev/intake_staging/C01_WD002",
    )

    audit = build_pre_b8a_clean_reset(tmp_path)

    assert audit["reset_status"] == "cleanup_required_before_b8a"
    assert audit["staged_files_outside_wd001"] == [
        "visual_dev/intake_staging/C01_WD002/rogue.jpg"
    ]


def test_unexpected_canonical_binary_before_b8a_returns_cleanup_required_before_b8a(
    tmp_path: Path,
) -> None:
    _seed_base_repo(tmp_path)
    unexpected = (
        tmp_path
        / "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_front.jpg"
    )
    unexpected.write_bytes(b"img")

    audit = build_pre_b8a_clean_reset(tmp_path)

    assert audit["reset_status"] == "cleanup_required_before_b8a"
    assert audit["unexpected_canonical_files"] == [
        "visual_dev/elements/characters/C01/wardrobe/WD001/c01_wd001_front.jpg"
    ]


def test_validator_accepts_written_audit_record(tmp_path: Path) -> None:
    _seed_base_repo(tmp_path)
    _copy_validator_schemas(tmp_path)

    output_path = write_pre_b8a_clean_reset(tmp_path)
    report = run_validation(tmp_path)

    assert output_path.exists()
    assert report.by_record_type["pre_b8a_clean_reset"] == 1
    assert report.invalid_files == 0


def test_no_files_are_deleted_moved_or_copied(tmp_path: Path) -> None:
    _seed_base_repo(tmp_path)
    _stage_file(tmp_path, "front.jpg")
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    output_path = tmp_path / "evidence/pre_b8a_clean_resets/SC0001_pre_b8a_clean_reset.yaml"

    written = write_pre_b8a_clean_reset(tmp_path, output_path=output_path)

    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file() and path != written
    }
    assert written == output_path
    assert output_path.exists()
    assert before == after


def test_cli_writes_schema_valid_clean_reset_record(tmp_path: Path) -> None:
    _seed_base_repo(tmp_path)
    output_path = tmp_path / "SC0001_pre_b8a_clean_reset.yaml"

    code = pre_b8a_clean_reset_main(
        [
            "--repo-root",
            str(tmp_path),
            "--output-path",
            str(output_path),
        ]
    )
    audit = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert code == 0
    assert list(Draft202012Validator(_load_schema()).iter_errors(audit)) == []
