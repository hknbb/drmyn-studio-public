"""
validate_shot_still_coverage.py

Scene-level Anchor & Animate coverage validator.

Checks (per scene with clip manifests):
  STILL_MISSING             — a manifest shot has no still_generation prompt in prompts/draft/
  CONTACT_SHEET_MISSING     — a manifest clip has no shot_design prompt in prompts/draft/
  CONTACT_SHEET_ORDER_MISMATCH — operator_upload_order doesn't match manifest shot archive order
  ARCHIVE_FILENAME_DUPLICATE   — same archive_filename in two different still prompts
  VISUAL_BUDGET_EXCEEDED    — an anchored_i2v Kling prompt carries visual_input_budget.total > 7
  PROTECTED_FLAGS_MISSING   — a C08-containing shot still lacks C08_NO_CONTACT/C08_DISTRESS_OFF_FRAME

Run scope: only runs for scenes where at least one still_generation OR shot_design prompt
already exists in prompts/draft/ (skips scenes that haven't started anchor-animate yet).
"""

from __future__ import annotations

import glob as _glob
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ShotStillCoverageIssue:
    scene_id: str
    error_code: str
    message: str
    clip_id: str = ""
    shot_id: str = ""
    severity: str = "error"


def validate_shot_still_coverage(
    repo_root: Path | str, scene_id: str
) -> list[ShotStillCoverageIssue]:
    """Return a list of coverage issues for *scene_id*.

    Returns an empty list when: no clip manifests exist, or no anchor-animate
    prompts have been generated yet (still_generation + shot_design both absent).
    """
    repo_root = Path(repo_root)
    issues: list[ShotStillCoverageIssue] = []

    manifests = _discover_manifests(repo_root, scene_id)
    if not manifests:
        return []

    still_prompts = _discover_prompts(repo_root, scene_id, "still_generation")
    cs_prompts = _discover_prompts(repo_root, scene_id, "shot_design")
    kling_prompts = _discover_prompts(repo_root, scene_id, "omni_instruction")

    # Scenes whose active Kling route is the v07 text-only literal profile do not
    # use the anchor-animate (still/contact) pipeline; skip its coverage contract.
    for p in kling_prompts:
        gp = p.get("generation_params") or {}
        if (
            gp.get("input_mode") == "text_only"
            or gp.get("language_profile") == "kling_literal_alias_locked"
        ):
            return []

    # Skip if anchor-animate pipeline hasn't produced any (non-deprecated) prompts yet.
    if not still_prompts and not cs_prompts:
        return []

    # ----------------------------------------------------------------
    # Index stills by shot_id; collect archive filenames for dup check
    # ----------------------------------------------------------------
    still_by_shot: dict[str, dict[str, Any]] = {}
    archive_seen: dict[str, str] = {}  # filename -> first prompt_id

    for p in still_prompts:
        gp = p.get("generation_params") or {}
        sid = gp.get("shot_id", "")
        fn = gp.get("archive_filename", "")
        pid = p.get("prompt_id", "?")
        if sid:
            still_by_shot[sid] = p
        if fn:
            if fn in archive_seen:
                issues.append(ShotStillCoverageIssue(
                    scene_id=scene_id,
                    error_code="ARCHIVE_FILENAME_DUPLICATE",
                    message=(
                        f"archive_filename {fn!r} appears in both "
                        f"{archive_seen[fn]!r} and {pid!r}"
                    ),
                ))
            else:
                archive_seen[fn] = pid

    # Index contact sheets by clip_id
    cs_by_clip: dict[str, dict[str, Any]] = {}
    for p in cs_prompts:
        gp = p.get("generation_params") or {}
        cid = gp.get("clip_id", "")
        if cid:
            cs_by_clip[cid] = p

    # ----------------------------------------------------------------
    # Per-manifest checks
    # ----------------------------------------------------------------
    for manifest_path in manifests:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        clip_id: str = manifest.get("clip_id", "")
        shots: list[dict[str, Any]] = manifest.get("shots") or []

        # Contact sheet exists for clip?
        if clip_id not in cs_by_clip:
            issues.append(ShotStillCoverageIssue(
                scene_id=scene_id,
                clip_id=clip_id,
                error_code="CONTACT_SHEET_MISSING",
                message=f"No shot_design prompt found for clip {clip_id!r}",
            ))
        else:
            # Upload order must match manifest shot archive order
            expected: list[str] = []
            for shot in shots:
                sid = shot.get("shot_id", "")
                sp = still_by_shot.get(sid)
                if sp:
                    fn = (sp.get("generation_params") or {}).get("archive_filename", "")
                    if fn:
                        expected.append(fn)
            actual = (cs_by_clip[clip_id].get("generation_params") or {}).get(
                "operator_upload_order", []
            )
            if expected and actual != expected:
                issues.append(ShotStillCoverageIssue(
                    scene_id=scene_id,
                    clip_id=clip_id,
                    error_code="CONTACT_SHEET_ORDER_MISMATCH",
                    message=(
                        f"operator_upload_order {actual} "
                        f"does not match expected {expected}"
                    ),
                ))

        # Per-shot: still exists + protected flags
        for shot in shots:
            sid = shot.get("shot_id", "")
            req = shot.get("required_element_ids") or []

            if sid not in still_by_shot:
                issues.append(ShotStillCoverageIssue(
                    scene_id=scene_id,
                    clip_id=clip_id,
                    shot_id=sid,
                    error_code="STILL_MISSING",
                    message=f"No still_generation prompt for shot {sid!r}",
                ))
                continue

            gp = (still_by_shot[sid].get("generation_params") or {})
            if "C08" in req:
                flags: list[str] = gp.get("protected_subject_flags") or []
                missing = [
                    f for f in ("C08_NO_CONTACT", "C08_DISTRESS_OFF_FRAME")
                    if f not in flags
                ]
                if missing:
                    issues.append(ShotStillCoverageIssue(
                        scene_id=scene_id,
                        clip_id=clip_id,
                        shot_id=sid,
                        error_code="PROTECTED_FLAGS_MISSING",
                        message=(
                            f"Shot {sid!r} contains C08 but still prompt "
                            f"missing protected_subject_flags: {missing}"
                        ),
                    ))

    # ----------------------------------------------------------------
    # anchored_i2v visual budget check
    # ----------------------------------------------------------------
    for p in kling_prompts:
        gp = p.get("generation_params") or {}
        if gp.get("input_mode") != "anchored_i2v":
            continue
        budget = gp.get("visual_input_budget") or {}
        total = budget.get("total", 0)
        if total > 7:
            issues.append(ShotStillCoverageIssue(
                scene_id=scene_id,
                clip_id=gp.get("clip_id", ""),
                error_code="VISUAL_BUDGET_EXCEEDED",
                message=(
                    f"Kling prompt {p.get('prompt_id')!r} has "
                    f"visual_input_budget.total={total} > 7"
                ),
            ))

    return issues


# ------------------------------------------------------------------
# Discovery helpers
# ------------------------------------------------------------------

def _discover_manifests(repo_root: Path, scene_id: str) -> list[Path]:
    pattern = str(
        repo_root / "planning" / "scenes" / scene_id / "manifests" / "CLIP_*.yaml"
    )
    return sorted(Path(p) for p in _glob.glob(pattern))


def _discover_prompts(
    repo_root: Path, scene_id: str, prompt_type: str
) -> list[dict[str, Any]]:
    """Load all prompt records in prompts/draft/ for scene_id with the given prompt_type."""
    draft_dir = repo_root / "prompts" / "draft"
    results: list[dict[str, Any]] = []
    if not draft_dir.is_dir():
        return results
    for path in sorted(draft_dir.glob(f"{scene_id}__*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        # Deprecated records (e.g. the retired v06 still/contact route) no longer
        # carry the anchor-animate coverage contract.
        if data.get("lifecycle_stage") == "deprecated" or data.get("status") == "deprecated":
            continue
        if data.get("prompt_type") == prompt_type:
            results.append(data)
    return results
