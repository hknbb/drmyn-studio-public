from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.operator_next_step import recommend_next_step  # noqa: E402


PROMPT_ID = "SC0001__t2i-char-c01-midjourney__v01"


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_scene(repo_root: Path, scene_id: str = "SC0001") -> None:
    scene_dir = repo_root / "planning" / "scenes" / scene_id
    _write_yaml(
        scene_dir / "scene_card.yaml",
        {
            "scene_id": scene_id,
            "excerpt_ref": "scene_excerpt.md",
            "canon_lock": False,
        },
    )
    (scene_dir / "scene_excerpt.md").write_text("Scene excerpt.", encoding="utf-8")


def _write_prompt_draft(repo_root: Path) -> Path:
    path = repo_root / "prompts" / "draft" / f"{PROMPT_ID}.yaml"
    _write_yaml(
        path,
        {
            "prompt_id": PROMPT_ID,
            "scene_id": "SC0001",
            "prompt_type": "t2i_character_element",
            "lifecycle_stage": "draft",
            "target_models": ["midjourney"],
            "source_refs": {
                "scene_card": "planning/scenes/SC0001/scene_card.yaml",
                "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md",
                "character_refs": ["C01"],
            },
            "prompt_text": "Generate a source-grounded character image.",
            "status": "active",
            "canon_lock": False,
        },
    )
    return path


def _valid_storyboard_options() -> dict:
    return {
        "scene_id": "SC0001",
        "round": 1,
        "source_refs": {
            "scene_card": "planning/scenes/SC0001/scene_card.yaml",
            "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md",
        },
        "options": [
            {
                "option_id": f"SC0001_SB{index:02d}",
                "purpose": "Source-grounded option.",
                "camera_angle": "Static coverage.",
                "framing": "Doorway frame.",
                "movement": "Minimal.",
                "lighting": "Soft daylight.",
                "source_field": "scene_card.visual_targets.framing_bias",
                "prompt_ids": [],
                "status": "candidate",
            }
            for index in range(1, 6)
        ],
        "selected_option": None,
        "review_status": "pending",
        "storage_policy": "no_binary_commits",
    }


def _assert_allowed_commands(step, expected: tuple[str, ...] | None = None) -> None:
    assert isinstance(step.allowed_commands, tuple)
    assert step.allowed_commands
    if expected is not None:
        assert step.allowed_commands == expected


def _assert_recommended_route(step, agent: str, reason: str) -> None:
    assert step.recommended_next_agent == agent
    assert step.recommended_reason == reason
    assert step.recommended_next_agent != "chatgpt_project"


def test_empty_repo_returns_blocked_no_available_task(tmp_path: Path) -> None:
    step = recommend_next_step(tmp_path)

    assert step.current_task == "blocked"
    assert step.scene_id is None
    _assert_recommended_route(step, "claude_code", "manual_pickup")
    _assert_allowed_commands(step, ("switch",))
    assert "No production status rows" in (step.blocked_reason or "")
    assert step.expected_outputs == ["No files are written by this guidance helper."]


def test_prompt_draft_recommends_external_image_generation(tmp_path: Path) -> None:
    _write_scene(tmp_path)
    prompt_path = _write_prompt_draft(tmp_path)

    step = recommend_next_step(tmp_path)

    assert step.current_task == "t2i_image_generation"
    assert step.scene_id == "SC0001"
    _assert_recommended_route(step, "claude_code", "manual_pickup")
    _assert_allowed_commands(step)
    assert prompt_path.relative_to(tmp_path).as_posix() in step.open_files
    assert "external tool" in " ".join(step.do_steps)
    assert "external T2I model" in step.next_command_or_manual_step


def test_candidate_images_without_review_notes_recommends_review_preparation(
    tmp_path: Path,
) -> None:
    _write_scene(tmp_path)
    _write_prompt_draft(tmp_path)
    candidate = (
        tmp_path
        / "visual_dev"
        / "elements"
        / "characters"
        / "C01"
        / "candidates"
        / "candidate_01.jpg"
    )
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"candidate placeholder")

    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    step = recommend_next_step(tmp_path)
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    assert step.current_task == "image_review_preparation"
    _assert_recommended_route(step, "claude_code", "drafting_assist")
    _assert_allowed_commands(step)
    assert "review notes are missing" in (step.blocked_reason or "")
    assert f"evidence/prompt_reviews/{PROMPT_ID}_review.md" in step.expected_outputs
    assert before == after


