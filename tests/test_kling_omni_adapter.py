from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.adapters.kling_omni import (  # noqa: E402
    KlingOmniAdapter,
    KlingOmniAdapterError,
)
from scripts.agents.critic import CriticAgent  # noqa: E402
from scripts.agents.graph import run_graph  # noqa: E402
from scripts.agents.run_pipeline import main as run_pipeline_main  # noqa: E402
from scripts.agents.state import PipelineState  # noqa: E402


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_core_files(repo_root: Path) -> None:
    for path in (
        "schemas/prompt_record.schema.json",
        "schemas/prompt_run.schema.json",
        "docs/model_guides/kling_omni.yaml",
        "docs/model_guides/model_capability_matrix.yaml",
    ):
        out_path = repo_root / path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text((REPO_ROOT / path).read_text(encoding="utf-8"), encoding="utf-8")


def _scene_card(*, shot_list: list[dict] | None = None) -> dict:
    return {
        "scene_id": "SC0001",
        "title": "Vale Residence Morning Inventory",
        "purpose": "Establish a contained domestic routine and a concrete object deviation.",
        "excerpt_ref": "scene_excerpt.md",
        "omni_set_ref": "visual_dev/omni_sets/SC0001/",
        "visual_targets": {
            "palette": "Pale stone and muted domestic neutrals.",
            "framing_bias": "Thresholds, corridor depth, and doorways.",
            "movement_bias": "Minimal, exact movement aligned to route logic.",
            "lighting_bias": "Filtered early daylight and low-key interior practicals.",
        },
        "shot_list_omni": shot_list if shot_list is not None else [],
        "canon_lock": False,
    }


def _shot_list() -> list[dict]:
    return [
        {
            "shot_id": "SC0001_OMNI01",
            "role": "establish_coverage",
            "subject": "Nadia crosses the kitchen passage and notices the photograph.",
            "camera_angle": "Static close coverage at the doorway.",
            "framing": "Doorway threshold geometry with the frame visible.",
            "camera_movement": "Minimal forward drift.",
            "lighting": "Filtered early daylight and low-key interior practicals.",
            "duration_seconds": 5,
            "source_storyboard_option": "SC0001_SB01",
            "source_coverage_role": "establish_coverage",
        }
    ]


def _multi_shot_list(*, shot_count: int, duration_seconds: int) -> list[dict]:
    return [
        {
            "shot_id": f"SC0001_OMNI{index:02d}",
            "role": f"coverage_{index}",
            "subject": f"Nadia source-grounded coverage beat {index}.",
            "camera_angle": "Static close coverage at the doorway.",
            "framing": "Doorway threshold geometry with the frame visible.",
            "camera_movement": "Minimal forward drift.",
            "lighting": "Filtered early daylight and low-key interior practicals.",
            "duration_seconds": duration_seconds,
            "source_storyboard_option": "SC0001_SB01",
            "source_coverage_role": f"coverage_{index}",
        }
        for index in range(1, shot_count + 1)
    ]


def _write_ready_scene(
    repo_root: Path,
    *,
    locked_packs: bool = True,
    shot_list: list[dict] | None = None,
) -> tuple[Path, Path]:
    _copy_core_files(repo_root)
    scene_dir = repo_root / "planning/scenes/SC0001"
    scene_card = scene_dir / "scene_card.yaml"
    _write_yaml(scene_card, _scene_card(shot_list=shot_list or _shot_list()))
    (scene_dir / "scene_excerpt.md").write_text("Nadia notices the photograph.", encoding="utf-8")

    _write_yaml(
        repo_root / "visual_dev/storyboards/SC0001/storyboard_options.yaml",
        {
            "scene_id": "SC0001",
            "selected_option": "SC0001_SB01",
            "options": [{"option_id": "SC0001_SB01"}],
        },
    )
    _write_yaml(
        repo_root / "visual_dev/storyboards/SC0001/shot_list_omni_suggestion.yaml",
        {"scene_id": "SC0001", "source_storyboard_option": "SC0001_SB01"},
    )
    _write_yaml(
        repo_root / "visual_dev/omni_sets/SC0001/element_set.yaml",
        {
            "scene_id": "SC0001",
            "element_refs": [
                "visual_dev/omni_sets/SC0001/elements_used/C01_nadia.yaml",
                "visual_dev/omni_sets/SC0001/elements_used/LOC001_vale.yaml",
            ],
        },
    )
    _write_yaml(
        repo_root / "visual_dev/omni_sets/SC0001/elements_used/C01_nadia.yaml",
        {"pack_path_expected": "visual_dev/elements/characters/C01/"},
    )
    _write_yaml(
        repo_root / "visual_dev/omni_sets/SC0001/elements_used/LOC001_vale.yaml",
        {"pack_path_expected": "visual_dev/elements/locations/LOC001/"},
    )
    for pack_path in (
        repo_root / "visual_dev/elements/characters/C01/pack_manifest.yaml",
        repo_root / "visual_dev/elements/locations/LOC001/pack_manifest.yaml",
    ):
        _write_yaml(
            pack_path,
            {
                "element_id": pack_path.parent.name,
                "pack_status": "locked" if locked_packs else "metadata_only",
                "approved": True,
                "locked": True,
            },
        )
    return scene_card, repo_root / "visual_dev/elements/characters/C01/pack_manifest.yaml"


