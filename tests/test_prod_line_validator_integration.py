from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_production_records import collect_production_files, run_validation  # noqa: E402


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_schemas(repo_root: Path) -> None:
    schemas_dir = repo_root / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "image_selection.schema.json",
        "local_media_index.schema.json",
        "asset_clearance.schema.json",
        "storyboard_option.schema.json",
        "shot_list_omni_suggestion.schema.json",
        "batch_job.schema.json",
        "operator_session.schema.json",
        "pre_b8a_clean_reset.schema.json",
        "gpt_images_perspective_pack.schema.json",
        "kling_element_reference_record.schema.json",
        "kling_character_look_element.schema.json",
        "kling_shot_prompt_record.schema.json",
        "dialogue_extract_record.schema.json",
        "performance_intent_record.schema.json",
        "voice_binding_record.schema.json",
        "native_audio_compatibility_record.schema.json",
        "production_batch.schema.json",
        "model_guidance_snapshot.schema.json",
        "perspective_qc_report.schema.json",
        "dialogue_qc_report.schema.json",
        "omni_qc_report.schema.json",
        "review_decision_record.schema.json",
        "character_identity_anchor.schema.json",
        "character_look_variant.schema.json",
        "scene_character_look_map.schema.json",
        "identity_evidence_set.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _valid_gpt_images_perspective_pack() -> dict:
    perspectives = [
        "front_hero",
        "three_quarter_left",
        "three_quarter_right",
        "rear_or_side",
    ]
    prompts = []
    for idx, perspective in enumerate(perspectives, start=1):
        prompts.append(
            {
                "prompt_id": f"SC0001__gpt-pack-{idx:02d}__v01",
                "perspective": perspective,
                "prompt_text": f"Render {perspective} preserving identity anchors.",
                "constraints": ["preserve facial structure", "preserve wardrobe colors"],
                "expected_output": {"asset_type": "still", "aspect_ratio": "1:1"},
            }
        )
    return {
        "schema_version": "0.x-draft",
        "record_type": "gpt_images_perspective_pack",
        "prompt_pack_id": "SC0001_GPTPACK_01",
        "status": "draft",
        "source_reference_id": "MJ_REF_SC0001_C01_HERO",
        "target_model": "gpt_images_2",
        "target_role": "multi_perspective_element_expander",
        "element_id": "C01",
        "element_type": "character",
        "shared_preservation_instruction": "Keep face topology and silhouette consistent.",
        "prompts": prompts,
        "qc_gate": {
            "minimum_score": 85,
            "all_perspectives_required": True,
            "failed_perspective_revision_only": True,
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }


def _valid_gpt_images_perspective_pack_matching_qc() -> dict:
    perspectives = [
        ("GPTIMG2_C01_P01_FRONT_V001", "front_hero"),
        ("GPTIMG2_C01_P02_LEFT_V001", "three_quarter_left"),
        ("GPTIMG2_C01_P03_RIGHT_V001", "three_quarter_right"),
        ("GPTIMG2_C01_P04_REAR_V001", "rear_or_side"),
    ]
    prompts = []
    for prompt_id, perspective in perspectives:
        prompts.append(
            {
                "prompt_id": prompt_id,
                "perspective": perspective,
                "prompt_text": f"Render {perspective} preserving identity anchors.",
                "constraints": ["preserve facial structure", "preserve wardrobe colors"],
                "expected_output": {"asset_type": "still", "aspect_ratio": "1:1"},
            }
        )
    return {
        "schema_version": "0.x-draft",
        "record_type": "gpt_images_perspective_pack",
        "prompt_pack_id": "GPTIMG2_C01_PERSPECTIVE_PACK_V001",
        "status": "draft",
        "source_reference_id": "MJ_REF_SC0001_C01_HERO",
        "target_model": "gpt_images_2",
        "target_role": "multi_perspective_element_expander",
        "element_id": "C01",
        "element_type": "character",
        "shared_preservation_instruction": "Keep face topology and silhouette consistent.",
        "prompts": prompts,
        "qc_gate": {
            "minimum_score": 85,
            "all_perspectives_required": True,
            "failed_perspective_revision_only": True,
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }


def _valid_kling_shot_prompt_record(*, repo_binary_committed: bool = False) -> dict:
    payload = {
        "schema_version": "0.x-draft",
        "record_type": "kling_shot_prompt_record",
        "kling_shot_prompt_id": "KSP_SC0001_01_A_SAFE_V01",
        "status": "draft",
        "scene_id": "SC0001",
        "shot_id": "SHOT_SC0001_01_A",
        "linked_element_refs": ["KER_SC0001_C01_V01"],
        "duration_seconds": 5,
        "aspect_ratio": "16:9",
        "variant_mode": "safe",
        "render_pass": "visual_test",
        "quality_tier": "test_720p",
        "native_audio": False,
        "camera_plan": {
            "framing": "medium",
            "movement": "tracking",
            "lens_feel": "natural",
        },
        "action_timeline": ["enters frame", "stops at sink", "settles"],
        "constraints": ["no identity drift"],
        "materialized_output": {
            "platform": "kling",
            "external_storage_ref": "gdrive://kling/sc0001/shot-a-v01.mp4",
            "platform_job_id": "job_abc123",
            "repo_binary_committed": repo_binary_committed,
        },
    }
    return payload


def _valid_production_batch() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "production_batch",
        "production_batch_id": "PB_SC0001_SEQ01_V01",
        "status": "draft",
        "scope": {"sequence_id": "SEQ01", "scenes": ["SC0001"]},
        "models": ["midjourney_v8_1", "gpt_images_2", "kling_omni_3"],
        "estimated_outputs": {
            "midjourney_images": 4,
            "gpt_images_perspectives": 4,
            "kling_video_takes": 3,
        },
        "retry_policy": {"max_retries_per_prompt": 2, "failure_reason_required": True},
        "cost_tracking": {"enabled": True, "estimated_budget": 25.0, "currency": "USD"},
    }


def _write_model_guidance_snapshot(
    repo_root: Path,
    *,
    target: str,
    provider: str,
    model_family: str,
    provider_surface: str,
    human_verified: bool = True,
    expires_days: int = 7,
) -> None:
    observed_at = datetime(2026, 5, 11, 0, 0, tzinfo=timezone.utc)
    expires_at = observed_at + timedelta(days=expires_days)
    provider_dir = repo_root / "model_guidance_snapshots" / provider
    filename = f"20260511T000000Z_{target}.yaml"
    payload = {
        "record_type": "model_guidance_snapshot",
        "schema_version": "0.x-draft",
        "snapshot_id": f"20260511T000000Z_{target}",
        "internal_model_target": target,
        "provider": provider,
        "model_family": model_family,
        "provider_surface": provider_surface,
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "human_verified": human_verified,
        "current_default_model": "best available",
        "latest_available_model": "best available",
        "best_for_this_task": "best available",
        "feature_required_model": {"base": "best available"},
        "version_policy": {
            "hardcode_in_adapter": False,
            "adapter_must_read_snapshot": True,
            "prompt_generation_blocks_if_expired": True,
            "prompt_generation_blocks_if_unverified": True,
        },
        "sources": [
            {
                "source_type": "official_docs",
                "title": "repo-locked guide reference",
                "retrieved_at": observed_at.isoformat().replace("+00:00", "Z"),
                "url": "https://docs.midjourney.com/hc/en-us/articles/32199405667853-Version",
            }
        ],
        "capabilities": {"output_type": "image"},
        "constraints": {"notes": "test fixture"},
        "prompting_rules": ["Use locked repo guidance only."],
        "provenance": {
            "created_by": "tests",
            "created_at": observed_at.isoformat().replace("+00:00", "Z"),
        },
    }
    _write_yaml(provider_dir / filename, payload)


def _write_required_batch_snapshots(repo_root: Path) -> None:
    _write_model_guidance_snapshot(
        repo_root,
        target="midjourney_image_best_available",
        provider="midjourney",
        model_family="image_generation",
        provider_surface="web_ui",
        expires_days=14,
    )
    _write_model_guidance_snapshot(
        repo_root,
        target="chatgpt_image_best_available",
        provider="openai",
        model_family="image_generation",
        provider_surface="chatgpt_ui",
        expires_days=14,
    )
    _write_model_guidance_snapshot(
        repo_root,
        target="kling_omni_video_best_available",
        provider="kling",
        model_family="video_generation",
        provider_surface="web_ui",
        expires_days=7,
    )


def _valid_kling_element_reference_record() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "kling_element_reference_record",
        "kling_element_reference_id": "KER_SC0001_C01_V01",
        "status": "draft",
        "element_id": "C01",
        "element_type": "character",
        "source_midjourney_reference": {
            "reference_id": "MJ_REF_SC0001_C01_HERO",
            "prompt_id": "SC0001__mj-c01-hero__v01",
        },
        "gpt_images_2_perspectives": {
            "front_hero": "SC0001__gpt-pack-01__v01",
            "three_quarter_left": "SC0001__gpt-pack-02__v01",
            "three_quarter_right": "SC0001__gpt-pack-03__v01",
            "rear_or_side": "SC0001__gpt-pack-04__v01",
        },
        "continuity_anchors": ["face topology", "wardrobe silhouette"],
        "approval_gate": {
            "all_perspectives_score_85_plus": True,
            "operator_approved": False,
            "operator_session_ref": "OP-SC0001-001",
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }


def _valid_dialogue_extract_record() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "dialogue_extract_record",
        "dialogue_extract_id": "DLG_SC0001_01",
        "status": "draft",
        "scene_id": "SC0001",
        "source_screenplay_span": {"start_line": 10, "end_line": 15},
        "speakers": [{"character_id": "C01", "display_name": "Nadia"}],
        "raw_lines": [{"speaker": "Nadia", "text": "I remember this place."}],
        "dialogue_function": "reveal memory trigger",
        "emotional_subtext": "contained anxiety",
        "target_language": "en",
        "language_support_status": "officially_supported",
    }


