"""
Production Status Agent for Batch 5.8.

Reads existing repo metadata and writes a conservative production status CSV.
It does not generate prompts, run external tools, or mutate lifecycle fields
such as pack_status, canon_lock, approved, or locked.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


STATUS_FIELDS = (
    "scene_id",
    "element_packs_status",
    "still_prompt_status",
    "omni_prompt_status",
    "takes_status",
    "selected_clip_status",
    "overall_status",
)

SCENE_DIR_RE = re.compile(r"^SC\d{4}$")


@dataclass(frozen=True)
class ProductionSceneStatus:
    scene_id: str
    element_packs_status: str
    still_prompt_status: str
    omni_prompt_status: str
    takes_status: str
    selected_clip_status: str
    overall_status: str


@dataclass(frozen=True)
class BatchJobValidationIssue:
    file: str
    field_path: str
    message: str


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _scene_ids(repo_root: Path) -> list[str]:
    scenes_dir = repo_root / "planning" / "scenes"
    if not scenes_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in scenes_dir.iterdir()
        if path.is_dir()
        and SCENE_DIR_RE.match(path.name)
        and (path / "scene_card.yaml").exists()
    )


def _has_any(root: Path, pattern: str) -> bool:
    return root.is_dir() and any(root.glob(pattern))


def _element_packs_status(repo_root: Path) -> str:
    elements_root = repo_root / "visual_dev" / "elements"
    if _has_any(elements_root, "**/image_selection.yaml"):
        return "image_review_pending"
    if _has_any(elements_root, "**/pack_manifest.yaml"):
        return "pending"
    return "not_started"


def _still_prompt_status(repo_root: Path, scene_id: str) -> str:
    prompts_root = repo_root / "prompts"
    if not prompts_root.exists():
        return "not_started"
    for path in prompts_root.glob(f"**/{scene_id}__*.yaml"):
        if "omni" not in path.name and "video" not in path.name:
            return "pending"
    return "not_started"


def _omni_prompt_status(repo_root: Path, scene_id: str) -> str:
    prompts_root = repo_root / "prompts"
    if not prompts_root.exists():
        return "not_started"
    for path in prompts_root.glob(f"**/{scene_id}__*.yaml"):
        if "omni" in path.name or "video" in path.name:
            return "pending"
    return "not_started"


def _takes_status(repo_root: Path, scene_id: str) -> str:
    path = repo_root / "visual_dev" / "omni_sets" / scene_id / "video_takes.yaml"
    if path.exists():
        return "pending"
    return "not_started"


def _selected_clip_status(repo_root: Path, scene_id: str) -> str:
    path = repo_root / "visual_dev" / "omni_sets" / scene_id / "selected_take.yaml"
    if path.exists():
        return "pending"
    return "not_started"


def _overall_status(
    *,
    element_packs_status: str,
    still_prompt_status: str,
    takes_status: str,
    selected_clip_status: str,
) -> str:
    if "blocked" in {
        element_packs_status,
        still_prompt_status,
        takes_status,
        selected_clip_status,
    }:
        return "blocked"
    if element_packs_status == "image_review_pending":
        return "ready_for_operator"
    if still_prompt_status == "pending":
        return "image_review_pending"
    return "phase1_pending"


def summarize_scene(repo_root: str | Path, scene_id: str) -> ProductionSceneStatus:
    """Summarize one scene from existing metadata only."""
    root = Path(repo_root)
    element_packs_status = _element_packs_status(root)
    still_prompt_status = _still_prompt_status(root, scene_id)
    omni_prompt_status = _omni_prompt_status(root, scene_id)
    takes_status = _takes_status(root, scene_id)
    selected_clip_status = _selected_clip_status(root, scene_id)

    return ProductionSceneStatus(
        scene_id=scene_id,
        element_packs_status=element_packs_status,
        still_prompt_status=still_prompt_status,
        omni_prompt_status=omni_prompt_status,
        takes_status=takes_status,
        selected_clip_status=selected_clip_status,
        overall_status=_overall_status(
            element_packs_status=element_packs_status,
            still_prompt_status=still_prompt_status,
            takes_status=takes_status,
            selected_clip_status=selected_clip_status,
        ),
    )


def build_production_status(repo_root: str | Path) -> list[ProductionSceneStatus]:
    """Build conservative per-scene status rows from planning/scenes."""
    root = Path(repo_root)
    return [summarize_scene(root, scene_id) for scene_id in _scene_ids(root)]


def write_production_status_csv(
    repo_root: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Write evidence/production_status.csv from current repo metadata."""
    root = Path(repo_root)
    out_path = Path(output_path) if output_path is not None else (
        root / "evidence" / "production_status.csv"
    )
    rows = build_production_status(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    return out_path


def validate_batch_job_file(
    path: Path,
    schema_path: Path,
) -> list[BatchJobValidationIssue]:
    """Validate one evidence/batch_jobs/*.yaml record."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    try:
        data = _read_yaml(path)
    except Exception as exc:
        return [
            BatchJobValidationIssue(
                file=str(path),
                field_path="",
                message=f"YAML parse error: {exc}",
            )
        ]
    if data is None:
        return [
            BatchJobValidationIssue(
                file=str(path),
                field_path="",
                message="File is empty or contains only comments.",
            )
        ]
    return [
        BatchJobValidationIssue(
            file=str(path),
            field_path=".".join(str(p) for p in error.absolute_path) or "(root)",
            message=error.message,
        )
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


def load_batch_jobs(repo_root: str | Path) -> list[dict[str, Any]]:
    """Load valid-looking batch job mappings; schema validation is separate."""
    jobs_dir = Path(repo_root) / "evidence" / "batch_jobs"
    if not jobs_dir.is_dir():
        return []
    jobs: list[dict[str, Any]] = []
    for path in sorted(jobs_dir.glob("*.yaml")):
        data = _read_yaml(path)
        if isinstance(data, dict):
            jobs.append(data)
    return jobs
