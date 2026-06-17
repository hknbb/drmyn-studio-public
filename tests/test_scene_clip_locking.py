from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.graph import run_graph  # noqa: E402
from scripts.agents.run_pipeline import main as run_pipeline_main  # noqa: E402
from scripts.agents.scene_clip_locking import (  # noqa: E402
    SCENE_CLIP_MAP_HEADER,
    SceneClipLockingAgent,
    SceneClipLockingError,
)
from scripts.agents.state import PipelineState  # noqa: E402
from scripts.validate_production_records import run_validation  # noqa: E402


PROMPT_ID = "SC0001__omni-kling-omni__v01"


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
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _scores() -> dict[str, int]:
    return {
        "identity_consistency": 4,
        "source_grounding": 5,
        "style_compliance": 4,
        "continuity": 4,
        "production_usability": 5,
    }


def _take(
    take_id: str,
    *,
    status: str,
    external_storage_ref: str | None = None,
    repo_binary_committed: bool = False,
) -> dict:
    return {
        "take_id": take_id,
        "platform_asset_ref": f"kling://{take_id.lower()}",
        "external_storage_ref": external_storage_ref
        if external_storage_ref is not None
        else f"dvc://closing-price/SC0001/{take_id.lower()}.mp4",
        "local_proxy_ref": None,
        "repo_binary_committed": repo_binary_committed,
        "storage_status": "stored_external",
        "status": status,
        "reason": "Human-reviewed external take metadata.",
        "quality_scores": _scores(),
        "failure_reason": None if status == "selected" else "camera_drift",
    }


def _video_takes_payload() -> dict:
    return {
        "scene_id": "SC0001",
        "prompt_id": PROMPT_ID,
        "takes": [
            _take("SC0001_TAKE001", status="rejected"),
            _take("SC0001_TAKE002", status="selected"),
        ],
        "selected_take": "SC0001_TAKE002",
        "round_status": "complete",
        "needs_prompt_revision": False,
        "storage_policy": "external_video_only",
    }


def _write_ready_repo(repo_root: Path) -> tuple[Path, Path, Path]:
    _copy_schemas(repo_root)
    video_takes_path = repo_root / "visual_dev/omni_sets/SC0001/video_takes.yaml"
    scene_card = repo_root / "planning/scenes/SC0001/scene_card.yaml"
    prompt_record = repo_root / "prompts/draft/SC0001__omni-kling-omni__v01.yaml"
    pack_manifest = repo_root / "visual_dev/elements/characters/C01/pack_manifest.yaml"
    _write_yaml(video_takes_path, _video_takes_payload())
    _write_yaml(scene_card, {"scene_id": "SC0001", "shot_list_omni": [{"shot_id": "x"}]})
    _write_yaml(prompt_record, {"prompt_id": PROMPT_ID, "lifecycle_stage": "draft"})
    _write_yaml(pack_manifest, {"element_id": "C01", "pack_status": "locked"})
    return video_takes_path, scene_card, prompt_record


def test_valid_video_takes_lock_selected_take_and_scene_clip_map(
    tmp_path: Path,
) -> None:
    video_takes_path, scene_card, prompt_record = _write_ready_repo(tmp_path)
    pack_manifest = tmp_path / "visual_dev/elements/characters/C01/pack_manifest.yaml"
    before_video_takes = video_takes_path.read_text(encoding="utf-8")
    before_scene = scene_card.read_text(encoding="utf-8")
    before_prompt = prompt_record.read_text(encoding="utf-8")
    before_pack = pack_manifest.read_text(encoding="utf-8")

    result = SceneClipLockingAgent(tmp_path).lock_scene_clip(
        scene_id="SC0001",
        locked_by="human_operator",
        locked_at="2026-04-30T00:00:00Z",
    )

    selected = yaml.safe_load(result.selected_take_path.read_text(encoding="utf-8"))
    with result.scene_clip_map_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert selected["selected_take"] == "SC0001_TAKE002"
    assert selected["repo_binary_committed"] is False
    assert selected["lock_status"] == "locked_metadata_only"
    assert reader.fieldnames == SCENE_CLIP_MAP_HEADER
    assert rows[0]["scene_id"] == "SC0001"
    assert rows[0]["repo_binary_committed"] == "false"
    assert video_takes_path.read_text(encoding="utf-8") == before_video_takes
    assert scene_card.read_text(encoding="utf-8") == before_scene
    assert prompt_record.read_text(encoding="utf-8") == before_prompt
    assert pack_manifest.read_text(encoding="utf-8") == before_pack
    assert run_validation(tmp_path).invalid_files == 0


def test_cli_lock_scene_clip_metadata_only(tmp_path: Path) -> None:
    _write_ready_repo(tmp_path)

    code = run_pipeline_main(
        [
            "--repo-root",
            str(tmp_path),
            "--mode",
            "lock-scene-clip",
            "--scene-id",
            "SC0001",
            "--locked-by",
            "operator_pr",
            "--locked-at",
            "2026-04-30T00:00:00Z",
        ]
    )

    assert code == 0
    assert (tmp_path / "visual_dev/omni_sets/SC0001/selected_take.yaml").exists()
    assert (tmp_path / "evidence/scene_clip_map.csv").exists()
    assert not list(tmp_path.rglob("*.mp4"))
    assert not list(tmp_path.rglob("*.mov"))
    assert not list(tmp_path.rglob("*.mkv"))
    assert not list(tmp_path.rglob("*.wav"))


