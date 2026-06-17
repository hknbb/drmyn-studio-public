"""
Golden-format test for the canonical Kling Omni (O3) multi-shot prompt builder.

Asserts that generate_from_clip_manifest emits the official VIDEO 3.0 Omni
multi-shot structure: per-shot "Shot N (Xs): ..." blocks, an anti-clone figure
roster with distinguishing details and a no-extra-people negative, the
action-not-appearance instruction, and inter-clip continuity hand-off lines
sourced from scene_continuity_ledger.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.agents.adapters.kling_omni import KlingOmniAdapter

REPO_ROOT = Path(__file__).parent.parent.parent


def _setup(tmp_path: Path) -> Path:
    scene_id = "SC0001"
    clip_id = "CLIP_SC0001_01"
    scenes_dir = tmp_path / "planning" / "scenes" / scene_id
    (scenes_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (scenes_dir / "scene_excerpt.md").write_text("# x", encoding="utf-8")
    (scenes_dir / "scene_card.yaml").write_text(
        yaml.safe_dump({"title": "T", "shot_list_omni": [{"duration_seconds": 5}]}),
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "0.x-draft",
        "record_type": "omni_clip_manifest",
        "scene_id": scene_id,
        "clip_id": clip_id,
        "source_scene_beat_plan_ref": f"planning/scenes/{scene_id}/scene_beat_plan.yaml",
        "source_dialogue_beats_ref": f"planning/scenes/{scene_id}/dialogue_beats.yaml",
        "total_duration_seconds": 7,
        "continuity_input_mode": "metadata_only",
        "shots": [
            {
                "shot_id": "SHOT_SC0001_01_A",
                "duration_seconds": 5,
                "source_beat_ids": ["TAKING"],
                "prompt_action": "@C10_HOLDER restrains @C01_NADIA while @C10_CARRIER lifts the child away",
                "duration_reason": "action 5s",
                "required_element_ids": ["C10", "LOC001"],
                "camera": {"framing": "medium", "movement": "static"},
                "performance_note": "still, contained dread",
                "figures": [
                    {
                        "figure_id": "FIG_HOLDER",
                        "base_element_id": "C10",
                        "kling_alias": "@C10_HOLDER",
                        "role": "restrains the adult",
                        "distinguishing_detail": "left operative, scar on jaw",
                    },
                    {
                        "figure_id": "FIG_CARRIER",
                        "base_element_id": "C10",
                        "kling_alias": "@C10_CARRIER",
                        "role": "carries the infant safely",
                        "distinguishing_detail": "right operative, shaved head",
                    },
                ],
            },
            {
                "shot_id": "SHOT_SC0001_01_B",
                "duration_seconds": 2,
                "source_beat_ids": ["BRACELET"],
                "prompt_action": "A hand closes around a small band",
                "duration_reason": "insert 2s",
                "required_element_ids": ["LOC001"],
                "coverage_role": "insert",
                "camera": {"framing": "insert", "movement": "static"},
                "diegetic_audio": "a small metallic click",
            },
        ],
        "kling_native_audio": {
            "enabled": False,
            "provider_policy": "kling_native_only",
            "external_tts_allowed": False,
            "adr_vendor_allowed": False,
        },
        "provenance": {"created_by": "test", "created_at": "2026-06-03T00:00:00Z"},
    }
    mpath = scenes_dir / "manifests" / f"{clip_id}_manifest.yaml"
    mpath.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    # Element bindings: two distinct C10 figure aliases + location.
    bindings_dir = tmp_path / "visual_dev" / "omni_sets" / scene_id
    bindings_dir.mkdir(parents=True, exist_ok=True)
    docs = [
        {"record_type": "element_binding", "element_id": "C10", "element_type": "character",
         "kling_alias": "@C10_HOLDER", "binding_status": "created"},
        {"record_type": "element_binding", "element_id": "C10", "element_type": "character",
         "kling_alias": "@C10_CARRIER", "binding_status": "created"},
        {"record_type": "element_binding", "element_id": "LOC001", "element_type": "location_sub_area",
         "kling_alias": "@LOC001_ROOM", "binding_status": "created"},
    ]
    (bindings_dir / "element_bindings.yaml").write_text(
        yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8"
    )

    # Continuity ledger entry/exit for this clip.
    ledger = {
        "schema_version": "0.x-draft",
        "record_type": "scene_continuity_ledger",
        "scene_continuity_ledger_id": "SCL_SC0001_V001",
        "scene_id": scene_id,
        "source_omni_clip_plan_ref": f"planning/scenes/{scene_id}/omni_clip_plan.yaml",
        "clip_chain": [
            {
                "clip_id": clip_id,
                "order": 1,
                "entry_state": {
                    "summary": "Nadia holding the child by the crib",
                    "camera_state": {"shot_size": "medium", "subject_screen_position": "center"},
                    "screen_direction": "left_to_right",
                },
                "exit_state": {
                    "summary": "Nadia's arms empty, child carried to the door",
                    "camera_state": {"shot_size": "close", "subject_screen_position": "center"},
                    "screen_direction": "left_to_right",
                },
            }
        ],
        "provenance": {"created_by": "test", "created_at": "2026-06-03T00:00:00Z"},
    }
    (scenes_dir / "scene_continuity_ledger.yaml").write_text(
        yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8"
    )
    return mpath


def test_golden_o3_multishot_format(tmp_path: Path) -> None:
    mpath = _setup(tmp_path)
    adapter = KlingOmniAdapter(tmp_path)
    result = adapter.generate_from_clip_manifest(str(mpath))
    text = result.prompt_record["prompt_text"]

    # Goro-style timecode-first shot headings (no "Shot N (Xs):" prefix, no added "Cut to").
    assert "[00:00 - 00:05]" in text
    assert "[00:05 - 00:07]" in text
    assert "Medium shot:" in text          # shot 1 framing=medium
    assert "Insert:" in text               # shot 2 coverage_role=insert
    assert "Shot 1 (5s):" not in text
    assert "Shot 2 (2s):" not in text
    assert "Cut to" not in text            # the timecode block is the cut
    assert "@@" not in text

    # Camera + performance woven as prose, not telemetry.
    assert "still, contained dread" in text           # performance_note woven into action
    assert "frame holds steady" in text                # static movement prose (no telemetry)
    assert "Motion:" not in text and "subject 0." not in text
    assert "Audio: a small metallic click" in text    # diegetic_audio rendered as Audio line

    # Anti-clone roster: both figure aliases, distinguishing details, no-extras negative.
    assert "@C10_HOLDER" in text and "@C10_CARRIER" in text
    assert "exactly 2 distinct figure" in text
    assert "scar on jaw" in text and "shaved head" in text
    assert "No additional, extra, or duplicated people" in text

    # Action-not-appearance rule.
    assert "Direct action and camera" in text

    # Inter-clip continuity hand-off reached the prompt.
    assert "Continue from previous clip:" in text
    assert "End state for next clip:" in text
    assert "screen direction left to right" in text

    # Both figure aliases are in the attach list (anti-clone: not collapsed by element_id).
    aliases = result.prompt_record["generation_params"]["required_element_aliases"]
    assert "@C10_HOLDER" in aliases and "@C10_CARRIER" in aliases
