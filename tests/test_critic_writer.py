"""
tests/test_critic_writer.py — Batch 5

Tests for CriticAgent v1 and PromptWriter.
- CriticAgent hard checks: schema, prompt_id, lifecycle, source_refs,
  canonical IDs, target_models, model_guidance_ref, negative_prompt rule
- CriticAgent soft checks: UNRESOLVED markers
- PromptWriter: file paths, YAML content, CSV rows, library updates
- WriterLifecycleError on non-draft records
- CriticResult + PromptWriter integration
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.critic import CriticAgent, CriticResult  # noqa: E402
from scripts.agents.writer import PromptWriter, WriteResult, WriterLifecycleError  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_valid_record(
    *,
    scene_id: str = "SC0003",
    prompt_id: str = "SC0003__t2i-char-c01-midjourney__v01",
    prompt_text: str = "Nadia, lean upright silhouette, muted domestic neutrals",
    negative_prompt: str | None = "neon cyberpunk, teal-orange grading",
    target_models: list | None = None,
    lifecycle_stage: str = "draft",
    prompt_type: str = "t2i_character_element",
    model_guidance_ref: str = "docs/model_guides/midjourney.yaml",
    model_guidance_mode: str = "locked_guide",
    model_guidance_snapshot: str | None = None,
    extra_generation_params: dict | None = None,
) -> dict:
    params: dict = {
        "model_guidance_mode": model_guidance_mode,
        "model_guidance_ref": model_guidance_ref,
        "adapter_name": (target_models or ["midjourney"])[0],
    }
    if model_guidance_snapshot:
        params["model_guidance_snapshot"] = model_guidance_snapshot
    if extra_generation_params:
        params.update(extra_generation_params)

    record: dict = {
        "prompt_id": prompt_id,
        "scene_id": scene_id,
        "prompt_type": prompt_type,
        "lifecycle_stage": lifecycle_stage,
        "target_models": target_models or ["midjourney"],
        "source_refs": {
            "scene_card": f"planning/scenes/{scene_id}/scene_card.yaml",
            "scene_excerpt": f"planning/scenes/{scene_id}/scene_excerpt.md",
            "character_refs": ["C01"],
        },
        "prompt_text": prompt_text,
        "generation_params": params,
        "expected_output": {"asset_type": "image_set", "variation_count": 4},
        "status": "active",
        "canon_lock": False,
    }

    if negative_prompt is not None:
        record["negative_prompt"] = negative_prompt

    return record


def _make_valid_run_record(
    *,
    run_id: str = "RUN_SC0003_MJ_0001",
    prompt_id: str = "SC0003__t2i-char-c01-midjourney__v01",
    model: str = "midjourney",
    run_at: str = "2026-04-30T12:00:00Z",
) -> dict:
    return {
        "run_id": run_id,
        "prompt_id": prompt_id,
        "model": model,
        "run_at": run_at,
        "outputs_expected": 4,
        "cost": {"unit": "credits", "value": 1},
        "status": "pending",
    }


# ---------------------------------------------------------------------------
# CriticAgent — hard checks
# ---------------------------------------------------------------------------


def test_critic_valid_midjourney_record_passes() -> None:
    """A well-formed Midjourney adapter record passes all hard checks."""
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record()
    result = critic.check(record)
    assert result.passed, f"Expected pass: {result.hard_errors}"


def test_critic_valid_chatgpt_image_record_passes() -> None:
    """ChatGPT Image record with constraint_strategy and no negative_prompt passes."""
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(
        prompt_id="SC0003__t2i-char-c01-chatgpt-image__v01",
        target_models=["chatgpt_image"],
        model_guidance_ref="docs/model_guides/chatgpt_image.yaml",
        negative_prompt=None,
        extra_generation_params={
            "constraint_strategy": "embedded_positive_constraints"
        },
    )
    result = critic.check(record)
    assert result.passed, f"Expected pass: {result.hard_errors}"


def test_critic_non_draft_lifecycle_fails() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(lifecycle_stage="review")
    result = critic.check(record)
    assert not result.passed
    assert any("lifecycle_stage" in e for e in result.hard_errors)


def test_critic_invalid_prompt_id_fails() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(prompt_id="INVALID__prompt__v01")
    result = critic.check(record)
    assert not result.passed
    assert any("prompt_id" in e for e in result.hard_errors)


def test_critic_empty_scene_card_ref_fails() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record()
    record["source_refs"]["scene_card"] = ""
    result = critic.check(record)
    assert not result.passed
    assert any("scene_card" in e for e in result.hard_errors)


def test_critic_canonical_id_c01_in_prompt_text_fails() -> None:
    """C01 appearing literally in prompt_text should be flagged."""
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(
        prompt_text="Reference image of C01 in a domestic setting."
    )
    result = critic.check(record)
    assert not result.passed
    assert any("C01" in e for e in result.hard_errors)


def test_critic_canonical_id_loc001_in_prompt_text_fails() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(
        prompt_text="Set in LOC001 with pale stone walls."
    )
    result = critic.check(record)
    assert not result.passed
    assert any("LOC001" in e for e in result.hard_errors)


def test_critic_multiple_target_models_fails() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(target_models=["midjourney", "chatgpt_image"])
    result = critic.check(record)
    assert not result.passed
    assert any("target_models" in e for e in result.hard_errors)


def test_critic_missing_model_guidance_ref_fails() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record()
    del record["generation_params"]["model_guidance_ref"]
    result = critic.check(record)
    assert not result.passed
    assert any("model_guidance_ref" in e for e in result.hard_errors)


def test_critic_nonexistent_model_guidance_ref_fails() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(
        model_guidance_ref="docs/model_guides/does_not_exist.yaml"
    )
    result = critic.check(record)
    assert not result.passed
    assert any("not found" in e for e in result.hard_errors)


def test_critic_model_id_mismatch_fails() -> None:
    """midjourney target_model but chatgpt_image guide → fails."""
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(
        target_models=["midjourney"],
        model_guidance_ref="docs/model_guides/chatgpt_image.yaml",
    )
    result = critic.check(record)
    assert not result.passed
    assert any("model_id" in e for e in result.hard_errors)


def test_critic_missing_negative_prompt_for_midjourney_fails() -> None:
    """Midjourney requires negative_prompt (limited support)."""
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(negative_prompt=None)
    result = critic.check(record)
    assert not result.passed
    assert any("negative_prompt" in e for e in result.hard_errors)


def test_critic_chatgpt_image_missing_constraint_strategy_fails() -> None:
    """ChatGPT Image without constraint_strategy fails."""
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(
        prompt_id="SC0003__t2i-char-c01-chatgpt-image__v01",
        target_models=["chatgpt_image"],
        model_guidance_ref="docs/model_guides/chatgpt_image.yaml",
        negative_prompt=None,
        # no constraint_strategy
    )
    result = critic.check(record)
    assert not result.passed
    assert any("constraint_strategy" in e for e in result.hard_errors)


def test_critic_dynamic_snapshot_kling_passes(tmp_path: Path) -> None:
    """Dynamic snapshot mode Kling record passes critic with A6.3 fields, no model_guidance_ref."""
    import shutil
    from datetime import datetime, timedelta, timezone

    # Set up repo structure
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    # Create a valid Kling snapshot
    snapshots_dir = tmp_path / "model_guidance_snapshots" / "kling"
    snapshots_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    snapshot = {
        "record_type": "model_guidance_snapshot",
        "schema_version": "0.x-draft",
        "snapshot_id": "20260509T120000Z_kling_omni",
        "internal_model_target": "kling_omni_video_best_available",
        "provider": "kling",
        "model_family": "video_generation",
        "provider_surface": "api",
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "human_verified": True,
        "current_default_model": "Kling 3.0 Omni",
        "latest_available_model": "Kling 3.0 Omni",
        "best_for_this_task": "Kling 3.0 Omni",
        "version_policy": {
            "hardcode_in_adapter": False,
            "adapter_must_read_snapshot": True,
            "prompt_generation_blocks_if_expired": True,
            "prompt_generation_blocks_if_unverified": True,
        },
        "sources": [
            {
                "source_type": "official_docs",
                "title": "Kling API Documentation",
                "retrieved_at": now.isoformat().replace("+00:00", "Z"),
                "url": "https://kling.ai/docs/api/video-generation",
            }
        ],
        "capabilities": {
            "output_type": "video",
            "supports_negative_prompt": True,
        },
    }
    snapshot_path = snapshots_dir / "20260509T120000Z_kling_omni_video_best_available.yaml"
    with open(snapshot_path, "w") as f:
        yaml.dump(snapshot, f)

    critic = CriticAgent(tmp_path)
    record = _make_valid_record(
        prompt_id="SC0003__omni-kling__v01",
        prompt_text="Create one external Kling Omni video instruction.",
        target_models=["kling_omni"],
        model_guidance_mode="dynamic_snapshot",
        model_guidance_ref=None,  # NOT present in dynamic_snapshot
        negative_prompt="blur, morphing",
        extra_generation_params={
            "model_guidance_snapshot_ref": "model_guidance_snapshots/kling/20260509T120000Z_kling_omni_video_best_available.yaml",
            "provider": "kling",
            "provider_surface": "api",
            "resolved_model_name": "Kling 3.0 Omni",
            "resolved_model_role": "best_for_this_task",
            "guidance_observed_at": now.isoformat().replace("+00:00", "Z"),
            "guidance_expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        },
    )
    # Remove model_guidance_ref since it's not used in dynamic_snapshot
    if "model_guidance_ref" in record["generation_params"]:
        del record["generation_params"]["model_guidance_ref"]

    result = critic.check(record)
    assert result.passed, f"Expected pass: {result.hard_errors}"


def test_critic_dynamic_snapshot_missing_snapshot_ref_fails(tmp_path: Path) -> None:
    """Dynamic snapshot mode without model_guidance_snapshot_ref fails."""
    import shutil

    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    record = _make_valid_record(
        model_guidance_mode="dynamic_snapshot",
        model_guidance_ref=None,  # Not in dynamic_snapshot mode
    )
    del record["generation_params"]["model_guidance_ref"]
    result = critic.check(record)
    assert not result.passed
    assert any("model_guidance_snapshot_ref" in e for e in result.hard_errors)


def test_critic_dynamic_snapshot_missing_snapshot_file_fails(tmp_path: Path) -> None:
    """Dynamic snapshot mode with non-existent snapshot file fails."""
    import shutil
    from datetime import datetime, timedelta, timezone

    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    record = _make_valid_record(
        prompt_id="SC0003__omni-kling__v01",
        target_models=["kling_omni"],
        model_guidance_mode="dynamic_snapshot",
        model_guidance_ref=None,
        extra_generation_params={
            "model_guidance_snapshot_ref": "model_guidance_snapshots/kling/nonexistent.yaml",
            "provider": "kling",
            "provider_surface": "api",
            "resolved_model_name": "Kling 3.0 Omni",
            "resolved_model_role": "best_for_this_task",
            "guidance_observed_at": now.isoformat().replace("+00:00", "Z"),
            "guidance_expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        },
    )
    del record["generation_params"]["model_guidance_ref"]
    result = critic.check(record)
    assert not result.passed
    assert any("not found" in e.lower() for e in result.hard_errors)


def test_critic_dynamic_snapshot_provider_mismatch_fails(tmp_path: Path) -> None:
    """Dynamic snapshot with provider mismatch fails."""
    import shutil
    from datetime import datetime, timedelta, timezone

    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    snapshots_dir = tmp_path / "model_guidance_snapshots" / "kling"
    snapshots_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    snapshot = {
        "record_type": "model_guidance_snapshot",
        "internal_model_target": "kling_omni_video_best_available",
        "provider": "kling",  # Real provider in snapshot
        "provider_surface": "api",
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "human_verified": True,
        "best_for_this_task": "Kling 3.0 Omni",
        "version_policy": {"hardcode_in_adapter": False},
        "sources": [{"source_type": "official_docs", "title": "test", "url": "https://test.com"}],
    }
    snapshot_path = snapshots_dir / "20260509T120000Z_kling_omni_video_best_available.yaml"
    with open(snapshot_path, "w") as f:
        yaml.dump(snapshot, f)

    critic = CriticAgent(tmp_path)
    record = _make_valid_record(
        prompt_id="SC0003__omni-kling__v01",
        target_models=["kling_omni"],
        model_guidance_mode="dynamic_snapshot",
        model_guidance_ref=None,
        extra_generation_params={
            "model_guidance_snapshot_ref": "model_guidance_snapshots/kling/20260509T120000Z_kling_omni_video_best_available.yaml",
            "provider": "midjourney",  # MISMATCH
            "provider_surface": "api",
            "resolved_model_name": "Kling 3.0 Omni",
            "resolved_model_role": "best_for_this_task",
            "guidance_observed_at": now.isoformat().replace("+00:00", "Z"),
            "guidance_expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        },
    )
    del record["generation_params"]["model_guidance_ref"]
    result = critic.check(record)
    assert not result.passed
    assert any("provider" in e.lower() for e in result.hard_errors)


def test_critic_dynamic_snapshot_expired_fails(tmp_path: Path) -> None:
    """Dynamic snapshot with expired expiry date fails."""
    import shutil
    from datetime import datetime, timedelta, timezone

    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    snapshots_dir = tmp_path / "model_guidance_snapshots" / "kling"
    snapshots_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=1)  # EXPIRED

    snapshot = {
        "record_type": "model_guidance_snapshot",
        "internal_model_target": "kling_omni_video_best_available",
        "provider": "kling",
        "provider_surface": "api",
        "observed_at": past.isoformat().replace("+00:00", "Z"),
        "expires_at": past.isoformat().replace("+00:00", "Z"),  # EXPIRED
        "human_verified": True,
        "best_for_this_task": "Kling 3.0 Omni",
        "version_policy": {"hardcode_in_adapter": False},
        "sources": [{"source_type": "official_docs", "title": "test", "url": "https://test.com"}],
    }
    snapshot_path = snapshots_dir / "20260509T120000Z_kling_omni_video_best_available.yaml"
    with open(snapshot_path, "w") as f:
        yaml.dump(snapshot, f)

    critic = CriticAgent(tmp_path)
    record = _make_valid_record(
        prompt_id="SC0003__omni-kling__v01",
        target_models=["kling_omni"],
        model_guidance_mode="dynamic_snapshot",
        model_guidance_ref=None,
        extra_generation_params={
            "model_guidance_snapshot_ref": "model_guidance_snapshots/kling/20260509T120000Z_kling_omni_video_best_available.yaml",
            "provider": "kling",
            "provider_surface": "api",
            "resolved_model_name": "Kling 3.0 Omni",
            "resolved_model_role": "best_for_this_task",
            "guidance_observed_at": past.isoformat().replace("+00:00", "Z"),
            "guidance_expires_at": past.isoformat().replace("+00:00", "Z"),
        },
    )
    del record["generation_params"]["model_guidance_ref"]
    result = critic.check(record)
    assert not result.passed
    assert any("expir" in e.lower() for e in result.hard_errors)


def test_critic_dynamic_snapshot_wrong_internal_target_fails(tmp_path: Path) -> None:
    """Dynamic snapshot with wrong internal_model_target fails."""
    import shutil
    from datetime import datetime, timedelta, timezone

    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    snapshots_dir = tmp_path / "model_guidance_snapshots" / "kling"
    snapshots_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    snapshot = {
        "record_type": "model_guidance_snapshot",
        "internal_model_target": "midjourney_image_best_available",  # WRONG
        "provider": "kling",
        "provider_surface": "api",
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "human_verified": True,
        "best_for_this_task": "Kling 3.0 Omni",
        "version_policy": {"hardcode_in_adapter": False},
        "sources": [{"source_type": "official_docs", "title": "test", "url": "https://test.com"}],
    }
    snapshot_path = snapshots_dir / "20260509T120000Z_kling_omni_video_best_available.yaml"
    with open(snapshot_path, "w") as f:
        yaml.dump(snapshot, f)

    critic = CriticAgent(tmp_path)
    record = _make_valid_record(
        prompt_id="SC0003__omni-kling__v01",
        target_models=["kling_omni"],
        model_guidance_mode="dynamic_snapshot",
        model_guidance_ref=None,
        extra_generation_params={
            "model_guidance_snapshot_ref": "model_guidance_snapshots/kling/20260509T120000Z_kling_omni_video_best_available.yaml",
            "provider": "kling",
            "provider_surface": "api",
            "resolved_model_name": "Kling 3.0 Omni",
            "resolved_model_role": "best_for_this_task",
            "guidance_observed_at": now.isoformat().replace("+00:00", "Z"),
            "guidance_expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        },
    )
    del record["generation_params"]["model_guidance_ref"]
    result = critic.check(record)
    assert not result.passed
    assert any("internal_model_target" in e.lower() for e in result.hard_errors)


# ---------------------------------------------------------------------------
# CriticAgent — soft checks
# ---------------------------------------------------------------------------


def test_critic_unresolved_in_prompt_text_is_soft_warning() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record(
        prompt_text="Nadia, UNRESOLVED state, lean silhouette"
    )
    result = critic.check(record)
    assert result.passed is False or (
        result.passed and any("UNRESOLVED" in w for w in result.soft_warnings)
    )
    # Specifically: soft warning must be present
    assert any("UNRESOLVED" in w for w in result.soft_warnings)


def test_critic_clean_record_has_no_soft_warnings() -> None:
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record()
    result = critic.check(record)
    assert result.soft_warnings == []


# ---------------------------------------------------------------------------
# PromptWriter — file I/O
# ---------------------------------------------------------------------------


def test_writer_creates_prompt_yaml(tmp_path: Path) -> None:
    writer = PromptWriter(tmp_path)
    record = _make_valid_record()
    run_record = _make_valid_run_record()

    result = writer.write(record, run_record)

    assert result.prompt_path.exists()
    assert result.prompt_path.name == "SC0003__t2i-char-c01-midjourney__v01.yaml"
    loaded = yaml.safe_load(result.prompt_path.read_text(encoding="utf-8"))
    assert loaded["prompt_id"] == "SC0003__t2i-char-c01-midjourney__v01"


def test_writer_creates_run_record_yaml(tmp_path: Path) -> None:
    writer = PromptWriter(tmp_path)
    record = _make_valid_record()
    run_record = _make_valid_run_record()

    result = writer.write(record, run_record)

    assert result.run_path.exists()
    assert result.run_path.name == "RUN_SC0003_MJ_0001.yaml"
    loaded = yaml.safe_load(result.run_path.read_text(encoding="utf-8"))
    assert loaded["run_id"] == "RUN_SC0003_MJ_0001"
    assert loaded["model"] == "midjourney"


def test_writer_prompt_yaml_in_draft_subdirectory(tmp_path: Path) -> None:
    writer = PromptWriter(tmp_path)
    result = writer.write(_make_valid_record(), _make_valid_run_record())
    assert "prompts" in str(result.prompt_path)
    assert "draft" in str(result.prompt_path)


def test_writer_run_record_in_evidence_prompt_runs(tmp_path: Path) -> None:
    writer = PromptWriter(tmp_path)
    result = writer.write(_make_valid_record(), _make_valid_run_record())
    assert "evidence" in str(result.run_path)
    assert "prompt_runs" in str(result.run_path)


def test_writer_appends_scene_prompt_map_row(tmp_path: Path) -> None:
    # Create CSV with header
    csv_path = tmp_path / "evidence" / "scene_prompt_map.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "scene_id,prompt_id,prompt_type,lifecycle_stage,target_model,"
        "asset_ref,article3_flag,notes\n",
        encoding="utf-8",
    )

    writer = PromptWriter(tmp_path)
    writer.write(_make_valid_record(), _make_valid_run_record())

    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    assert rows[0]["scene_id"] == "SC0003"
    assert rows[0]["prompt_id"] == "SC0003__t2i-char-c01-midjourney__v01"
    assert rows[0]["asset_ref"] == "pending_generation"


def test_writer_appends_run_costs_row(tmp_path: Path) -> None:
    csv_path = tmp_path / "evidence" / "run_costs.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "run_id,scene_id,model,prompt_type,outputs_expected,"
        "cost_value,cost_unit,status\n",
        encoding="utf-8",
    )

    writer = PromptWriter(tmp_path)
    writer.write(_make_valid_record(), _make_valid_run_record())

    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    assert rows[0]["run_id"] == "RUN_SC0003_MJ_0001"
    assert rows[0]["model"] == "midjourney"
    assert rows[0]["cost_unit"] == "credits"


def test_writer_updates_prompt_library(tmp_path: Path) -> None:
    lib_path = tmp_path / "prompts" / "prompt_library.yaml"
    lib_path.parent.mkdir(parents=True)
    lib_path.write_text(
        "version: '0.1.0'\ndescription: test\nprompts: []\n",
        encoding="utf-8",
    )

    writer = PromptWriter(tmp_path)
    result = writer.write(_make_valid_record(), _make_valid_run_record())

    assert result.library_updated is True
    lib = yaml.safe_load(lib_path.read_text(encoding="utf-8"))
    assert len(lib["prompts"]) == 1
    assert lib["prompts"][0]["prompt_id"] == "SC0003__t2i-char-c01-midjourney__v01"


def test_writer_library_idempotent_second_write(tmp_path: Path) -> None:
    """Writing the same prompt_id twice does not duplicate the library entry."""
    writer = PromptWriter(tmp_path)
    writer.write(_make_valid_record(), _make_valid_run_record())
    result2 = writer.write(_make_valid_record(), _make_valid_run_record())

    assert result2.library_updated is False  # already present

    lib_path = tmp_path / "prompts" / "prompt_library.yaml"
    lib = yaml.safe_load(lib_path.read_text(encoding="utf-8"))
    assert len(lib["prompts"]) == 1


def test_writer_non_draft_raises() -> None:
    writer = PromptWriter(Path("."))
    record = _make_valid_record(lifecycle_stage="review")
    run_record = _make_valid_run_record()
    with pytest.raises(WriterLifecycleError):
        writer.write(record, run_record)


def test_writer_creates_csv_with_header_if_absent(tmp_path: Path) -> None:
    """Writer creates the CSV with header when the file doesn't exist yet."""
    writer = PromptWriter(tmp_path)
    writer.write(_make_valid_record(), _make_valid_run_record())

    csv_path = tmp_path / "evidence" / "scene_prompt_map.csv"
    assert csv_path.exists()
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("scene_id")  # header present