def _valid_performance_intent_record() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "performance_intent_record",
        "performance_intent_id": "PERF_SC0001_01",
        "status": "draft",
        "scene_id": "SC0001",
        "shot_id": "SHOT_SC0001_01_A",
        "speaker": "Nadia",
        "spoken_line": "I remember this place.",
        "language": "en",
        "delivery": {
            "volume": "low",
            "pace": "measured",
            "tone": "dry",
            "emotional_state": "guarded",
        },
        "subtext": "concealing fear",
        "face_direction": "toward sink",
        "mouth_behavior": "controlled articulation",
    }


def _valid_voice_binding_record(*, binding_status: str = "prebound") -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "voice_binding_record",
        "voice_binding_id": "VOICE_SC0001_C01_V01",
        "status": "review",
        "character_id": "C01",
        "binding_status": binding_status,
        "binding_method": "prompt_described",
        "visual_reference_pack": "KER_SC0001_C01_V01",
        "language": "en",
        "operator_approved": False,
        "asset_clearance_ref": "evidence/asset_clearance/C01_nadia_front_v01.yaml",
    }


def _valid_native_audio_compatibility_record(
    *, compatible: bool = True, status: str = "review"
) -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "native_audio_compatibility_record",
        "native_audio_compatibility_id": "NAC_SC0001_01",
        "status": status,
        "scene_id": "SC0001",
        "shot_id": "SHOT_SC0001_01_A",
        "native_audio": True,
        "uses_video_input": False,
        "uses_image_or_element_refs": True,
        "compatible": compatible,
        "checked_against_snapshot": "model_guidance_snapshots/kling/20260508T140000Z_kling_omni_video_best_available.yaml",
    }