def test_empty_shot_list_blocks_without_prompt_written(tmp_path: Path) -> None:
    _copy_core_files(tmp_path)
    scene_dir = tmp_path / "planning/scenes/SC0001"
    _write_yaml(scene_dir / "scene_card.yaml", _scene_card(shot_list=[]))
    (scene_dir / "scene_excerpt.md").write_text("Scene excerpt.", encoding="utf-8")

    with pytest.raises(KlingOmniAdapterError, match="shot_list_omni is empty"):
        KlingOmniAdapter(tmp_path).generate("SC0001")

    assert not list((tmp_path / "prompts").rglob("*.yaml"))
    assert not list((tmp_path / "evidence").rglob("*.yaml"))


def test_non_empty_shot_list_builds_critic_passing_prompt(tmp_path: Path) -> None:
    _write_ready_scene(tmp_path)

    result = KlingOmniAdapter(tmp_path).generate("SC0001", run_at="2026-04-30T00:00:00Z")
    critic_result = CriticAgent(tmp_path).check(result.prompt_record)

    assert critic_result.passed, critic_result.hard_errors
    assert result.prompt_record["prompt_type"] == "omni_instruction"
    assert result.prompt_record["lifecycle_stage"] == "draft"
    assert result.prompt_record["target_models"] == ["kling_omni"]
    assert "SC0001" not in result.prompt_record["prompt_text"]
    assert "C01" not in result.prompt_record["prompt_text"]
    assert "LOC001" not in result.prompt_record["prompt_text"]
    assert result.run_record["model"] == "kling_omni"
    assert result.run_record["status"] == "pending"
    assert result.run_record["outputs_expected"] == 1
    assert result.prompt_record["expected_output"]["duration_seconds"] == 5
    assert "Shot 1 (5s):" in result.prompt_record["prompt_text"]


def test_unlocked_pack_blocks_without_modifying_pack_manifest(tmp_path: Path) -> None:
    _, pack_manifest = _write_ready_scene(tmp_path, locked_packs=False)
    before_pack = pack_manifest.read_text(encoding="utf-8")

    with pytest.raises(KlingOmniAdapterError, match="pack_status"):
        KlingOmniAdapter(tmp_path).generate("SC0001")

    assert pack_manifest.read_text(encoding="utf-8") == before_pack
    assert not list((tmp_path / "prompts").rglob("*.yaml"))


def test_run_pipeline_writes_draft_prompt_and_run_record_only(tmp_path: Path) -> None:
    scene_card, pack_manifest = _write_ready_scene(tmp_path)
    before_scene = scene_card.read_text(encoding="utf-8")
    before_pack = pack_manifest.read_text(encoding="utf-8")

    code = run_pipeline_main(
        [
            "--repo-root",
            str(tmp_path),
            "--mode",
            "generate-kling-omni-prompts",
            "--scene-id",
            "SC0001",
        ]
    )

    prompt_path = tmp_path / "prompts/draft/SC0001__omni-kling-omni__v01.yaml"
    run_path = tmp_path / "evidence/prompt_runs/RUN_SC0001_KO_0001.yaml"
    assert code == 0
    assert prompt_path.exists()
    assert run_path.exists()
    assert yaml.safe_load(prompt_path.read_text(encoding="utf-8"))["target_models"] == [
        "kling_omni"
    ]
    assert yaml.safe_load(run_path.read_text(encoding="utf-8"))["status"] == "pending"
    assert scene_card.read_text(encoding="utf-8") == before_scene
    assert pack_manifest.read_text(encoding="utf-8") == before_pack


