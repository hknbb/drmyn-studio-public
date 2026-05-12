"""
validate_production_records.py

Validates non-prompt production metadata records introduced from Batch 5.5
onward, including image selection, asset clearance, storyboard options, shot
list suggestions, batch jobs, operator sessions, video takes, and video review
evidence. This validator is metadata-only: it reads YAML records and never
mutates pack manifests, lifecycle state, image binaries, video files, or
prompts.

Usage:
    python scripts/validate_production_records.py --repo-root .
    python scripts/validate_production_records.py --repo-root . --report-json evidence/validation_reports/production_records_validation_report.json

Exit codes:
    0 - all files pass (or no files found)
    1 - one or more files fail validation

CI contract:
    - Empty production metadata paths exit 0 with message "0 files validated"
    - Missing optional directories do not fail validation
    - Writes JSON report to evidence/validation_reports/ if --report-json specified
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


IMAGE_SELECTION_PATTERN = "visual_dev/elements/**/image_selection.yaml"
PACK_SUGGESTION_PATTERN = "visual_dev/elements/**/pack_manifest_update_suggestion.yaml"
ASSET_CLEARANCE_PATTERN = "evidence/asset_clearance/*.yaml"
PROMPT_REVIEW_BRIEF_PATTERN = "evidence/prompt_reviews/*_brief.yaml"
STORYBOARD_OPTIONS_PATTERN = "visual_dev/storyboards/SC*/storyboard_options.yaml"
SHOT_LIST_OMNI_SUGGESTION_PATTERN = (
    "visual_dev/storyboards/SC*/shot_list_omni_suggestion.yaml"
)
BATCH_JOB_PATTERN = "evidence/batch_jobs/*.yaml"
PRODUCTION_BATCH_PATTERN = "evidence/batch_jobs/production_batch_*.yaml"
OPERATOR_SESSION_PATTERN = "evidence/operator_sessions/*.yaml"
AGENT_HANDOFF_PATTERN = "evidence/agent_handoffs/*.yaml"
LOCAL_MEDIA_INDEX_PATTERN = "evidence/local_media_indices/*.yaml"
VIDEO_TAKE_PATTERN = "visual_dev/omni_sets/SC*/video_takes.yaml"
VIDEO_REVIEW_PATTERN = "evidence/video_reviews/*.yaml"
SELECTED_TAKE_PATTERN = "visual_dev/omni_sets/SC*/selected_take.yaml"
OMNI_SET_GATE_PATTERN = "evidence/omni_set_gates/*.yaml"
PACK_LOCK_READINESS_PATTERN = "evidence/pack_lock_readiness/*.yaml"
CANONICAL_ASSET_WORK_ORDER_PATTERN = "evidence/canonical_asset_work_orders/*.yaml"
CANONICAL_ASSET_INTAKE_SCAFFOLD_PATTERN = (
    "evidence/canonical_asset_intake_scaffolds/*.yaml"
)
CANONICAL_ASSET_INTAKE_INSTRUCTION_PATTERN = (
    "evidence/canonical_asset_intake_instructions/*.yaml"
)
CANONICAL_ASSET_INTAKE_SLOT_PATTERN = "visual_dev/elements/**/intake_slot.yaml"
CLEAN_START_AUDIT_PATTERN = "evidence/clean_start_audits/*.yaml"
PRE_B8A_CLEAN_RESET_PATTERN = "evidence/pre_b8a_clean_resets/*.yaml"
OMNI_QC_REPORT_PATTERN = "evidence/omni_qc/*.yaml"
PERSPECTIVE_QC_REPORT_PATTERN = "evidence/perspective_qc/*.yaml"
DIALOGUE_QC_REPORT_PATTERN = "evidence/dialogue_qc/*.yaml"
REVIEW_DECISION_PATTERN = "evidence/review_decisions/*.yaml"
GPT_IMAGES_PERSPECTIVE_PACK_PATTERN = (
    "visual_dev/elements/**/gpt_images_perspective_pack.yaml"
)
KLING_ELEMENT_REFERENCE_PATTERN = "visual_dev/elements/**/kling_element_reference.yaml"
KLING_CHARACTER_LOOK_ELEMENT_PATTERN = (
    "visual_dev/elements/characters/*/kling_elements/*.yaml"
)
KLING_SHOT_PROMPT_PATTERN = "visual_dev/omni_sets/SC*/kling_shot_prompt_*.yaml"
DIALOGUE_EXTRACT_PATTERN = "planning/dialogue/DLG_*.yaml"
PERFORMANCE_INTENT_PATTERN = "planning/dialogue/PERF_*.yaml"
VOICE_BINDING_PATTERN = "planning/dialogue/VOICE_*.yaml"
NATIVE_AUDIO_COMPATIBILITY_PATTERN = "evidence/native_audio_compatibility/*.yaml"
CHARACTER_IDENTITY_ANCHOR_PATTERN = (
    "visual_dev/elements/characters/*/character_identity_anchor.yaml"
)
CHARACTER_LOOK_VARIANT_PATTERN = (
    "visual_dev/elements/characters/*/look_variants/*.yaml"
)
SCENE_CHARACTER_LOOK_MAP_PATTERN = "visual_dev/omni_sets/SC*/scene_character_look_map.yaml"
AESTHETIC_BIBLE_PATH = "planning/aesthetic_bible.yaml"
SCENE_CLIP_MAP_PATH = "evidence/scene_clip_map.csv"

SCENE_CLIP_MAP_HEADER = [
    "scene_id",
    "selected_take",
    "prompt_id",
    "external_storage_ref",
    "platform_asset_ref",
    "local_proxy_ref",
    "repo_binary_committed",
    "lock_status",
]

FORBIDDEN_LIFECYCLE_KEYS = {"pack_status", "canon_lock", "approved", "locked"}
PACK_SUGGESTION_REQUIRED_KEYS = {
    "element_id",
    "suggested_field",
    "suggested_value",
    "reason",
    "applied_by",
    "applied_at",
}
PACK_SUGGESTION_ALLOWED_VALUES = {"metadata_only", "seeded"}
PROMPT_REVIEW_REQUIRED_KEYS = {"source_prompt_id", "corrected_brief"}
AGENT_HANDOFF_BRANCH_RE = re.compile(r"^(main$|feat/|fix/|docs/|chore/|review/)")
AGENT_HANDOFF_HEAD_SHA_RE = re.compile(r"^[A-Fa-f0-9]{7,40}$")
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[/\\]")
PRODUCTION_BATCH_MODEL_GUIDANCE_TARGETS: dict[str, str] = {
    "midjourney_v8_1": "midjourney_image_best_available",
    "gpt_images_2": "chatgpt_image_best_available",
    "kling_omni_3": "kling_omni_video_best_available",
}


@dataclass
class ProductionValidationIssue:
    file: str
    record_type: str
    field_path: str
    message: str


@dataclass
class ProductionValidationReport:
    total_files: int
    valid_files: int
    invalid_files: int
    by_record_type: dict[str, int]
    issues: list[ProductionValidationIssue]

    @property
    def has_errors(self) -> bool:
        return self.invalid_files > 0


def load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def collect_production_files(repo_root: Path) -> dict[str, list[Path]]:
    """Return production metadata YAML files grouped by validation target."""
    all_batch_job_files = sorted(repo_root.glob(BATCH_JOB_PATTERN))
    production_batch_files: list[Path] = []
    batch_job_files: list[Path] = []
    for path in all_batch_job_files:
        # Keep legacy batch_job coverage but prevent double-validation of
        # production_batch records against the batch_job schema. Prefer explicit
        # filename convention first, then fall back to record_type detection.
        if path.match(PRODUCTION_BATCH_PATTERN):
            production_batch_files.append(path)
            continue
        try:
            data = load_yaml_file(path)
        except Exception:
            data = None
        if isinstance(data, dict) and data.get("record_type") == "production_batch":
            production_batch_files.append(path)
        else:
            batch_job_files.append(path)

    return {
        "image_selection": sorted(repo_root.glob(IMAGE_SELECTION_PATTERN)),
        "asset_clearance": sorted(repo_root.glob(ASSET_CLEARANCE_PATTERN)),
        "pack_manifest_update_suggestion": sorted(repo_root.glob(PACK_SUGGESTION_PATTERN)),
        "prompt_review_brief": sorted(repo_root.glob(PROMPT_REVIEW_BRIEF_PATTERN)),
        "storyboard_options": sorted(repo_root.glob(STORYBOARD_OPTIONS_PATTERN)),
        "shot_list_omni_suggestion": sorted(
            repo_root.glob(SHOT_LIST_OMNI_SUGGESTION_PATTERN)
        ),
        "batch_job": batch_job_files,
        "production_batch": production_batch_files,
        "operator_session": sorted(repo_root.glob(OPERATOR_SESSION_PATTERN)),
        "agent_handoff": sorted(repo_root.glob(AGENT_HANDOFF_PATTERN)),
        "local_media_index": sorted(repo_root.glob(LOCAL_MEDIA_INDEX_PATTERN)),
        "video_take": sorted(repo_root.glob(VIDEO_TAKE_PATTERN)),
        "video_review": sorted(repo_root.glob(VIDEO_REVIEW_PATTERN)),
        "selected_take": sorted(repo_root.glob(SELECTED_TAKE_PATTERN)),
        "omni_set_gate": sorted(repo_root.glob(OMNI_SET_GATE_PATTERN)),
        "pack_lock_readiness": sorted(repo_root.glob(PACK_LOCK_READINESS_PATTERN)),
        "canonical_asset_work_order": sorted(
            repo_root.glob(CANONICAL_ASSET_WORK_ORDER_PATTERN)
        ),
        "canonical_asset_intake_scaffold": sorted(
            repo_root.glob(CANONICAL_ASSET_INTAKE_SCAFFOLD_PATTERN)
        ),
        "canonical_asset_intake_instruction": sorted(
            repo_root.glob(CANONICAL_ASSET_INTAKE_INSTRUCTION_PATTERN)
        ),
        "canonical_asset_intake_slot": sorted(
            repo_root.glob(CANONICAL_ASSET_INTAKE_SLOT_PATTERN)
        ),
        "clean_start_audit": sorted(repo_root.glob(CLEAN_START_AUDIT_PATTERN)),
        "pre_b8a_clean_reset": sorted(repo_root.glob(PRE_B8A_CLEAN_RESET_PATTERN)),
        "omni_qc_report": sorted(repo_root.glob(OMNI_QC_REPORT_PATTERN)),
        "perspective_qc_report": sorted(repo_root.glob(PERSPECTIVE_QC_REPORT_PATTERN)),
        "dialogue_qc_report": sorted(repo_root.glob(DIALOGUE_QC_REPORT_PATTERN)),
        "review_decision_record": sorted(repo_root.glob(REVIEW_DECISION_PATTERN)),
        "gpt_images_perspective_pack": sorted(
            repo_root.glob(GPT_IMAGES_PERSPECTIVE_PACK_PATTERN)
        ),
        "kling_element_reference_record": sorted(
            repo_root.glob(KLING_ELEMENT_REFERENCE_PATTERN)
        ),
        "kling_character_look_element": sorted(
            repo_root.glob(KLING_CHARACTER_LOOK_ELEMENT_PATTERN)
        ),
        "kling_shot_prompt_record": sorted(repo_root.glob(KLING_SHOT_PROMPT_PATTERN)),
        "dialogue_extract_record": sorted(repo_root.glob(DIALOGUE_EXTRACT_PATTERN)),
        "performance_intent_record": sorted(repo_root.glob(PERFORMANCE_INTENT_PATTERN)),
        "voice_binding_record": sorted(repo_root.glob(VOICE_BINDING_PATTERN)),
        "native_audio_compatibility_record": sorted(
            repo_root.glob(NATIVE_AUDIO_COMPATIBILITY_PATTERN)
        ),
        "character_identity_anchor": sorted(
            repo_root.glob(CHARACTER_IDENTITY_ANCHOR_PATTERN)
        ),
        "character_look_variant": sorted(repo_root.glob(CHARACTER_LOOK_VARIANT_PATTERN)),
        "scene_character_look_map": sorted(repo_root.glob(SCENE_CHARACTER_LOOK_MAP_PATTERN)),
        "aesthetic_bible": (
            [repo_root / AESTHETIC_BIBLE_PATH]
            if (repo_root / AESTHETIC_BIBLE_PATH).is_file()
            else []
        ),
        "scene_clip_map": [repo_root / SCENE_CLIP_MAP_PATH]
        if (repo_root / SCENE_CLIP_MAP_PATH).exists()
        or list(repo_root.glob(SELECTED_TAKE_PATTERN))
        else [],
    }


def _schema_issues(
    *,
    path: Path,
    repo_root: Path,
    record_type: str,
    validator: Draft202012Validator,
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []

    try:
        data = load_yaml_file(path)
    except Exception as exc:
        return [
            ProductionValidationIssue(
                file=_relative(path, repo_root),
                record_type=record_type,
                field_path="",
                message=f"YAML parse error: {exc}",
            )
        ]

    if data is None:
        return [
            ProductionValidationIssue(
                file=_relative(path, repo_root),
                record_type=record_type,
                field_path="",
                message="File is empty or contains only comments.",
            )
        ]

    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        field_path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        issues.append(
            ProductionValidationIssue(
                file=_relative(path, repo_root),
                record_type=record_type,
                field_path=field_path,
                message=error.message,
            )
        )

    if isinstance(data, dict):
        forbidden = sorted(FORBIDDEN_LIFECYCLE_KEYS & set(data))
        for key in forbidden:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type=record_type,
                    field_path=key,
                    message="Lifecycle state must not be set directly in production metadata.",
                )
            )

    return issues


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    """Best-effort mapping loader for cross-record checks."""
    try:
        data = load_yaml_file(path)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def validate_prod_line_cross_references(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    """Lightweight cross-record consistency checks for PROD-LINE records."""
    issues: list[ProductionValidationIssue] = []

    # Index perspective prompt IDs from GPT Images perspective packs.
    gpt_prompt_ids: set[str] = set()
    for path in grouped_files.get("gpt_images_perspective_pack", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        prompts = data.get("prompts")
        if not isinstance(prompts, list):
            continue
        for item in prompts:
            if isinstance(item, dict):
                pid = item.get("prompt_id")
                if isinstance(pid, str) and pid:
                    gpt_prompt_ids.add(pid)

    # Index Kling element references by ID.
    kling_element_refs: set[str] = set()
    for path in grouped_files.get("kling_element_reference_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        ref_id = data.get("kling_element_reference_id")
        if isinstance(ref_id, str) and ref_id:
            kling_element_refs.add(ref_id)

        perspectives = data.get("gpt_images_2_perspectives")
        if isinstance(perspectives, dict):
            for key in (
                "front_hero",
                "three_quarter_left",
                "three_quarter_right",
                "rear_or_side",
            ):
                ref = perspectives.get(key)
                if isinstance(ref, str) and ref and ref not in gpt_prompt_ids:
                    issues.append(
                        ProductionValidationIssue(
                            file=_relative(path, repo_root),
                            record_type="kling_element_reference_record",
                            field_path="gpt_images_2_perspectives",
                            message=f"missing GPT Images 2 perspective prompt: {ref}",
                        )
                    )
        # TODO(PROD-LINE): When Midjourney hero reference schema/path is introduced,
        # enforce strict source_midjourney_reference existence checks here.

    # Index dialogue/performance/voice/native-audio records.
    dialogue_extract_ids: set[str] = set()
    for path in grouped_files.get("dialogue_extract_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        rec_id = data.get("dialogue_extract_id")
        if isinstance(rec_id, str) and rec_id:
            dialogue_extract_ids.add(rec_id)

    performance_intent_ids: set[str] = set()
    for path in grouped_files.get("performance_intent_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        rec_id = data.get("performance_intent_id")
        if isinstance(rec_id, str) and rec_id:
            performance_intent_ids.add(rec_id)

    voice_binding_by_id: dict[str, dict[str, Any]] = {}
    for path in grouped_files.get("voice_binding_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        rec_id = data.get("voice_binding_id")
        if isinstance(rec_id, str) and rec_id:
            voice_binding_by_id[rec_id] = data

    native_audio_compat_by_id: dict[str, dict[str, Any]] = {}
    for path in grouped_files.get("native_audio_compatibility_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        rec_id = data.get("native_audio_compatibility_id")
        if isinstance(rec_id, str) and rec_id:
            native_audio_compat_by_id[rec_id] = data
        if data.get("native_audio") is True and data.get("compatible") is False:
            if data.get("status") != "blocked":
                issues.append(
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type="native_audio_compatibility_record",
                        field_path="status",
                        message="incompatible native audio record must use blocked status",
                    )
                )

    # Validate Kling shot prompt cross-links.
    for path in grouped_files.get("kling_shot_prompt_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue

        linked_refs = data.get("linked_element_refs")
        if isinstance(linked_refs, list):
            for ref_id in linked_refs:
                if isinstance(ref_id, str) and ref_id and ref_id not in kling_element_refs:
                    issues.append(
                        ProductionValidationIssue(
                            file=_relative(path, repo_root),
                            record_type="kling_shot_prompt_record",
                            field_path="linked_element_refs",
                            message=f"missing linked Kling element reference: {ref_id}",
                        )
                    )

        status = data.get("status")
        materialized_output = data.get("materialized_output")
        if status == "materialized" and isinstance(materialized_output, dict):
            ext_ref = materialized_output.get("external_storage_ref")
            platform_job_id = materialized_output.get("platform_job_id")
            repo_binary_committed = materialized_output.get("repo_binary_committed")
            if not isinstance(ext_ref, str) or not ext_ref.strip():
                issues.append(
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type="kling_shot_prompt_record",
                        field_path="materialized_output.external_storage_ref",
                        message="materialized shot output requires external_storage_ref",
                    )
                )
            if not isinstance(platform_job_id, str) or not platform_job_id.strip():
                issues.append(
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type="kling_shot_prompt_record",
                        field_path="materialized_output.platform_job_id",
                        message="materialized shot output requires platform_job_id",
                    )
                )
            if repo_binary_committed is not False:
                issues.append(
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type="kling_shot_prompt_record",
                        field_path="materialized_output.repo_binary_committed",
                        message="materialized shot output must keep repo_binary_committed=false",
                    )
                )

        if data.get("native_audio") is True:
            dialogue_items = data.get("dialogue")
            dialogue_refs: set[str] = set()
            performance_refs: set[str] = set()
            if isinstance(dialogue_items, list):
                for item in dialogue_items:
                    if isinstance(item, str):
                        if item.startswith("DLG_"):
                            dialogue_refs.add(item)
                        if item.startswith("PERF_"):
                            performance_refs.add(item)
            missing_dialogue = sorted(ref for ref in dialogue_refs if ref not in dialogue_extract_ids)
            missing_performance = sorted(
                ref for ref in performance_refs if ref not in performance_intent_ids
            )
            if not dialogue_refs or not performance_refs or missing_dialogue or missing_performance:
                missing_id = (
                    (missing_dialogue + missing_performance)[0]
                    if (missing_dialogue + missing_performance)
                    else "DLG_/PERF_ reference"
                )
                issues.append(
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type="kling_shot_prompt_record",
                        field_path="dialogue",
                        message=(
                            "missing dialogue extract/performance intent reference: "
                            f"{missing_id}"
                        ),
                    )
                )

            voice_binding_id = data.get("voice_binding")
            if isinstance(voice_binding_id, str) and voice_binding_id:
                voice_record = voice_binding_by_id.get(voice_binding_id)
                if voice_record is None:
                    issues.append(
                        ProductionValidationIssue(
                            file=_relative(path, repo_root),
                            record_type="kling_shot_prompt_record",
                            field_path="voice_binding",
                            message=f"missing voice binding record: {voice_binding_id}",
                        )
                    )
                elif voice_record.get("binding_status") == "pending":
                    issues.append(
                        ProductionValidationIssue(
                            file=_relative(path, repo_root),
                            record_type="kling_shot_prompt_record",
                            field_path="voice_binding",
                            message=(
                                "voice binding is pending and blocks dialogue shot production: "
                                f"{voice_binding_id}"
                            ),
                        )
                    )

            native_audio_compat_ref = data.get("native_audio_compatibility")
            if isinstance(native_audio_compat_ref, str) and native_audio_compat_ref:
                if native_audio_compat_ref not in native_audio_compat_by_id:
                    issues.append(
                        ProductionValidationIssue(
                            file=_relative(path, repo_root),
                            record_type="kling_shot_prompt_record",
                            field_path="dialogue",
                            message=(
                                "missing dialogue extract/performance intent reference: "
                                f"{native_audio_compat_ref}"
                            ),
                        )
                    )

    return issues


def validate_production_batch_model_guidance_gate(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    """Require fresh model guidance snapshots for each production batch model."""
    issues: list[ProductionValidationIssue] = []
    batch_targets: dict[str, set[str]] = {}

    for path in grouped_files.get("production_batch", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        models = data.get("models")
        if not isinstance(models, list):
            continue
        required_targets = {
            PRODUCTION_BATCH_MODEL_GUIDANCE_TARGETS[model]
            for model in models
            if isinstance(model, str)
            and model in PRODUCTION_BATCH_MODEL_GUIDANCE_TARGETS
        }
        if required_targets:
            batch_targets[_relative(path, repo_root)] = required_targets

    if not batch_targets:
        return issues

    required_targets = sorted({t for targets in batch_targets.values() for t in targets})
    gate_func = None
    import_error: Exception | None = None
    try:
        from scripts.validators.validate_model_research_gate import (
            validate_model_research_gate as imported_gate_func,
        )
        gate_func = imported_gate_func
    except Exception as exc:
        import_error = exc
        module_path = repo_root / "scripts" / "validators" / "validate_model_research_gate.py"
        try:
            spec = importlib.util.spec_from_file_location(
                "validate_model_research_gate_module",
                module_path,
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                gate_func = getattr(module, "validate_model_research_gate", None)
        except Exception as fallback_exc:
            import_error = fallback_exc

    if gate_func is None:
        for file in sorted(batch_targets):
            issues.append(
                ProductionValidationIssue(
                    file=file,
                    record_type="production_batch",
                    field_path="models",
                    message=f"model guidance gate unavailable: {import_error}",
                )
            )
        return issues

    results = gate_func(
        repo_root=repo_root,
        required_targets=required_targets,
        reference_time=datetime.now(timezone.utc),
    )
    failures = {result.target for result in results if not result.passed}
    for file, targets in batch_targets.items():
        for target in sorted(targets):
            if target in failures:
                issues.append(
                    ProductionValidationIssue(
                        file=file,
                        record_type="production_batch",
                        field_path="models",
                        message=f"model guidance gate failed for target: {target}",
                    )
                )

    return issues


def _is_int_score(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_perspective_qc_readiness(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []
    score_fields = (
        "identity_preservation",
        "perspective_usefulness",
        "material_palette_continuity",
        "production_reference_cleanliness",
        "hallucination_absence",
        "total_score",
    )
    blocked_decisions = {"pending", "fail", "revise"}

    for path in grouped_files.get("perspective_qc_report", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        gate = data.get("gate")
        if not isinstance(gate, dict) or gate.get("can_advance_to_kling_reference") is not True:
            continue

        scores = data.get("perspective_scores")
        minimum_score = gate.get("minimum_score")
        can_advance = True
        if not isinstance(scores, list) or len(scores) != 4:
            can_advance = False
        if not _is_int_score(minimum_score):
            can_advance = False

        if can_advance:
            for score_entry in scores:
                if not isinstance(score_entry, dict):
                    can_advance = False
                    break
                for field in score_fields:
                    if not _is_int_score(score_entry.get(field)):
                        can_advance = False
                        break
                decision = score_entry.get("decision")
                if not isinstance(decision, str) or decision in blocked_decisions:
                    can_advance = False
                total_score = score_entry.get("total_score")
                if _is_int_score(total_score) and _is_int_score(minimum_score):
                    if total_score < minimum_score:
                        can_advance = False
                if not can_advance:
                    break

        if not can_advance:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="perspective_qc_report",
                    field_path="gate.can_advance_to_kling_reference",
                    message="perspective QC cannot advance before all scores meet threshold",
                )
            )
    return issues


def validate_dialogue_qc_readiness(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []
    blocking_checks = (
        "speaker_identity_correctness",
        "line_accuracy",
        "lip_sync_stability",
        "performance_tone_match",
        "unwanted_speech_or_subtitles",
        "unsupported_input_mode_combination",
    )
    for path in grouped_files.get("dialogue_qc_report", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        gate = data.get("gate")
        if not isinstance(gate, dict) or gate.get("can_advance_to_candidate") is not True:
            continue
        checks = data.get("checks")
        valid = isinstance(checks, dict)
        if valid:
            for name in blocking_checks:
                value = checks.get(name)
                if value in {"pending", "fail"}:
                    valid = False
                    break
        if not valid:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="dialogue_qc_report",
                    field_path="gate.can_advance_to_candidate",
                    message="dialogue QC cannot advance while checks are pending or failing",
                )
            )
    return issues


def validate_omni_qc_readiness(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []
    for path in grouped_files.get("omni_qc_report", []):
        data = _load_yaml_mapping(path)
        if not data or data.get("selected_for_next_pass") is not True:
            continue
        checks = data.get("checks")
        retry_rule = data.get("retry_rule")
        provenance = data.get("provenance")
        valid = isinstance(checks, dict) and isinstance(provenance, dict)
        if valid:
            if checks.get("identity_consistency") != "pass":
                valid = False
            if checks.get("camera_stability") != "pass":
                valid = False
            if checks.get("narrative_beat") != "pass":
                valid = False
            if checks.get("audio_sync") not in {"pass", "not_applicable"}:
                valid = False
            if checks.get("unwanted_speech") not in {"pass", "not_applicable"}:
                valid = False
            motion = checks.get("motion_artifacts")
            hand_face = checks.get("hand_face_artifacts")
            if motion == "warn" and not isinstance(retry_rule, dict):
                valid = False
            if hand_face == "warn" and not isinstance(retry_rule, dict):
                valid = False
            if motion not in {"pass", "warn"}:
                valid = False
            if hand_face not in {"pass", "warn"}:
                valid = False
            if provenance.get("reviewed_by") == "human_operator_pending":
                valid = False
        if not valid:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="omni_qc_report",
                    field_path="selected_for_next_pass",
                    message="selected_for_next_pass requires completed passing Omni QC",
                )
            )
    return issues


def validate_qc_cross_record_gates(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []
    issues.extend(
        validate_perspective_qc_readiness(repo_root=repo_root, grouped_files=grouped_files)
    )
    issues.extend(
        validate_dialogue_qc_readiness(repo_root=repo_root, grouped_files=grouped_files)
    )
    issues.extend(validate_omni_qc_readiness(repo_root=repo_root, grouped_files=grouped_files))

    perspective_qc_records: list[dict[str, Any]] = []
    for path in grouped_files.get("perspective_qc_report", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        perspective_qc_records.append(data)

    dialogue_qc_by_scene_shot: dict[tuple[str, str], dict[str, Any]] = {}
    for path in grouped_files.get("dialogue_qc_report", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        scene_id = data.get("scene_id")
        shot_id = data.get("shot_id")
        if isinstance(scene_id, str) and isinstance(shot_id, str):
            dialogue_qc_by_scene_shot[(scene_id, shot_id)] = data

    for path in grouped_files.get("kling_element_reference_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        approval_gate = data.get("approval_gate")
        if not isinstance(approval_gate, dict):
            continue
        if approval_gate.get("all_perspectives_score_85_plus") is not True:
            continue
        element_id = data.get("element_id")
        has_passing = False
        for pqc in perspective_qc_records:
            if pqc.get("element_id") != element_id:
                continue
            gate = pqc.get("gate")
            if isinstance(gate, dict) and gate.get("can_advance_to_kling_reference") is True:
                has_passing = True
                break
        if not has_passing:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="kling_element_reference_record",
                    field_path="approval_gate.all_perspectives_score_85_plus",
                    message="all_perspectives_score_85_plus requires completed perspective QC report",
                )
            )

    advanced_statuses = {"final_candidate", "final_locked", "materialized"}
    for path in grouped_files.get("kling_shot_prompt_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        if data.get("native_audio") is not True:
            continue
        status = data.get("status")
        if status not in advanced_statuses:
            continue
        scene_id = data.get("scene_id")
        shot_id = data.get("shot_id")
        dialogue_qc = dialogue_qc_by_scene_shot.get((scene_id, shot_id))
        gate = dialogue_qc.get("gate") if isinstance(dialogue_qc, dict) else None
        if not isinstance(gate, dict) or gate.get("can_advance_to_candidate") is not True:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="kling_shot_prompt_record",
                    field_path="native_audio",
                    message="native audio shot cannot advance without completed dialogue QC",
                )
            )
    return issues


def build_gptimg2_prompt_index(
    *,
    grouped_files: dict[str, list[Path]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in grouped_files.get("gpt_images_perspective_pack", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        prompt_pack_id = data.get("prompt_pack_id")
        element_id = data.get("element_id")
        prompts = data.get("prompts")
        if not isinstance(prompts, list):
            continue
        for prompt in prompts:
            if not isinstance(prompt, dict):
                continue
            prompt_id = prompt.get("prompt_id")
            if not isinstance(prompt_id, str) or not prompt_id:
                continue
            index[prompt_id] = {
                "prompt_pack_id": prompt_pack_id,
                "element_id": element_id,
                "perspective": prompt.get("perspective"),
            }
    return index


def build_image_selection_candidate_index(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for path in grouped_files.get("image_selection", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        candidates = data.get("candidate_images")
        if not isinstance(candidates, list):
            continue
        rel_file = _relative(path, repo_root)
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            asset_id = candidate.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id:
                continue
            index.setdefault(asset_id, []).append(
                {
                    "file": rel_file,
                    "asset_id": asset_id,
                    "external_storage_ref": candidate.get("external_storage_ref"),
                    "repo_binary_committed": candidate.get("repo_binary_committed"),
                    "status": candidate.get("status"),
                    "path": candidate.get("path"),
                }
            )
    return index


def build_local_media_index_entry_index(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for path in grouped_files.get("local_media_index", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        entries = data.get("entries")
        if not isinstance(entries, list):
            continue
        rel_file = _relative(path, repo_root)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("element_id_or_take_id")
            if not isinstance(entry_id, str) or not entry_id:
                continue
            index.setdefault(entry_id, []).append(
                {
                    "file": rel_file,
                    "element_id_or_take_id": entry_id,
                    "external_storage_ref": entry.get("external_storage_ref"),
                    "repo_binary_committed": entry.get("repo_binary_committed"),
                    "storage_backend": entry.get("storage_backend"),
                    "kind": entry.get("kind"),
                    "local_path": entry.get("local_path"),
                }
            )
    return index


def _has_non_pending_registration_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and not value.startswith("pending_external://")
    )


def _is_perspective_qc_populated(entry: dict[str, Any]) -> bool:
    if entry.get("decision") != "pending":
        return True
    for field in (
        "identity_preservation",
        "perspective_usefulness",
        "material_palette_continuity",
        "production_reference_cleanliness",
        "hallucination_absence",
        "total_score",
    ):
        if entry.get(field) is not None:
            return True
    return False


def validate_gptimg2_registration_gates(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []
    prompt_index = build_gptimg2_prompt_index(grouped_files=grouped_files)
    image_selection_index = build_image_selection_candidate_index(
        repo_root=repo_root,
        grouped_files=grouped_files,
    )
    local_media_index = build_local_media_index_entry_index(
        repo_root=repo_root,
        grouped_files=grouped_files,
    )

    for path in grouped_files.get("perspective_qc_report", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        scores = data.get("perspective_scores")
        if not isinstance(scores, list):
            continue
        prompt_ids: list[str] = []
        populated = False
        for score in scores:
            if not isinstance(score, dict):
                continue
            prompt_id = score.get("prompt_id")
            if isinstance(prompt_id, str) and prompt_id:
                prompt_ids.append(prompt_id)
            if _is_perspective_qc_populated(score):
                populated = True

        for prompt_id in prompt_ids:
            if prompt_id not in prompt_index:
                continue
            selection_entries = image_selection_index.get(prompt_id, [])
            media_entries = local_media_index.get(prompt_id, [])
            has_valid_selection = any(
                entry.get("repo_binary_committed") is False
                and isinstance(entry.get("external_storage_ref"), str)
                and bool(str(entry.get("external_storage_ref")).strip())
                for entry in selection_entries
            )
            has_valid_media = any(
                entry.get("repo_binary_committed") is False
                and isinstance(entry.get("external_storage_ref"), str)
                and bool(str(entry.get("external_storage_ref")).strip())
                for entry in media_entries
            )
            if populated and (not has_valid_selection or not has_valid_media):
                issues.append(
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type="perspective_qc_report",
                        field_path="perspective_scores",
                        message=(
                            "perspective QC cannot be populated before GPT Images 2 output "
                            f"registration metadata exists: {prompt_id}"
                        ),
                    )
                )

        gate = data.get("gate")
        if not isinstance(gate, dict) or gate.get("can_advance_to_kling_reference") is not True:
            continue

        for prompt_id in prompt_ids:
            if prompt_id not in prompt_index:
                continue
            selection_entries = image_selection_index.get(prompt_id, [])
            media_entries = local_media_index.get(prompt_id, [])
            has_ready_selection = any(
                entry.get("repo_binary_committed") is False
                and _has_non_pending_registration_ref(entry.get("external_storage_ref"))
                and entry.get("status") in {"candidate", "selected"}
                for entry in selection_entries
            )
            has_ready_media = any(
                entry.get("repo_binary_committed") is False
                and _has_non_pending_registration_ref(entry.get("external_storage_ref"))
                for entry in media_entries
            )
            if not has_ready_selection or not has_ready_media:
                issues.append(
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type="perspective_qc_report",
                        field_path="gate.can_advance_to_kling_reference",
                        message=(
                            "perspective QC cannot advance while GPT Images 2 external refs "
                            f"are pending: {prompt_id}"
                        ),
                    )
                )

    return issues


def validate_review_decision_records(
    *,
    repo_root: Path,
    grouped_files: dict[str, list[Path]],
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []
    id_field_by_record_type: dict[str, str] = {
        "gpt_images_perspective_pack": "prompt_pack_id",
        "kling_element_reference_record": "kling_element_reference_id",
        "kling_character_look_element": "kling_character_look_element_id",
        "dialogue_extract_record": "dialogue_extract_id",
        "performance_intent_record": "performance_intent_id",
        "voice_binding_record": "voice_binding_id",
        "native_audio_compatibility_record": "native_audio_compatibility_id",
        "kling_shot_prompt_record": "kling_shot_prompt_id",
        "perspective_qc_report": "perspective_qc_id",
        "dialogue_qc_report": "dialogue_qc_id",
        "omni_qc_report": "clip_id",
        "production_batch": "production_batch_id",
    }
    operator_session_ids: set[str] = set()
    for path in grouped_files.get("operator_session", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        session_id = data.get("session_id")
        if isinstance(session_id, str) and session_id:
            operator_session_ids.add(session_id)

    for path in grouped_files.get("review_decision_record", []):
        data = _load_yaml_mapping(path)
        if not data:
            continue
        session_ref = data.get("operator_session_ref")
        if not isinstance(session_ref, str) or session_ref not in operator_session_ids:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="review_decision_record",
                    field_path="operator_session_ref",
                    message="operator_session_ref must reference an existing operator_session record",
                )
            )
        target_path = data.get("target_path")
        invalid_path = False
        if not isinstance(target_path, str) or not target_path.strip():
            invalid_path = True
        else:
            normalized = target_path.replace("\\", "/")
            if normalized.startswith("/") or WINDOWS_ABSOLUTE_PATH_RE.match(target_path):
                invalid_path = True
            if ".." in normalized.split("/"):
                invalid_path = True
        if invalid_path:
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="review_decision_record",
                    field_path="target_path",
                    message="target_path must be a safe repo-relative path",
                )
            )
        elif not (repo_root / target_path).exists():
            issues.append(
                ProductionValidationIssue(
                    file=_relative(path, repo_root),
                    record_type="review_decision_record",
                    field_path="target_path",
                    message="target_path must exist in repository",
                )
            )
        else:
            target_record_type = data.get("target_record_type")
            expected_id = data.get("target_record_id")
            if isinstance(target_record_type, str) and isinstance(expected_id, str):
                target_data = _load_yaml_mapping(repo_root / target_path)
                if not isinstance(target_data, dict):
                    issues.append(
                        ProductionValidationIssue(
                            file=_relative(path, repo_root),
                            record_type="review_decision_record",
                            field_path="target_path",
                            message="target_path must point to a YAML mapping record",
                        )
                    )
                else:
                    actual_type = target_data.get("record_type")
                    if actual_type != target_record_type:
                        issues.append(
                            ProductionValidationIssue(
                                file=_relative(path, repo_root),
                                record_type="review_decision_record",
                                field_path="target_record_type",
                                message="target_record_type must match record_type at target_path",
                            )
                        )
                    id_field = id_field_by_record_type.get(target_record_type)
                    if id_field:
                        actual_id = target_data.get(id_field)
                        if actual_id != expected_id:
                            issues.append(
                                ProductionValidationIssue(
                                    file=_relative(path, repo_root),
                                    record_type="review_decision_record",
                                    field_path="target_record_id",
                                    message="target_record_id must match record id at target_path",
                                )
                            )
    return issues


def validate_character_continuity_records(
    *,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    issues: list[ProductionValidationIssue] = []
    gate_func = None
    import_error: Exception | None = None
    try:
        from scripts.validators.validate_character_continuity import (
            validate_character_continuity,
        )
        gate_func = validate_character_continuity
    except Exception as exc:
        import_error = exc
        module_path = repo_root / "scripts" / "validators" / "validate_character_continuity.py"
        try:
            spec = importlib.util.spec_from_file_location(
                "validate_character_continuity_module",
                module_path,
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                gate_func = getattr(module, "validate_character_continuity", None)
        except Exception as fallback_exc:
            import_error = fallback_exc

    if gate_func is None:
        issues.append(
            ProductionValidationIssue(
                file="scripts/validate_production_records.py",
                record_type="character_continuity_gate",
                field_path="validate_character_continuity import",
                message=f"character continuity gate unavailable: {import_error}",
            )
        )
        return issues

    for item in gate_func(repo_root):
        if getattr(item, "severity", "error") != "error":
            # Soft-gate: ignore warnings as non-failing informational checks.
            continue
        issues.append(
            ProductionValidationIssue(
                file=item.file,
                record_type=item.record_type,
                field_path=item.field_path,
                message=item.message,
            )
        )
    return issues


def _load_structural_record(
    *,
    path: Path,
    repo_root: Path,
    record_type: str,
) -> tuple[Any | None, list[ProductionValidationIssue]]:
    try:
        data = load_yaml_file(path)
    except Exception as exc:
        return None, [
            ProductionValidationIssue(
                file=_relative(path, repo_root),
                record_type=record_type,
                field_path="",
                message=f"YAML parse error: {exc}",
            )
        ]

    if not isinstance(data, dict):
        return data, [
            ProductionValidationIssue(
                file=_relative(path, repo_root),
                record_type=record_type,
                field_path="(root)",
                message="Record must be a mapping.",
            )
        ]
    return data, []


def _structural_issue(
    *,
    path: Path,
    repo_root: Path,
    record_type: str,
    field_path: str,
    message: str,
) -> ProductionValidationIssue:
    return ProductionValidationIssue(
        file=_relative(path, repo_root),
        record_type=record_type,
        field_path=field_path,
        message=message,
    )


def validate_pack_suggestion_file(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Validate a pack manifest suggestion without mutating pack_manifest.yaml."""
    record_type = "pack_manifest_update_suggestion"
    data, issues = _load_structural_record(
        path=path,
        repo_root=repo_root,
        record_type=record_type,
    )
    if issues:
        return issues

    missing = sorted(PACK_SUGGESTION_REQUIRED_KEYS - set(data))
    for key in missing:
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path=key,
                message="Required field is missing.",
            )
        )

    forbidden = sorted(FORBIDDEN_LIFECYCLE_KEYS & set(data))
    for key in forbidden:
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path=key,
                message="Lifecycle state must not be set directly in a suggestion record.",
            )
        )

    if data.get("suggested_field") != "pack_status":
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="suggested_field",
                message='suggested_field must be "pack_status".',
            )
        )

    if data.get("suggested_value") not in PACK_SUGGESTION_ALLOWED_VALUES:
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="suggested_value",
                message=(
                    "suggested_value must be metadata_only or seeded; "
                    "approval/lock promotion is out of Batch 5.6 scope."
                ),
            )
        )

    reason = data.get("reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="reason",
                message="reason must be a non-empty string.",
            )
        )

    return issues