# ---------------------------------------------------------------------------
# Integration: Critic → Writer pipeline
# ---------------------------------------------------------------------------


def test_critic_then_writer_integration(tmp_path: Path) -> None:
    """
    Integration: only write when critic passes.

    Valid record → critic passes → writer writes files.
    Invalid record → critic fails → writer is not called.
    """
    import shutil

    # Set up a minimal repo in tmp_path so the Critic can resolve file paths
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    for guide in ("midjourney.yaml", "chatgpt_image.yaml"):
        shutil.copy(
            REPO_ROOT / "docs" / "model_guides" / guide,
            tmp_path / "docs" / "model_guides" / guide,
        )
    (tmp_path / "schemas").mkdir()
    shutil.copy(
        REPO_ROOT / "schemas" / "prompt_record.schema.json",
        tmp_path / "schemas" / "prompt_record.schema.json",
    )

    critic = CriticAgent(tmp_path)
    writer = PromptWriter(tmp_path)

    # Valid Midjourney record
    valid_record = _make_valid_record()
    run_record = _make_valid_run_record()

    result = critic.check(valid_record)
    assert result.passed, f"Expected pass: {result.hard_errors}"

    write_result = writer.write(valid_record, run_record)
    assert write_result.prompt_path.exists()
    assert write_result.run_path.exists()

    # Invalid record (no negative_prompt for Midjourney)
    invalid_record = _make_valid_record(
        prompt_id="SC0003__t2i-char-c01-midjourney__v02",
        negative_prompt=None,
    )
    fail_result = critic.check(invalid_record)
    assert not fail_result.passed

    # Writer should NOT be called for invalid records
    invalid_path = tmp_path / "prompts" / "draft" / "SC0003__t2i-char-c01-midjourney__v02.yaml"
    assert not invalid_path.exists()


