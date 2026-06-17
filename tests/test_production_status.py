from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.production_status import (  # noqa: E402
    STATUS_FIELDS,
    build_production_status,
    load_batch_jobs,
    validate_batch_job_file,
    write_production_status_csv,
)
from scripts.validate_production_records import run_validation  # noqa: E402


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_scene(repo_root: Path, scene_id: str = "SC0001") -> None:
    _write_yaml(
        repo_root / "planning" / "scenes" / scene_id / "scene_card.yaml",
        {"scene_id": scene_id, "excerpt_ref": "scene_excerpt.md"},
    )


def _copy_production_schemas(repo_root: Path) -> None:
    schemas_dir = repo_root / "schemas"
    schemas_dir.mkdir(parents=True)
    for name in (
        "image_selection.schema.json",
        "asset_clearance.schema.json",
        "batch_job.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _valid_storyboard_options(scene_id: str = "SC0001") -> dict:
    return {
        "scene_id": scene_id,
        "round": 1,
        "source_refs": {
            "scene_card": f"planning/scenes/{scene_id}/scene_card.yaml",
            "scene_excerpt": f"planning/scenes/{scene_id}/scene_excerpt.md",
        },
        "options": [
            {
                "option_id": f"{scene_id}_SB{index:02d}",
                "purpose": "Source-grounded composition option.",
                "camera_angle": "Restrained intimate coverage.",
                "framing": "Thresholds and corridor depth.",
                "movement": "Minimal exact movement.",
                "lighting": "Filtered early daylight.",
                "source_field": "scene_card.visual_targets.framing_bias",
                "prompt_ids": [],
                "status": "candidate",
            }
            for index in range(1, 6)
        ],
        "selected_option": None,
        "review_status": "pending",
        "storage_policy": "no_binary_commits",
    }


def _valid_batch_job() -> dict:
    return {
        "job_id": "JOB-SC0001-STORYBOARD",
        "job_type": "generate_storyboard",
        "scenes": ["SC0001"],
        "models": [],
        "prompt_types": [],
        "expected_outputs": 1,
        "cost_limit": 0,
        "retry_limit": 0,
        "priority": "normal",
        "status": "queued",
        "created_at": "2026-04-30T00:00:00Z",
    }


def test_empty_repo_status_generation_writes_header_only(tmp_path: Path) -> None:
    out_path = write_production_status_csv(tmp_path)

    assert out_path == tmp_path / "evidence" / "production_status.csv"
    rows = list(csv.DictReader(out_path.open("r", encoding="utf-8")))
    assert rows == []
    assert out_path.read_text(encoding="utf-8").splitlines()[0] == ",".join(
        STATUS_FIELDS
    )


def test_scene_without_metadata_is_phase1_pending(tmp_path: Path) -> None:
    _write_scene(tmp_path)

    rows = build_production_status(tmp_path)

    assert len(rows) == 1
    assert rows[0].scene_id == "SC0001"
    assert rows[0].element_packs_status == "not_started"
    assert rows[0].overall_status == "phase1_pending"


def test_write_status_csv_uses_existing_scene_ids_only(tmp_path: Path) -> None:
    _write_scene(tmp_path, "SC0002")
    (tmp_path / "visual_dev" / "storyboards" / "SC9999").mkdir(parents=True)

    out_path = write_production_status_csv(tmp_path)
    rows = list(csv.DictReader(out_path.open("r", encoding="utf-8")))

    assert [row["scene_id"] for row in rows] == ["SC0002"]


def test_valid_batch_job_passes_direct_and_production_validation(tmp_path: Path) -> None:
    _copy_production_schemas(tmp_path)
    job_path = tmp_path / "evidence" / "batch_jobs" / "JOB-SC0001-STORYBOARD.yaml"
    _write_yaml(job_path, _valid_batch_job())

    direct_issues = validate_batch_job_file(
        job_path,
        tmp_path / "schemas" / "batch_job.schema.json",
    )
    report = run_validation(tmp_path)

    assert direct_issues == []
    assert report.total_files == 1
    assert report.by_record_type["batch_job"] == 1
    assert report.valid_files == 1


def test_invalid_batch_job_status_fails(tmp_path: Path) -> None:
    _copy_production_schemas(tmp_path)
    payload = _valid_batch_job()
    payload["status"] = "waiting"
    _write_yaml(
        tmp_path / "evidence" / "batch_jobs" / "JOB-SC0001-STORYBOARD.yaml",
        payload,
    )

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any("status" in issue.field_path for issue in report.issues)


def test_load_batch_jobs_returns_yaml_mappings(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "evidence" / "batch_jobs" / "JOB-SC0001-STORYBOARD.yaml",
        _valid_batch_job(),
    )

    jobs = load_batch_jobs(tmp_path)

    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "JOB-SC0001-STORYBOARD"


def test_no_binaries_or_lifecycle_files_are_created(tmp_path: Path) -> None:
    _write_scene(tmp_path)
    write_production_status_csv(tmp_path)

    assert not list(tmp_path.rglob("*.png"))
    assert not list(tmp_path.rglob("*.mp4"))
    assert not list(tmp_path.rglob("pack_manifest.yaml"))
    assert (tmp_path / "planning" / "scenes" / "SC0001" / "scene_card.yaml").exists()
