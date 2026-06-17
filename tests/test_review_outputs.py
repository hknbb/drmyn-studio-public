from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.review_outputs import (  # noqa: E402
    FAILURE_REASONS,
    QUALITY_SCORE_FIELDS,
    ImageReviewAgent,
    ReviewOutputError,
)


PROMPT_ID = "SC0003__t2i-char-c01-midjourney__v01"


def _scores(value: int = 4) -> dict[str, int]:
    return {field: value for field in QUALITY_SCORE_FIELDS}


def _candidate(
    *,
    path: str = "visual_dev/elements/characters/C01/candidates/nadia_front_v01.png",
    status: str = "selected",
    reason: str = "Best identity consistency and correct silhouette.",
    scores: dict[str, int] | None = None,
    failure_reason: str | None = None,
    asset_id: str = "C01_nadia_front_v01",
) -> dict:
    return {
        "asset_id": asset_id,
        "path": path,
        "status": status,
        "reason": reason,
        "quality_scores": scores or _scores(),
        "failure_reason": failure_reason,
    }


def _rejected_candidate() -> dict:
    return _candidate(
        path="visual_dev/elements/characters/C01/candidates/nadia_alt_v01.png",
        status="rejected",
        reason="Too fashion editorial for the source-grounded character.",
        scores=_scores(2),
        failure_reason="output_too_stylized",
        asset_id="C01_nadia_alt_v01",
    )


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validate(schema_name: str, payload: dict) -> list[str]:
    schema_path = REPO_ROOT / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = Draft202012Validator(schema).iter_errors(payload)
    return [
        f"{'.'.join(str(p) for p in error.absolute_path) or '(root)'}: {error.message}"
        for error in errors
    ]


def test_review_agent_writes_metadata_only_records(tmp_path: Path) -> None:
    agent = ImageReviewAgent(tmp_path)
    result = agent.write_review(
        element_type="character",
        element_id="C01",
        source_prompt_ids=[PROMPT_ID],
        source_model="midjourney",
        candidate_images=[_candidate(), _rejected_candidate()],
        canonical_images=[
            "visual_dev/elements/characters/C01/candidates/nadia_front_v01.png"
        ],
        review_notes="Use the selected front-facing candidate as the seeded image.",
    )

    assert result.image_selection_path == (
        tmp_path
        / "visual_dev"
        / "elements"
        / "characters"
        / "C01"
        / "image_selection.yaml"
    )
    assert result.pack_manifest_suggestion_path.name == (
        "pack_manifest_update_suggestion.yaml"
    )
    assert len(result.asset_clearance_paths) == 1

    # The agent records metadata paths only; it does not copy/create image binaries.
    candidate_binary = (
        tmp_path
        / "visual_dev"
        / "elements"
        / "characters"
        / "C01"
        / "candidates"
        / "nadia_front_v01.png"
    )
    assert not candidate_binary.exists()


def test_image_selection_output_passes_schema(tmp_path: Path) -> None:
    result = ImageReviewAgent(tmp_path).write_review(
        element_type="characters",
        element_id="C01",
        source_prompt_ids=[PROMPT_ID],
        source_model="midjourney",
        candidate_images=[_candidate(), _rejected_candidate()],
        canonical_images=[
            "visual_dev/elements/characters/C01/candidates/nadia_front_v01.png"
        ],
    )
    payload = _load_yaml(result.image_selection_path)
    errors = _validate("image_selection.schema.json", payload)
    assert errors == []
    assert payload["pack_manifest_sync"] == "pending"
    assert payload["round_status"] == "complete"
    assert payload["candidate_images"][1]["failure_reason"] == "output_too_stylized"


def test_asset_clearance_output_passes_schema(tmp_path: Path) -> None:
    result = ImageReviewAgent(tmp_path).write_review(
        element_type="character",
        element_id="C01",
        source_prompt_ids=[PROMPT_ID],
        source_model="midjourney",
        candidate_images=[_candidate()],
        canonical_images=[
            "visual_dev/elements/characters/C01/candidates/nadia_front_v01.png"
        ],
        review_notes="Pending human clearance.",
    )
    payload = _load_yaml(result.asset_clearance_paths[0])
    errors = _validate("asset_clearance.schema.json", payload)
    assert errors == []
    assert payload["commercial_use_allowed"] == "pending_review"
    assert payload["actor_likeness_risk"] is False
    assert payload["style_imitation_risk"] is False
    assert payload["watermark_detected"] is False
    assert payload["face_identity_drift"] is False
    assert payload["review_notes"] == "Pending human clearance."


