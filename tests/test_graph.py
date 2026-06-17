from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.graph import SUPPORTED_GRAPH_MODES, run_graph  # noqa: E402
from scripts.agents.state import PipelineState  # noqa: E402


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_scene(repo_root: Path, scene_id: str = "SC0001") -> None:
    scene_dir = repo_root / "planning" / "scenes" / scene_id
    _write_yaml(
        scene_dir / "scene_card.yaml",
        {
            "scene_id": scene_id,
            "excerpt_ref": "scene_excerpt.md",
            "visual_targets": {
                "palette": "Muted domestic neutrals.",
                "lens_bias": "Static close coverage.",
                "framing_bias": "Doorway threshold geometry.",
                "movement_bias": "Minimal movement.",
                "lighting_bias": "Soft morning daylight.",
            },
        },
    )
    (scene_dir / "scene_excerpt.md").write_text("Scene excerpt.", encoding="utf-8")


def test_pipeline_state_serializes_to_dict(tmp_path: Path) -> None:
    state = PipelineState(
        repo_root=str(tmp_path),
        mode="operator-next-step",
        scene_ids=["SC0001"],
        models=["midjourney"],
        prompt_ids=["SC0001__t2i-char-c01-midjourney__v01"],
        current_task="blocked",
        written_files=["evidence/example.yaml"],
        skipped=["not ready"],
        errors=[],
        next_step={"current_task": "blocked"},
    )

    payload = state.to_dict()
    restored = PipelineState.from_dict(payload)

    assert payload["repo_root"] == str(tmp_path)
    assert restored.scene_ids == ["SC0001"]
    assert restored.next_step == {"current_task": "blocked"}


def test_graph_operator_next_step_empty_repo_returns_blocked(tmp_path: Path) -> None:
    result = run_graph(
        PipelineState(
            repo_root=str(tmp_path),
            mode="operator-next-step",
        )
    )

    assert result.errors == []
    assert result.current_task == "blocked"
    assert result.next_step is not None
    assert result.next_step["current_task"] == "blocked"


def test_graph_future_render_modes_are_not_supported(tmp_path: Path) -> None:
    result = run_graph(
        PipelineState(
            repo_root=str(tmp_path),
            mode="render-final-film",
            scene_ids=["SC0001"],
        )
    )

    assert "render-final-film" not in SUPPORTED_GRAPH_MODES
    assert result.errors
    assert "Unsupported graph mode" in result.errors[0]
    assert not list(tmp_path.rglob("video_takes.yaml"))
    assert not list(tmp_path.rglob("selected_take.yaml"))