def _valid_identity_evidence_set_record() -> dict:
    return {
        "record_type": "identity_evidence_set",
        "record_id": "C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001",
        "character_id": "C01",
        "target_stage": "GPT_IMAGES_2_FRONT_HERO_LOCK",
        "target_look_id": "C01_LOOK_HOME_MORNING_V001",
        "target_alias": "@C01_HOME_MORNING",
        "upload_count": 3,
        "evidence_slots": [
            {
                "slot_id": "E01_STAGE1_WINNER",
                "source_stage": "STAGE_1_IDENTITY_EXPLORATION",
                "role": "primary_identity_direction",
                "external_ref": "pending_external://C01_STAGE1_IDENTITY_WINNER_HOME_MORNING_V001",
                "included": True,
            },
            {
                "slot_id": "E02_STAGE2A_PORTRAIT",
                "source_stage": "STAGE_2A_IDENTITY_PORTRAIT_PROBE",
                "role": "face_topology_anchor",
                "external_ref": "pending_external://C01_STAGE2A_IDENTITY_PORTRAIT_HOME_MORNING_V001",
                "included": True,
            },
            {
                "slot_id": "E03_STAGE2B_FULL_BODY",
                "source_stage": "STAGE_2B_IDENTITY_FULL_BODY_PROBE",
                "role": "silhouette_body_proportion_anchor",
                "external_ref": "pending_external://C01_STAGE2B_IDENTITY_FULL_BODY_HOME_MORNING_V001",
                "included": True,
            },
            {
                "slot_id": "E04_STAGE2C_EXPRESSION_BAND",
                "source_stage": "STAGE_2C_IDENTITY_EXPRESSION_BAND_PROBE",
                "role": "expression_range_check",
                "external_ref": "pending_external://C01_STAGE2C_IDENTITY_EXPRESSION_BAND_HOME_MORNING_V001",
                "included": False,
                "excluded_reason": "Optional expression-band probe reserved unless identity consistency is confirmed by operator.",
            },
        ],
        "lifecycle": {
            "status": "draft",
            "approved": False,
            "locked": False,
            "canon_lock": False,
            "materialized": False,
        },
        "notes": "Draft scaffold.",
    }


def _valid_perspective_qc_report() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "perspective_qc_report",
        "perspective_qc_id": "PQC_C01_PERSPECTIVE_PACK_V001",
        "status": "draft",
        "scene_id": "SC0001",
        "element_id": "C01",
        "prompt_pack_id": "GPTIMG2_C01_PERSPECTIVE_PACK_V001",
        "operator_session_ref": "OP-PROD-LINE-6-SC0001-PERSPECTIVE-REVIEW",
        "perspective_scores": [
            {
                "prompt_id": "GPTIMG2_C01_P01_FRONT_V001",
                "perspective": "front_hero",
                "identity_preservation": None,
                "perspective_usefulness": None,
                "material_palette_continuity": None,
                "production_reference_cleanliness": None,
                "hallucination_absence": None,
                "total_score": None,
                "decision": "pending",
            },
            {
                "prompt_id": "GPTIMG2_C01_P02_LEFT_V001",
                "perspective": "three_quarter_left",
                "identity_preservation": None,
                "perspective_usefulness": None,
                "material_palette_continuity": None,
                "production_reference_cleanliness": None,
                "hallucination_absence": None,
                "total_score": None,
                "decision": "pending",
            },
            {
                "prompt_id": "GPTIMG2_C01_P03_RIGHT_V001",
                "perspective": "three_quarter_right",
                "identity_preservation": None,
                "perspective_usefulness": None,
                "material_palette_continuity": None,
                "production_reference_cleanliness": None,
                "hallucination_absence": None,
                "total_score": None,
                "decision": "pending",
            },
            {
                "prompt_id": "GPTIMG2_C01_P04_REAR_V001",
                "perspective": "rear_or_side",
                "identity_preservation": None,
                "perspective_usefulness": None,
                "material_palette_continuity": None,
                "production_reference_cleanliness": None,
                "hallucination_absence": None,
                "total_score": None,
                "decision": "pending",
            },
        ],
        "gate": {
            "minimum_score": 85,
            "all_four_required": True,
            "can_advance_to_kling_reference": False,
        },
        "notes": "QC scaffold only; generated images do not exist yet.",
    }


def _valid_gptimg2_registration_image_selection() -> dict:
    ids = [
        "GPTIMG2_C01_P01_FRONT_V001",
        "GPTIMG2_C01_P02_LEFT_V001",
        "GPTIMG2_C01_P03_RIGHT_V001",
        "GPTIMG2_C01_P04_REAR_V001",
    ]
    candidates = []
    for prompt_id in ids:
        candidates.append(
            {
                "asset_id": prompt_id,
                "path": f"pending_external://{prompt_id}",
                "external_storage_ref": f"pending_external://{prompt_id}",
                "repo_binary_committed": False,
                "status": "candidate",
                "reason": "Pending external output registration.",
                "quality_scores": {
                    "identity_consistency": 1,
                    "source_grounding": 1,
                    "style_compliance": 1,
                    "continuity": 1,
                    "production_usability": 1,
                },
                "failure_reason": None,
            }
        )
    return {
        "element_id": "C01",
        "element_type": "character",
        "selection_round": 1,
        "source_prompt_ids": ["SC0001__gptimg2-perspective-pack__v01"],
        "candidate_images": candidates,
        "canonical_images": [],
        "round_status": "in_progress",
        "pack_manifest_sync": "pending",
    }


def _valid_gptimg2_registration_local_media_index() -> dict:
    ids = [
        "GPTIMG2_C01_P01_FRONT_V001",
        "GPTIMG2_C01_P02_LEFT_V001",
        "GPTIMG2_C01_P03_RIGHT_V001",
        "GPTIMG2_C01_P04_REAR_V001",
    ]
    entries = []
    for prompt_id in ids:
        entries.append(
            {
                "kind": "gpt_images_2_perspective_output",
                "element_id_or_take_id": prompt_id,
                "storage_backend": "local_manual",
                "last_seen_at": "2026-05-12T00:00:00Z",
                "repo_binary_committed": False,
                "external_storage_ref": f"pending_external://{prompt_id}",
            }
        )
    return {
        "scene_id": "_elements",
        "created_at": "2026-05-12T00:00:00Z",
        "storage_policy": "external_image_only",
        "entries": entries,
    }


def _valid_dialogue_qc_report() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "dialogue_qc_report",
        "dialogue_qc_id": "DQC_SC0001_SH001_V001",
        "status": "draft",
        "scene_id": "SC0001",
        "shot_id": "SH001",
        "linked_dialogue_extract": "DLG_SC0001_V001",
        "linked_performance_intent": "PERF_SC0001_SH001_V001",
        "linked_voice_binding": "VOICE_C01_V001",
        "linked_native_audio_compatibility": "NAC_SC0001_SH001_V001",
        "operator_session_ref": "OP-PROD-LINE-6-SC0001-DIALOGUE-REVIEW",
        "checks": {
            "speaker_identity_correctness": "pending",
            "line_accuracy": "pending",
            "lip_sync_stability": "pending",
            "performance_tone_match": "pending",
            "unwanted_speech_or_subtitles": "pending",
            "voice_binding_respected": "pending",
            "language_accent_followed": "pending",
            "unsupported_input_mode_combination": "pending",
        },
        "gate": {
            "approve_candidate_threshold": 90,
            "revise_threshold_min": 80,
            "can_advance_to_candidate": False,
        },
        "notes": "QC scaffold only; no generated video/audio take exists yet.",
    }


