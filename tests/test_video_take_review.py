from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.graph import run_graph  # noqa: E402
from scripts.agents.run_pipeline import main as run_pipeline_main  # noqa: E402
from scripts.agents.state import PipelineState  # noqa: E402
from scripts.agents.video_take_review import VideoTakeReviewAgent  # noqa: E402
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
        "batch_job.schema.json",
        "operator_session.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _quality_scores(value: int = 4) -> dict[str, int]:
    return {
        "identity_consistency": value,
        "source_grounding": value,
        "style_compliance": value,
        "continuity": value,
        "production_usability": value,
    }


def _take(
    take_id: str = "SC0001_TAKE001",
    *,
    status: str = "selected",
    external_storage_ref: str | None = "dvc://closing-price/SC0001/take001.mp4",
    platform_asset_ref: str | None = "kling://job-001",
    storage_status: str = "stored_external",
    repo_binary_committed: bool = False,
    failure_reason: str | None = None,
) -> dict:
    return {
        "take_id": take_id,
        "platform_asset_ref": platform_asset_ref,
        "external_storage_ref": external_storage_ref,
        "local_proxy_ref": None,
        "repo_binary_committed": repo_binary_committed,
        "storage_status": storage_status,
        "status": status,
        "reason": "Human review metadata for the external Kling take.",
        "quality_scores": _quality_scores(),
        "failure_reason": failure_reason,
    }


def _valid_video_takes() -> dict:
    return {
        "scene_id": "SC0001",
        "prompt_id": PROMPT_ID,
        "takes": [
            _take("SC0001_TAKE001", status="rejected", failure_reason="camera_drift"),
            _take("SC0001_TAKE002", status="selected"),
        ],
        "selected_take": "SC0001_TAKE002",
        "round_status": "complete",
        "needs_prompt_revision": False,
        "storage_policy": "external_video_only",
    }


def _write_review_inputs(repo_root: Path, payload: dict | None = None) -> tuple[Path, Path]:
    takes_path = repo_root / "handoff/takes.yaml"
    notes_path = repo_root / "evidence/video_reviews/SC0001_review_notes.md"
    _write_yaml(takes_path, payload or {"takes": _valid_video_takes()["takes"]})
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text("Human video review notes.", encoding="utf-8")
    return takes_path, notes_path


def test_valid_takes_metadata_writes_schema_valid_video_takes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    takes_path, notes_path = _write_review_inputs(tmp_path)

    result = VideoTakeReviewAgent(tmp_path).write_review(
        scene_id="SC0001",
        prompt_id=PROMPT_ID,
        takes_metadata_path=takes_path,
        review_notes_path=notes_path,
    )

    payload = yaml.safe_load(result.video_takes_path.read_text(encoding="utf-8"))
    report = run_validation(tmp_path)
    assert payload["selected_take"] == "SC0001_TAKE002"
    assert payload["needs_prompt_revision"] is False
    assert result.review_path.exists()
    assert report.invalid_files == 0


