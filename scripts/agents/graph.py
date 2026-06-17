"""
Batch 7 orchestration wrapper.

This module provides a LangGraph-compatible control-flow layer around existing
agent/CLI functions. It adds no new production logic and does not bypass critic,
writer, review, storage, or lifecycle boundaries.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from scripts.agents.operator_next_step import recommend_next_step
from scripts.agents.run_pipeline import (
    PipelineError,
    run_generate_kling_omni_prompts,
    run_generate_prompts,
    run_lock_scene_clip,
    run_refresh_model_guidance,
    run_review_outputs,
    run_review_video_takes,
)
from scripts.agents.state import PipelineState


SUPPORTED_GRAPH_MODES = {
    "refresh-model-guidance",
    "generate-prompts",
    "review-outputs",
    "generate-kling-omni-prompts",
    "review-video-takes",
    "lock-scene-clip",
    "operator-next-step",
}


def langgraph_available() -> bool:
    try:
        import langgraph.graph  # noqa: F401
    except ImportError:
        return False
    return True


def _first(items: list[str]) -> str | None:
    return items[0] if items else None


def _namespace(state: PipelineState) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=Path(state.repo_root),
        mode=state.mode,
        format=state.output_format,
        models=",".join(state.models) if state.models else None,
        save_snapshot=state.save_snapshot,
        scene_id=_first(state.scene_ids),
        scene_ids=",".join(state.scene_ids) if len(state.scene_ids) > 1 else None,
        model_guidance_snapshot_dir=state.model_guidance_snapshot_dir,
        model_guidance_snapshots=state.model_guidance_snapshots,
        prompt_id=_first(state.prompt_ids),
        images=state.images,
        review_notes=state.review_notes,
        takes_metadata=state.takes_metadata,
        locked_by=state.locked_by,
        locked_at=state.locked_at,
    )


def _copy_result(state: PipelineState, *, message: str, written: list[str], skipped: list[str]) -> PipelineState:
    state.current_task = state.mode
    state.written_files.extend(written)
    state.skipped.extend(skipped)
    state.next_step = {
        "current_task": state.mode,
        "message": message,
        "written_files": list(written),
        "skipped": list(skipped),
    }
    return state


def _run_operator_next_step(state: PipelineState) -> PipelineState:
    step = recommend_next_step(Path(state.repo_root))
    state.current_task = step.current_task
    state.next_step = step.to_dict()
    return state


def _run_pipeline_result(
    state: PipelineState,
    runner: Callable[[argparse.Namespace], Any],
) -> PipelineState:
    result = runner(_namespace(state))
    return _copy_result(
        state,
        message=result.message,
        written=list(result.written_files),
        skipped=list(result.skipped),
    )


def run_graph_state(state: PipelineState) -> PipelineState:
    """Run one supported mode through the Batch 7 orchestration wrapper."""
    if state.mode not in SUPPORTED_GRAPH_MODES:
        state.errors.append(
            f"Unsupported graph mode: {state.mode}. Future production modes are not implemented in Batch 7."
        )
        return state

    try:
        if state.mode == "operator-next-step":
            return _run_operator_next_step(state)
        if state.mode == "refresh-model-guidance":
            return _run_pipeline_result(state, run_refresh_model_guidance)
        if state.mode == "generate-prompts":
            return _run_pipeline_result(state, run_generate_prompts)
        if state.mode == "review-outputs":
            return _run_pipeline_result(state, run_review_outputs)
        if state.mode == "generate-kling-omni-prompts":
            return _run_pipeline_result(state, run_generate_kling_omni_prompts)
        if state.mode == "review-video-takes":
            return _run_pipeline_result(state, run_review_video_takes)
        if state.mode == "lock-scene-clip":
            return _run_pipeline_result(state, run_lock_scene_clip)
    except (PipelineError, OSError, ValueError, ImportError) as exc:
        state.errors.append(str(exc))
    return state


class FallbackGraph:
    """Small invoke-compatible runner used when LangGraph is unavailable."""

    def invoke(self, input_state: PipelineState | dict[str, Any]) -> dict[str, Any]:
        state = (
            input_state
            if isinstance(input_state, PipelineState)
            else PipelineState.from_dict(input_state)
        )
        return run_graph_state(state).to_dict()


def build_graph() -> Any:
    """
    Build a LangGraph StateGraph when available, otherwise return FallbackGraph.

    The LangGraph path uses one dispatch node so behavior stays identical to
    the fallback runner and all production logic remains in existing agents.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return FallbackGraph()

    def dispatch(data: dict[str, Any]) -> dict[str, Any]:
        return run_graph_state(PipelineState.from_dict(data)).to_dict()

    graph = StateGraph(dict)
    graph.add_node("dispatch", dispatch)
    graph.set_entry_point("dispatch")
    graph.add_edge("dispatch", END)
    return graph.compile()


def run_graph(input_state: PipelineState | dict[str, Any]) -> PipelineState:
    """Run through the available graph implementation and return PipelineState."""
    graph = build_graph()
    payload = (
        input_state.to_dict()
        if isinstance(input_state, PipelineState)
        else PipelineState.from_dict(input_state).to_dict()
    )
    result = graph.invoke(payload)
    return PipelineState.from_dict(result)
