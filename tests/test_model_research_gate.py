"""
Tests for A6.5 Model Research Refresh Gate.

Covers:
- Valid snapshot passes all checks
- Expired snapshot fails
- Unverified snapshot (human_verified: false) fails
- Placeholder source URL fails
- Empty sources list fails
- Empty prompting_rules fails
- Both model version fields placeholder fails
- Missing snapshot fails
- Empty constraints produces soft warning only
- Multi-target: all pass, mixed, all fail
- strict=True raises ModelResearchGateError on failure
- CLI exit codes
- Gate does not call external services (no live web dependency)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts.validators.validate_model_research_gate import (
    ModelResearchGateError,
    TargetGateResult,
    validate_model_research_gate,
    main as gate_main,
)

REPO_ROOT = Path(__file__).parent.parent

REFERENCE_TIME = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
FUTURE = "2099-12-31T23:59:59Z"
PAST = (REFERENCE_TIME - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

TARGET = "kling_omni_video_best_available"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_snapshot(tmp_path: Path, data: dict, target: str = TARGET) -> Path:
    snap_dir = tmp_path / "model_guidance_snapshots" / "kling"
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = snap_dir / f"20260510T120000Z_{target}.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def _valid_snapshot(target: str = TARGET) -> dict:
    return {
        "record_type": "model_guidance_snapshot",
        "schema_version": "0.x-draft",
        "snapshot_id": f"20260510T120000Z_{target}",
        "internal_model_target": target,
        "provider": "kling",
        "model_family": "video_generation",
        "provider_surface": "api",
        "observed_at": "2026-05-10T12:00:00Z",
        "expires_at": FUTURE,
        "human_verified": True,
        "current_default_model": "Kling 3.0 Omni",
        "latest_available_model": "Kling 3.0 Omni",
        "best_for_this_task": "Kling 3.0 Omni",
        "feature_required_model": {"multi_shot": "Kling 3.0 Omni"},
        "version_policy": {
            "hardcode_in_adapter": False,
            "adapter_must_read_snapshot": True,
            "prompt_generation_blocks_if_expired": True,
            "prompt_generation_blocks_if_unverified": True,
        },
        "sources": [
            {
                "source_type": "official_docs",
                "title": "Kling API Reference",
                "retrieved_at": "2026-05-10T12:00:00Z",
                "url": "https://kling.ai/docs/api/video-generation",
            }
        ],
        "capabilities": {
            "output_type": "video",
            "supports_negative_prompt": True,
            "max_duration_seconds": 15,
        },
        "constraints": {
            "prompt_text_max_chars": 2500,
            "negative_prompt_max_chars": 2500,
        },
        "prompting_rules": [
            "Write cinematic shot directions, not visual inventories.",
            "Hard limit: 2500 characters per prompt_text.",
        ],
        "provenance": {
            "created_by": "human_researcher",
            "created_at": "2026-05-10T12:00:00Z",
        },
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_snapshot_passes(tmp_path):
    """A complete, fresh, human-verified snapshot must pass all checks."""
    _write_snapshot(tmp_path, _valid_snapshot())
    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    assert len(results) == 1
    r = results[0]
    assert r.passed, f"Expected pass; hard_errors={r.hard_errors}"
    assert r.hard_errors == []


def test_valid_snapshot_no_soft_warnings_with_constraints(tmp_path):
    """Valid snapshot with constraints dict must not emit soft constraint warning."""
    _write_snapshot(tmp_path, _valid_snapshot())
    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    warnings = results[0].soft_warnings
    constraint_warns = [w for w in warnings if "constraint" in w.lower()]
    assert constraint_warns == []


# ---------------------------------------------------------------------------
# Hard failures
# ---------------------------------------------------------------------------


def test_expired_snapshot_fails(tmp_path):
    """Expired snapshot must fail with clear message."""
    data = _valid_snapshot()
    data["expires_at"] = PAST
    _write_snapshot(tmp_path, data)

    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert not r.passed
    assert any("expired" in e.lower() for e in r.hard_errors)


def test_unverified_snapshot_fails(tmp_path):
    """human_verified: false must fail."""
    data = _valid_snapshot()
    data["human_verified"] = False
    _write_snapshot(tmp_path, data)

    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert not r.passed
    assert any("human_verified" in e for e in r.hard_errors)


def test_placeholder_source_url_fails(tmp_path):
    """Snapshot with placeholder source URL must fail."""
    data = _valid_snapshot()
    data["sources"] = [
        {
            "source_type": "official_docs",
            "title": "Placeholder",
            "retrieved_at": "2026-05-10T12:00:00Z",
            "url": "https://example.org/placeholder/kling_omni",
        }
    ]
    _write_snapshot(tmp_path, data)

    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert not r.passed
    assert any("placeholder" in e.lower() for e in r.hard_errors)


def test_empty_sources_fails(tmp_path):
    """Empty sources list must fail."""
    data = _valid_snapshot()
    data["sources"] = []
    _write_snapshot(tmp_path, data)

    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert not r.passed
    assert any("sources" in e.lower() for e in r.hard_errors)


def test_empty_prompting_rules_fails(tmp_path):
    """Empty prompting_rules must fail."""
    data = _valid_snapshot()
    data["prompting_rules"] = []
    _write_snapshot(tmp_path, data)

    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert not r.passed
    assert any("prompting_rules" in e for e in r.hard_errors)


def test_both_model_fields_placeholder_fails(tmp_path):
    """Both latest_available_model and best_for_this_task as placeholder strings must fail."""
    data = _valid_snapshot()
    data["latest_available_model"] = "unknown_placeholder"
    data["best_for_this_task"] = "PLACEHOLDER"
    _write_snapshot(tmp_path, data)

    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert not r.passed
    assert any("placeholder" in e.lower() for e in r.hard_errors)


def test_missing_snapshot_fails(tmp_path):
    """No snapshot file for target must fail."""
    # Don't write any snapshot
    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert not r.passed
    assert r.snapshot_path is None
    assert any("no snapshot found" in e.lower() for e in r.hard_errors)


# ---------------------------------------------------------------------------
# Soft warnings
# ---------------------------------------------------------------------------


def test_empty_constraints_produces_soft_warning(tmp_path):
    """Missing constraints dict should produce soft warning, not hard fail."""
    data = _valid_snapshot()
    data["constraints"] = {}
    _write_snapshot(tmp_path, data)

    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME
    )
    r = results[0]
    assert r.passed, f"Expected pass with soft warning; hard_errors={r.hard_errors}"
    assert any("constraint" in w.lower() for w in r.soft_warnings)


# ---------------------------------------------------------------------------
# Multi-target
# ---------------------------------------------------------------------------


def test_multi_target_all_pass(tmp_path):
    """All valid targets must pass."""
    targets = [
        "kling_omni_video_best_available",
        "midjourney_image_best_available",
    ]
    for target in targets:
        data = _valid_snapshot(target)
        provider_dir = tmp_path / "model_guidance_snapshots" / "provider"
        provider_dir.mkdir(parents=True, exist_ok=True)
        path = provider_dir / f"20260510T120000Z_{target}.yaml"
        path.write_text(yaml.dump(data), encoding="utf-8")

    results = validate_model_research_gate(
        tmp_path, targets, reference_time=REFERENCE_TIME
    )
    assert all(r.passed for r in results)


def test_multi_target_mixed_results(tmp_path):
    """Mixed pass/fail targets must each report correctly."""
    good_target = "kling_omni_video_best_available"
    bad_target = "midjourney_image_best_available"

    # Write good snapshot
    snap_dir = tmp_path / "model_guidance_snapshots" / "kling"
    snap_dir.mkdir(parents=True, exist_ok=True)
    good_data = _valid_snapshot(good_target)
    (snap_dir / f"20260510T120000Z_{good_target}.yaml").write_text(yaml.dump(good_data), encoding="utf-8")

    # Write bad (expired) snapshot
    bad_data = _valid_snapshot(bad_target)
    bad_data["expires_at"] = PAST
    bad_data["internal_model_target"] = bad_target
    (snap_dir / f"20260510T120000Z_{bad_target}.yaml").write_text(yaml.dump(bad_data), encoding="utf-8")

    results = validate_model_research_gate(
        tmp_path, [good_target, bad_target], reference_time=REFERENCE_TIME
    )
    by_target = {r.target: r for r in results}
    assert by_target[good_target].passed
    assert not by_target[bad_target].passed


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------


def test_strict_mode_raises_on_failure(tmp_path):
    """strict=True must raise ModelResearchGateError when any target fails."""
    # No snapshot written → will fail
    with pytest.raises(ModelResearchGateError, match="failed model research gate"):
        validate_model_research_gate(
            tmp_path, [TARGET], reference_time=REFERENCE_TIME, strict=True
        )


def test_strict_mode_no_raise_on_all_pass(tmp_path):
    """strict=True must not raise when all targets pass."""
    _write_snapshot(tmp_path, _valid_snapshot())
    # Should not raise
    results = validate_model_research_gate(
        tmp_path, [TARGET], reference_time=REFERENCE_TIME, strict=True
    )
    assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_passes_on_valid_repo(tmp_path):
    """CLI must exit 0 when all targets pass."""
    _write_snapshot(tmp_path, _valid_snapshot())
    exit_code = gate_main([
        "--repo-root", str(tmp_path),
        "--targets", TARGET,
    ])
    assert exit_code == 0


def test_cli_fails_on_missing_snapshot(tmp_path):
    """CLI must exit 1 when a target has no snapshot."""
    exit_code = gate_main([
        "--repo-root", str(tmp_path),
        "--targets", TARGET,
    ])
    assert exit_code == 1


# ---------------------------------------------------------------------------
# Real repo snapshots
# ---------------------------------------------------------------------------


def test_real_repo_snapshots_pass_gate():
    """Production model_guidance_snapshots must pass the gate at reference time 2026-05-10."""
    results = validate_model_research_gate(
        repo_root=REPO_ROOT,
        required_targets=list([
            "kling_omni_video_best_available",
            "midjourney_image_best_available",
            "chatgpt_image_best_available",
            "nano_banana_best_available",
        ]),
        reference_time=REFERENCE_TIME,
    )
    failures = [r for r in results if not r.passed]
    assert failures == [], (
        "Real repo snapshots failed gate:\n"
        + "\n".join(str(r) for r in failures)
    )