# ---------------------------------------------------------------------------
# A7.4f: element alias + character limit validation
# ---------------------------------------------------------------------------


def _make_kling_omni_record(
    *,
    prompt_text: str = (
        "Create one Kling Omni element-based video clip. Total duration: 15 seconds. "
        "Active elements: @Nadia, @ValeResidenceKitchenPassage. "
        "Shot 1 (5s): @ValeResidenceKitchenPassage, pale stone surfaces. "
        "Shot 2 (5s): @Nadia moves through. "
        "Shot 3 (5s): @Nadia fills a glass. "
        "Continuity: frame_input_eligible. Keep clip at 15 seconds."
    ),
    negative_prompt: str = "sliding-feet, morphing, floating-objects",
    required_element_aliases: list | None = None,
    model_guidance_ref: str = "docs/model_guides/kling_omni.yaml",
) -> dict:
    params: dict = {
        "model_guidance_mode": "locked_guide",
        "model_guidance_ref": model_guidance_ref,
        "adapter_name": "kling_omni",
        "clip_id": "CLIP_SC0003_01",
        "total_duration_seconds": 15,
        "continuity_input_mode": "frame_input_eligible",
        "omni_clip_manifest_ref": "planning/scenes/SC0003/manifests/CLIP_SC0003_01_manifest.yaml",
        "source_scene_beat_plan_ref": "planning/scenes/SC0003/scene_beat_plan.yaml",
        "source_dialogue_beats_ref": "planning/scenes/SC0003/dialogue_beats.yaml",
        "repo_binary_committed": False,
        "external_generation_required": True,
        "recommended_cfg_scale": 0.5,
        "recommended_ar": "16:9",
    }
    if required_element_aliases is not None:
        params["required_element_aliases"] = required_element_aliases

    record: dict = {
        "prompt_id": "SC0003__omni-kling-omni-clip-clip-sc0003-01__v01",
        "scene_id": "SC0003",
        "prompt_type": "omni_instruction",
        "lifecycle_stage": "draft",
        "target_models": ["kling_omni"],
        "source_refs": {
            "scene_card": "planning/scenes/SC0003/scene_card.yaml",
            "scene_excerpt": "planning/scenes/SC0003/scene_excerpt.md",
        },
        "prompt_text": prompt_text,
        "negative_prompt": negative_prompt,
        "generation_params": params,
        "expected_output": {"asset_type": "clip", "duration_seconds": 15},
        "status": "active",
        "canon_lock": False,
    }
    return record