def test_two_selected_takes_fail_validation(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_video_takes()
    payload["takes"][0]["status"] = "selected"
    payload["takes"][0]["failure_reason"] = None
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any("At most one" in issue.message for issue in report.issues)


def test_selected_take_not_matching_selected_status_fails_validation(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_video_takes()
    payload["selected_take"] = "SC0001_TAKE001"
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any("must match" in issue.message for issue in report.issues)


def test_repo_binary_committed_true_fails_validation(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_video_takes()
    payload["takes"][1]["repo_binary_committed"] = True
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any("repo_binary_committed" in issue.field_path for issue in report.issues)


def test_missing_external_storage_ref_fails_unless_pending_candidate(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    invalid = _valid_video_takes()
    invalid["takes"][1]["external_storage_ref"] = None
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", invalid)
    assert run_validation(tmp_path).invalid_files == 1

    valid_pending = _valid_video_takes()
    valid_pending["takes"] = [
        _take(
            "SC0001_TAKE001",
            status="candidate",
            external_storage_ref=None,
            platform_asset_ref=None,
            storage_status="pending_external",
        )
    ]
    valid_pending["selected_take"] = None
    valid_pending["round_status"] = "in_progress"
    valid_pending["needs_prompt_revision"] = False
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml", valid_pending)

    assert run_validation(tmp_path).invalid_files == 0


def test_needs_prompt_revision_true_writes_corrected_brief(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    takes_path, notes_path = _write_review_inputs(
        tmp_path,
        {
            "takes": [
                _take(
                    "SC0001_TAKE001",
                    status="needs_revision",
                    failure_reason="camera_drift",
                )
            ],
            "needs_prompt_revision": True,
        },
    )

    result = VideoTakeReviewAgent(tmp_path).write_review(
        scene_id="SC0001",
        prompt_id=PROMPT_ID,
        takes_metadata_path=takes_path,
        review_notes_path=notes_path,
    )

    assert result.corrected_brief_path is not None
    assert result.corrected_brief_path.name == "SC0001__omni-kling-omni__v02_brief.yaml"
    brief = yaml.safe_load(result.corrected_brief_path.read_text(encoding="utf-8"))
    assert brief["source_prompt_id"] == PROMPT_ID
    assert brief["corrected_brief"]["failed_take_ids"] == ["SC0001_TAKE001"]
    assert run_validation(tmp_path).invalid_files == 0


def test_cli_review_video_takes_does_not_modify_scene_or_prompt_records(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    scene_card = tmp_path / "planning/scenes/SC0001/scene_card.yaml"
    prompt_record = tmp_path / "prompts/draft/SC0001__omni-kling-omni__v01.yaml"
    _write_yaml(scene_card, {"scene_id": "SC0001", "shot_list_omni": [{"shot_id": "x"}]})
    _write_yaml(prompt_record, {"prompt_id": PROMPT_ID, "lifecycle_stage": "draft"})
    before_scene = scene_card.read_text(encoding="utf-8")
    before_prompt = prompt_record.read_text(encoding="utf-8")
    takes_path, notes_path = _write_review_inputs(tmp_path)

    code = run_pipeline_main(
        [
            "--repo-root",
            str(tmp_path),
            "--mode",
            "review-video-takes",
            "--scene-id",
            "SC0001",
            "--prompt-id",
            PROMPT_ID,
            "--takes-metadata",
            takes_path.relative_to(tmp_path).as_posix(),
            "--review-notes",
            notes_path.relative_to(tmp_path).as_posix(),
        ]
    )

    assert code == 0
    assert (tmp_path / "visual_dev/omni_sets/SC0001/video_takes.yaml").exists()
    assert scene_card.read_text(encoding="utf-8") == before_scene
    assert prompt_record.read_text(encoding="utf-8") == before_prompt
    assert not list(tmp_path.rglob("*.mp4"))
    assert not list(tmp_path.rglob("*.mov"))
    assert not list(tmp_path.rglob("*.mkv"))
    assert not list(tmp_path.rglob("*.wav"))
    assert not list(tmp_path.rglob("selected_take.yaml"))
    assert not (tmp_path / "evidence/scene_clip_map.csv").exists()


def test_graph_mode_delegates_video_take_review(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    takes_path, notes_path = _write_review_inputs(tmp_path)

    result = run_graph(
        PipelineState(
            repo_root=str(tmp_path),
            mode="review-video-takes",
            scene_ids=["SC0001"],
            prompt_ids=[PROMPT_ID],
            takes_metadata=takes_path.relative_to(tmp_path).as_posix(),
            review_notes=notes_path.relative_to(tmp_path).as_posix(),
        )
    )

    assert result.errors == []
    assert "visual_dev/omni_sets/SC0001/video_takes.yaml" in result.written_files
    assert not list(tmp_path.rglob("selected_take.yaml"))
    assert not (tmp_path / "evidence/scene_clip_map.csv").exists()