def test_pack_manifest_is_not_modified_directly(tmp_path: Path) -> None:
    element_dir = tmp_path / "visual_dev" / "elements" / "characters" / "C01"
    element_dir.mkdir(parents=True)
    pack_manifest = element_dir / "pack_manifest.yaml"
    pack_manifest.write_text("pack_status: metadata_only\n", encoding="utf-8")

    result = ImageReviewAgent(tmp_path).write_review(
        element_type="character",
        element_id="C01",
        source_prompt_ids=[PROMPT_ID],
        source_model="midjourney",
        candidate_images=[_candidate()],
        canonical_images=[
            "visual_dev/elements/characters/C01/candidates/nadia_front_v01.png"
        ],
    )

    assert pack_manifest.read_text(encoding="utf-8") == "pack_status: metadata_only\n"
    suggestion = _load_yaml(result.pack_manifest_suggestion_path)
    assert suggestion["suggested_field"] == "pack_status"
    assert suggestion["suggested_value"] == "seeded"
    assert "approved" not in suggestion
    assert "locked" not in suggestion
    assert "canon_lock" not in suggestion


def test_rejected_candidate_requires_failure_reason(tmp_path: Path) -> None:
    bad_candidate = _candidate(status="rejected", failure_reason=None)
    with pytest.raises(ReviewOutputError, match="failure_reason"):
        ImageReviewAgent(tmp_path).write_review(
            element_type="character",
            element_id="C01",
            source_prompt_ids=[PROMPT_ID],
            source_model="midjourney",
            candidate_images=[bad_candidate],
        )


def test_quality_scores_must_include_all_fields(tmp_path: Path) -> None:
    bad_scores = _scores()
    bad_scores.pop("continuity")
    with pytest.raises(ReviewOutputError, match="Missing quality score"):
        ImageReviewAgent(tmp_path).write_review(
            element_type="character",
            element_id="C01",
            source_prompt_ids=[PROMPT_ID],
            source_model="midjourney",
            candidate_images=[_candidate(scores=bad_scores)],
        )


def test_quality_scores_must_be_one_to_five(tmp_path: Path) -> None:
    bad_scores = _scores()
    bad_scores["source_grounding"] = 6
    with pytest.raises(ReviewOutputError, match="source_grounding"):
        ImageReviewAgent(tmp_path).write_review(
            element_type="character",
            element_id="C01",
            source_prompt_ids=[PROMPT_ID],
            source_model="midjourney",
            candidate_images=[_candidate(scores=bad_scores)],
        )


def test_corrected_brief_written_to_prompt_reviews(tmp_path: Path) -> None:
    result = ImageReviewAgent(tmp_path).write_review(
        element_type="character",
        element_id="C01",
        source_prompt_ids=[PROMPT_ID],
        source_model="midjourney",
        candidate_images=[_rejected_candidate()],
        corrected_brief={
            "revision_reason": "Reduce editorial styling.",
            "negative_constraints": ["No fashion editorial lighting."],
        },
    )
    assert result.corrected_brief_path == (
        tmp_path
        / "evidence"
        / "prompt_reviews"
        / "SC0003__t2i-char-c01-midjourney__v02_brief.yaml"
    )
    payload = _load_yaml(result.corrected_brief_path)
    assert payload["source_prompt_id"] == PROMPT_ID
    assert payload["corrected_brief"]["revision_reason"] == "Reduce editorial styling."


def test_failure_taxonomy_contains_required_values() -> None:
    assert set(FAILURE_REASONS) == {
        "source_missing",
        "continuity_unresolved",
        "model_guidance_stale",
        "output_too_stylized",
        "identity_drift",
        "camera_drift",
        "storage_policy_violation",
        "schema_validation_error",
        "unsourced_assertion",
        "continuity_contradiction",
    }