def _valid_omni_qc_placeholder() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "omni_qc_report",
        "scene_id": "SC0001",
        "clip_id": "CLIP_SC0001_SH001_PILOT_V001",
        "prompt_id": "SC0001__kling-shot-pilot__v01",
        "variant_mode": "safe",
        "render_pass": "performance_test",
        "checks": {
            "identity_consistency": "warn",
            "location_continuity": "warn",
            "camera_stability": "warn",
            "motion_artifacts": "warn",
            "hand_face_artifacts": "warn",
            "audio_sync": "not_applicable",
            "unwanted_speech": "not_applicable",
            "narrative_beat": "warn",
        },
        "failure_risks": ["lip_sync_drift", "identity_drift", "unwanted_speech"],
        "retry_rule": {
            "action": "increase_constraints",
            "note": "Placeholder QC scaffold before external Kling materialization; run actual QC after platform output exists.",
        },
        "selected_for_next_pass": False,
        "provenance": {
            "reviewed_by": "human_operator_pending",
            "reviewed_at": "2026-05-11T00:00:00Z",
        },
    }


def _valid_review_decision_record() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "review_decision_record",
        "review_decision_id": "RD_SC0001_PERSPECTIVE_REVISE_DRAFT",
        "status": "draft",
        "scene_id": "SC0001",
        "target_record_type": "perspective_qc_report",
        "target_record_id": "PQC_C01_PERSPECTIVE_PACK_V001",
        "target_path": "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        "operator_session_ref": "OP-SC0001-20260430",
        "decision": "revise",
        "rationale": "QC is scaffold-only and not score-complete.",
        "required_followup": ["Populate scores after external outputs exist."],
        "applied": False,
        "resulting_status": None,
        "provenance": {
            "created_by": "codex",
            "created_at": "2026-05-12T00:00:00Z",
        },
    }


def _valid_operator_session_record() -> dict:
    return {
        "session_id": "OP-SC0001-20260430",
        "created_at": "2026-04-30T00:00:00Z",
        "scene_id": "SC0001",
        "current_task": "t2i_image_generation",
        "recommended_files": ["prompts/draft/SC0001__t2i-char-c01-midjourney__v01.yaml"],
        "recommended_steps": ["Run external T2I generation manually."],
        "status": "planned",
        "notes": "Metadata-only operator session.",
    }


def test_collect_production_files_includes_prod_line_types(tmp_path: Path) -> None:
    files = collect_production_files(tmp_path)
    for record_type in (
        "gpt_images_perspective_pack",
        "kling_element_reference_record",
        "kling_character_look_element",
        "kling_shot_prompt_record",
        "dialogue_extract_record",
        "performance_intent_record",
        "voice_binding_record",
        "native_audio_compatibility_record",
        "production_batch",
        "perspective_qc_report",
        "dialogue_qc_report",
        "review_decision_record",
        "character_identity_anchor",
        "character_look_variant",
        "scene_character_look_map",
    ):
        assert record_type in files
        assert files[record_type] == []


def test_valid_gpt_images_perspective_pack_validates(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack(),
    )
    report = run_validation(tmp_path)
    assert report.total_files == 1
    assert report.invalid_files == 0
    assert report.by_record_type["gpt_images_perspective_pack"] == 1


def test_kling_shot_prompt_repo_binary_committed_false_enforced(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/kling_shot_prompt_001.yaml",
        _valid_kling_shot_prompt_record(repo_binary_committed=True),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 1
    assert any(
        issue.record_type == "kling_shot_prompt_record"
        and "repo_binary_committed" in issue.field_path
        for issue in report.issues
    )


def test_production_batch_not_double_counted_as_batch_job(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_required_batch_snapshots(tmp_path)
    _write_yaml(
        tmp_path / "evidence/batch_jobs/production_batch_sc0001.yaml",
        _valid_production_batch(),
    )
    report = run_validation(tmp_path)
    assert report.by_record_type["production_batch"] == 1
    assert report.by_record_type["batch_job"] == 0
    assert report.invalid_files == 0


def test_production_batch_record_type_detected_without_filename_prefix(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_required_batch_snapshots(tmp_path)
    _write_yaml(
        tmp_path / "evidence/batch_jobs/PB_SC0001_SEQ01_V01.yaml",
        _valid_production_batch(),
    )
    grouped = collect_production_files(tmp_path)
    assert len(grouped["production_batch"]) == 1
    assert len(grouped["batch_job"]) == 0

    report = run_validation(tmp_path)
    assert report.by_record_type["production_batch"] == 1
    assert report.by_record_type["batch_job"] == 0
    assert report.invalid_files == 0


def test_new_directories_missing_still_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    report = run_validation(tmp_path, report_json=tmp_path / "report.json")
    assert report.total_files == 0
    assert report.invalid_files == 0
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["total_files"] == 0


def test_valid_minimal_prod_line_chain_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_required_batch_snapshots(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/kling_element_reference.yaml",
        {
            **_valid_kling_element_reference_record(),
            "approval_gate": {
                "all_perspectives_score_85_plus": False,
                "operator_approved": False,
                "operator_session_ref": "OP-SC0001-001",
            },
        },
    )
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/kling_shot_prompt_001.yaml",
        _valid_kling_shot_prompt_record(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_missing_kling_element_reference_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    shot = _valid_kling_shot_prompt_record()
    shot["linked_element_refs"] = ["KLING_REF_MISSING"]
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/kling_shot_prompt_001.yaml", shot)
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "kling_shot_prompt_record"
        and i.field_path == "linked_element_refs"
        and "missing linked Kling element reference" in i.message
        for i in report.issues
    )


def test_missing_gpt_images_perspective_prompt_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack(),
    )
    ker = _valid_kling_element_reference_record()
    ker["gpt_images_2_perspectives"]["rear_or_side"] = "SC0001__gpt-pack-99__v01"
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/kling_element_reference.yaml",
        ker,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "kling_element_reference_record"
        and i.field_path == "gpt_images_2_perspectives.rear_or_side"
        and "missing GPT Images 2 perspective prompt" in i.message
        for i in report.issues
    )


def test_native_audio_requires_dialogue_extract_and_performance_intent(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/kling_element_reference.yaml",
        _valid_kling_element_reference_record(),
    )
    shot = _valid_kling_shot_prompt_record()
    shot["native_audio"] = True
    shot["dialogue"] = ["DLG_SC0001_01", "PERF_SC0001_01"]
    shot["speech_constraints"] = ["single speaker only"]
    shot["native_audio_compatibility"] = "NAC_SC0001_01"
    shot["voice_binding"] = "VOICE_SC0001_C01_V01"
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/kling_shot_prompt_001.yaml", shot)
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "kling_shot_prompt_record"
        and i.field_path == "dialogue"
        and "missing dialogue extract/performance intent reference" in i.message
        for i in report.issues
    )