def test_graph_mode_delegates_kling_prompt_generation(tmp_path: Path) -> None:
    _write_ready_scene(tmp_path)

    result = run_graph(
        PipelineState(
            repo_root=str(tmp_path),
            mode="generate-kling-omni-prompts",
            scene_ids=["SC0001"],
        )
    )

    assert result.errors == []
    assert "prompts/draft/SC0001__omni-kling-omni__v01.yaml" in result.written_files
    assert "evidence/prompt_runs/RUN_SC0001_KO_0001.yaml" in result.written_files


def test_no_video_or_clip_locking_files_created(tmp_path: Path) -> None:
    _write_ready_scene(tmp_path)

    run_pipeline_main(
        [
            "--repo-root",
            str(tmp_path),
            "--mode",
            "generate-kling-omni-prompts",
            "--scene-id",
            "SC0001",
        ]
    )

    assert not list(tmp_path.rglob("*.mp4"))
    assert not list(tmp_path.rglob("*.mov"))
    assert not list(tmp_path.rglob("video_takes.yaml"))
    assert not list(tmp_path.rglob("selected_take.yaml"))
    assert not (tmp_path / "evidence/scene_clip_map.csv").exists()


def test_fifteen_second_five_shot_prompt_is_accepted(tmp_path: Path) -> None:
    scene_card, _ = _write_ready_scene(
        tmp_path,
        shot_list=_multi_shot_list(shot_count=5, duration_seconds=3),
    )
    before_scene = scene_card.read_text(encoding="utf-8")

    result = KlingOmniAdapter(tmp_path).generate("SC0001", run_at="2026-04-30T00:00:00Z")

    prompt_text = result.prompt_record["prompt_text"]
    assert "Total duration: 15 seconds." in prompt_text
    assert "Shot 1 (3s):" in prompt_text
    assert "Shot 5 (3s):" in prompt_text
    assert "Filtered early daylight" in prompt_text
    assert "settled state" in prompt_text
    assert "Do not add new story facts." in prompt_text
    assert result.prompt_record["expected_output"]["duration_seconds"] == 15
    assert scene_card.read_text(encoding="utf-8") == before_scene


def test_duration_overflow_blocks_without_clamping(tmp_path: Path) -> None:
    _write_ready_scene(tmp_path, shot_list=_multi_shot_list(shot_count=4, duration_seconds=4))

    with pytest.raises(KlingOmniAdapterError, match="exceeds max 15s"):
        KlingOmniAdapter(tmp_path).generate("SC0001")


@pytest.mark.parametrize(
    ("shot_list", "expected_error"),
    [
        (_multi_shot_list(shot_count=6, duration_seconds=1), "max allowed is 5"),
        (_multi_shot_list(shot_count=7, duration_seconds=2), "max allowed is 6"),
        (_multi_shot_list(shot_count=3, duration_seconds=1), "max allowed is 2"),
    ],
)
def test_shot_count_limit_blocks_by_total_duration(
    tmp_path: Path,
    shot_list: list[dict],
    expected_error: str,
) -> None:
    _write_ready_scene(tmp_path, shot_list=shot_list)

    with pytest.raises(KlingOmniAdapterError, match=expected_error):
        KlingOmniAdapter(tmp_path).generate("SC0001")


@pytest.mark.parametrize(
    "bad_duration",
    [None, "3", 0, -1, 1.5],
)
def test_invalid_duration_seconds_blocks(tmp_path: Path, bad_duration: object) -> None:
    shot_list = _multi_shot_list(shot_count=1, duration_seconds=3)
    if bad_duration is None:
        shot_list[0].pop("duration_seconds")
    else:
        shot_list[0]["duration_seconds"] = bad_duration
    _write_ready_scene(tmp_path, shot_list=shot_list)

    with pytest.raises(KlingOmniAdapterError, match="duration_seconds"):
        KlingOmniAdapter(tmp_path).generate("SC0001")