def test_critic_kling_with_aliases_present_passes(tmp_path: Path) -> None:
    """Kling prompt with all required aliases in prompt_text must pass."""
    import shutil
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "docs" / "model_guides" / "kling_omni.yaml",
                tmp_path / "docs" / "model_guides" / "kling_omni.yaml")
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    record = _make_kling_omni_record(
        required_element_aliases=["@Nadia", "@ValeResidenceKitchenPassage"]
    )
    result = critic.check(record)
    assert result.passed, f"Expected pass; hard_errors={result.hard_errors}"


def test_critic_kling_missing_alias_fails(tmp_path: Path) -> None:
    """Kling prompt missing a required alias from prompt_text must fail."""
    import shutil
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "docs" / "model_guides" / "kling_omni.yaml",
                tmp_path / "docs" / "model_guides" / "kling_omni.yaml")
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    # @Birta is listed as required but not in prompt_text
    record = _make_kling_omni_record(
        required_element_aliases=["@Nadia", "@Birta"]
    )
    result = critic.check(record)
    assert not result.passed
    assert any("@Birta" in e for e in result.hard_errors)


def test_critic_kling_invalid_alias_syntax_fails(tmp_path: Path) -> None:
    """Alias not matching ^@[A-Za-z0-9_]+$ must be a hard error."""
    import shutil
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "docs" / "model_guides" / "kling_omni.yaml",
                tmp_path / "docs" / "model_guides" / "kling_omni.yaml")
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    record = _make_kling_omni_record(
        required_element_aliases=["@Nadia", "NotAnAlias"]  # missing @
    )
    result = critic.check(record)
    assert not result.passed
    assert any("NotAnAlias" in e for e in result.hard_errors)