def validate_prompt_review_brief_file(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Validate a corrected prompt brief produced from image review feedback."""
    record_type = "prompt_review_brief"
    data, issues = _load_structural_record(
        path=path,
        repo_root=repo_root,
        record_type=record_type,
    )
    if issues:
        return issues

    missing = sorted(PROMPT_REVIEW_REQUIRED_KEYS - set(data))
    for key in missing:
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path=key,
                message="Required field is missing.",
            )
        )

    source_prompt_id = data.get("source_prompt_id")
    if source_prompt_id is not None:
        if not isinstance(source_prompt_id, str) or not source_prompt_id:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path="source_prompt_id",
                    message="source_prompt_id must be a non-empty string.",
                )
            )

    corrected_brief = data.get("corrected_brief")
    if corrected_brief is not None:
        if not isinstance(corrected_brief, dict) or not corrected_brief:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path="corrected_brief",
                    message="corrected_brief must be a non-empty mapping.",
                )
            )

    return issues


def _is_safe_handoff_context_path(value: str) -> bool:
    if value.startswith("/"):
        return False
    if WINDOWS_ABSOLUTE_PATH_RE.match(value):
        return False
    parts = value.replace("\\", "/").split("/")
    return ".." not in parts


def validate_agent_handoff_consistency(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Validate handoff rules that sit outside JSON Schema."""
    record_type = "agent_handoff"
    data, issues = _load_structural_record(
        path=path,
        repo_root=repo_root,
        record_type=record_type,
    )
    if issues:
        return issues

    if data.get("from_agent") == data.get("to_agent"):
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="to_agent",
                message="from_agent and to_agent must be different.",
            )
        )

    context_files = data.get("context_files")
    if isinstance(context_files, list):
        for index, context_path in enumerate(context_files):
            if isinstance(context_path, str) and not _is_safe_handoff_context_path(
                context_path
            ):
                issues.append(
                    _structural_issue(
                        path=path,
                        repo_root=repo_root,
                        record_type=record_type,
                        field_path=f"context_files.{index}",
                        message=(
                            "context_files entries must be repo-relative paths "
                            "with no absolute paths or traversal segments."
                        ),
                    )
                )

    head_sha = data.get("head_sha")
    if head_sha is not None and (
        not isinstance(head_sha, str) or not AGENT_HANDOFF_HEAD_SHA_RE.match(head_sha)
    ):
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="head_sha",
                message="head_sha must be 7 to 40 hex characters.",
            )
        )

    branch = data.get("branch")
    if branch is not None and (
        not isinstance(branch, str) or not AGENT_HANDOFF_BRANCH_RE.match(branch)
    ):
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="branch",
                message="branch must start with main, feat/, fix/, docs/, chore/, or review/.",
            )
        )

    return issues


