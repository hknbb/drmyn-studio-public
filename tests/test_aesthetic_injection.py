"""
AB-2 tests — aesthetic bible injection into source_context, neutral_brief,
adapters (midjourney, chatgpt_image, nano_banana), and storyboard_options.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.agents.aesthetic_bible import (
    get_pack_ids_from_records,
    load_aesthetic_bible,
    resolve_pack_keywords,
    resolve_pack_negatives,
)
from scripts.agents.source_context import SourceContextAgent
from scripts.agents.neutral_brief import NeutralBrief, NeutralBriefAgent, _resolve_aesthetic
from scripts.agents.adapters.midjourney import MidjourneyAdapter
from scripts.agents.adapters.chatgpt_image import ChatGPTImageAdapter
from scripts.agents.adapters.nano_banana import NanaBananaAdapter

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _minimal_scene(tmp_path: Path, *, pack_refs: list[str] | None = None) -> Path:
    scene_dir = tmp_path / "planning" / "scenes" / "SC0001"
    scene_dir.mkdir(parents=True)
    vt: dict = {
        "palette": "Pale stone.",
        "lens_bias": "Restrained intimate.",
        "framing_bias": "Threshold depth.",
        "movement_bias": "Minimal exact.",
        "lighting_bias": "Filtered daylight.",
    }
    if pack_refs:
        vt["aesthetic_pack_refs"] = pack_refs
    (scene_dir / "scene_card.yaml").write_text(
        yaml.safe_dump({"scene_id": "SC0001", "excerpt_ref": "scene_excerpt.md",
                        "visual_targets": vt}),
        encoding="utf-8",
    )
    (scene_dir / "scene_excerpt.md").write_text("Nadia notices the frame.", encoding="utf-8")
    return tmp_path


def _copy_aesthetic_bible(tmp_path: Path) -> None:
    src = REPO_ROOT / "planning" / "aesthetic_bible.yaml"
    dst = tmp_path / "planning" / "aesthetic_bible.yaml"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _copy_schema(tmp_path: Path, name: str) -> None:
    src = REPO_ROOT / "schemas" / name
    dst = tmp_path / "schemas" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _make_brief(
    *,
    element_type: str = "character",
    pack_refs: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
    negative_constraints: list[str] | None = None,
) -> NeutralBrief:
    return NeutralBrief(
        scene_id="SC0001",
        element_type=element_type,
        element_id="C01",
        element_name="Nadia",
        visual_anchors=[],
        negative_constraints=negative_constraints or [],
        continuity_state=None,
        continuity_note=None,
        continuity_warning=None,
        model_guidance_required=True,
        is_ready=True,
        aesthetic_pack_refs=pack_refs,
        aesthetic_keywords=keywords,
    )


# ---------------------------------------------------------------------------
# SourceContext — aesthetic bible loading
# ---------------------------------------------------------------------------


def test_source_context_loads_aesthetic_bible_when_present(tmp_path: Path) -> None:
    _minimal_scene(tmp_path)
    _copy_aesthetic_bible(tmp_path)
    ctx = SourceContextAgent(tmp_path).build("SC0001")
    assert ctx.aesthetic_bible is not None
    assert len(ctx.aesthetic_bible.packs) >= 1


def test_source_context_tolerates_missing_aesthetic_bible(tmp_path: Path) -> None:
    _minimal_scene(tmp_path)
    ctx = SourceContextAgent(tmp_path).build("SC0001")
    assert ctx.aesthetic_bible is None


def test_source_context_aesthetic_bible_is_none_does_not_crash(tmp_path: Path) -> None:
    _minimal_scene(tmp_path)
    ctx = SourceContextAgent(tmp_path).build("SC0001")
    assert ctx.escalate is False


# ---------------------------------------------------------------------------
# NeutralBrief — aesthetic_pack_refs and aesthetic_keywords fields
# ---------------------------------------------------------------------------


def test_neutral_brief_has_aesthetic_fields_by_default() -> None:
    brief = _make_brief()
    assert brief.aesthetic_pack_refs == ()
    assert brief.aesthetic_keywords == ()


def test_neutral_brief_includes_aesthetic_keywords_deterministic(tmp_path: Path) -> None:
    _minimal_scene(tmp_path, pack_refs=["VALE_DOMESTIC_RESTRAINT"])
    _copy_aesthetic_bible(tmp_path)
    ctx = SourceContextAgent(tmp_path).build("SC0001")
    bible = ctx.aesthetic_bible
    assert bible is not None
    pack_ids = get_pack_ids_from_records(ctx.scene_card, None)
    keywords = resolve_pack_keywords(bible.packs, pack_ids, "t2i_character_element", limit_per_pack=2)
    # Same call returns same result
    keywords2 = resolve_pack_keywords(bible.packs, pack_ids, "t2i_character_element", limit_per_pack=2)
    assert keywords == keywords2
    assert len(keywords) >= 1


def test_neutral_brief_merges_pack_negatives_into_constraints(tmp_path: Path) -> None:
    _minimal_scene(tmp_path, pack_refs=["VALE_DOMESTIC_RESTRAINT"])
    _copy_aesthetic_bible(tmp_path)
    ctx = SourceContextAgent(tmp_path).build("SC0001")
    bible = ctx.aesthetic_bible
    assert bible is not None
    pack_ids = get_pack_ids_from_records(ctx.scene_card, None)
    negatives = resolve_pack_negatives(bible.packs, pack_ids)
    assert len(negatives) >= 1
    assert all(isinstance(n, str) and n for n in negatives)


def test_resolve_aesthetic_returns_empty_when_no_bible() -> None:
    pack_refs, keywords, negatives, warnings = _resolve_aesthetic(None, {}, None, "character")
    assert pack_refs == []
    assert keywords == []
    assert negatives == []
    assert warnings == []


def test_resolve_aesthetic_returns_empty_when_no_pack_refs(tmp_path: Path) -> None:
    _copy_aesthetic_bible(tmp_path)
    bible = load_aesthetic_bible(tmp_path)
    assert bible is not None
    scene_card: dict = {"visual_targets": {}}
    pack_refs, keywords, negatives, warnings = _resolve_aesthetic(bible, scene_card, None, "character")
    assert pack_refs == []
    assert keywords == []
    assert negatives == []
    assert warnings == []


def test_unknown_aesthetic_pack_ref_warns_without_inventing(tmp_path: Path) -> None:
    """Unknown pack refs produce a warning; no keywords or negatives are invented."""
    _copy_aesthetic_bible(tmp_path)
    bible = load_aesthetic_bible(tmp_path)
    assert bible is not None

    scene_card: dict = {"visual_targets": {"aesthetic_pack_refs": ["UNKNOWN_PACK"]}}
    pack_refs, keywords, negatives, warnings = _resolve_aesthetic(
        bible, scene_card, None, "character"
    )
    assert any("UNKNOWN_PACK" in w for w in warnings)
    assert keywords == []
    assert negatives == []
    # Unknown ref preserved in pack_refs for provenance
    assert "UNKNOWN_PACK" in pack_refs


def test_neutral_brief_deterministic_order_across_runs(tmp_path: Path) -> None:
    _minimal_scene(tmp_path, pack_refs=["VALE_DOMESTIC_RESTRAINT"])
    _copy_aesthetic_bible(tmp_path)
    bible = load_aesthetic_bible(tmp_path)
    assert bible is not None
    scene_card = {"visual_targets": {"aesthetic_pack_refs": ["VALE_DOMESTIC_RESTRAINT"]}}
    results = [
        get_pack_ids_from_records(scene_card, None)
        for _ in range(5)
    ]
    assert all(r == results[0] for r in results)


# ---------------------------------------------------------------------------
# Midjourney adapter — compact comma-tail within 60 words (updated from research)
# ---------------------------------------------------------------------------


def test_midjourney_prompt_includes_aesthetic_tail(tmp_path: Path) -> None:
    adapter = MidjourneyAdapter(tmp_path)
    keywords = ("gritty neo-noir film still", "pale stone institutional")
    brief = _make_brief(
        element_type="character",
        pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        keywords=keywords,
    )
    brief_ready = NeutralBrief(
        **{**brief.__dict__,
           "visual_anchors": [
               type("VA", (), {"description": "Lean upright posture", "source_field": "x"})()
           ],
           "is_ready": True}
    )
    # Build a real brief with visual anchors
    from scripts.agents.neutral_brief import VisualAnchor
    brief2 = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean upright posture with no wasted motion.",
                                     source_field="char")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
        aesthetic_pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        aesthetic_keywords=keywords,
    )
    text = adapter._build_prompt_text(brief2)
    assert "gritty neo-noir" in text or "pale stone" in text
    assert len(text.split()) <= 60


def test_midjourney_prompt_respects_60_word_limit(tmp_path: Path) -> None:
    adapter = MidjourneyAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    long_keywords = tuple(f"keyword-{i}" for i in range(30))
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean upright posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
        aesthetic_pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        aesthetic_keywords=long_keywords,
    )
    text = adapter._build_prompt_text(brief)
    assert len(text.split()) <= 60


# ---------------------------------------------------------------------------
# ChatGPT Image adapter — natural language aesthetic phrase
# ---------------------------------------------------------------------------


def test_chatgpt_adapter_uses_visual_world_phrase(tmp_path: Path) -> None:
    adapter = ChatGPTImageAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
        aesthetic_pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        aesthetic_keywords=("pale stone institutional", "controlled domestic restraint"),
    )
    text = adapter._build_prompt_text(brief)
    assert "Visual world:" in text
    assert "pale stone institutional" in text


def test_chatgpt_adapter_no_raw_comma_tail(tmp_path: Path) -> None:
    adapter = ChatGPTImageAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
        aesthetic_pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        aesthetic_keywords=("pale stone institutional",),
    )
    text = adapter._build_prompt_text(brief)
    # Should NOT just be a bare comma-separated suffix — must be in natural phrase
    assert "Visual world:" in text


# ---------------------------------------------------------------------------
# Nano Banana adapter — world consistency anchor
# ---------------------------------------------------------------------------


def test_nano_adapter_uses_world_consistency_anchor(tmp_path: Path) -> None:
    adapter = NanaBananaAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
        aesthetic_pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        aesthetic_keywords=("pale stone institutional", "controlled domestic restraint"),
    )
    text = adapter._build_prompt_text(brief)
    assert "World consistency:" in text
    assert "pale stone institutional" in text


def test_nano_adapter_no_aesthetic_when_empty(tmp_path: Path) -> None:
    adapter = NanaBananaAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
    )
    text = adapter._build_prompt_text(brief)
    assert "World consistency:" not in text


# ---------------------------------------------------------------------------
# BaseAdapter — source_refs.aesthetic_refs and generation_params
# ---------------------------------------------------------------------------


def test_prompt_record_has_aesthetic_refs_in_source_refs(tmp_path: Path) -> None:
    adapter = MidjourneyAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
        aesthetic_pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        aesthetic_keywords=("pale stone institutional",),
    )
    prompt_record, _ = adapter.generate(brief)
    assert "aesthetic_refs" in prompt_record["source_refs"]
    assert prompt_record["source_refs"]["aesthetic_refs"] == ["VALE_DOMESTIC_RESTRAINT"]


def test_generation_params_records_aesthetic_keywords_injected(tmp_path: Path) -> None:
    adapter = MidjourneyAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
        aesthetic_pack_refs=("VALE_DOMESTIC_RESTRAINT",),
        aesthetic_keywords=("pale stone institutional",),
    )
    prompt_record, _ = adapter.generate(brief)
    assert "aesthetic_keywords_injected" in prompt_record["generation_params"]
    assert prompt_record["generation_params"]["aesthetic_keywords_injected"] == [
        "pale stone institutional"
    ]


def test_no_aesthetic_refs_when_pack_refs_empty(tmp_path: Path) -> None:
    adapter = MidjourneyAdapter(tmp_path)
    from scripts.agents.neutral_brief import VisualAnchor
    brief = NeutralBrief(
        scene_id="SC0001", element_type="character", element_id="C01",
        element_name="Nadia",
        visual_anchors=[VisualAnchor(description="Lean posture.", source_field="x")],
        negative_constraints=[],
        continuity_state=None, continuity_note=None, continuity_warning=None,
        model_guidance_required=True, is_ready=True,
    )
    prompt_record, _ = adapter.generate(brief)
    assert "aesthetic_refs" not in prompt_record["source_refs"]
    assert "aesthetic_keywords_injected" not in prompt_record["generation_params"]


# ---------------------------------------------------------------------------
# prompt_record schema validation with aesthetic_refs
# ---------------------------------------------------------------------------


def test_prompt_record_with_aesthetic_refs_passes_schema(tmp_path: Path) -> None:
    from jsonschema import Draft202012Validator
    schema = json.loads(
        (REPO_ROOT / "schemas" / "prompt_record.schema.json").read_text(encoding="utf-8")
    )
    payload = {
        "prompt_id": "SC0001__t2i-char-c01-midjourney__v01",
        "scene_id": "SC0001",
        "prompt_type": "t2i_character_element",
        "lifecycle_stage": "draft",
        "target_models": ["midjourney"],
        "source_refs": {
            "scene_card": "planning/scenes/SC0001/scene_card.yaml",
            "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md",
            "character_refs": ["C01"],
            "aesthetic_refs": ["VALE_DOMESTIC_RESTRAINT"],
        },
        "prompt_text": "Nadia, pale stone institutional, controlled domestic restraint",
        "status": "active",
        "canon_lock": False,
    }
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(payload)]
    assert errors == [], errors


# ---------------------------------------------------------------------------
# Storyboard options — aesthetic_pack_refs propagation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Backward compatibility — existing records without aesthetic fields stay valid
# ---------------------------------------------------------------------------


def test_existing_scene_card_without_aesthetic_pack_refs_still_valid() -> None:
    from jsonschema import Draft202012Validator
    schema = json.loads(
        (REPO_ROOT / "schemas" / "scene_card.schema.json").read_text(encoding="utf-8")
    )
    # Load an existing scene card that has no aesthetic_pack_refs
    sc_path = REPO_ROOT / "planning" / "scenes" / "SC0001" / "scene_card.yaml"
    if sc_path.exists():
        payload = yaml.safe_load(sc_path.read_text(encoding="utf-8"))
        errors = [e.message for e in Draft202012Validator(schema).iter_errors(payload)]
        assert errors == [], errors


def test_existing_prompt_record_without_aesthetic_refs_still_valid() -> None:
    from jsonschema import Draft202012Validator
    schema = json.loads(
        (REPO_ROOT / "schemas" / "prompt_record.schema.json").read_text(encoding="utf-8")
    )
    payload = {
        "prompt_id": "SC0001__t2i-char-c01-midjourney__v01",
        "scene_id": "SC0001",
        "prompt_type": "t2i_character_element",
        "lifecycle_stage": "draft",
        "target_models": ["midjourney"],
        "source_refs": {
            "scene_card": "planning/scenes/SC0001/scene_card.yaml",
            "scene_excerpt": "planning/scenes/SC0001/scene_excerpt.md",
        },
        "prompt_text": "Nadia, lean upright posture",
        "status": "active",
        "canon_lock": False,
    }
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(payload)]
    assert errors == [], errors