def test_critic_prompt_text_over_2500_chars_fails(tmp_path: Path) -> None:
    """prompt_text exceeding 2500 characters must be a hard error."""
    import shutil
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "docs" / "model_guides" / "kling_omni.yaml",
                tmp_path / "docs" / "model_guides" / "kling_omni.yaml")
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    long_text = "A " * 1300  # 2600 chars
    record = _make_kling_omni_record(prompt_text=long_text)
    result = critic.check(record)
    assert not result.passed
    assert any("2500" in e for e in result.hard_errors)


def test_critic_negative_prompt_over_2500_chars_fails(tmp_path: Path) -> None:
    """negative_prompt exceeding 2500 characters must be a hard error."""
    import shutil
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "docs" / "model_guides" / "kling_omni.yaml",
                tmp_path / "docs" / "model_guides" / "kling_omni.yaml")
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    long_neg = "blur, " * 450  # > 2500 chars
    record = _make_kling_omni_record(negative_prompt=long_neg)
    result = critic.check(record)
    assert not result.passed
    assert any("2500" in e and "negative" in e.lower() for e in result.hard_errors)


def test_critic_over_100_words_but_under_2500_chars_not_hard_fail(tmp_path: Path) -> None:
    """Word count > 100 must NOT cause a hard failure (soft guidance only)."""
    import shutil
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO_ROOT / "docs" / "model_guides" / "kling_omni.yaml",
                tmp_path / "docs" / "model_guides" / "kling_omni.yaml")
    shutil.copy(REPO_ROOT / "schemas" / "prompt_record.schema.json",
                tmp_path / "schemas" / "prompt_record.schema.json")

    critic = CriticAgent(tmp_path)
    # 110 words, well under 2500 chars
    many_words = " ".join(["@Nadia action"] * 37)  # 111 words, ~450 chars
    record = _make_kling_omni_record(prompt_text=many_words)
    result = critic.check(record)
    # Must not fail purely due to word count
    word_count_errors = [e for e in result.hard_errors if "word" in e.lower() and "count" in e.lower()]
    assert word_count_errors == [], (
        f"Word count must not be a hard error; got: {word_count_errors}"
    )