def validate_video_take_consistency(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Validate cross-field video take rules that JSON Schema cannot express."""
    record_type = "video_take"
    data, issues = _load_structural_record(
        path=path,
        repo_root=repo_root,
        record_type=record_type,
    )
    if issues:
        return issues

    takes = data.get("takes")
    if not isinstance(takes, list):
        return issues

    selected_takes = [
        take for take in takes if isinstance(take, dict) and take.get("status") == "selected"
    ]
    if len(selected_takes) > 1:
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="takes",
                message="At most one take may have status selected.",
            )
        )

    selected_take = data.get("selected_take")
    if selected_take is not None:
        matching_selected = [
            take
            for take in selected_takes
            if isinstance(take, dict) and take.get("take_id") == selected_take
        ]
        if not matching_selected:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path="selected_take",
                    message="selected_take must match a take_id whose status is selected.",
                )
            )
    elif selected_takes:
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="selected_take",
                message="selected_take must be set when a take has status selected.",
            )
        )

    for index, take in enumerate(takes):
        if not isinstance(take, dict):
            continue
        field_prefix = f"takes.{index}"
        if take.get("repo_binary_committed") is not False:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.repo_binary_committed",
                    message="repo_binary_committed must be false for every video take.",
                )
            )
        external_storage_ref = take.get("external_storage_ref")
        missing_external_allowed = (
            take.get("status") == "candidate"
            and take.get("storage_status") == "pending_external"
        )
        if not external_storage_ref and not missing_external_allowed:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.external_storage_ref",
                    message=(
                        "external_storage_ref is required unless the take is a "
                        "candidate with storage_status pending_external."
                    ),
                )
            )

    return issues


_VIDEO_BINARY_EXTENSIONS = {".mp4", ".mov", ".mkv", ".wav"}
_IMAGE_BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".psd", ".tiff", ".tif"}


def _looks_like_repo_video_binary(value: object) -> bool:
    if not value:
        return False
    text = str(value)
    if "://" in text:
        return False
    return Path(text).suffix.lower() in _VIDEO_BINARY_EXTENSIONS


def _looks_like_repo_image_binary(value: object) -> bool:
    if not value:
        return False
    text = str(value)
    if "://" in text:
        return False
    return Path(text).suffix.lower() in _IMAGE_BINARY_EXTENSIONS


def validate_image_selection_extra(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Cross-field checks for image_selection beyond JSON Schema."""
    record_type = "image_selection"
    data, issues = _load_structural_record(
        path=path,
        repo_root=repo_root,
        record_type=record_type,
    )
    if issues:
        return issues

    rel_path = _relative(path, repo_root)
    is_gptimg2_registration = "/gptimg2_perspectives/image_selection.yaml" in rel_path

    candidates = data.get("candidate_images")
    if not isinstance(candidates, list):
        return issues

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        field_prefix = f"candidate_images.{index}"
        if is_gptimg2_registration and candidate.get("repo_binary_committed") is not False:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.repo_binary_committed",
                    message="repo_binary_committed must be false for every image selection candidate.",
                )
            )
        if is_gptimg2_registration and candidate.get("status") == "canonical":
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.status",
                    message=(
                        "GPT Images 2 registration checklist must not select or canonicalize candidates"
                    ),
                )
            )

    if is_gptimg2_registration:
        if data.get("canonical_images") not in ([],):
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path="canonical_images",
                    message=(
                        "GPT Images 2 registration checklist must not select or canonicalize candidates"
                    ),
                )
            )
        if data.get("pack_manifest_sync") != "pending":
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path="pack_manifest_sync",
                    message=(
                        "GPT Images 2 registration checklist must not select or canonicalize candidates"
                    ),
                )
            )

    return issues


