from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

import scripts.reports.export_prod_line_pilot_status as pilot_status
from scripts.reports.export_prod_line_pilot_status import build_report, main


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_report_contains_core_chain_ids() -> None:
    report = build_report(repo_root=REPO_ROOT, scene_id="SC0001")
    assert "GPTIMG2_C01_PERSPECTIVE_PACK_V001" in report
    assert "KLING_REF_C01_V001" in report
    assert "DLG_SC0001_V001" in report
    assert "PERF_SC0001_SH001_V001" in report
    assert "VOICE_C01_V001" in report
    assert "NAC_SC0001_SH001_V001" in report
    assert "KLING_SC0001_SH001_V001" in report
    assert "BATCH_SEQ01_PILOT_V001" in report


def test_report_marks_qc_not_ready_and_decisions_draft() -> None:
    report = build_report(repo_root=REPO_ROOT, scene_id="SC0001")
    assert "perspective QC: NOT READY" in report
    assert "dialogue QC: NOT READY" in report
    assert "Omni QC: NOT READY" in report
    assert "DRAFT ONLY, not applied: YES" in report


def test_script_stdout_mode() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--repo-root", str(REPO_ROOT), "--scene-id", "SC0001"])
    assert rc == 0
    out = buf.getvalue()
    assert "# PROD-LINE Pilot Status Report - SC0001" in out


def test_script_output_writes_only_report_file(tmp_path: Path) -> None:
    target_source = REPO_ROOT / "evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml"
    before = target_source.read_text(encoding="utf-8")

    output = tmp_path / "SC0001_PROD_LINE_PILOT_STATUS.md"
    rc = main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--scene-id",
            "SC0001",
            "--output",
            str(output),
        ]
    )
    assert rc == 0
    assert output.exists()
    assert "## Summary" in output.read_text(encoding="utf-8")

    after = target_source.read_text(encoding="utf-8")
    assert before == after


def test_missing_required_file_fails(tmp_path: Path) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    try:
        build_report(repo_root=fake_repo, scene_id="SC0001")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_perspective_failed_scores_still_not_ready(monkeypatch) -> None:
    original_load = pilot_status._load_yaml

    def _patched_load(path: Path):
        data = original_load(path)
        if path.as_posix().endswith("evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml"):
            data["gate"] = {
                "minimum_score": 85,
                "all_four_required": True,
                "can_advance_to_kling_reference": True,
            }
            data["perspective_scores"] = [
                {
                    "prompt_id": "GPTIMG2_C01_P01_FRONT_V001",
                    "perspective": "front_hero",
                    "identity_preservation": 90,
                    "perspective_usefulness": 90,
                    "material_palette_continuity": 90,
                    "production_reference_cleanliness": 90,
                    "hallucination_absence": 90,
                    "total_score": 80,
                    "decision": "revise",
                }
            ]
        return data

    monkeypatch.setattr(pilot_status, "_load_yaml", _patched_load)
    report = build_report(repo_root=REPO_ROOT, scene_id="SC0001")
    assert "perspective QC: NOT READY" in report


def test_dialogue_failed_blocking_check_still_not_ready(monkeypatch) -> None:
    original_load = pilot_status._load_yaml

    def _patched_load(path: Path):
        data = original_load(path)
        if path.as_posix().endswith("evidence/dialogue_qc/DQC_SC0001_SH001_V001.yaml"):
            checks = dict(data.get("checks", {}))
            checks["line_accuracy"] = "fail"
            checks["speaker_identity_correctness"] = "pass"
            data["checks"] = checks
            data["gate"] = {
                "approve_candidate_threshold": 90,
                "revise_threshold_min": 80,
                "can_advance_to_candidate": True,
            }
        return data

    monkeypatch.setattr(pilot_status, "_load_yaml", _patched_load)
    report = build_report(repo_root=REPO_ROOT, scene_id="SC0001")
    assert "dialogue QC: NOT READY" in report


def test_omni_unselected_stays_not_ready_even_if_reviewed(monkeypatch) -> None:
    original_load = pilot_status._load_yaml

    def _patched_load(path: Path):
        data = original_load(path)
        if path.as_posix().endswith("evidence/omni_qc/QC_SC0001_CLIP_SC0001_SH001_PILOT_V001.yaml"):
            data["selected_for_next_pass"] = False
            data["provenance"] = {
                "reviewed_by": "human_operator",
                "reviewed_at": "2026-05-12T00:00:00Z",
            }
        return data

    monkeypatch.setattr(pilot_status, "_load_yaml", _patched_load)
    report = build_report(repo_root=REPO_ROOT, scene_id="SC0001")
    assert "Omni QC: NOT READY" in report
