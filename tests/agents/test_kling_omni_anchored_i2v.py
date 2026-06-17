"""
Golden test for KlingOmniAdapter anchored_i2v render mode (Faz 3, Anchor & Animate).

Validates:
1. input_mode='anchored_i2v' accepted; 'text_only' is the unchanged default
2. start_frame_ref is required for anchored_i2v; missing raises KlingOmniAdapterError
3. generation_params carries input_mode, start_frame_ref, visual_input_budget, frame_chain_source
4. contact_sheet_ref is optional; when set, contact_sheet present in budget + negative_prompt
5. active_element_aliases flows into generation_params
6. Entry-state anchors are suppressed (start-frame provides visual continuity)
7. 2500-char hard cap still enforced on final passes
8. invalid input_mode raises KlingOmniAdapterError
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts.agents.adapters.kling_omni import KlingOmniAdapter, KlingOmniAdapterError

REPO_ROOT = Path(__file__).parent.parent.parent


def _create_kling_snapshot(tmpdir: Path) -> Path:
    snapshots_dir = tmpdir / "model_guidance_snapshots" / "kling"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)
    snapshot = {
        "record_type": "model_guidance_snapshot",
        "schema_version": "0.x-draft",
        "snapshot_id": "20260615T000000Z_kling_omni_anchored_test",
        "internal_model_target": "kling_omni_video_best_available",
        "provider": "kling",
        "model_family": "video_generation",
        "provider_surface": "manual_external",
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "human_verified": True,
        "current_default_model": "Kling VIDEO 3.0 Omni Test",
        "latest_available_model": "Kling VIDEO 3.0 Omni Test",
        "best_for_this_task": "Kling VIDEO 3.0 Omni Test",
        "feature_required_model": {"anchored_i2v": "Kling VIDEO 3.0 Omni Test"},
        "version_policy": {
            "hardcode_in_adapter": False,
            "adapter_must_read_snapshot": True,
            "prompt_generation_blocks_if_expired": True,
            "prompt_generation_blocks_if_unverified": True,
        },
        "sources": [
            {
                "source_type": "official_docs",
                "title": "Kling API docs (test)",
                "retrieved_at": now.isoformat().replace("+00:00", "Z"),
                "url": "https://kling.ai/quickstart/klingai-video-3-omni-model-user-guide",
            }
        ],
        "capabilities": {"output_type": "video", "supports_anchored_i2v": True},
        "constraints": {"max_duration_seconds": 15, "max_shots_per_generation": 6},
        "prompting_rules": ["Test rule."],
        "provenance": {
            "created_by": "test",
            "created_at": now.isoformat().replace("+00:00", "Z"),
        },
    }
    path = snapshots_dir / "20260615T000000Z_kling_omni_video_best_available.yaml"
    with open(path, "w") as f:
        yaml.dump(snapshot, f)
    return path


def _create_manifest(tmpdir: Path, scene_id: str = "SC9001", clip_id: str = "CLIP_SC9001_01") -> Path:
    manifests_dir = tmpdir / "planning" / "scenes" / scene_id / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    shots = [
        {
            "shot_id": "SHOT_SC9001_01_A",
            "duration_seconds": 5,
            "source_beat_ids": ["BEAT_01"],
            "prompt_action": "NADIA crosses the room, picks up the bracelet.",
            "duration_reason": "normal 5s",
            "entry_state": {"summary": "Nadia at doorway, bracelet on table."},
        },
        {
            "shot_id": "SHOT_SC9001_01_B",
            "duration_seconds": 5,
            "source_beat_ids": ["BEAT_02"],
            "prompt_action": "She holds it up to the light, studying the inscription.",
            "duration_reason": "normal 5s",
            "entry_state": {"summary": "Nadia center frame, bracelet in hand."},
        },
    ]
    manifest = {
        "schema_version": "0.x-draft",
        "record_type": "omni_clip_manifest",
        "scene_id": scene_id,
        "clip_id": clip_id,
        "source_scene_beat_plan_ref": f"planning/scenes/{scene_id}/scene_beat_plan.yaml",
        "source_dialogue_beats_ref": "",
        "total_duration_seconds": 10,
        "continuity_input_mode": "frame_input_active",
        "shots": shots,
        "kling_native_audio": {
            "enabled": False,
            "provider_policy": "kling_native_only",
            "external_tts_allowed": False,
            "adr_vendor_allowed": False,
        },
        "notes": "Test manifest for anchored_i2v",
        "provenance": {"created_by": "test", "created_at": "2026-06-15T00:00:00Z"},
    }
    path = manifests_dir / f"{clip_id}_manifest.yaml"
    with open(path, "w") as f:
        yaml.dump(manifest, f)
    return path


def _create_scene_card(tmpdir: Path, scene_id: str = "SC9001") -> None:
    scenes_dir = tmpdir / "planning" / "scenes" / scene_id
    scenes_dir.mkdir(parents=True, exist_ok=True)
    scene_card = {"title": "Test Scene", "purpose": "anchored_i2v test"}
    with open(scenes_dir / "scene_card.yaml", "w") as f:
        yaml.dump(scene_card, f)
    (scenes_dir / "scene_excerpt.md").write_text("# Excerpt\n", encoding="utf-8")


def _create_scene_beat_plan(tmpdir: Path, scene_id: str = "SC9001") -> None:
    plan_dir = tmpdir / "planning" / "scenes" / scene_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    with open(plan_dir / "scene_beat_plan.yaml", "w") as f:
        yaml.dump({"beats": []}, f)


def _create_element_bindings(tmpdir: Path, scene_id: str = "SC9001") -> None:
    bindings_dir = tmpdir / "planning" / "scenes" / scene_id / "element_bindings"
    bindings_dir.mkdir(parents=True, exist_ok=True)


def _create_continuity_ledger(tmpdir: Path, scene_id: str = "SC9001") -> None:
    ledger_dir = tmpdir / "planning" / "scenes" / scene_id
    ledger_dir.mkdir(parents=True, exist_ok=True)
    with open(ledger_dir / "scene_continuity_ledger.yaml", "w") as f:
        yaml.dump({"clip_states": []}, f)


def _setup_tmpdir(tmpdir: Path, scene_id: str = "SC9001") -> Path:
    _create_kling_snapshot(tmpdir)
    _create_manifest(tmpdir, scene_id=scene_id)
    _create_scene_card(tmpdir, scene_id=scene_id)
    _create_scene_beat_plan(tmpdir, scene_id=scene_id)
    _create_element_bindings(tmpdir, scene_id=scene_id)
    _create_continuity_ledger(tmpdir, scene_id=scene_id)
    # Copy schemas directory
    import shutil
    real_schemas = REPO_ROOT / "schemas"
    if real_schemas.exists():
        shutil.copytree(real_schemas, tmpdir / "schemas", dirs_exist_ok=True)
    return tmpdir / "planning" / "scenes" / scene_id / "manifests" / "CLIP_SC9001_01_manifest.yaml"


@pytest.fixture(scope="module")
def anchored_result():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        manifest_path = _setup_tmpdir(tmpdir)
        adapter = KlingOmniAdapter(repo_root=tmpdir, model_guidance_mode="dynamic_snapshot")
        result = adapter.generate_from_clip_manifest(
            manifest_path,
            input_mode="anchored_i2v",
            start_frame_ref="archive/nexuszero/SC9001/shots/SC9001_02_clip-sc9001-01_shot-sc9001-01-b.png",
            active_element_aliases=["@C01_NADIA"],
        )
    return result


@pytest.fixture(scope="module")
def anchored_with_contact_sheet_result():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        manifest_path = _setup_tmpdir(tmpdir)
        adapter = KlingOmniAdapter(repo_root=tmpdir, model_guidance_mode="dynamic_snapshot")
        result = adapter.generate_from_clip_manifest(
            manifest_path,
            input_mode="anchored_i2v",
            start_frame_ref="archive/nexuszero/SC9001/shots/SC9001_02.png",
            contact_sheet_ref="archive/nexuszero/SC9001/contact_sheets/SC9001_clip01_contact.png",
        )
    return result


# -------------------------------------------------------------------------
# input_mode validation
# -------------------------------------------------------------------------

def test_invalid_input_mode_raises():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        manifest_path = _setup_tmpdir(tmpdir)
        adapter = KlingOmniAdapter(repo_root=tmpdir, model_guidance_mode="dynamic_snapshot")
        with pytest.raises(KlingOmniAdapterError, match="Invalid input_mode"):
            adapter.generate_from_clip_manifest(
                manifest_path,
                input_mode="bad_mode",
                start_frame_ref="some/ref.png",
            )


def test_anchored_i2v_requires_start_frame_ref():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        manifest_path = _setup_tmpdir(tmpdir)
        adapter = KlingOmniAdapter(repo_root=tmpdir, model_guidance_mode="dynamic_snapshot")
        with pytest.raises(KlingOmniAdapterError, match="start_frame_ref"):
            adapter.generate_from_clip_manifest(
                manifest_path,
                input_mode="anchored_i2v",
            )


# -------------------------------------------------------------------------
# anchored_i2v generation_params
# -------------------------------------------------------------------------

def test_anchored_input_mode_in_params(anchored_result):
    gp = anchored_result.prompt_record["generation_params"]
    assert gp["input_mode"] == "anchored_i2v"


def test_anchored_start_frame_ref_in_params(anchored_result):
    gp = anchored_result.prompt_record["generation_params"]
    assert "start_frame_ref" in gp
    assert gp["start_frame_ref"]


def test_anchored_visual_input_budget_no_contact_sheet(anchored_result):
    gp = anchored_result.prompt_record["generation_params"]
    budget = gp["visual_input_budget"]
    assert budget["total"] == 7
    assert budget["start_frame"] == 1
    assert budget["element_slots"] == 6
    assert "contact_sheet" not in budget


def test_anchored_frame_chain_source(anchored_result):
    gp = anchored_result.prompt_record["generation_params"]
    assert gp["frame_chain_source"] == "designed_still_pass1"


def test_anchored_active_element_aliases(anchored_result):
    gp = anchored_result.prompt_record["generation_params"]
    assert gp["active_element_aliases"] == ["@C01_NADIA"]


def test_anchored_prompt_text_under_2500(anchored_result):
    assert len(anchored_result.prompt_record["prompt_text"]) <= 2500


def test_anchored_no_contact_sheet_in_negative_when_not_set(anchored_result):
    neg = anchored_result.prompt_record.get("negative_prompt", "")
    assert "subtitles" not in neg
    assert "visible-grid" not in neg
    assert "timecode-overlay" not in neg


# -------------------------------------------------------------------------
# with contact_sheet_ref
# -------------------------------------------------------------------------

def test_contact_sheet_in_params(anchored_with_contact_sheet_result):
    gp = anchored_with_contact_sheet_result.prompt_record["generation_params"]
    assert "contact_sheet_ref" in gp


def test_visual_input_budget_with_contact_sheet(anchored_with_contact_sheet_result):
    gp = anchored_with_contact_sheet_result.prompt_record["generation_params"]
    budget = gp["visual_input_budget"]
    assert budget["total"] == 7
    assert budget["start_frame"] == 1
    assert budget["contact_sheet"] == 1
    assert budget["element_slots"] == 5


def test_negative_prompt_has_contact_sheet_terms(anchored_with_contact_sheet_result):
    neg = anchored_with_contact_sheet_result.prompt_record.get("negative_prompt", "")
    assert "subtitles" in neg
    assert "visible-grid" in neg
    assert "timecode-overlay" in neg


# -------------------------------------------------------------------------
# Entry anchor suppression
# -------------------------------------------------------------------------

def test_entry_anchors_suppressed_in_anchored_mode(anchored_result):
    """Start-frame provides visual state; per-shot entry-state text should be absent."""
    text = anchored_result.prompt_record["prompt_text"]
    # The entry_state summary in the manifest says "Nadia at doorway" — should not appear
    assert "Nadia at doorway" not in text
    assert "Nadia center frame" not in text


# -------------------------------------------------------------------------
# text_only (default) remains unaffected
# -------------------------------------------------------------------------

def test_text_only_default_no_anchored_fields_in_params():
    """text_only records the input_mode but never the anchored_i2v visual triplet."""
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        manifest_path = _setup_tmpdir(tmpdir)
        adapter = KlingOmniAdapter(repo_root=tmpdir, model_guidance_mode="dynamic_snapshot")
        result = adapter.generate_from_clip_manifest(manifest_path)
    gp = result.prompt_record["generation_params"]
    assert gp["input_mode"] == "text_only"
    assert "start_frame_ref" not in gp
    assert "contact_sheet_ref" not in gp
    assert "visual_input_budget" not in gp