def test_pending_voice_binding_blocks_dialogue_shot(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/kling_element_reference.yaml",
        _valid_kling_element_reference_record(),
    )
    _write_yaml(tmp_path / "planning/dialogue/DLG_SC0001_01.yaml", _valid_dialogue_extract_record())
    _write_yaml(
        tmp_path / "planning/dialogue/PERF_SC0001_01.yaml",
        _valid_performance_intent_record(),
    )
    _write_yaml(
        tmp_path / "planning/dialogue/VOICE_SC0001_C01_V01.yaml",
        _valid_voice_binding_record(binding_status="pending"),
    )
    _write_yaml(
        tmp_path / "evidence/native_audio_compatibility/NAC_SC0001_01.yaml",
        _valid_native_audio_compatibility_record(compatible=True, status="review"),
    )
    shot = _valid_kling_shot_prompt_record()
    shot["native_audio"] = True
    shot["dialogue"] = ["DLG_SC0001_01", "PERF_SC0001_01"]
    shot["speech_constraints"] = ["single speaker only"]
    shot["native_audio_compatibility"] = "NAC_SC0001_01"
    shot["voice_binding"] = "VOICE_SC0001_C01_V01"
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/kling_shot_prompt_001.yaml", shot)
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "kling_shot_prompt_record"
        and i.field_path == "voice_binding"
        and "voice binding is pending and blocks dialogue shot production" in i.message
        for i in report.issues
    )


def test_incompatible_native_audio_must_be_blocked(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/native_audio_compatibility/NAC_SC0001_01.yaml",
        _valid_native_audio_compatibility_record(compatible=False, status="review"),
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "native_audio_compatibility_record"
        and i.field_path == "status"
        and "must use blocked status" in i.message
        for i in report.issues
    )


