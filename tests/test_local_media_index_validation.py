from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_production_records import run_validation  # noqa: E402


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_schemas(repo_root: Path) -> None:
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
        "agent_handoff.schema.json",
        "local_media_index.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _write_index(repo_root: Path, filename: str, payload: dict) -> None:
    _write_yaml(repo_root / "evidence" / "local_media_indices" / filename, payload)


def _valid_sc_entry() -> dict:
    return {
        "kind": "video_take",
        "element_id_or_take_id": "SC0006_TAKE001",
        "storage_backend": "gdrive_manual",
        "last_seen_at": "2026-05-01T10:00:00Z",
        "repo_binary_committed": False,
        "external_storage_ref": "gdrive://ClosingPriceMedia/video/SC0006/take001.mp4",
    }


def _valid_element_entry() -> dict:
    return {
        "kind": "image_candidate",
        "element_id_or_take_id": "C01_nadia_001",
        "storage_backend": "local_manual",
        "last_seen_at": "2026-05-01T10:00:00Z",
        "repo_binary_committed": False,
        "local_path": "local://ClosingPriceMedia/elements/characters/C01/nadia_001.png",
    }


def test_valid_sc_index_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_video_only",
            "entries": [_valid_sc_entry()],
        },
    )
    report = run_validation(tmp_path)
    assert report.by_record_type["local_media_index"] == 1
    assert report.issues == []


def test_valid_elements_index_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_index(
        tmp_path,
        "_elements.yaml",
        {
            "scene_id": "_elements",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_image_only",
            "entries": [_valid_element_entry()],
        },
    )
    report = run_validation(tmp_path)
    assert report.by_record_type["local_media_index"] == 1
    assert report.issues == []


def test_entry_with_both_local_and_external_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = _valid_sc_entry()
    entry["local_path"] = "local://ClosingPriceMedia/video/SC0006/take001.mp4"
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "mixed_external",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.issues == []


def test_missing_both_local_path_and_external_storage_ref_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = _valid_sc_entry()
    del entry["external_storage_ref"]
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_video_only",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.invalid_files >= 1
    messages = " ".join(i.message for i in report.issues)
    assert "any of the given schemas" in messages or "local_path" in messages or "external_storage_ref" in messages


def test_repo_binary_committed_true_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = _valid_sc_entry()
    entry["repo_binary_committed"] = True
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_video_only",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.invalid_files >= 1
    messages = " ".join(i.message for i in report.issues)
    assert "repo_binary_committed" in messages


def test_invalid_storage_backend_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = _valid_sc_entry()
    entry["storage_backend"] = "dropbox"
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_video_only",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.invalid_files >= 1


def test_invalid_sha256_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = _valid_sc_entry()
    entry["sha256"] = "tooshort"
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_video_only",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.invalid_files >= 1
    messages = " ".join(i.message for i in report.issues)
    assert "does not match" in messages or "sha256" in messages


def test_valid_sha256_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = _valid_sc_entry()
    entry["sha256"] = "a" * 64
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_video_only",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.issues == []


def test_video_local_path_without_external_storage_ref_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = {
        "kind": "video_take",
        "element_id_or_take_id": "SC0006_TAKE001",
        "storage_backend": "local_manual",
        "last_seen_at": "2026-05-01T10:00:00Z",
        "repo_binary_committed": False,
        "local_path": "D:/ClosingPriceMedia/video/SC0006/take001.mp4",
    }
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "mixed_external",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.invalid_files >= 1
    messages = " ".join(i.message for i in report.issues)
    assert "external_storage_ref" in messages


def test_video_local_path_with_external_storage_ref_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    entry = {
        "kind": "video_take",
        "element_id_or_take_id": "SC0006_TAKE001",
        "storage_backend": "local_manual",
        "last_seen_at": "2026-05-01T10:00:00Z",
        "repo_binary_committed": False,
        "local_path": "D:/ClosingPriceMedia/video/SC0006/take001.mp4",
        "external_storage_ref": "gdrive://ClosingPriceMedia/video/SC0006/take001.mp4",
    }
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "mixed_external",
            "entries": [entry],
        },
    )
    report = run_validation(tmp_path)
    assert report.issues == []


def test_empty_local_media_indices_dir_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    (tmp_path / "evidence" / "local_media_indices").mkdir(parents=True)
    report = run_validation(tmp_path)
    assert report.by_record_type["local_media_index"] == 0
    assert report.issues == []


def test_no_binaries_created(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_index(
        tmp_path,
        "SC0006.yaml",
        {
            "scene_id": "SC0006",
            "created_at": "2026-05-01T10:00:00Z",
            "storage_policy": "external_video_only",
            "entries": [_valid_sc_entry()],
        },
    )
    run_validation(tmp_path)
    binary_extensions = {".mp4", ".mov", ".mkv", ".png", ".jpg", ".jpeg", ".webp"}
    binaries = [p for p in tmp_path.rglob("*") if p.suffix.lower() in binary_extensions]
    assert binaries == []