def test_no_selected_take_blocks_safely(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _video_takes_payload()
    payload["selected_take"] = None
    payload["takes"][1]["status"] = "candidate"
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", payload)

    with pytest.raises(SceneClipLockingError, match="no selected_take"):
        SceneClipLockingAgent(tmp_path).lock_scene_clip(
            scene_id="SC0001",
            locked_by="human_operator",
        )

    assert not list(tmp_path.rglob("selected_take.yaml"))
    assert not (tmp_path / "evidence/scene_clip_map.csv").exists()


def test_two_selected_takes_block_safely(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _video_takes_payload()
    payload["takes"][0]["status"] = "selected"
    payload["takes"][0]["failure_reason"] = None
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", payload)

    with pytest.raises(SceneClipLockingError, match="exactly one selected"):
        SceneClipLockingAgent(tmp_path).lock_scene_clip(
            scene_id="SC0001",
            locked_by="human_operator",
        )


def test_selected_take_missing_external_storage_ref_blocks(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _video_takes_payload()
    payload["takes"][1]["external_storage_ref"] = None
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", payload)

    with pytest.raises(SceneClipLockingError, match="external_storage_ref"):
        SceneClipLockingAgent(tmp_path).lock_scene_clip(
            scene_id="SC0001",
            locked_by="human_operator",
        )


def test_repo_binary_committed_true_blocks(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _video_takes_payload()
    payload["takes"][1]["repo_binary_committed"] = True
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", payload)

    with pytest.raises(SceneClipLockingError, match="repo_binary_committed"):
        SceneClipLockingAgent(tmp_path).lock_scene_clip(
            scene_id="SC0001",
            locked_by="human_operator",
        )


def test_graph_mode_delegates_scene_clip_locking(tmp_path: Path) -> None:
    _write_ready_repo(tmp_path)

    result = run_graph(
        PipelineState(
            repo_root=str(tmp_path),
            mode="lock-scene-clip",
            scene_ids=["SC0001"],
            locked_by="human_operator",
            locked_at="2026-04-30T00:00:00Z",
        )
    )

    assert result.errors == []
    assert "visual_dev/omni_sets/SC0001/selected_take.yaml" in result.written_files
    assert "evidence/scene_clip_map.csv" in result.written_files


def test_production_validator_rejects_bad_scene_clip_map(tmp_path: Path) -> None:
    _write_ready_repo(tmp_path)
    (tmp_path / "evidence").mkdir(exist_ok=True)
    (tmp_path / "evidence/scene_clip_map.csv").write_text(
        "scene_id,selected_take,prompt_id,external_storage_ref,platform_asset_ref,local_proxy_ref,repo_binary_committed,lock_status\n"
        "SC0001,SC0001_TAKE002,SC0001__omni-kling-omni__v01,dvc://x,kling://x,,true,locked_metadata_only\n",
        encoding="utf-8",
    )
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/selected_take.yaml",
        {
            "scene_id": "SC0001",
            "selected_take": "SC0001_TAKE002",
            "source_video_takes": "visual_dev/omni_sets/SC0001/video_takes.yaml",
            "prompt_id": PROMPT_ID,
            "platform_asset_ref": "kling://x",
            "external_storage_ref": "dvc://x",
            "local_proxy_ref": None,
            "repo_binary_committed": False,
            "lock_status": "locked_metadata_only",
            "locked_by": "human_operator",
            "locked_at": "2026-04-30T00:00:00Z",
            "storage_policy": "external_video_only",
            "notes": "Metadata-only lock.",
        },
    )

    report = run_validation(tmp_path)

    assert report.invalid_files >= 1
    assert any("repo_binary_committed" in issue.field_path for issue in report.issues)


def test_production_validator_rejects_local_proxy_repo_binary_path(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/selected_take.yaml",
        {
            "scene_id": "SC0001",
            "selected_take": "SC0001_TAKE002",
            "source_video_takes": "visual_dev/omni_sets/SC0001/video_takes.yaml",
            "prompt_id": PROMPT_ID,
            "platform_asset_ref": "kling://x",
            "external_storage_ref": "dvc://x",
            "local_proxy_ref": "post/edit/proxies/SC0001/proxy.mp4",
            "repo_binary_committed": False,
            "lock_status": "locked_metadata_only",
            "locked_by": "human_operator",
            "locked_at": "2026-04-30T00:00:00Z",
            "storage_policy": "external_video_only",
            "notes": "Bad: local_proxy_ref points to a repo video binary.",
        },
    )
    (tmp_path / "evidence/scene_clip_map.csv").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "evidence/scene_clip_map.csv").write_text(
        "scene_id,selected_take,prompt_id,external_storage_ref,platform_asset_ref,local_proxy_ref,repo_binary_committed,lock_status\n"
        "SC0001,SC0001_TAKE002,SC0001__omni-kling-omni__v01,dvc://x,kling://x,,false,locked_metadata_only\n",
        encoding="utf-8",
    )

    report = run_validation(tmp_path)

    assert report.invalid_files >= 1
    assert any("local_proxy_ref" in issue.field_path for issue in report.issues)
