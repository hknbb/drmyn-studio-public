"""
Thin metadata-only production pipeline CLI.

This module exposes implemented agent steps behind one argparse entry point.
It does not run external platforms, move binaries, create video/proxy binaries,
select storyboard options, or promote lifecycle state. Clip locking is
metadata-only: it writes selected_take.yaml and scene_clip_map.csv only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.adapters import MODEL_ALIAS_MAP, get_adapter, resolve_model_key
from scripts.agents.adapters._base import BriefNotReadyError
from scripts.agents.copilot_command import apply_command
from scripts.agents.adapters.kling_omni import KlingOmniAdapter
from scripts.agents.critic import CriticAgent
from scripts.agents.model_research import ModelResearchAgent, find_latest_snapshot
from scripts.agents.neutral_brief import NeutralBriefAgent
from scripts.agents.operator_next_step import recommend_next_step
from scripts.agents.scene_readiness import compute_scene_readiness, render_report
from scripts.agents.pr_helper import suggest_pr
from scripts.agents.review_outputs import ImageReviewAgent, QUALITY_SCORE_FIELDS
from scripts.agents.scene_clip_locking import SceneClipLockingAgent
from scripts.agents.shot_list_omni_suggestion import ShotListOmniSuggestionAgent
from scripts.agents.source_context import SourceContextAgent
from scripts.agents.storyboard_options import StoryboardOptionsAgent
from scripts.agents.writer import PromptWriter
from scripts.agents.video_take_review import VideoTakeReviewAgent


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
PROMPT_ID_RE = re.compile(
    r"^(?P<scene_id>SC\d{4})__(?P<body>[a-z0-9\-]+)__v(?P<version>\d{2})$"
)


class PipelineError(ValueError):
    """Raised when a CLI mode cannot run safely."""


@dataclass(frozen=True)
class PipelineResult:
    mode: str
    written_files: list[str]
    skipped: list[str]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _model_ids(values: list[str]) -> list[str]:
    model_ids: list[str] = []
    for value in values:
        key = resolve_model_key(value)
        model_ids.append(MODEL_ALIAS_MAP[key]["model_id"])
    return model_ids


def _parse_snapshot_mapping(value: str | None, repo_root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in _split_csv(value):
        if "=" not in item:
            raise PipelineError(
                "--model-guidance-snapshots entries must use model=path format"
            )
        model, raw_path = item.split("=", 1)
        key = resolve_model_key(model.strip())
        model_id = MODEL_ALIAS_MAP[key]["model_id"]
        path = (repo_root / raw_path.strip()).resolve()
        if not path.exists():
            raise PipelineError(f"Snapshot path not found: {raw_path.strip()}")
        mapping[model_id] = _relative(path, repo_root)
    return mapping


def _snapshot_for_model(
    *,
    repo_root: Path,
    model_id: str,
    snapshot_dir: Path | None,
    mapping: dict[str, str],
) -> str | None:
    if model_id in mapping:
        return mapping[model_id]
    if snapshot_dir is None:
        return None
    snapshot = find_latest_snapshot(snapshot_dir, model_id)
    if snapshot is None:
        raise PipelineError(
            f"No model guidance snapshot found for {model_id} in {snapshot_dir}"
        )
    return _relative(snapshot.resolve(), repo_root)


def _scene_ids(args: argparse.Namespace) -> list[str]:
    scene_ids = []
    if args.scene_id:
        scene_ids.append(args.scene_id)
    scene_ids.extend(_split_csv(args.scene_ids))
    seen: set[str] = set()
    deduped: list[str] = []
    for scene_id in scene_ids:
        if scene_id not in seen:
            seen.add(scene_id)
            deduped.append(scene_id)
    if not deduped:
        raise PipelineError("Provide --scene-id or --scene-ids.")
    return deduped


def _print_result(result: PipelineResult, output_format: str = "text") -> None:
    if output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    print(f"mode: {result.mode}")
    print(f"message: {result.message}")
    print("written_files:")
    for path in result.written_files:
        print(f"- {path}")
    if result.skipped:
        print("skipped:")
        for item in result.skipped:
            print(f"- {item}")


def run_refresh_model_guidance(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    raw_models = _split_csv(args.models)
    if not raw_models:
        raise PipelineError("refresh-model-guidance requires --models.")
    models = _model_ids(raw_models)
    agent = ModelResearchAgent(repo_root)
    results = agent.run(models=models, save=args.save_snapshot)
    written = [
        _relative(path.resolve(), repo_root)
        for path in results.values()
        if isinstance(path, Path)
    ]
    message = (
        "Placeholder model guidance snapshots written; human verification required."
        if args.save_snapshot
        else "Dry run complete; no model guidance snapshots were written."
    )
    return PipelineResult(
        mode=args.mode,
        written_files=written,
        skipped=[],
        message=message,
    )


def run_generate_storyboard_options(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    if not args.scene_id:
        raise PipelineError("generate-storyboard-options requires --scene-id.")
    result = StoryboardOptionsAgent(repo_root).build(args.scene_id)
    selected = result.payload.get("selected_option")
    if selected is not None:
        raise PipelineError("StoryboardOptionsAgent returned a selected option unexpectedly.")
    return PipelineResult(
        mode=args.mode,
        written_files=[_relative(result.storyboard_options_path, repo_root)],
        skipped=[],
        message="Storyboard options written with selected_option left null.",
    )


def run_generate_shot_list_omni_suggestion(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    if not args.scene_id:
        raise PipelineError("generate-shot-list-omni-suggestion requires --scene-id.")
    result = ShotListOmniSuggestionAgent(repo_root).build(
        args.scene_id,
        target_duration_seconds=getattr(args, "target_duration_seconds", None) or 10,
    )
    return PipelineResult(
        mode=args.mode,
        written_files=[_relative(result.suggestion_path, repo_root)],
        skipped=[],
        message=(
            "Shot list Omni suggestion written; scene_card.yaml remains human-gated."
        ),
    )


def run_operator_next_step(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    if args.scene:
        if not re.fullmatch(r"SC\d{4}", args.scene):
            raise PipelineError(
                f"--scene expects an SC#### id (e.g. SC0001); got {args.scene!r}"
            )
        report = compute_scene_readiness(repo_root=repo_root, scene_id=args.scene)
        print(render_report(report, fmt=args.format))
        return 0
    step = recommend_next_step(repo_root)
    if args.format == "json":
        print(json.dumps(step.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(step.render())
    return 0


def run_copilot_command(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    if not args.command:
        raise PipelineError("copilot-command requires --command.")
    auto_handoff = getattr(args, "auto_handoff", True)
    result = apply_command(
        repo_root,
        command=args.command,
        target_agent=args.to_agent,
        reason=args.reason,
        session_id=args.session_id,
        note=args.note,
        auto_handoff=auto_handoff,
    )
    return PipelineResult(
        mode=args.mode,
        written_files=list(result.written_files),
        skipped=[],
        message=result.message,
    )


_PICKUP_ROLE_LABELS = {
    "claude_code": "Producer",
    "codex": "Critic",
    "gemini_code_assist": "Director",
}

_PICKUP_ALLOWED_AGENTS = frozenset({"claude_code", "codex", "gemini_code_assist"})


def run_pickup(args: argparse.Namespace) -> int:
    """Print a ready-to-use agent prompt from the latest matching open handoff."""
    repo_root = args.repo_root.resolve()
    agent_name = os.environ.get("CP_AGENT_NAME", "").strip()
    if not agent_name:
        print("error: CP_AGENT_NAME environment variable is not set.", file=sys.stderr)
        return 2
    if agent_name not in _PICKUP_ALLOWED_AGENTS:
        print(
            f"error: CP_AGENT_NAME '{agent_name}' is not a valid pickup agent. "
            f"Allowed: {', '.join(sorted(_PICKUP_ALLOWED_AGENTS))}",
            file=sys.stderr,
        )
        return 2

    handoffs_dir = repo_root / "evidence" / "agent_handoffs"
    if not handoffs_dir.is_dir():
        print("error: no evidence/agent_handoffs directory found.", file=sys.stderr)
        return 2

    candidates = sorted(handoffs_dir.glob("HO-*.yaml"), reverse=True)
    matched_path: Path | None = None
    matched_payload: dict | None = None
    for ho_path in candidates:
        try:
            payload = yaml.safe_load(ho_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("to_agent") == agent_name and payload.get("status") == "open":
            matched_path = ho_path
            matched_payload = payload
            break

    if matched_path is None or matched_payload is None:
        print(
            f"error: no open handoff found for agent '{agent_name}'.",
            file=sys.stderr,
        )
        return 2

    ho_rel = _relative(matched_path, repo_root)
    role_label = _PICKUP_ROLE_LABELS.get(agent_name, agent_name)
    current_task = matched_payload.get("current_task", "unknown")
    scene_id = matched_payload.get("scene_id", "n/a")
    branch = matched_payload.get("branch", "unknown")
    head_sha = matched_payload.get("head_sha", "unknown")
    context_files: list[str] = matched_payload.get("context_files", []) or []
    do_steps: list[str] = matched_payload.get("do_steps", []) or []
    expected_outputs: list[str] = matched_payload.get("expected_outputs", []) or []
    safety_warnings: list[str] = matched_payload.get("safety_warnings", []) or []

    context_lines = "\n".join(f"  - {f}" for f in context_files) or "  (none)"
    steps_lines = "\n".join(f"  - {s}" for s in do_steps) or "  (none)"
    outputs_lines = "\n".join(f"  - {o}" for o in expected_outputs) or "  (none)"
    warnings_lines = "\n".join(f"  - {w}" for w in safety_warnings) or "  (none)"

    prompt_block = f"""\
