from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.archive_media import archive_one, build_parser  # noqa: E402
from scripts.validate_production_records import run_validation  # noqa: E402


def _src_image(tmp_path: Path, name: str = "ChatGPT Image front.png") -> Path:
    src = tmp_path / "incoming" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes" * 8)
    return src


def _run(repo_root: Path, src: Path, **extra: str) -> dict:
    argv = [
        "--src", str(src),
        "--repo-root", str(repo_root),
        "--scene", extra.pop("scene", "_elements"),
        "--element", extra.pop("element", "C10"),
        "--stage", extra.pop("stage", "3"),
        "--kind", extra.pop("kind", "gpt_images_2_perspective_output"),
        "--id", extra.pop("id", "GPTIMG2_C10_P01_FRONT_V001"),
    ]
    for key, value in extra.items():
        argv += [f"--{key.replace('_', '-')}", value]
    args = build_parser().parse_args(argv)
    return archive_one(args)


def _copy_local_media_schema(repo_root: Path) -> None:
    schemas_dir = repo_root / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    for schema in (REPO_ROOT / "schemas").glob("*.schema.json"):
        (schemas_dir / schema.name).write_text(
            schema.read_text(encoding="utf-8"), encoding="utf-8"
        )


def test_archives_image_into_standard_tree(tmp_path: Path) -> None:
    src = _src_image(tmp_path)
    entry = _run(tmp_path, src)

    dest = tmp_path / "archive" / "nexuszero" / "_elements" / "C10" / "stage3" / "images" / src.name
    assert dest.is_file(), "binary should be copied into the gitignored archive tree"
    assert src.is_file(), "default mode copies (does not move) the source"

    assert entry["local_path"] == "archive/nexuszero/_elements/C10/stage3/images/" + src.name
    assert entry["external_storage_ref"].startswith("external://local_manual/archive/")
    assert entry["repo_binary_committed"] is False
    assert len(entry["sha256"]) == 64
    assert entry["size_bytes"] == dest.stat().st_size


def test_writes_schema_valid_index(tmp_path: Path) -> None:
    _copy_local_media_schema(tmp_path)
    _run(tmp_path, _src_image(tmp_path))

    index_file = (
        tmp_path / "evidence" / "local_media_indices"
        / "LOCAL_MEDIA_INDEX__elements_ARCHIVE_V001.yaml"
    )
    assert index_file.is_file()
    data = yaml.safe_load(index_file.read_text(encoding="utf-8"))
    assert data["scene_id"] == "_elements"
    assert data["storage_policy"] == "external_image_only"
    assert len(data["entries"]) == 1

    report = run_validation(tmp_path)
    assert report.by_record_type["local_media_index"] == 1
    assert report.issues == []


def test_rearchiving_same_file_is_idempotent(tmp_path: Path) -> None:
    src = _src_image(tmp_path)
    _run(tmp_path, src)
    _run(tmp_path, src)
    index_file = (
        tmp_path / "evidence" / "local_media_indices"
        / "LOCAL_MEDIA_INDEX__elements_ARCHIVE_V001.yaml"
    )
    data = yaml.safe_load(index_file.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 1, "same local_path must not duplicate entries"


def test_video_routes_to_video_bucket(tmp_path: Path) -> None:
    src = tmp_path / "incoming" / "kling_take.mp4"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"fake-video" * 16)
    entry = _run(
        tmp_path, src, scene="SC0001", element="SC0001_TAKE001",
        kind="kling_video_take", id="SC0001_TAKE001",
    )
    dest = tmp_path / "archive" / "nexuszero" / "SC0001" / "SC0001_TAKE001" / "stage3" / "video" / src.name
    assert dest.is_file()
    assert "/video/" in entry["local_path"]

    index_file = (
        tmp_path / "evidence" / "local_media_indices"
        / "LOCAL_MEDIA_INDEX_SC0001_ARCHIVE_V001.yaml"
    )
    data = yaml.safe_load(index_file.read_text(encoding="utf-8"))
    assert data["storage_policy"] == "external_video_only"