def validate_selected_take_extra(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Cross-field checks for selected_take.yaml beyond JSON Schema."""
    issues: list[ProductionValidationIssue] = []
    try:
        data = load_yaml_file(path)
    except Exception:
        return issues
    if not isinstance(data, dict):
        return issues
    local_proxy_ref = data.get("local_proxy_ref")
    if _looks_like_repo_video_binary(local_proxy_ref):
        issues.append(
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type="selected_take",
                field_path="local_proxy_ref",
                message=(
                    "local_proxy_ref must not point to a repo video binary. "
                    "Use an external storage ref (dvc://, s3://, etc.) or null."
                ),
            )
        )
    return issues


def validate_local_media_index_extra(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Cross-field checks for local_media_index beyond JSON Schema."""
    record_type = "local_media_index"
    data, issues = _load_structural_record(
        path=path,
        repo_root=repo_root,
        record_type=record_type,
    )
    if issues:
        return issues

    entries = data.get("entries")
    if not isinstance(entries, list):
        return issues

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        field_prefix = f"entries.{index}"

        if entry.get("repo_binary_committed") is not False:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.repo_binary_committed",
                    message="repo_binary_committed must be false for every media index entry.",
                )
            )
            if entry.get("kind") == "gpt_images_2_perspective_output":
                issues.append(
                    _structural_issue(
                        path=path,
                        repo_root=repo_root,
                        record_type=record_type,
                        field_path=f"{field_prefix}.repo_binary_committed",
                        message="GPT Images 2 output registration must remain external metadata only",
                    )
                )

        local_path = entry.get("local_path")
        if _looks_like_repo_video_binary(local_path) and not entry.get("external_storage_ref"):
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.external_storage_ref",
                    message=(
                        "Video-like local_path must also have external_storage_ref "
                        "to ensure the master copy is tracked in external storage."
                    ),
                )
            )
        if (
            entry.get("kind") == "gpt_images_2_perspective_output"
            and _looks_like_repo_image_binary(local_path)
            and not entry.get("external_storage_ref")
        ):
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.external_storage_ref",
                    message="GPT Images 2 output registration must remain external metadata only",
                )
            )
        if entry.get("kind") == "gpt_images_2_perspective_output":
            if not entry.get("external_storage_ref"):
                issues.append(
                    _structural_issue(
                        path=path,
                        repo_root=repo_root,
                        record_type=record_type,
                        field_path=f"{field_prefix}.external_storage_ref",
                        message="GPT Images 2 output registration must remain external metadata only",
                    )
                )

    if any(
        isinstance(entry, dict) and entry.get("kind") == "gpt_images_2_perspective_output"
        for entry in entries
    ):
        storage_policy = data.get("storage_policy")
        if storage_policy not in {"external_image_only", "mixed_external"}:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path="storage_policy",
                    message="GPT Images 2 output registration must remain external metadata only",
                )
            )

    return issues