def test_critic_no_required_element_aliases_field_unaffected(tmp_path: Path) -> None:
    """Non-Kling prompts without required_element_aliases must not be affected by new checks."""
    critic = CriticAgent(REPO_ROOT)
    record = _make_valid_record()  # Midjourney prompt, no required_element_aliases
    result = critic.check(record)
    # Should pass as before
    assert result.passed, f"Non-Kling prompt unexpectedly failed: {result.hard_errors}"


def test_adapters_produce_critic_passing_records(tmp_path: Path) -> None:
    """
    End-to-end: adapter-generated records pass the Critic when using real model guides.

    This test bridges Batch 4 (adapters) and Batch 5 (critic).
    """
    import shutil

    from scripts.agents.adapters.midjourney import MidjourneyAdapter
    from scripts.agents.adapters.chatgpt_image import ChatGPTImageAdapter
    from scripts.agents.adapters.nano_banana import NanaBananaAdapter
    from scripts.agents.neutral_brief import NeutralBrief, VisualAnchor

    # Set up schemas and guides in tmp_path
    (tmp_path / "docs" / "model_guides").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    for guide in ("midjourney.yaml", "chatgpt_image.yaml", "nano_banana.yaml"):
        shutil.copy(
            REPO_ROOT / "docs" / "model_guides" / guide,
            tmp_path / "docs" / "model_guides" / guide,
        )
    shutil.copy(
        REPO_ROOT / "schemas" / "prompt_record.schema.json",
        tmp_path / "schemas" / "prompt_record.schema.json",
    )

    # Create a brief with clean prompt text (no canonical IDs, no planning names)
    brief = NeutralBrief(
        scene_id="SC0003",
        element_type="character",
        element_id="C01",
        element_name="Nadia Vale",
        visual_anchors=[
            VisualAnchor(
                description="Lean, upright, economical silhouette",
                source_field="character.C01.visual_profile.silhouette",
            ),
            VisualAnchor(
                description="Muted neutrals and controlled domestic tones",
                source_field="character.C01.visual_profile.color_bias",
            ),
        ],
        negative_constraints=[
            "Neon cyberpunk color design",
            "Do not soften her into generalized maternal warmth",
        ],
        continuity_state=None,
        continuity_note=None,
        continuity_warning=None,
        model_guidance_required=True,
        is_ready=True,
        prompt_subject_label="Nadia",
        planning_aliases=("Nadia Vale",),
    )

    critic = CriticAgent(tmp_path)

    for AdapterCls in (MidjourneyAdapter, ChatGPTImageAdapter, NanaBananaAdapter):
        adapter = AdapterCls(tmp_path)
        record, _ = adapter.generate(brief)
        result = critic.check(record)
        assert result.passed, (
            f"{AdapterCls.__name__} generated record failed critic:\n"
            + "\n".join(result.hard_errors)
        )


# NOTE: The "Kling metadata consumption" critic check (lighting/motion telemetry
# must appear per "Shot N" prompt segment) was removed when the Kling Omni prompt
# format moved to Goro-style prose: lighting/motion stay in the manifest for QC and
# are intentionally NOT restated as telemetry in prompt_text. Manifest-level
# lighting/motion QC is enforced by the omni_clip_manifest validators instead.
