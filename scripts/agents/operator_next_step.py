"""
Operator guidance layer for Batch 5.85.

Reads repository metadata and recommends the next safe human production task.
It does not generate prompts, run external tools, copy binaries, or mutate
scene cards, pack manifests, lifecycle fields, storyboard selections, or
production status records.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.production_status import (
    ProductionSceneStatus,
    build_production_status,
)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
SCENE_ID_RE = re.compile(r"SC\d{4}")
RECOMMENDED_ROUTE_BY_TASK = {
    "storyboard_selection": ("gemini_code_assist", "second_opinion"),
    "model_guidance_snapshot_refresh": ("gemini_code_assist", "drafting_assist"),
    "image_review_preparation": ("claude_code", "drafting_assist"),
    "image_review": ("codex", "review_requested"),
    "t2i_image_generation": ("claude_code", "manual_pickup"),
    "blocked": ("claude_code", "manual_pickup"),
}
ALLOWED_RECOMMENDED_NEXT_AGENTS = frozenset(
    {"human_operator", "claude_code", "codex", "gemini_code_assist"}
)
ALLOWED_RECOMMENDED_REASONS = frozenset(
    {
        "limit_reached",
        "review_requested",
        "second_opinion",
        "drafting_assist",
        "manual_pickup",
        "context_too_large",
        "task_complete",
    }
)

PROMPT_TYPE_TARGETS = {
    "t2i_character_element": ("characters", "character_refs"),
    "character": ("characters", "character_refs"),
    "t2i_location_element": ("locations", "location_refs"),
    "environment": ("locations", "location_refs"),
    "t2i_prop_element": ("props", "prop_refs"),
    "t2i_wardrobe_element": ("wardrobe", "wardrobe_refs"),
    "t2i_style_reference": ("style_refs", None),
}

PROMPT_ID_TARGET_PATTERNS = (
    (re.compile(r"t2i-(?:char|character)-(?P<id>c\d{2})", re.IGNORECASE), "characters"),
    (re.compile(r"t2i-(?:loc|location)-(?P<id>loc\d{3})", re.IGNORECASE), "locations"),
    (re.compile(r"t2i-(?:prop)-(?P<id>prop\d{3})", re.IGNORECASE), "props"),
    (re.compile(r"t2i-(?:wardrobe|wd)-(?P<id>wd\d{3})", re.IGNORECASE), "wardrobe"),
)


@dataclass(frozen=True)
class OperatorNextStep:
    current_task: str
    scene_id: str | None
    recommended_next_agent: str
    recommended_reason: str
    open_files: list[str]
    do_steps: list[str]
    expected_outputs: list[str]
    next_command_or_manual_step: str
    safety_warnings: list[str]
    allowed_commands: tuple[str, ...] = ("yes", "no", "revise", "switch")
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        if self.recommended_next_agent not in ALLOWED_RECOMMENDED_NEXT_AGENTS:
            raise ValueError(
                f"Unsupported recommended_next_agent: {self.recommended_next_agent}"
            )
        if self.recommended_reason not in ALLOWED_RECOMMENDED_REASONS:
            raise ValueError(f"Unsupported recommended_reason: {self.recommended_reason}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render(self) -> str:
        lines = [
            f"current_task: {self.current_task}",
            f"scene_id: {self.scene_id or 'none'}",
            f"recommended_next_agent: {self.recommended_next_agent}",
            f"recommended_reason: {self.recommended_reason}",
            "open_files:",
        ]
        lines.extend(f"- {path}" for path in self.open_files)
        lines.append("do_steps:")
        lines.extend(f"- {step}" for step in self.do_steps)
        lines.append("expected_outputs:")
        lines.extend(f"- {item}" for item in self.expected_outputs)
        lines.append(
            f"next_command_or_manual_step: {self.next_command_or_manual_step}"
        )
        lines.append("safety_warnings:")
        lines.extend(f"- {warning}" for warning in self.safety_warnings)
        lines.append("allowed_commands:")
        lines.extend(f"- {command}" for command in self.allowed_commands)
        if self.blocked_reason:
            lines.append(f"blocked_reason: {self.blocked_reason}")
        return "\n".join(lines)


@dataclass(frozen=True)
class PromptDraft:
    path: Path
    payload: dict[str, Any]
    prompt_id: str
    scene_id: str | None
    prompt_type: str
    element_dir_name: str | None
    element_id: str | None


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _existing_rel(path: Path, repo_root: Path) -> str | None:
    return _relative(path, repo_root) if path.exists() else None


def _existing_rels(paths: list[Path], repo_root: Path) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        rel = _existing_rel(path, repo_root)
        if rel is not None and rel not in seen:
            seen.add(rel)
            result.append(rel)
    return result


def _scene_id_from_name(name: str) -> str | None:
    match = SCENE_ID_RE.search(name)
    return match.group(0) if match else None


def load_status_csv(repo_root: str | Path) -> list[dict[str, str]]:
    """Read evidence/production_status.csv if present."""
    root = Path(repo_root)
    path = root / "evidence" / "production_status.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_prompt_drafts(repo_root: Path) -> list[PromptDraft]:
    prompts_root = repo_root / "prompts" / "draft"
    if not prompts_root.is_dir():
        return []

    drafts: list[PromptDraft] = []
    for path in sorted(prompts_root.glob("*.yaml")):
        try:
            payload = _read_yaml(path)
        except Exception:
            payload = None
        if not isinstance(payload, dict):
            continue

        prompt_id = str(payload.get("prompt_id") or path.stem)
        scene_id = str(payload.get("scene_id") or "") or _scene_id_from_name(path.stem)
        prompt_type = str(payload.get("prompt_type") or "")
        element_dir_name, element_id = _infer_prompt_target(payload, prompt_id)
        drafts.append(
            PromptDraft(
                path=path,
                payload=payload,
                prompt_id=prompt_id,
                scene_id=scene_id,
                prompt_type=prompt_type,
                element_dir_name=element_dir_name,
                element_id=element_id,
            )
        )
    return drafts


def _infer_prompt_target(
    payload: dict[str, Any],
    prompt_id: str,
) -> tuple[str | None, str | None]:
    prompt_type = str(payload.get("prompt_type") or "")
    source_refs = payload.get("source_refs")
    if not isinstance(source_refs, dict):
        source_refs = {}

    target = PROMPT_TYPE_TARGETS.get(prompt_type)
    if target is not None:
        dir_name, ref_key = target
        if ref_key is None:
            return dir_name, None
        refs = source_refs.get(ref_key) or []
        if isinstance(refs, list) and refs:
            return dir_name, str(refs[0])

    for pattern, dir_name in PROMPT_ID_TARGET_PATTERNS:
        match = pattern.search(prompt_id)
        if match:
            return dir_name, match.group("id").upper()

    return None, None


def _element_dir(repo_root: Path, draft: PromptDraft) -> Path | None:
    if not draft.element_dir_name or not draft.element_id:
        return None
    return repo_root / "visual_dev" / "elements" / draft.element_dir_name / draft.element_id


def _candidate_images(element_dir: Path | None) -> list[Path]:
    if element_dir is None:
        return []
    candidates_dir = element_dir / "candidates"
    if not candidates_dir.is_dir():
        return []
    return sorted(
        path
        for path in candidates_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _review_notes_path(repo_root: Path, prompt_id: str) -> Path:
    return repo_root / "evidence" / "prompt_reviews" / f"{prompt_id}_review.md"


def _safe_warnings() -> list[str]:
    return [
        "Metadata/text guidance only; do not commit image or video binaries in this step.",
        "Do not edit scene_card.yaml, pack_manifest.yaml, selected_option, pack_status, canon_lock, approved, or locked fields.",
        "External image/video tools are manual operator actions; this agent did not run them.",
    ]


def _recommended_route(current_task: str) -> tuple[str, str]:
    return RECOMMENDED_ROUTE_BY_TASK.get(current_task, ("human_operator", "manual_pickup"))


def _snapshot_payload_needs_refresh(payload: dict[str, Any]) -> bool:
    if payload.get("model_version_observed") == "unknown_placeholder":
        return True
    for source in payload.get("sources") or []:
        if isinstance(source, dict):
            if "example.org/placeholder" in str(source.get("url") or ""):
                return True
            if source.get("human_verified") is not True:
                return True
    for rule in payload.get("extracted_rules") or []:
        if "PLACEHOLDER" in str(rule):
            return True
    return bool(payload.get("do_not_use_without_verification") or [])


def _placeholder_snapshot_refresh_step(
    repo_root: Path,
    draft: PromptDraft,
) -> OperatorNextStep | None:
    params = draft.payload.get("generation_params")
    if not isinstance(params, dict):
        return None
    if params.get("model_guidance_mode") != "dynamic_snapshot":
        return None
    snapshot_ref = params.get("model_guidance_snapshot")
    if not snapshot_ref:
        return None

    snapshot_path = repo_root / str(snapshot_ref)
    try:
        snapshot_payload = _read_yaml(snapshot_path)
    except Exception:
        return None
    if not isinstance(snapshot_payload, dict):
        return None
    if not _snapshot_payload_needs_refresh(snapshot_payload):
        return None

    open_files = _existing_rels(
        [
            draft.path,
            snapshot_path,
            repo_root / "docs" / "operator_guides" / "model_guidance_refresh_playbook.md",
        ],
        repo_root,
    )
    current_task = "model_guidance_snapshot_refresh"
    recommended_next_agent, recommended_reason = _recommended_route(current_task)
    return OperatorNextStep(
        current_task=current_task,
        scene_id=draft.scene_id,
        recommended_next_agent=recommended_next_agent,
        recommended_reason=recommended_reason,
        open_files=open_files,
        do_steps=[
            "Run a web-capable agent such as Gemini Code Assist to refresh the snapshot from official model documentation.",
            "Record source URLs, retrieval timestamps, content hashes, and human verification in the snapshot YAML.",
            "Set do_not_use_without_verification to an empty list only after the human has verified the extracted rules.",
            "Rerun prompt generation or review only after the refreshed snapshot passes the critic gate.",
        ],
        expected_outputs=[
            str(snapshot_ref),
            "A human-verified model guidance snapshot with current official sources.",
        ],
        next_command_or_manual_step=(
            "Manual step: refresh the listed model guidance snapshot before using this prompt draft."
        ),
        safety_warnings=_safe_warnings(),
        allowed_commands=("switch", "revise"),
        blocked_reason="Prompt draft references a placeholder or unverified dynamic model guidance snapshot.",
    )


def _storyboard_selection_step(repo_root: Path) -> OperatorNextStep | None:
    storyboards_root = repo_root / "visual_dev" / "storyboards"
    if not storyboards_root.is_dir():
        return None

    for path in sorted(storyboards_root.glob("SC*/storyboard_options.yaml")):
        try:
            data = _read_yaml(path)
        except Exception:
            continue
        if not isinstance(data, dict) or data.get("selected_option") is not None:
            continue

        scene_id = str(data.get("scene_id") or path.parent.name)
        source_refs = data.get("source_refs") if isinstance(data.get("source_refs"), dict) else {}
        source_paths = [
            repo_root / str(source_refs[key])
            for key in ("scene_card", "scene_excerpt")
            if source_refs.get(key)
        ]
        open_files = _existing_rels([path, *source_paths], repo_root)
        current_task = "storyboard_selection"
        recommended_next_agent, recommended_reason = _recommended_route(current_task)
        return OperatorNextStep(
            current_task=current_task,
            scene_id=scene_id,
            recommended_next_agent=recommended_next_agent,
            recommended_reason=recommended_reason,
            open_files=open_files,
            do_steps=[
                "Read each option and compare purpose, camera_angle, framing, movement, lighting, and status.",
                "Reject options marked blocked unless the source issue has been resolved in a separate PR.",
                "Choose the strongest human preference, but leave selected_option unchanged in this Batch 5.85 guidance pass.",
            ],
            expected_outputs=[
                "A human decision ready to be recorded later through the approved storyboard selection workflow.",
                "No storyboard frames, videos, prompt records, or lifecycle state changes from this helper.",
            ],
            next_command_or_manual_step=(
                "Manual step: open the listed storyboard_options.yaml and decide which option should be selected."
            ),
            safety_warnings=_safe_warnings(),
        )

    return None


def _prompt_review_or_generation_step(repo_root: Path) -> OperatorNextStep | None:
    all_drafts = _load_prompt_drafts(repo_root)
    for draft in all_drafts:
        refresh_step = _placeholder_snapshot_refresh_step(repo_root, draft)
        if refresh_step is not None:
            return refresh_step

        element_dir = _element_dir(repo_root, draft)
        image_selection_path = (
            element_dir / "image_selection.yaml" if element_dir is not None else None
        )
        if image_selection_path is not None and image_selection_path.exists():
            continue

        candidates = _candidate_images(element_dir)
        notes_path = _review_notes_path(repo_root, draft.prompt_id)
        sibling_drafts = [
            d for d in all_drafts
            if d.path != draft.path
            and d.scene_id == draft.scene_id
            and d.element_dir_name == draft.element_dir_name
            and d.element_id == draft.element_id
        ]
        for sibling in sibling_drafts:
            sibling_refresh = _placeholder_snapshot_refresh_step(repo_root, sibling)
            if sibling_refresh is not None:
                return sibling_refresh
        sibling_paths = [d.path for d in sibling_drafts]
        open_file_paths = [draft.path, *sibling_paths, notes_path]
        if element_dir is not None:
            open_file_paths.append(element_dir)
        open_files = _existing_rels(open_file_paths, repo_root)

        if candidates and notes_path.exists():
            current_task = "image_review"
            recommended_next_agent, recommended_reason = _recommended_route(current_task)
            return OperatorNextStep(
                current_task=current_task,
                scene_id=draft.scene_id,
                recommended_next_agent=recommended_next_agent,
                recommended_reason=recommended_reason,
                open_files=open_files,
                do_steps=[
                    "Review the existing candidate images against the prompt draft and source references.",
                    "Prepare candidate metadata with paths, status, reasons, and quality scores.",
                    "Use the metadata-only ImageReviewAgent workflow to write review records; do not copy binaries.",
                ],
                expected_outputs=[
                    "visual_dev/elements/{type}/{id}/image_selection.yaml",
                    "evidence/asset_clearance/*.yaml for selected assets only",
                    "Optional evidence/prompt_reviews/*_brief.yaml if prompt repair is needed",
                ],
                next_command_or_manual_step=(
                    "Manual step: complete image review metadata from the listed prompt and review notes."
                ),
                safety_warnings=_safe_warnings(),
            )

        if candidates and not notes_path.exists():
            missing = _relative(notes_path, repo_root)
            current_task = "image_review_preparation"
            recommended_next_agent, recommended_reason = _recommended_route(current_task)
            return OperatorNextStep(
                current_task=current_task,
                scene_id=draft.scene_id,
                recommended_next_agent=recommended_next_agent,
                recommended_reason=recommended_reason,
                open_files=open_files,
                do_steps=[
                    "Open the prompt draft and inspect the candidate images already present.",
                    f"Create review notes at {missing} before running any metadata review writer.",
                    "Keep notes text-only and reference candidate paths exactly as they exist.",
                ],
                expected_outputs=[
                    missing,
                    "A later metadata-only image review pass once notes exist.",
                ],
                next_command_or_manual_step=(
                    f"Manual step: write the missing review notes file {missing}."
                ),
                safety_warnings=_safe_warnings(),
                blocked_reason=f"Candidate images exist, but review notes are missing: {missing}",
            )

        current_task = "t2i_image_generation"
        recommended_next_agent, recommended_reason = _recommended_route(current_task)
        return OperatorNextStep(
            current_task=current_task,
            scene_id=draft.scene_id,
            recommended_next_agent=recommended_next_agent,
            recommended_reason=recommended_reason,
            open_files=open_files,
            do_steps=[
                "Open the prompt draft and copy only the prompt text needed by the external T2I tool.",
                "Generate candidate images manually in the external tool named by target_models.",
                "Save candidates according to the storage policy before requesting image review.",
            ],
            expected_outputs=[
                "Candidate image files saved by the human operator under the correct element candidates folder or external storage reference.",
                f"Text review notes at {_relative(notes_path, repo_root)} after candidates are available.",
            ],
            next_command_or_manual_step=(
                "Manual step: run the external T2I model yourself using the listed prompt draft."
            ),
            safety_warnings=_safe_warnings(),
        )

    return None


def _blocked_step(
    repo_root: Path,
    statuses: list[ProductionSceneStatus],
    csv_rows: list[dict[str, str]],
) -> OperatorNextStep:
    open_files = _existing_rels(
        [
            repo_root / "evidence" / "production_status.csv",
            repo_root / "docs" / "operator_guides" / "production_operator_runbook.md",
        ],
        repo_root,
    )
    reason = (
        "No prompt drafts, unselected storyboard options, or review-ready candidate images were found."
    )
    if not statuses and not csv_rows:
        reason = "No production status rows or actionable production metadata were found."

    current_task = "blocked"
    recommended_next_agent, recommended_reason = _recommended_route(current_task)
    return OperatorNextStep(
        current_task=current_task,
        scene_id=None,
        recommended_next_agent=recommended_next_agent,
        recommended_reason=recommended_reason,
        open_files=open_files,
        do_steps=[
            "Inspect production_status.csv if it exists.",
            "Create the missing upstream metadata in its own approved batch before asking for operator guidance again.",
        ],
        expected_outputs=[
            "No files are written by this guidance helper.",
        ],
        next_command_or_manual_step=(
            "Manual step: run the appropriate upstream batch, then rerun operator_next_step.py."
        ),
        safety_warnings=_safe_warnings(),
        allowed_commands=("switch",),
        blocked_reason=reason,
    )


def recommend_next_step(repo_root: str | Path = ".") -> OperatorNextStep:
    """Return the next safe human operator task from current repo metadata."""
    root = Path(repo_root)
    statuses = build_production_status(root)
    csv_rows = load_status_csv(root)

    storyboard_step = _storyboard_selection_step(root)
    if storyboard_step is not None:
        return storyboard_step

    prompt_step = _prompt_review_or_generation_step(root)
    if prompt_step is not None:
        return prompt_step

    return _blocked_step(root, statuses, csv_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recommend the next safe human production task."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root to inspect.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args(argv)

    step = recommend_next_step(args.repo_root.resolve())
    if args.format == "json":
        print(json.dumps(step.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(step.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