=== AGENT PICKUP PROMPT ===

Role: {agent_name} ({role_label})
Agent Role Contract: docs/operator_guides/agent_role_contract.md

Handoff: {ho_rel}
Current Task: {current_task}
Scene ID: {scene_id}
Branch: {branch}
Head SHA: {head_sha}

Context Files:
{context_lines}

Steps To Complete:
{steps_lines}

Expected Outputs:
{outputs_lines}

Safety Warnings:
{warnings_lines}

--- SCOPE GUARD ---
Read the handoff, verify branch/head_sha, inspect context_files and
safety_warnings. Complete only the listed expected_outputs.
Do not touch files outside the approved batch scope.
Do not promote lifecycle fields, pack locks, or copyright/provenance status.
Do not commit image, video, audio, or binary production outputs.
Do not modify prompts/prompt_library.yaml or visual_dev/elements/**.
---
"""
    print(prompt_block, end="")
    return 0


def run_suggest_pr(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    suggestion = suggest_pr(repo_root, branch=args.branch, base=args.base)
    message = "\n".join(
        [
            f"title: {suggestion.title}",
            f"command: {suggestion.gh_command_str}",
            "body:",
            *suggestion.body_lines,
        ]
    )
    return PipelineResult(
        mode=args.mode,
        written_files=[],
        skipped=list(suggestion.changed_files),
        message=message,
    )


def run_generate_prompts(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    raw_models = _split_csv(args.models)
    if not raw_models:
        raise PipelineError("generate-prompts requires --models.")

    scene_ids = _scene_ids(args)
    model_ids = _model_ids(raw_models)
    if "kling_omni" in model_ids:
        raise PipelineError("Kling Omni prompt generation is not implemented until Batch 8.")

    snapshot_dir = (
        (repo_root / args.model_guidance_snapshot_dir).resolve()
        if args.model_guidance_snapshot_dir
        else None
    )
    if snapshot_dir is not None and not snapshot_dir.is_dir():
        raise PipelineError(f"Snapshot directory not found: {args.model_guidance_snapshot_dir}")
    snapshot_mapping = _parse_snapshot_mapping(args.model_guidance_snapshots, repo_root)

    source_agent = SourceContextAgent(repo_root)
    brief_agent = NeutralBriefAgent(repo_root)
    critic = CriticAgent(repo_root)
    writer = PromptWriter(repo_root)

    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    skipped: list[str] = []
    run_counter = 1

    for scene_id in scene_ids:
        context = source_agent.build(scene_id)
        if context.escalate:
            skipped.append(f"{scene_id}: source context escalated: {context.missing_records}")
            continue
        briefs = brief_agent.build_scene_briefs(context)
        for brief in briefs:
            if not brief.is_ready:
                skipped.append(
                    f"{scene_id}: {brief.element_type}.{brief.element_id} not ready: {brief.warnings}"
                )
                continue
            for model_id in model_ids:
                snapshot = _snapshot_for_model(
                    repo_root=repo_root,
                    model_id=model_id,
                    snapshot_dir=snapshot_dir,
                    mapping=snapshot_mapping,
                )
                adapter = get_adapter(
                    model_id,
                    repo_root,
                    model_guidance_mode="dynamic_snapshot" if snapshot else "locked_guide",
                    model_guidance_snapshot=snapshot,
                )
                try:
                    prompt_record, run_record = adapter.generate(
                        brief,
                        version=1,
                        run_counter=run_counter,
                    )
                except BriefNotReadyError as exc:
                    skipped.append(str(exc))
                    continue
                result = critic.check(prompt_record)
                if not result.passed:
                    raise PipelineError(
                        "Critic rejected generated prompt "
                        f"{prompt_record.get('prompt_id')}: {result.hard_errors}"
                    )
                pending.append((prompt_record, run_record))
                run_counter += 1

    if not pending:
        raise PipelineError("No prompt records were generated; see skipped items.")

    written: list[str] = []
    for prompt_record, run_record in pending:
        write_result = writer.write(prompt_record, run_record)
        written.extend(
            [
                _relative(write_result.prompt_path, repo_root),
                _relative(write_result.run_path, repo_root),
            ]
        )

    return PipelineResult(
        mode=args.mode,
        written_files=written,
        skipped=skipped,
        message="Draft prompt records and prompt run records written.",
    )


def run_generate_kling_omni_prompts(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    scene_ids = _scene_ids(args)
    snapshot_dir = (
        (repo_root / args.model_guidance_snapshot_dir).resolve()
        if args.model_guidance_snapshot_dir
        else None
    )
    if snapshot_dir is not None and not snapshot_dir.is_dir():
        raise PipelineError(f"Snapshot directory not found: {args.model_guidance_snapshot_dir}")
    snapshot_mapping = _parse_snapshot_mapping(args.model_guidance_snapshots, repo_root)

    critic = CriticAgent(repo_root)
    writer = PromptWriter(repo_root)
    pending: list[tuple[dict[str, Any], dict[str, Any], list[str]]] = []
    run_counter = 1

    for scene_id in scene_ids:
        snapshot = _snapshot_for_model(
            repo_root=repo_root,
            model_id="kling_omni",
            snapshot_dir=snapshot_dir,
            mapping=snapshot_mapping,
        )
        adapter = KlingOmniAdapter(
            repo_root,
            model_guidance_mode="dynamic_snapshot" if snapshot else "locked_guide",
            model_guidance_snapshot=snapshot,
        )
        result = adapter.generate(scene_id, run_counter=run_counter)
        critic_result = critic.check(result.prompt_record)
        if not critic_result.passed:
            raise PipelineError(
                "Critic rejected generated Kling prompt "
                f"{result.prompt_record.get('prompt_id')}: {critic_result.hard_errors}"
            )
        pending.append((result.prompt_record, result.run_record, result.warnings))
        run_counter += 1

    written: list[str] = []
    skipped: list[str] = []
    for prompt_record, run_record, warnings in pending:
        write_result = writer.write(prompt_record, run_record)
        written.extend(
            [
                _relative(write_result.prompt_path, repo_root),
                _relative(write_result.run_path, repo_root),
            ]
        )
        skipped.extend(warnings)

    return PipelineResult(
        mode=args.mode,
        written_files=written,
        skipped=skipped,
        message="Draft Kling Omni prompt records written; external Kling was not run.",
    )


def _infer_review_target(prompt_id: str) -> tuple[str, str, str]:
    match = PROMPT_ID_RE.match(prompt_id)
    if not match:
        raise PipelineError(f"Invalid prompt id: {prompt_id}")
    body = match.group("body")
    model_key = None
    for key in sorted(MODEL_ALIAS_MAP, key=len, reverse=True):
        suffix = f"-{key}"
        if body.endswith(suffix):
            model_key = key
            body = body[: -len(suffix)]
            break
    if model_key is None:
        raise PipelineError(f"Could not infer source model from prompt id: {prompt_id}")
    source_model = MODEL_ALIAS_MAP[model_key]["model_id"]

    if body.startswith("t2i-char-"):
        return "character", body.removeprefix("t2i-char-").upper(), source_model
    if body.startswith("t2i-loc-"):
        return "location", body.removeprefix("t2i-loc-").upper(), source_model
    if body.startswith("t2i-prop-"):
        return "prop", body.removeprefix("t2i-prop-").upper(), source_model
    if body.startswith("t2i-ward-"):
        return "wardrobe", body.removeprefix("t2i-ward-").upper(), source_model
    if body.startswith("t2i-style-"):
        element_id = body.removeprefix("t2i-style-").replace("-", "_").upper()
        return "style_ref", f"STYLE_{element_id}", source_model
    raise PipelineError(f"Could not infer element target from prompt id: {prompt_id}")


def _image_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in IMAGE_EXTENSIONS else []
    if not path.is_dir():
        raise PipelineError(f"Images path not found: {path}")
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def run_review_outputs(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    if not args.prompt_id:
        raise PipelineError("review-outputs requires --prompt-id.")
    if not args.images:
        raise PipelineError("review-outputs requires --images.")
    if not args.review_notes:
        raise PipelineError("review-outputs requires --review-notes.")

    review_notes_path = (repo_root / args.review_notes).resolve()
    if not review_notes_path.exists():
        raise PipelineError(f"Review notes not found: {args.review_notes}")
    review_notes = review_notes_path.read_text(encoding="utf-8")

    images = _image_paths((repo_root / args.images).resolve())
    if not images:
        raise PipelineError(f"No candidate image paths found under: {args.images}")

    element_type, element_id, source_model = _infer_review_target(args.prompt_id)
    score = {field: 3 for field in QUALITY_SCORE_FIELDS}
    candidate_images = [
        {
            "path": _relative(path, repo_root),
            "status": "candidate",
            "reason": "Candidate path registered from CLI review handoff; detailed human review pending.",
            "quality_scores": score,
            "failure_reason": None,
            "repo_binary_committed": False,
        }
        for path in images
    ]

    result = ImageReviewAgent(repo_root).write_review(
        element_type=element_type,
        element_id=element_id,
        source_prompt_ids=[args.prompt_id],
        source_model=source_model,
        candidate_images=candidate_images,
        canonical_images=[],
        review_notes=review_notes,
    )

    written = [
        _relative(result.image_selection_path, repo_root),
        _relative(result.pack_manifest_suggestion_path, repo_root),
    ]
    written.extend(_relative(path, repo_root) for path in result.asset_clearance_paths)
    if result.corrected_brief_path is not None:
        written.append(_relative(result.corrected_brief_path, repo_root))

    return PipelineResult(
        mode=args.mode,
        written_files=written,
        skipped=[],
        message="Image review metadata written; image binaries were not copied.",
    )


def run_review_video_takes(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    if not args.scene_id:
        raise PipelineError("review-video-takes requires --scene-id.")
    if not args.prompt_id:
        raise PipelineError("review-video-takes requires --prompt-id.")
    if not args.takes_metadata:
        raise PipelineError("review-video-takes requires --takes-metadata.")
    if not args.review_notes:
        raise PipelineError("review-video-takes requires --review-notes.")

    result = VideoTakeReviewAgent(repo_root).write_review(
        scene_id=args.scene_id,
        prompt_id=args.prompt_id,
        takes_metadata_path=args.takes_metadata,
        review_notes_path=args.review_notes,
    )

    written = [
        _relative(result.video_takes_path, repo_root),
        _relative(result.review_path, repo_root),
    ]
    if result.corrected_brief_path is not None:
        written.append(_relative(result.corrected_brief_path, repo_root))

    return PipelineResult(
        mode=args.mode,
        written_files=written,
        skipped=[],
        message=(
            "Video take review metadata written; video binaries were not copied "
            "and clip locking was not performed."
        ),
    )


def run_lock_scene_clip(args: argparse.Namespace) -> PipelineResult:
    repo_root = args.repo_root.resolve()
    if not args.scene_id:
        raise PipelineError("lock-scene-clip requires --scene-id.")
    if not args.locked_by:
        raise PipelineError("lock-scene-clip requires --locked-by.")

    result = SceneClipLockingAgent(repo_root).lock_scene_clip(
        scene_id=args.scene_id,
        locked_by=args.locked_by,
        locked_at=args.locked_at,
    )

    return PipelineResult(
        mode=args.mode,
        written_files=[
            _relative(result.selected_take_path, repo_root),
            _relative(result.scene_clip_map_path, repo_root),
        ],
        skipped=[],
        message=(
            "Scene clip locked as metadata only; video/proxy binaries were not copied."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one existing metadata-only production pipeline mode."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "refresh-model-guidance",
            "generate-prompts",
            "review-outputs",
            "generate-storyboard-options",
            "generate-shot-list-omni-suggestion",
            "generate-kling-omni-prompts",
            "review-video-takes",
            "lock-scene-clip",
            "operator-next-step",
            "copilot-command",
            "suggest-pr",
            "pickup",
        ],
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--models")
    parser.add_argument("--save-snapshot", action="store_true")
    parser.add_argument("--scene-id")
    parser.add_argument("--scene")
    parser.add_argument("--scene-ids")
    parser.add_argument("--model-guidance-snapshot-dir")
    parser.add_argument("--model-guidance-snapshots")
    parser.add_argument("--prompt-id")
    parser.add_argument("--images")
    parser.add_argument("--takes-metadata")
    parser.add_argument("--review-notes")
    parser.add_argument("--locked-by")
    parser.add_argument("--locked-at")
    parser.add_argument("--target-duration-seconds", type=int)
    parser.add_argument("--command", choices=("yes", "no", "revise", "switch"))
    parser.add_argument(
        "--to-agent",
        choices=(
            "human_operator",
            "claude_code",
            "codex",
            "gemini_code_assist",
        ),
    )
    parser.add_argument("--reason", default="limit_reached")
    parser.add_argument("--session-id")
    parser.add_argument("--note")
    parser.add_argument("--branch")
    parser.add_argument("--base", default="main")
    handoff_group = parser.add_mutually_exclusive_group()
    handoff_group.add_argument(
        "--auto-handoff",
        dest="auto_handoff",
        action="store_true",
        default=True,
        help="Automatically write a handoff record when yes command routes to an agent (default on).",
    )
    handoff_group.add_argument(
        "--no-auto-handoff",
        dest="auto_handoff",
        action="store_false",
        help="Disable automatic handoff writing for the yes command.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.mode == "operator-next-step":
            return run_operator_next_step(args)
        if args.mode == "pickup":
            return run_pickup(args)
        if args.mode == "refresh-model-guidance":
            result = run_refresh_model_guidance(args)
        elif args.mode == "copilot-command":
            result = run_copilot_command(args)
        elif args.mode == "suggest-pr":
            result = run_suggest_pr(args)
        elif args.mode == "generate-prompts":
            result = run_generate_prompts(args)
        elif args.mode == "review-outputs":
            result = run_review_outputs(args)
        elif args.mode == "generate-storyboard-options":
            result = run_generate_storyboard_options(args)
        elif args.mode == "generate-shot-list-omni-suggestion":
            result = run_generate_shot_list_omni_suggestion(args)
        elif args.mode == "generate-kling-omni-prompts":
            result = run_generate_kling_omni_prompts(args)
        elif args.mode == "review-video-takes":
            result = run_review_video_takes(args)
        elif args.mode == "lock-scene-clip":
            result = run_lock_scene_clip(args)
        else:  # pragma: no cover - argparse choices prevent this
            raise PipelineError(f"Unsupported mode: {args.mode}")
    except (PipelineError, OSError, ValueError, ImportError) as exc:
        parser.exit(2, f"error: {exc}\n")

    _print_result(result, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