def validate_scene_clip_map_file(
    path: Path,
    repo_root: Path,
) -> list[ProductionValidationIssue]:
    """Validate the metadata-only scene clip map CSV."""
    record_type = "scene_clip_map"
    issues: list[ProductionValidationIssue] = []
    if not path.exists():
        return [
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="",
                message="scene_clip_map.csv is required when selected_take.yaml exists.",
            )
        ]
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != SCENE_CLIP_MAP_HEADER:
                return [
                    _structural_issue(
                        path=path,
                        repo_root=repo_root,
                        record_type=record_type,
                        field_path="header",
                        message="scene_clip_map.csv header is invalid.",
                    )
                ]
            rows = list(reader)
    except Exception as exc:
        return [
            _structural_issue(
                path=path,
                repo_root=repo_root,
                record_type=record_type,
                field_path="",
                message=f"CSV parse error: {exc}",
            )
        ]

    seen_scene_rows: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows):
        scene_id = row.get("scene_id", "")
        field_prefix = f"rows.{index}"
        if not scene_id:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.scene_id",
                    message="scene_id is required.",
                )
            )
            continue
        selected_path = (
            repo_root / "visual_dev" / "omni_sets" / scene_id / "selected_take.yaml"
        )
        if not selected_path.exists():
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.scene_id",
                    message="scene_clip_map row requires matching selected_take.yaml.",
                )
            )
        if scene_id in seen_scene_rows and seen_scene_rows[scene_id] != row:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.scene_id",
                    message="Duplicate scene_id rows must be identical.",
                )
            )
        seen_scene_rows[scene_id] = row
        if not row.get("selected_take"):
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.selected_take",
                    message="selected_take is required.",
                )
            )
        if not row.get("external_storage_ref"):
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.external_storage_ref",
                    message="external_storage_ref is required.",
                )
            )
        if row.get("repo_binary_committed") != "false":
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path=f"{field_prefix}.repo_binary_committed",
                    message='repo_binary_committed must be "false".',
                )
            )

    selected_take_files = sorted(repo_root.glob(SELECTED_TAKE_PATTERN))
    mapped_scene_ids = set(seen_scene_rows)
    for selected_path in selected_take_files:
        scene_id = selected_path.parent.name
        if scene_id not in mapped_scene_ids:
            issues.append(
                _structural_issue(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    field_path="scene_id",
                    message=f"Missing scene_clip_map row for {scene_id}.",
                )
            )

    return issues