def test_production_batch_requires_model_guidance_snapshots_passes_when_fresh(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    _write_required_batch_snapshots(tmp_path)
    _write_yaml(
        tmp_path / "evidence/batch_jobs/production_batch_sc0001.yaml",
        _valid_production_batch(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_production_batch_fails_when_required_snapshot_missing(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_model_guidance_snapshot(
        tmp_path,
        target="midjourney_image_best_available",
        provider="midjourney",
        model_family="image_generation",
        provider_surface="web_ui",
    )
    _write_model_guidance_snapshot(
        tmp_path,
        target="chatgpt_image_best_available",
        provider="openai",
        model_family="image_generation",
        provider_surface="chatgpt_ui",
    )
    _write_yaml(
        tmp_path / "evidence/batch_jobs/production_batch_sc0001.yaml",
        _valid_production_batch(),
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "production_batch"
        and i.field_path == "models"
        and "model guidance gate failed for target: kling_omni_video_best_available"
        in i.message
        for i in report.issues
    )


def test_production_batch_fails_when_required_snapshot_expired(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_model_guidance_snapshot(
        tmp_path,
        target="midjourney_image_best_available",
        provider="midjourney",
        model_family="image_generation",
        provider_surface="web_ui",
    )
    _write_model_guidance_snapshot(
        tmp_path,
        target="chatgpt_image_best_available",
        provider="openai",
        model_family="image_generation",
        provider_surface="chatgpt_ui",
    )
    _write_model_guidance_snapshot(
        tmp_path,
        target="kling_omni_video_best_available",
        provider="kling",
        model_family="video_generation",
        provider_surface="web_ui",
        expires_days=-1,
    )
    _write_yaml(
        tmp_path / "evidence/batch_jobs/production_batch_sc0001.yaml",
        _valid_production_batch(),
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "production_batch"
        and i.field_path == "models"
        and "model guidance gate failed for target: kling_omni_video_best_available"
        in i.message
        for i in report.issues
    )


def test_production_batch_fails_when_required_snapshot_unverified(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_model_guidance_snapshot(
        tmp_path,
        target="midjourney_image_best_available",
        provider="midjourney",
        model_family="image_generation",
        provider_surface="web_ui",
    )
    _write_model_guidance_snapshot(
        tmp_path,
        target="chatgpt_image_best_available",
        provider="openai",
        model_family="image_generation",
        provider_surface="chatgpt_ui",
    )
    _write_model_guidance_snapshot(
        tmp_path,
        target="kling_omni_video_best_available",
        provider="kling",
        model_family="video_generation",
        provider_surface="web_ui",
        human_verified=False,
    )
    _write_yaml(
        tmp_path / "evidence/batch_jobs/production_batch_sc0001.yaml",
        _valid_production_batch(),
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "production_batch"
        and i.field_path == "models"
        and "model guidance gate failed for target: kling_omni_video_best_available"
        in i.message
        for i in report.issues
    )


def test_production_batch_does_not_require_nano_banana_when_not_listed(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    _write_required_batch_snapshots(tmp_path)
    batch = _valid_production_batch()
    batch["models"] = ["midjourney_v8_1", "gpt_images_2", "kling_omni_3"]
    _write_yaml(
        tmp_path / "evidence/batch_jobs/production_batch_sc0001.yaml",
        batch,
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_perspective_qc_scaffold_with_null_scores_validates(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0
    assert report.by_record_type["perspective_qc_report"] == 1


def test_dialogue_qc_scaffold_with_pending_checks_validates(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml",
        _valid_dialogue_qc_report(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0
    assert report.by_record_type["dialogue_qc_report"] == 1


def test_omni_qc_placeholder_validates_with_selected_false(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/omni_qc/QC_SC0001_CLIP_SC0001_SH001_PILOT_V001.yaml",
        _valid_omni_qc_placeholder(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0
    assert report.by_record_type["omni_qc_report"] == 1


def test_qc_scaffolds_do_not_require_binary_media_refs(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    _write_yaml(
        tmp_path / "evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml",
        _valid_dialogue_qc_report(),
    )
    _write_yaml(
        tmp_path / "evidence/omni_qc/QC_SC0001_CLIP_SC0001_SH001_PILOT_V001.yaml",
        _valid_omni_qc_placeholder(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_perspective_qc_fails_if_advance_true_with_null_scores(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_perspective_qc_report()
    payload["gate"]["can_advance_to_kling_reference"] = True
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "perspective_qc_report"
        and i.field_path == "gate.can_advance_to_kling_reference"
        and "perspective QC cannot advance before all scores meet threshold" in i.message
        for i in report.issues
    )


def test_perspective_qc_fails_if_total_score_below_threshold(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_perspective_qc_report()
    payload["gate"]["can_advance_to_kling_reference"] = True
    for score in payload["perspective_scores"]:
        score["identity_preservation"] = 90
        score["perspective_usefulness"] = 90
        score["material_palette_continuity"] = 90
        score["production_reference_cleanliness"] = 90
        score["hallucination_absence"] = 90
        score["total_score"] = 90
        score["decision"] = "pass"
    payload["perspective_scores"][0]["total_score"] = 84
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "perspective_qc_report"
        and i.field_path == "gate.can_advance_to_kling_reference"
        and "perspective QC cannot advance before all scores meet threshold" in i.message
        for i in report.issues
    )


def test_kling_element_reference_fails_without_completed_perspective_qc(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    ker = _valid_kling_element_reference_record()
    ker["approval_gate"]["all_perspectives_score_85_plus"] = True
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/kling_element_reference.yaml",
        ker,
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "kling_element_reference_record"
        and i.field_path == "approval_gate.all_perspectives_score_85_plus"
        and "requires completed perspective QC report" in i.message
        for i in report.issues
    )


def test_dialogue_qc_fails_if_advance_true_with_pending_checks(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_dialogue_qc_report()
    payload["gate"]["can_advance_to_candidate"] = True
    _write_yaml(
        tmp_path / "evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "dialogue_qc_report"
        and i.field_path == "gate.can_advance_to_candidate"
        and "dialogue QC cannot advance while checks are pending or failing" in i.message
        for i in report.issues
    )


def test_native_audio_shot_fails_if_advanced_without_completed_dialogue_qc(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(tmp_path / "planning/dialogue/DLG_SC0001_01.yaml", _valid_dialogue_extract_record())
    _write_yaml(tmp_path / "planning/dialogue/PERF_SC0001_01.yaml", _valid_performance_intent_record())
    _write_yaml(
        tmp_path / "planning/dialogue/VOICE_SC0001_C01_V01.yaml",
        _valid_voice_binding_record(binding_status="none"),
    )
    _write_yaml(
        tmp_path / "evidence/native_audio_compatibility/NAC_SC0001_01.yaml",
        _valid_native_audio_compatibility_record(compatible=True, status="review"),
    )
    _write_yaml(
        tmp_path / "evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml",
        _valid_dialogue_qc_report(),
    )
    shot = _valid_kling_shot_prompt_record()
    shot["status"] = "materialized"
    shot["shot_id"] = "SH001"
    shot["native_audio"] = True
    shot["dialogue"] = ["DLG_SC0001_01", "PERF_SC0001_01"]
    shot["speech_constraints"] = ["single speaker only"]
    shot["native_audio_compatibility"] = "NAC_SC0001_01"
    shot["voice_binding"] = "VOICE_SC0001_C01_V01"
    _write_yaml(tmp_path / "visual_dev/omni_sets/SC0001/kling_shot_prompt_001.yaml", shot)
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "kling_shot_prompt_record"
        and i.field_path == "native_audio"
        and "native audio shot cannot advance without completed dialogue QC" in i.message
        for i in report.issues
    )


def test_omni_qc_fails_if_selected_true_with_placeholder_review(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_omni_qc_placeholder()
    payload["selected_for_next_pass"] = True
    _write_yaml(
        tmp_path / "evidence/omni_qc/QC_SC0001_CLIP_SC0001_SH001_PILOT_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "omni_qc_report"
        and i.field_path == "selected_for_next_pass"
        and "selected_for_next_pass requires completed passing Omni QC" in i.message
        for i in report.issues
    )


def test_valid_review_decision_record_validates(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/operator_sessions/OP-SC0001-20260430.yaml",
        _valid_operator_session_record(),
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    _write_yaml(
        tmp_path / "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
        _valid_review_decision_record(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_review_decision_rejects_approve_or_yes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/operator_sessions/OP-SC0001-20260430.yaml",
        _valid_operator_session_record(),
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    payload = _valid_review_decision_record()
    payload["decision"] = "approve"
    _write_yaml(
        tmp_path / "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 1


def test_review_decision_applied_true_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/operator_sessions/OP-SC0001-20260430.yaml",
        _valid_operator_session_record(),
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    payload = _valid_review_decision_record()
    payload["applied"] = True
    _write_yaml(
        tmp_path / "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 1


def test_review_decision_resulting_status_non_null_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/operator_sessions/OP-SC0001-20260430.yaml",
        _valid_operator_session_record(),
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    payload = _valid_review_decision_record()
    payload["resulting_status"] = "draft"
    _write_yaml(
        tmp_path / "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 1


def test_review_decision_missing_operator_session_ref_fails_consistency(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    payload = _valid_review_decision_record()
    payload["operator_session_ref"] = "OP-MISSING-SESSION"
    _write_yaml(
        tmp_path / "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "review_decision_record"
        and i.field_path == "operator_session_ref"
        for i in report.issues
    )


def test_review_decision_invalid_target_path_fails_consistency(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/operator_sessions/OP-SC0001-20260430.yaml",
        _valid_operator_session_record(),
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    payload = _valid_review_decision_record()
    payload["target_path"] = "../outside.yaml"
    _write_yaml(
        tmp_path / "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "review_decision_record"
        and i.field_path == "target_path"
        and "safe repo-relative path" in i.message
        for i in report.issues
    )


def test_review_decision_target_record_mismatch_fails_consistency(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "evidence/operator_sessions/OP-SC0001-20260430.yaml",
        _valid_operator_session_record(),
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    _write_yaml(
        tmp_path / "evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml",
        _valid_dialogue_qc_report(),
    )
    payload = _valid_review_decision_record()
    payload["target_record_type"] = "perspective_qc_report"
    payload["target_record_id"] = "PQC_C01_PERSPECTIVE_PACK_V001"
    payload["target_path"] = "evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml"
    _write_yaml(
        tmp_path / "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "review_decision_record"
        and i.field_path in {"target_record_type", "target_record_id"}
        for i in report.issues
    )


def test_gptimg2_registration_scaffold_passes_with_pending_refs(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack_matching_qc(),
    )
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        _valid_perspective_qc_report(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml",
        _valid_gptimg2_registration_image_selection(),
    )
    _write_yaml(
        tmp_path
        / "evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml",
        _valid_gptimg2_registration_local_media_index(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_perspective_qc_populated_fails_without_image_selection_candidate(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack_matching_qc(),
    )
    _write_yaml(
        tmp_path
        / "evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml",
        _valid_gptimg2_registration_local_media_index(),
    )
    image_selection = _valid_gptimg2_registration_image_selection()
    image_selection["candidate_images"] = image_selection["candidate_images"][1:]
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml",
        image_selection,
    )
    payload = _valid_perspective_qc_report()
    payload["perspective_scores"][0]["identity_preservation"] = 90
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "perspective_qc_report"
        and i.field_path == "perspective_scores"
        and "cannot be populated before GPT Images 2 output registration metadata exists"
        in i.message
        for i in report.issues
    )


def test_perspective_qc_populated_fails_without_local_media_entry(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack_matching_qc(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml",
        _valid_gptimg2_registration_image_selection(),
    )
    media_index = _valid_gptimg2_registration_local_media_index()
    media_index["entries"] = media_index["entries"][1:]
    _write_yaml(
        tmp_path
        / "evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml",
        media_index,
    )
    payload = _valid_perspective_qc_report()
    payload["perspective_scores"][0]["identity_preservation"] = 90
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "perspective_qc_report"
        and i.field_path == "perspective_scores"
        and "cannot be populated before GPT Images 2 output registration metadata exists"
        in i.message
        for i in report.issues
    )


def test_perspective_qc_advance_true_fails_with_pending_external_refs(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
        _valid_gpt_images_perspective_pack_matching_qc(),
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml",
        _valid_gptimg2_registration_image_selection(),
    )
    _write_yaml(
        tmp_path
        / "evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml",
        _valid_gptimg2_registration_local_media_index(),
    )
    payload = _valid_perspective_qc_report()
    payload["gate"]["can_advance_to_kling_reference"] = True
    for score in payload["perspective_scores"]:
        score["identity_preservation"] = 90
        score["perspective_usefulness"] = 90
        score["material_palette_continuity"] = 90
        score["production_reference_cleanliness"] = 90
        score["hallucination_absence"] = 90
        score["total_score"] = 90
        score["decision"] = "pass"
    _write_yaml(
        tmp_path / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "perspective_qc_report"
        and i.field_path == "gate.can_advance_to_kling_reference"
        and "cannot advance while GPT Images 2 external refs are pending" in i.message
        for i in report.issues
    )


def test_gptimg2_image_selection_fails_if_candidate_is_canonical(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_gptimg2_registration_image_selection()
    payload["candidate_images"][0]["status"] = "canonical"
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "image_selection"
        and "must not select or canonicalize candidates" in i.message
        for i in report.issues
    )


def test_gptimg2_image_selection_fails_if_canonical_images_non_empty(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_gptimg2_registration_image_selection()
    payload["canonical_images"] = ["pending_external://GPTIMG2_C01_P01_FRONT_V001"]
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "image_selection"
        and i.field_path == "canonical_images"
        and "must not select or canonicalize candidates" in i.message
        for i in report.issues
    )


def test_gptimg2_local_media_index_fails_if_repo_binary_committed_true(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_gptimg2_registration_local_media_index()
    payload["entries"][0]["repo_binary_committed"] = True
    _write_yaml(
        tmp_path
        / "evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "local_media_index"
        and i.field_path.endswith("repo_binary_committed")
        for i in report.issues
    )


def test_gptimg2_local_media_index_fails_if_local_image_path_without_external_ref(
    tmp_path: Path,
) -> None:
    _copy_schemas(tmp_path)
    payload = _valid_gptimg2_registration_local_media_index()
    payload["entries"][0].pop("external_storage_ref", None)
    payload["entries"][0]["local_path"] = "visual_dev/foo.png"
    _write_yaml(
        tmp_path
        / "evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(
        i.record_type == "local_media_index"
        and i.field_path.endswith("external_storage_ref")
        and "external metadata only" in i.message
        for i in report.issues
    )


def test_new_character_identity_look_records_validate(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/character_identity_anchor.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "character_identity_anchor",
            "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
            "character_id": "C01",
            "status": "draft",
            "source_reference_strategy": {
                "reference_sheet_allowed_as_identity_source": True,
                "final_hero_lock_requires_single_clean_image": True,
                "contact_sheet_layout_forbidden_as_lock": True,
            },
            "source_reference_sheet_ref": "MJ_ELEMENT_C01_HERO_LOCKED_V001",
            "front_hero_lock_ref": {
                "pending": True,
                "external_ref": "pending_external://C01_FRONT_HERO_LOCK_V001",
            },
            "fixed_identity_anchors": ["facial topology"],
            "mutable_appearance_allowed": ["wardrobe variation"],
            "forbidden_drift": ["new face"],
            "provenance": {
                "created_by": "tests",
                "created_at": "2026-05-12T00:00:00Z",
            },
        },
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "character_look_variant",
            "look_id": "C01_LOOK_HOME_MORNING_V001",
            "character_id": "C01",
            "inherits_identity_anchor": "C01_IDENTITY_ANCHOR_V001",
            "status": "draft",
            "look_role": "domestic_morning",
            "wardrobe_refs": {
                "primary_wardrobe_id": "WD001",
                "supplementary_wardrobe_ids": [],
            },
            "continuity_scope": {"start_scene": "SC0001", "end_scene": "SC0003"},
            "change_reason": "opening continuity",
            "provenance": {
                "created_by": "tests",
                "created_at": "2026-05-12T00:00:00Z",
            },
        },
    )
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/scene_character_look_map.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "scene_character_look_map",
            "scene_id": "SC0001",
            "status": "draft",
            "characters": [
                {
                    "character_id": "C01",
                    "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
                    "look_id": "C01_LOOK_HOME_MORNING_V001",
                    "required": True,
                }
            ],
            "provenance": {
                "created_by": "tests",
                "created_at": "2026-05-12T00:00:00Z",
            },
        },
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/wardrobe/WD001/element_view_plan.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "element_view_plan",
            "element_id": "WD001",
            "element_type": "wardrobe",
            "retrofit_status": "planned",
            "views": [
                {
                    "view_id": "main_front",
                    "view_label": "main front",
                    "generation_pattern": "anchor_t2i",
                    "anchor_dependency": "none",
                    "status": "not_started",
                }
            ],
            "provenance": {
                "created_by": "tests",
                "created_at": "2026-05-12T00:00:00Z",
            },
        },
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "kling_character_look_element",
            "kling_character_look_element_id": "KLING_ELEM_C01_HOME_MORNING_V001",
            "character_id": "C01",
            "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
            "look_id": "C01_LOOK_HOME_MORNING_V001",
            "kling_element_alias": "@C01_HOME_MORNING",
            "display_name": "C01 Home Morning",
            "status": "draft",
            "element_role": "character_look_composite",
            "source_reference_chain": {
                "identity_source_ref": "MJ_ELEMENT_C01_HERO_LOCKED_V001",
                "front_hero_lock_ref": "pending_external://C01_FRONT_HERO_LOCK_V001",
                "perspective_pack_id": None,
                "wardrobe_ids": ["WD001"],
            },
            "omni_usage_policy": {
                "use_as_primary_character_element": True,
                "do_not_mix_with_other_same_character_look_aliases_in_same_shot": True,
                "wardrobe_is_baked_into_element": True,
                "separate_wardrobe_element_optional": False,
            },
            "provenance": {
                "created_by": "tests",
                "created_at": "2026-05-12T00:00:00Z",
            },
        },
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def _write_identity_evidence_dependencies(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/look_variants/C01_LOOK_HOME_MORNING_V001.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "character_look_variant",
            "look_id": "C01_LOOK_HOME_MORNING_V001",
            "character_id": "C01",
            "inherits_identity_anchor": "C01_IDENTITY_ANCHOR_V001",
            "status": "draft",
            "look_role": "domestic_morning",
            "wardrobe_refs": {
                "primary_wardrobe_id": "WD001",
                "supplementary_wardrobe_ids": [],
            },
            "continuity_scope": {"start_scene": "SC0001", "end_scene": "SC0003"},
            "change_reason": "opening continuity",
            "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
        },
    )
    _write_yaml(
        tmp_path / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "kling_character_look_element",
            "kling_character_look_element_id": "KLING_ELEM_C01_HOME_MORNING_V001",
            "character_id": "C01",
            "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
            "look_id": "C01_LOOK_HOME_MORNING_V001",
            "kling_element_alias": "@C01_HOME_MORNING",
            "display_name": "C01 Home Morning",
            "status": "draft",
            "element_role": "character_look_composite",
            "source_reference_chain": {
                "identity_source_ref": "MJ_ELEMENT_C01_HERO_LOCKED_V001",
                "front_hero_lock_ref": "pending_external://C01_FRONT_HERO_LOCK_V001",
                "perspective_pack_id": None,
                "wardrobe_ids": ["WD001"],
            },
            "omni_usage_policy": {
                "use_as_primary_character_element": True,
                "do_not_mix_with_other_same_character_look_aliases_in_same_shot": True,
                "wardrobe_is_baked_into_element": True,
                "separate_wardrobe_element_optional": False,
            },
            "provenance": {"created_by": "tests", "created_at": "2026-05-12T00:00:00Z"},
        },
    )


def test_identity_evidence_set_valid_record_passes(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        _valid_identity_evidence_set_record(),
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_identity_evidence_set_upload_count_mismatch_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["upload_count"] = 2
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(i.field_path == "upload_count" for i in report.issues)


def test_identity_evidence_set_duplicate_slot_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["evidence_slots"][1]["slot_id"] = "E01_STAGE1_WINNER"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any("Duplicate slot_id" in i.message for i in report.issues)


def test_identity_evidence_set_missing_e01_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["evidence_slots"][0]["included"] = False
    payload["evidence_slots"][0]["excluded_reason"] = "drop"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any("E01_STAGE1_WINNER must be included" in i.message for i in report.issues)


def test_identity_evidence_set_excluded_reason_rules_failures(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["evidence_slots"][3].pop("excluded_reason")
    payload["evidence_slots"][1]["excluded_reason"] = "should-not-exist"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any("included=false requires non-empty excluded_reason" in i.message for i in report.issues)
    assert any("included=true must not have excluded_reason" in i.message for i in report.issues)


def test_identity_evidence_set_slot_stage_role_mismatch_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["evidence_slots"][1]["source_stage"] = "STAGE_2B_IDENTITY_FULL_BODY_PROBE"
    payload["evidence_slots"][2]["role"] = "face_topology_anchor"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any("slot_id/source_stage mismatch" in i.message for i in report.issues)
    assert any("slot_id/role mismatch" in i.message for i in report.issues)


def test_identity_evidence_set_character_look_prefix_mismatch_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["target_look_id"] = "C02_LOOK_HOME_MORNING_V001"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any(i.field_path == "target_look_id" for i in report.issues)


def test_identity_evidence_set_lifecycle_promotion_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["lifecycle"]["approved"] = True
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any("Lifecycle promotion is forbidden" in i.message for i in report.issues)


def test_identity_evidence_set_local_path_external_ref_fails(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["evidence_slots"][0]["external_ref"] = "C:\\Users\\test\\image.png"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert any("local absolute path" in i.message for i in report.issues)


def test_identity_evidence_set_pending_external_allowed(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    for slot in payload["evidence_slots"]:
        slot["external_ref"] = "pending_external://placeholder"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0


def test_identity_evidence_set_hosted_media_url_allowed(tmp_path: Path) -> None:
    _copy_schemas(tmp_path)
    _write_identity_evidence_dependencies(tmp_path)
    payload = _valid_identity_evidence_set_record()
    payload["evidence_slots"][0]["external_ref"] = "https://storage.example/C01.png"
    payload["evidence_slots"][1]["external_ref"] = "https://storage.example/C01-left.jpg"
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml",
        payload,
    )
    report = run_validation(tmp_path)
    assert report.invalid_files == 0
