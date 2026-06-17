"""
Tests for A6.6 Model Guidance Research Refresh Operator.

Covers:
- All known targets have research profiles
- Each profile has at least one Tier 1 source
- Each profile has fields_to_verify non-empty
- generate_research_checklist produces useful output for a failing target
- generate_snapshot_scaffold produces a valid scaffold structure
- Scaffold has human_verified: false and TODO_ placeholders
- Scaffold sources come from the model profile
- generate_refresh_report: all pass → no scaffolds
- generate_refresh_report: failing target → checklist + scaffold
- CLI exit 0 when gate passes, exit 1 when gate fails
- Scaffold write: --write-scaffolds creates YAML files for failing targets
- No web calls or external model calls in any code path
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts.operators.model_guidance_refresh_operator import (
    KNOWN_TARGETS,
    RESEARCH_PROFILES,
    generate_research_checklist,
    generate_refresh_report,
    generate_snapshot_scaffold,
    main as operator_main,
)

REPO_ROOT = Path(__file__).parent.parent
REFERENCE_TIME = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
FUTURE = "2099-12-31T23:59:59Z"
PAST = (REFERENCE_TIME - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Profile registry integrity
# ---------------------------------------------------------------------------


def test_all_known_targets_have_profiles():
    """Every entry in KNOWN_TARGETS must have a research profile."""
    for target in KNOWN_TARGETS:
        assert target in RESEARCH_PROFILES, f"Missing profile for {target}"


def test_each_profile_has_tier1_source():
    """Every research profile must have at least one Tier 1 official source."""
    for target, profile in RESEARCH_PROFILES.items():
        tier1 = [s for s in profile.known_sources if s.tier == 1]
        assert tier1, f"Profile {target!r} has no Tier 1 official sources"


def test_each_profile_has_fields_to_verify():
    """Every research profile must list fields to verify."""
    for target, profile in RESEARCH_PROFILES.items():
        assert profile.fields_to_verify, f"Profile {target!r} has empty fields_to_verify"


def test_tier1_sources_have_valid_source_types():
    """Tier 1 sources must use official source types."""
    official_types = {"official_docs", "official_release_notes", "official_help_center"}
    for target, profile in RESEARCH_PROFILES.items():
        for src in profile.known_sources:
            if src.tier == 1:
                assert src.source_type in official_types, (
                    f"Profile {target!r}, source {src.url!r}: "
                    f"Tier 1 source has non-official source_type {src.source_type!r}"
                )


def test_community_notes_not_in_source_list():
    """Community notes must be separate from known_sources (low-confidence, not Tier 1/2)."""
    for target, profile in RESEARCH_PROFILES.items():
        # community_notes must be strings, not ResearchSource objects
        for note in profile.community_notes:
            assert isinstance(note, str), f"Profile {target!r}: community_note must be str, got {type(note)}"


def test_profiles_cover_all_four_standard_targets():
    """All four standard model targets must be in profiles."""
    required = {
        "kling_omni_video_best_available",
        "midjourney_image_best_available",
        "chatgpt_image_best_available",
        "nano_banana_best_available",
    }
    assert required <= set(RESEARCH_PROFILES.keys())


# ---------------------------------------------------------------------------
# generate_research_checklist
# ---------------------------------------------------------------------------


def test_checklist_includes_hard_errors():
    """Checklist must display hard errors from gate result."""
    checklist = generate_research_checklist(
        "kling_omni_video_best_available",
        hard_errors=["Snapshot expired at 2026-05-09T00:00:00Z"],
        soft_warnings=[],
    )
    assert "expired" in checklist.lower()
    assert "Gate Failures" in checklist


def test_checklist_includes_soft_warnings():
    """Checklist must display soft warnings."""
    checklist = generate_research_checklist(
        "kling_omni_video_best_available",
        hard_errors=[],
        soft_warnings=["constraints dict is empty"],
    )
    assert "constraint" in checklist.lower()
    assert "Soft Warnings" in checklist


def test_checklist_includes_tier1_sources():
    """Checklist must list Tier 1 official sources."""
    checklist = generate_research_checklist(
        "kling_omni_video_best_available",
        hard_errors=["Snapshot missing"],
        soft_warnings=[],
    )
    assert "Tier 1" in checklist
    assert "kling.ai" in checklist or "magnific.com" in checklist


def test_checklist_includes_community_notes_as_low_confidence():
    """Checklist must flag community notes as low-confidence."""
    checklist = generate_research_checklist(
        "kling_omni_video_best_available",
        hard_errors=[],
        soft_warnings=[],
    )
    assert "Low Confidence" in checklist or "low-confidence" in checklist.lower()


def test_checklist_for_unknown_target_is_graceful():
    """Unknown target must produce a graceful message, not raise."""
    checklist = generate_research_checklist(
        "unknown_target_xyz",
        hard_errors=["Missing snapshot"],
        soft_warnings=[],
    )
    assert "unknown_target_xyz" in checklist
    assert "no research profile" in checklist.lower()


# ---------------------------------------------------------------------------
# generate_snapshot_scaffold
# ---------------------------------------------------------------------------


def test_scaffold_has_correct_target():
    """Scaffold internal_model_target must match requested target."""
    scaffold = generate_snapshot_scaffold("kling_omni_video_best_available", REFERENCE_TIME)
    assert scaffold["internal_model_target"] == "kling_omni_video_best_available"


def test_scaffold_human_verified_false():
    """Scaffold must have human_verified: false — operator must set it to true after research."""
    scaffold = generate_snapshot_scaffold("kling_omni_video_best_available", REFERENCE_TIME)
    assert scaffold["human_verified"] is False


def test_scaffold_has_todo_placeholders():
    """Scaffold must have TODO_ placeholders for operator to fill in."""
    scaffold = generate_snapshot_scaffold("kling_omni_video_best_available", REFERENCE_TIME)
    yaml_text = yaml.dump(scaffold)
    assert "TODO_" in yaml_text


def test_scaffold_sources_from_profile():
    """Scaffold sources must use URLs from the research profile."""
    scaffold = generate_snapshot_scaffold("kling_omni_video_best_available", REFERENCE_TIME)
    profile = RESEARCH_PROFILES["kling_omni_video_best_available"]
    profile_urls = {s.url for s in profile.known_sources[:2]}
    scaffold_urls = {s.get("url", "") for s in scaffold.get("sources", [])}
    assert profile_urls & scaffold_urls, "Scaffold sources must include URLs from profile"


def test_scaffold_expires_at_correct_freshness():
    """Scaffold expires_at must be observed_at + model freshness days."""
    scaffold = generate_snapshot_scaffold("kling_omni_video_best_available", REFERENCE_TIME)
    observed = datetime.fromisoformat(scaffold["observed_at"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(scaffold["expires_at"].replace("Z", "+00:00"))
    delta = expires - observed
    assert delta.days == 7  # Kling freshness = 7 days


def test_scaffold_is_yaml_serializable():
    """Scaffold must serialize to YAML without error."""
    scaffold = generate_snapshot_scaffold("midjourney_image_best_available", REFERENCE_TIME)
    yaml_text = yaml.dump(scaffold, allow_unicode=True)
    assert len(yaml_text) > 10


# ---------------------------------------------------------------------------
# generate_refresh_report
# ---------------------------------------------------------------------------


def _write_valid_snapshot(tmp_path: Path, target: str) -> None:
    """Write a valid snapshot for the given target."""
    profile = RESEARCH_PROFILES.get(target)
    subdir = profile.snapshot_subdir if profile else "provider"
    snap_dir = tmp_path / "model_guidance_snapshots" / subdir
    snap_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "record_type": "model_guidance_snapshot",
        "schema_version": "0.x-draft",
        "snapshot_id": f"20260510T120000Z_{target}",
        "internal_model_target": target,
        "provider": profile.provider if profile else "unknown",
        "model_family": "test",
        "provider_surface": profile.provider_surface if profile else "api",
        "observed_at": "2026-05-10T12:00:00Z",
        "expires_at": FUTURE,
        "human_verified": True,
        "current_default_model": "test-model-v1",
        "latest_available_model": "test-model-v1",
        "best_for_this_task": "test-model-v1",
        "version_policy": {
            "hardcode_in_adapter": False,
            "adapter_must_read_snapshot": True,
            "prompt_generation_blocks_if_expired": True,
            "prompt_generation_blocks_if_unverified": True,
        },
        "sources": [{"source_type": "official_docs", "title": "Test", "retrieved_at": "2026-05-10T12:00:00Z", "url": "https://example.com/docs"}],
        "constraints": {"prompt_text_max_chars": 2500},
        "prompting_rules": ["Test rule."],
        "provenance": {"created_by": "test", "created_at": "2026-05-10T12:00:00Z"},
    }
    path = snap_dir / f"20260510T120000Z_{target}.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")


def test_report_all_pass_no_scaffolds(tmp_path):
    """When all targets pass, generate_refresh_report must return no scaffolds."""
    target = "kling_omni_video_best_available"
    _write_valid_snapshot(tmp_path, target)

    report, scaffolds = generate_refresh_report(
        repo_root=tmp_path,
        required_targets=[target],
        reference_time=REFERENCE_TIME,
    )
    assert scaffolds == []
    assert "All targets pass" in report or "✅" in report


def test_report_failing_target_produces_scaffold(tmp_path):
    """Failing target must produce checklist in report and scaffold in output."""
    target = "kling_omni_video_best_available"
    # No snapshot → gate will fail

    report, scaffolds = generate_refresh_report(
        repo_root=tmp_path,
        required_targets=[target],
        reference_time=REFERENCE_TIME,
    )
    assert len(scaffolds) == 1
    assert scaffolds[0]["internal_model_target"] == target
    assert "research checklist" in report.lower() or "gate failures" in report.lower()


def test_report_mixed_results(tmp_path):
    """Mixed pass/fail produces scaffolds only for failing targets."""
    good = "kling_omni_video_best_available"
    bad = "midjourney_image_best_available"
    _write_valid_snapshot(tmp_path, good)
    # bad has no snapshot

    report, scaffolds = generate_refresh_report(
        repo_root=tmp_path,
        required_targets=[good, bad],
        reference_time=REFERENCE_TIME,
    )
    assert len(scaffolds) == 1
    assert scaffolds[0]["internal_model_target"] == bad


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_exit_0_all_pass(tmp_path):
    """CLI must exit 0 when all targets pass (no scaffolds)."""
    target = "kling_omni_video_best_available"
    _write_valid_snapshot(tmp_path, target)

    exit_code = operator_main([
        "--repo-root", str(tmp_path),
        "--targets", target,
    ])
    assert exit_code == 0


def test_cli_exit_1_on_failure(tmp_path):
    """CLI must exit 1 when any target fails."""
    exit_code = operator_main([
        "--repo-root", str(tmp_path),
        "--targets", "kling_omni_video_best_available",
    ])
    assert exit_code == 1


def test_cli_write_scaffolds_creates_file(tmp_path):
    """--write-scaffolds must create a YAML file for failing targets."""
    exit_code = operator_main([
        "--repo-root", str(tmp_path),
        "--targets", "kling_omni_video_best_available",
        "--write-scaffolds",
    ])
    assert exit_code == 1
    scaffolds = list((tmp_path / "model_guidance_snapshots").rglob("*_SCAFFOLD.yaml"))
    assert len(scaffolds) == 1


def test_cli_report_file(tmp_path):
    """--report-file must write markdown report to specified path."""
    target = "kling_omni_video_best_available"
    _write_valid_snapshot(tmp_path, target)
    report_path = tmp_path / "report.md"

    operator_main([
        "--repo-root", str(tmp_path),
        "--targets", target,
        "--report-file", str(report_path),
    ])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Model Guidance Research Refresh Report" in content


# ---------------------------------------------------------------------------
# Real repo integration
# ---------------------------------------------------------------------------


def test_real_repo_all_targets_pass_operator():
    """Real repo snapshots must produce no scaffolds at reference time 2026-05-10."""
    _, scaffolds = generate_refresh_report(
        repo_root=REPO_ROOT,
        required_targets=KNOWN_TARGETS,
        reference_time=REFERENCE_TIME,
    )
    assert scaffolds == [], (
        "Real repo snapshots produced scaffolds (gate failures):\n"
        + "\n".join(s["internal_model_target"] for s in scaffolds)
    )
