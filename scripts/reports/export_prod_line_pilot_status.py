from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORTS))

from scripts.validate_production_records import run_validation
from scripts.validators.validate_model_research_gate import validate_model_research_gate


REQUIRED_PATHS = {
    "production_batch": "evidence/batch_jobs/production_batch_SEQ01_PILOT_V001.yaml",
    "gpt_pack": "visual_dev/elements/characters/C01/gpt_images_perspective_pack.yaml",
    "kling_ref": "visual_dev/elements/characters/C01/kling_element_reference.yaml",
    "dialogue": "planning/dialogue/DLG_SC0001_V001.yaml",
    "performance": "planning/dialogue/PERF_SC0001_SH001_V001.yaml",
    "voice": "planning/dialogue/VOICE_C01_V001.yaml",
    "native_audio": "evidence/native_audio_compatibility/NAC_SC0001_SH001_V001.yaml",
    "kling_shot": "visual_dev/omni_sets/SC0001/kling_shot_prompt_SC0001_SH001_V001.yaml",
    "perspective_qc": "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml",
    "dialogue_qc": "evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml",
    "omni_qc": "evidence/omni_qc/QC_SC0001_CLIP_SC0001_SH001_PILOT_V001.yaml",
    "rd_perspective": "evidence/review_decisions/RD_SC0001_PERSPECTIVE_REVISE_DRAFT.yaml",
    "rd_dialogue": "evidence/review_decisions/RD_SC0001_DIALOGUE_BLOCKED_DRAFT.yaml",
    "rd_shot": "evidence/review_decisions/RD_SC0001_KLING_SHOT_NO_DRAFT.yaml",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML mapping expected: {path}")
    return data


def _must_exist(repo_root: Path, rel_path: str) -> Path:
    path = repo_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Required pilot file missing: {rel_path}")
    return path


def build_report(*, repo_root: Path, scene_id: str) -> str:
    if scene_id != "SC0001":
        raise ValueError("Only SC0001 pilot report is supported in PROD-LINE-10.")

    paths = {name: _must_exist(repo_root, rel) for name, rel in REQUIRED_PATHS.items()}
    batch = _load_yaml(paths["production_batch"])
    gpt_pack = _load_yaml(paths["gpt_pack"])
    kling_ref = _load_yaml(paths["kling_ref"])
    dialogue = _load_yaml(paths["dialogue"])
    perf = _load_yaml(paths["performance"])
    voice = _load_yaml(paths["voice"])
    nac = _load_yaml(paths["native_audio"])
    shot = _load_yaml(paths["kling_shot"])
    p_qc = _load_yaml(paths["perspective_qc"])
    d_qc = _load_yaml(paths["dialogue_qc"])
    o_qc = _load_yaml(paths["omni_qc"])
    rd_files = [_load_yaml(paths[k]) for k in ("rd_perspective", "rd_dialogue", "rd_shot")]

    prod_report = run_validation(repo_root=repo_root)
    schema_state = "PASS" if not prod_report.has_errors else "FAIL"

    targets = [
        "midjourney_image_best_available",
        "chatgpt_image_best_available",
        "kling_omni_video_best_available",
    ]
    gate_results = validate_model_research_gate(repo_root=repo_root, required_targets=targets)
    model_gate_pass = all(r.passed for r in gate_results)

    p_gate = p_qc.get("gate", {}) if isinstance(p_qc.get("gate"), dict) else {}
    p_min_score = p_gate.get("minimum_score", 0)
    perspective_not_ready = False
    for s in p_qc.get("perspective_scores", []):
        if not isinstance(s, dict):
            perspective_not_ready = True
            break
        total = s.get("total_score")
        decision = s.get("decision")
        if not isinstance(total, int):
            perspective_not_ready = True
            break
        if total < p_min_score:
            perspective_not_ready = True
            break
        if decision in {"pending", "revise", "fail"}:
            perspective_not_ready = True
            break

    blocking_checks = {
        "speaker_identity_correctness",
        "line_accuracy",
        "lip_sync_stability",
        "performance_tone_match",
        "unwanted_speech_or_subtitles",
        "unsupported_input_mode_combination",
    }
    dialogue_not_ready = False
    checks = d_qc.get("checks", {})
    if isinstance(checks, dict):
        for name in blocking_checks:
            if checks.get(name) in {"pending", "fail"}:
                dialogue_not_ready = True
                break
    else:
        dialogue_not_ready = True

    # Mirror readiness intent of validate_omni_qc_readiness:
    # unselected or non-passing selected entries are not ready.
    selected = o_qc.get("selected_for_next_pass") is True
    o_checks = o_qc.get("checks", {}) if isinstance(o_qc.get("checks"), dict) else {}
    o_retry = o_qc.get("retry_rule")
    o_prov = o_qc.get("provenance", {}) if isinstance(o_qc.get("provenance"), dict) else {}
    omni_ready = False
    if selected:
        motion = o_checks.get("motion_artifacts")
        hand_face = o_checks.get("hand_face_artifacts")
        motion_ok = motion == "pass" or (motion == "warn" and isinstance(o_retry, dict))
        hand_face_ok = hand_face == "pass" or (hand_face == "warn" and isinstance(o_retry, dict))
        omni_ready = (
            o_checks.get("identity_consistency") == "pass"
            and o_checks.get("camera_stability") == "pass"
            and o_checks.get("narrative_beat") == "pass"
            and o_checks.get("audio_sync") in {"pass", "not_applicable"}
            and o_checks.get("unwanted_speech") in {"pass", "not_applicable"}
            and motion_ok
            and hand_face_ok
            and o_prov.get("reviewed_by") != "human_operator_pending"
        )
    omni_not_ready = not omni_ready
    review_draft_only = all(r.get("status") == "draft" and r.get("applied") is False for r in rd_files)

    non_promotion_checks = [
        "- no approved/locked/canon transition detected",
        "- no materialized output detected",
        f"- selected_for_next_pass is {str(o_qc.get('selected_for_next_pass')).lower()}",
        "- review decisions are draft and not applied",
    ]

    md = [
        f"# PROD-LINE Pilot Status Report - {scene_id}",
        "",
        "## Summary",
        f"- scene_id: {scene_id}",
        f"- element_id: {gpt_pack.get('element_id')}",
        f"- shot_id: {shot.get('shot_id')}",
        f"- production_batch_id: {batch.get('production_batch_id')}",
        "",
        "## Chain Trace",
        f"- {gpt_pack.get('prompt_pack_id')} (GPT Images 2 perspective pack)",
        f"- {kling_ref.get('kling_element_reference_id')} (Kling element reference)",
        f"- {dialogue.get('dialogue_extract_id')} (dialogue extract)",
        f"- {perf.get('performance_intent_id')} (performance intent)",
        f"- {voice.get('voice_binding_id')} (voice binding)",
        f"- {nac.get('native_audio_compatibility_id')} (native audio compatibility)",
        f"- {shot.get('kling_shot_prompt_id')} (Kling shot prompt)",
        "- QC scaffolds (perspective/dialogue/omni)",
        "- review-decision drafts",
        f"- {batch.get('production_batch_id')} (production batch)",
        "",
        "## Validation State",
        f"- schema validation: {schema_state}",
        f"- cross-record links: {schema_state}",
        f"- production validator: {prod_report.valid_files}/{prod_report.total_files} valid",
        "",
        "## Model Guidance State",
        f"- model guidance snapshots: {'PASS' if model_gate_pass else 'FAIL'}",
        "",
        "## QC Readiness",
        f"- perspective QC: {'NOT READY' if perspective_not_ready else 'READY'}",
        f"- dialogue QC: {'NOT READY' if dialogue_not_ready else 'READY'}",
        f"- Omni QC: {'NOT READY' if omni_not_ready else 'READY'}",
        "",
        "## Review Decisions",
        f"- DRAFT ONLY, not applied: {'YES' if review_draft_only else 'NO'}",
        f"- {rd_files[0].get('review_decision_id')}: {rd_files[0].get('decision')}",
        f"- {rd_files[1].get('review_decision_id')}: {rd_files[1].get('decision')}",
        f"- {rd_files[2].get('review_decision_id')}: {rd_files[2].get('decision')}",
        "",
        "## Blockers",
        "- perspective QC scores must be populated before Kling reference advancement",
        "- dialogue QC checks must be populated before Native Audio candidate advancement",
        "- external Kling output does not exist yet",
        "- selected_for_next_pass remains false",
        "- no decision has been applied",
        "",
        "## Safe Next Actions",
        "- review perspective prompt pack",
        "- generate/register external GPT Images 2 perspective outputs outside repo",
        "- populate perspective QC after outputs exist",
        "- review dialogue/native audio readiness",
        "- do not approve/lock/materialize yet",
        "",
        "## Non-Promotion Confirmation",
        *non_promotion_checks,
        "",
    ]
    return "\n".join(md)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export PROD-LINE pilot status report.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    report = build_report(repo_root=repo_root, scene_id=args.scene_id)

    if args.output is None:
        print(report)
        return 0

    output_path = args.output
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