def test_candidate_images_with_review_notes_recommends_image_review(
    tmp_path: Path,
) -> None:
    _write_scene(tmp_path)
    _write_prompt_draft(tmp_path)
    candidate = (
        tmp_path
        / "visual_dev"
        / "elements"
        / "characters"
        / "C01"
        / "candidates"
        / "candidate_01.png"
    )
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"candidate placeholder")
    notes = tmp_path / "evidence" / "prompt_reviews" / f"{PROMPT_ID}_review.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("Candidate review notes.", encoding="utf-8")

    step = recommend_next_step(tmp_path)

    assert step.current_task == "image_review"
    _assert_recommended_route(step, "claude_code", "review_requested")
    _assert_allowed_commands(step)
    assert notes.relative_to(tmp_path).as_posix() in step.open_files
    assert any("ImageReviewAgent" in item for item in step.do_steps)


def test_no_binaries_or_lifecycle_files_are_created(tmp_path: Path) -> None:
    _write_scene(tmp_path)
    _write_prompt_draft(tmp_path)
    pack_manifest = (
        tmp_path
        / "visual_dev"
        / "elements"
        / "characters"
        / "C01"
        / "pack_manifest.yaml"
    )
    _write_yaml(
        pack_manifest,
        {
            "element_id": "C01",
            "pack_status": "metadata_only",
            "approved": False,
            "locked": False,
        },
    )
    scene_card = tmp_path / "planning" / "scenes" / "SC0001" / "scene_card.yaml"
    before_scene_card = scene_card.read_text(encoding="utf-8")
    before_pack_manifest = pack_manifest.read_text(encoding="utf-8")

    step = recommend_next_step(tmp_path)

    assert step.current_task == "t2i_image_generation"
    _assert_allowed_commands(step)
    assert not list(tmp_path.rglob("*.mp4"))
    assert not list(tmp_path.rglob("*.mov"))
    assert not list(tmp_path.rglob("*.png"))
    assert scene_card.read_text(encoding="utf-8") == before_scene_card
    assert pack_manifest.read_text(encoding="utf-8") == before_pack_manifest
    assert not (tmp_path / "scripts" / "agents" / "run_pipeline.py").exists()


def test_placeholder_snapshot_refresh_recommends_gemini_drafting_assist(
    tmp_path: Path,
) -> None:
    _write_scene(tmp_path)
    prompt_path = _write_prompt_draft(tmp_path)
    snapshot_ref = "evidence/model_guidance_snapshots/placeholder_midjourney.yaml"
    _write_yaml(
        tmp_path / snapshot_ref,
        {
            "model_id": "midjourney",
            "model_version_observed": "unknown_placeholder",
            "sources": [
                {
                    "url": "https://example.org/placeholder",
                    "human_verified": False,
                }
            ],
            "extracted_rules": ["PLACEHOLDER"],
            "do_not_use_without_verification": ["placeholder"],
        },
    )
    payload = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    payload["generation_params"] = {
        "model_guidance_mode": "dynamic_snapshot",
        "model_guidance_snapshot": snapshot_ref,
    }
    _write_yaml(prompt_path, payload)

    step = recommend_next_step(tmp_path)

    assert step.current_task == "model_guidance_snapshot_refresh"
    _assert_recommended_route(step, "gemini_code_assist", "drafting_assist")
    assert snapshot_ref in step.expected_outputs


def test_recommendation_serialization_and_render_include_routing(
    tmp_path: Path,
) -> None:
    _write_scene(tmp_path)
    _write_prompt_draft(tmp_path)

    step = recommend_next_step(tmp_path)
    payload = step.to_dict()
    rendered = step.render()

    assert payload["recommended_next_agent"] == "claude_code"
    assert payload["recommended_reason"] == "manual_pickup"
    assert "recommended_next_agent: claude_code" in rendered
    assert "recommended_reason: manual_pickup" in rendered
    assert "chatgpt_project" not in rendered