def run_validation(
    repo_root: Path,
    report_json: Path | None = None,
) -> ProductionValidationReport:
    """Run production metadata validation."""
    image_selection_schema = load_schema(repo_root / "schemas" / "image_selection.schema.json")
    asset_clearance_schema = load_schema(repo_root / "schemas" / "asset_clearance.schema.json")
    storyboard_options_schema = load_schema(
        repo_root / "schemas" / "storyboard_option.schema.json"
    )
    batch_job_schema = load_schema(repo_root / "schemas" / "batch_job.schema.json")
    image_selection_validator = Draft202012Validator(image_selection_schema)
    asset_clearance_validator = Draft202012Validator(asset_clearance_schema)
    storyboard_options_validator = Draft202012Validator(storyboard_options_schema)
    shot_list_omni_suggestion_schema = load_schema(
        repo_root / "schemas" / "shot_list_omni_suggestion.schema.json"
    )
    batch_job_validator = Draft202012Validator(batch_job_schema)
    shot_list_omni_suggestion_validator = Draft202012Validator(
        shot_list_omni_suggestion_schema
    )
    operator_session_validator: Draft202012Validator | None = None
    agent_handoff_validator: Draft202012Validator | None = None
    local_media_index_validator: Draft202012Validator | None = None
    video_take_validator: Draft202012Validator | None = None
    video_review_validator: Draft202012Validator | None = None
    selected_take_validator: Draft202012Validator | None = None
    omni_set_gate_validator: Draft202012Validator | None = None
    pack_lock_readiness_validator: Draft202012Validator | None = None
    canonical_asset_work_order_validator: Draft202012Validator | None = None
    canonical_asset_intake_scaffold_validator: Draft202012Validator | None = None
    canonical_asset_intake_instruction_validator: Draft202012Validator | None = None
    canonical_asset_intake_slot_validator: Draft202012Validator | None = None
    clean_start_audit_validator: Draft202012Validator | None = None
    pre_b8a_clean_reset_validator: Draft202012Validator | None = None
    omni_qc_report_validator: Draft202012Validator | None = None
    perspective_qc_report_validator: Draft202012Validator | None = None
    dialogue_qc_report_validator: Draft202012Validator | None = None
    review_decision_record_validator: Draft202012Validator | None = None
    gpt_images_perspective_pack_validator: Draft202012Validator | None = None
    kling_element_reference_validator: Draft202012Validator | None = None
    kling_character_look_element_validator: Draft202012Validator | None = None
    kling_shot_prompt_record_validator: Draft202012Validator | None = None
    dialogue_extract_record_validator: Draft202012Validator | None = None
    performance_intent_record_validator: Draft202012Validator | None = None
    voice_binding_record_validator: Draft202012Validator | None = None
    native_audio_compatibility_record_validator: Draft202012Validator | None = None
    character_identity_anchor_validator: Draft202012Validator | None = None
    character_look_variant_validator: Draft202012Validator | None = None
    scene_character_look_map_validator: Draft202012Validator | None = None
    production_batch_validator: Draft202012Validator | None = None
    aesthetic_bible_validator: Draft202012Validator | None = None

    grouped_files = collect_production_files(repo_root)
    total = sum(len(files) for files in grouped_files.values())
    by_record_type = {record_type: len(files) for record_type, files in grouped_files.items()}

    all_issues: list[ProductionValidationIssue] = []
    invalid_files: set[str] = set()

    for record_type, files in grouped_files.items():
        for path in files:
            if record_type == "image_selection":
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=image_selection_validator,
                )
                file_issues.extend(validate_image_selection_extra(path, repo_root))
            elif record_type == "asset_clearance":
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=asset_clearance_validator,
                )
            elif record_type == "pack_manifest_update_suggestion":
                file_issues = validate_pack_suggestion_file(path, repo_root)
            elif record_type == "prompt_review_brief":
                file_issues = validate_prompt_review_brief_file(path, repo_root)
            elif record_type == "storyboard_options":
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=storyboard_options_validator,
                )
            elif record_type == "shot_list_omni_suggestion":
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=shot_list_omni_suggestion_validator,
                )
            elif record_type == "batch_job":
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=batch_job_validator,
                )
            elif record_type == "operator_session":
                if operator_session_validator is None:
                    operator_session_schema = load_schema(
                        repo_root / "schemas" / "operator_session.schema.json"
                    )
                    operator_session_validator = Draft202012Validator(
                        operator_session_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=operator_session_validator,
                )
            elif record_type == "production_batch":
                if production_batch_validator is None:
                    production_batch_schema = load_schema(
                        repo_root / "schemas" / "production_batch.schema.json"
                    )
                    production_batch_validator = Draft202012Validator(
                        production_batch_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=production_batch_validator,
                )
            elif record_type == "agent_handoff":
                if agent_handoff_validator is None:
                    agent_handoff_schema = load_schema(
                        repo_root / "schemas" / "agent_handoff.schema.json"
                    )
                    agent_handoff_validator = Draft202012Validator(
                        agent_handoff_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=agent_handoff_validator,
                )
                file_issues.extend(validate_agent_handoff_consistency(path, repo_root))
            elif record_type == "local_media_index":
                if local_media_index_validator is None:
                    local_media_index_schema = load_schema(
                        repo_root / "schemas" / "local_media_index.schema.json"
                    )
                    local_media_index_validator = Draft202012Validator(
                        local_media_index_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=local_media_index_validator,
                )
                file_issues.extend(validate_local_media_index_extra(path, repo_root))
            elif record_type == "video_take":
                if video_take_validator is None:
                    video_take_schema = load_schema(
                        repo_root / "schemas" / "video_take.schema.json"
                    )
                    video_take_validator = Draft202012Validator(video_take_schema)
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=video_take_validator,
                )
                file_issues.extend(validate_video_take_consistency(path, repo_root))
            elif record_type == "video_review":
                if video_review_validator is None:
                    video_review_schema = load_schema(
                        repo_root / "schemas" / "video_review.schema.json"
                    )
                    video_review_validator = Draft202012Validator(video_review_schema)
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=video_review_validator,
                )
            elif record_type == "selected_take":
                if selected_take_validator is None:
                    selected_take_schema = load_schema(
                        repo_root / "schemas" / "selected_take.schema.json"
                    )
                    selected_take_validator = Draft202012Validator(selected_take_schema)
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=selected_take_validator,
                )
                file_issues.extend(validate_selected_take_extra(path, repo_root))
            elif record_type == "omni_set_gate":
                if omni_set_gate_validator is None:
                    omni_set_gate_schema = load_schema(
                        repo_root / "schemas" / "omni_set_gate.schema.json"
                    )
                    omni_set_gate_validator = Draft202012Validator(
                        omni_set_gate_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=omni_set_gate_validator,
                )
            elif record_type == "pack_lock_readiness":
                if pack_lock_readiness_validator is None:
                    pack_lock_readiness_schema = load_schema(
                        repo_root / "schemas" / "pack_lock_readiness.schema.json"
                    )
                    pack_lock_readiness_validator = Draft202012Validator(
                        pack_lock_readiness_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=pack_lock_readiness_validator,
                )
            elif record_type == "canonical_asset_work_order":
                if canonical_asset_work_order_validator is None:
                    canonical_asset_work_order_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "canonical_asset_work_order.schema.json"
                    )
                    canonical_asset_work_order_validator = Draft202012Validator(
                        canonical_asset_work_order_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=canonical_asset_work_order_validator,
                )
            elif record_type == "canonical_asset_intake_scaffold":
                if canonical_asset_intake_scaffold_validator is None:
                    canonical_asset_intake_scaffold_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "canonical_asset_intake_scaffold.schema.json"
                    )
                    canonical_asset_intake_scaffold_validator = Draft202012Validator(
                        canonical_asset_intake_scaffold_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=canonical_asset_intake_scaffold_validator,
                )
            elif record_type == "canonical_asset_intake_instruction":
                if canonical_asset_intake_instruction_validator is None:
                    canonical_asset_intake_instruction_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "canonical_asset_intake_instruction.schema.json"
                    )
                    canonical_asset_intake_instruction_validator = Draft202012Validator(
                        canonical_asset_intake_instruction_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=canonical_asset_intake_instruction_validator,
                )
            elif record_type == "canonical_asset_intake_slot":
                if canonical_asset_intake_slot_validator is None:
                    canonical_asset_intake_slot_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "canonical_asset_intake_slot.schema.json"
                    )
                    canonical_asset_intake_slot_validator = Draft202012Validator(
                        canonical_asset_intake_slot_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=canonical_asset_intake_slot_validator,
                )
            elif record_type == "clean_start_audit":
                if clean_start_audit_validator is None:
                    clean_start_audit_schema = load_schema(
                        repo_root / "schemas" / "clean_start_audit.schema.json"
                    )
                    clean_start_audit_validator = Draft202012Validator(
                        clean_start_audit_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=clean_start_audit_validator,
                )
            elif record_type == "pre_b8a_clean_reset":
                if pre_b8a_clean_reset_validator is None:
                    pre_b8a_clean_reset_schema = load_schema(
                        repo_root / "schemas" / "pre_b8a_clean_reset.schema.json"
                    )
                    pre_b8a_clean_reset_validator = Draft202012Validator(
                        pre_b8a_clean_reset_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=pre_b8a_clean_reset_validator,
                )
            elif record_type == "omni_qc_report":
                if omni_qc_report_validator is None:
                    omni_qc_report_schema = load_schema(
                        repo_root / "schemas" / "omni_qc_report.schema.json"
                    )
                    omni_qc_report_validator = Draft202012Validator(
                        omni_qc_report_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=omni_qc_report_validator,
                )
            elif record_type == "perspective_qc_report":
                if perspective_qc_report_validator is None:
                    perspective_qc_report_schema = load_schema(
                        repo_root / "schemas" / "perspective_qc_report.schema.json"
                    )
                    perspective_qc_report_validator = Draft202012Validator(
                        perspective_qc_report_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=perspective_qc_report_validator,
                )
            elif record_type == "dialogue_qc_report":
                if dialogue_qc_report_validator is None:
                    dialogue_qc_report_schema = load_schema(
                        repo_root / "schemas" / "dialogue_qc_report.schema.json"
                    )
                    dialogue_qc_report_validator = Draft202012Validator(
                        dialogue_qc_report_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=dialogue_qc_report_validator,
                )
            elif record_type == "review_decision_record":
                if review_decision_record_validator is None:
                    review_decision_record_schema = load_schema(
                        repo_root / "schemas" / "review_decision_record.schema.json"
                    )
                    review_decision_record_validator = Draft202012Validator(
                        review_decision_record_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=review_decision_record_validator,
                )
            elif record_type == "gpt_images_perspective_pack":
                if gpt_images_perspective_pack_validator is None:
                    gpt_images_perspective_pack_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "gpt_images_perspective_pack.schema.json"
                    )
                    gpt_images_perspective_pack_validator = Draft202012Validator(
                        gpt_images_perspective_pack_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=gpt_images_perspective_pack_validator,
                )
            elif record_type == "kling_element_reference_record":
                if kling_element_reference_validator is None:
                    kling_element_reference_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "kling_element_reference_record.schema.json"
                    )
                    kling_element_reference_validator = Draft202012Validator(
                        kling_element_reference_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=kling_element_reference_validator,
                )
            elif record_type == "kling_character_look_element":
                if kling_character_look_element_validator is None:
                    kling_character_look_element_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "kling_character_look_element.schema.json"
                    )
                    kling_character_look_element_validator = Draft202012Validator(
                        kling_character_look_element_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=kling_character_look_element_validator,
                )
            elif record_type == "kling_shot_prompt_record":
                if kling_shot_prompt_record_validator is None:
                    kling_shot_prompt_record_schema = load_schema(
                        repo_root / "schemas" / "kling_shot_prompt_record.schema.json"
                    )
                    kling_shot_prompt_record_validator = Draft202012Validator(
                        kling_shot_prompt_record_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=kling_shot_prompt_record_validator,
                )
            elif record_type == "dialogue_extract_record":
                if dialogue_extract_record_validator is None:
                    dialogue_extract_record_schema = load_schema(
                        repo_root / "schemas" / "dialogue_extract_record.schema.json"
                    )
                    dialogue_extract_record_validator = Draft202012Validator(
                        dialogue_extract_record_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=dialogue_extract_record_validator,
                )
            elif record_type == "performance_intent_record":
                if performance_intent_record_validator is None:
                    performance_intent_record_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "performance_intent_record.schema.json"
                    )
                    performance_intent_record_validator = Draft202012Validator(
                        performance_intent_record_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=performance_intent_record_validator,
                )
            elif record_type == "voice_binding_record":
                if voice_binding_record_validator is None:
                    voice_binding_record_schema = load_schema(
                        repo_root / "schemas" / "voice_binding_record.schema.json"
                    )
                    voice_binding_record_validator = Draft202012Validator(
                        voice_binding_record_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=voice_binding_record_validator,
                )
            elif record_type == "native_audio_compatibility_record":
                if native_audio_compatibility_record_validator is None:
                    native_audio_compatibility_record_schema = load_schema(
                        repo_root
                        / "schemas"
                        / "native_audio_compatibility_record.schema.json"
                    )
                    native_audio_compatibility_record_validator = Draft202012Validator(
                        native_audio_compatibility_record_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=native_audio_compatibility_record_validator,
                )
            elif record_type == "character_identity_anchor":
                if character_identity_anchor_validator is None:
                    character_identity_anchor_schema = load_schema(
                        repo_root / "schemas" / "character_identity_anchor.schema.json"
                    )
                    character_identity_anchor_validator = Draft202012Validator(
                        character_identity_anchor_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=character_identity_anchor_validator,
                )
            elif record_type == "character_look_variant":
                if character_look_variant_validator is None:
                    character_look_variant_schema = load_schema(
                        repo_root / "schemas" / "character_look_variant.schema.json"
                    )
                    character_look_variant_validator = Draft202012Validator(
                        character_look_variant_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=character_look_variant_validator,
                )
            elif record_type == "scene_character_look_map":
                if scene_character_look_map_validator is None:
                    scene_character_look_map_schema = load_schema(
                        repo_root / "schemas" / "scene_character_look_map.schema.json"
                    )
                    scene_character_look_map_validator = Draft202012Validator(
                        scene_character_look_map_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=scene_character_look_map_validator,
                )
            elif record_type == "aesthetic_bible":
                if aesthetic_bible_validator is None:
                    aesthetic_bible_schema = load_schema(
                        repo_root / "schemas" / "aesthetic_bible.schema.json"
                    )
                    aesthetic_bible_validator = Draft202012Validator(
                        aesthetic_bible_schema
                    )
                file_issues = _schema_issues(
                    path=path,
                    repo_root=repo_root,
                    record_type=record_type,
                    validator=aesthetic_bible_validator,
                )
            elif record_type == "scene_clip_map":
                file_issues = validate_scene_clip_map_file(path, repo_root)
            else:
                file_issues = [
                    ProductionValidationIssue(
                        file=_relative(path, repo_root),
                        record_type=record_type,
                        field_path="",
                        message=f"Unsupported record type: {record_type}",
                    )
                ]

            if file_issues:
                invalid_files.add(_relative(path, repo_root))
                all_issues.extend(file_issues)

    cross_record_issues = validate_prod_line_cross_references(
        repo_root=repo_root,
        grouped_files=grouped_files,
    )
    if cross_record_issues:
        all_issues.extend(cross_record_issues)
        invalid_files.update(issue.file for issue in cross_record_issues)

    model_guidance_issues = validate_production_batch_model_guidance_gate(
        repo_root=repo_root,
        grouped_files=grouped_files,
    )
    if model_guidance_issues:
        all_issues.extend(model_guidance_issues)
        invalid_files.update(issue.file for issue in model_guidance_issues)

    qc_readiness_issues = validate_qc_cross_record_gates(
        repo_root=repo_root,
        grouped_files=grouped_files,
    )
    if qc_readiness_issues:
        all_issues.extend(qc_readiness_issues)
        invalid_files.update(issue.file for issue in qc_readiness_issues)

    gptimg2_registration_issues = validate_gptimg2_registration_gates(
        repo_root=repo_root,
        grouped_files=grouped_files,
    )
    if gptimg2_registration_issues:
        all_issues.extend(gptimg2_registration_issues)
        invalid_files.update(issue.file for issue in gptimg2_registration_issues)

    review_decision_issues = validate_review_decision_records(
        repo_root=repo_root,
        grouped_files=grouped_files,
    )
    if review_decision_issues:
        all_issues.extend(review_decision_issues)
        invalid_files.update(issue.file for issue in review_decision_issues)

    character_continuity_issues = validate_character_continuity_records(
        repo_root=repo_root,
    )
    if character_continuity_issues:
        all_issues.extend(character_continuity_issues)
        invalid_files.update(issue.file for issue in character_continuity_issues)

    report = ProductionValidationReport(
        total_files=total,
        valid_files=total - len(invalid_files),
        invalid_files=len(invalid_files),
        by_record_type=by_record_type,
        issues=all_issues,
    )

    if report_json is not None:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_data = {
            "total_files": report.total_files,
            "valid_files": report.valid_files,
            "invalid_files": report.invalid_files,
            "by_record_type": report.by_record_type,
            "issues": [asdict(i) for i in report.issues],
        }
        with report_json.open("w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

    return report


def print_report(report: ProductionValidationReport) -> None:
    if report.total_files == 0:
        print("0 files validated - no production metadata YAML files found.")
        return

    print(f"Production record validation: {report.total_files} files scanned.")
    print(f"  Valid:   {report.valid_files}")
    print(f"  Invalid: {report.invalid_files}")
    print("  By type:")
    for record_type, count in sorted(report.by_record_type.items()):
        print(f"    {record_type}: {count}")

    if report.issues:
        print()
        print("Validation errors:")
        for issue in report.issues:
            print(
                f"  [{issue.file}] {issue.record_type} "
                f"{issue.field_path}: {issue.message}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate production metadata YAML/CSV records."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Path to repository root (default: current directory).",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Path to write JSON validation report (optional).",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    report_json = args.report_json.resolve() if args.report_json else None

    report = run_validation(repo_root=repo_root, report_json=report_json)
    print_report(report)

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
