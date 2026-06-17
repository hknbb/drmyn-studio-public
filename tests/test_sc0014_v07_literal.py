"""
SC0014 v07 text-only literal multi-shot tests.

Golden assertions on the literal kling_literal_alias_locked render (Clip 01
establish+reveal, Clip 02 alias-only close coverage, Clip 03 door-open with
alias-only figures), the strict validator bans (role nouns, metaphor, bare
center, missing profile, text_only seed-lock), and the anchor-animate coverage
skip for the retired still/contact route.
"""

from pathlib import Path

from scripts.agents.adapters.kling_omni import KlingOmniAdapter
from scripts.validate_prompt_records import _prompt_semantic_errors
from scripts.validators.validate_shot_still_coverage import validate_shot_still_coverage

REPO = Path(__file__).resolve().parents[1]

_BANNED = [
    "infant", "mother", " child", "protected center", "about to lose",
    " center", "centered", "already elsewhere", "held stillness",
]


def _gen(clip: str) -> dict:
    adapter = KlingOmniAdapter(repo_root=REPO, model_guidance_mode="locked_guide")
    return adapter.generate_from_clip_manifest(
        f"planning/scenes/SC0014/manifests/CLIP_SC0014_{clip}_manifest.yaml",
        version=7,
        input_mode="text_only",
        language_profile="kling_literal_alias_locked",
    ).prompt_record


def _has_banned(text: str) -> list[str]:
    low = text.lower()
    return [b for b in _BANNED if b in low]


# ---------------------------------------------------------------- golden ----

def test_clip01_establishes_then_reveals_nadia_and_jin():
    text = _gen("01")["prompt_text"]
    assert "@LOC001_NURSERY" in text
    assert "No people in frame" in text  # establish first
    assert "@C01_NADIA" in text and "@C08_JIN" in text  # reveal
    assert text.index("No people in frame") < text.index("reveals @C01_NADIA")
    assert not _has_banned(text)


def test_clip02_alias_only_close_coverage():
    text = _gen("02")["prompt_text"]
    assert "@C01_NADIA" in text and "@C08_JIN" in text
    # emotion via physical performance, not abstraction
    assert "eyes lowered" in text or "face still" in text or "jaw tight" in text
    assert not _has_banned(text)


def test_clip03_door_open_alias_only_figures_with_dialogue():
    text = _gen("03")["prompt_text"]
    assert "The door of @LOC001_NURSERY opens" in text
    for alias in ("@C04_DIMITRI", "@C10_CARRIER", "@C10_HOLDER", "@C01_NADIA", "@C08_JIN"):
        assert alias in text
    assert '"Mrs. Vale."' in text  # literal dialogue stays inline
    assert not _has_banned(text)


def test_all_v07_clips_clean_and_under_budget():
    for i in range(1, 9):
        rec = _gen(f"{i:02d}")
        text = rec["prompt_text"]
        assert not _has_banned(text), f"clip {i}: {_has_banned(text)}"
        assert len(text) <= 2500
        assert rec["generation_params"]["language_profile"] == "kling_literal_alias_locked"
        assert rec["generation_params"]["input_mode"] == "text_only"
        assert "contact_sheet_ref" not in rec["generation_params"]
        assert "visual_input_budget" not in rec["generation_params"]


# ------------------------------------------------------------- validator ----

def _strict_hits(rec: dict) -> list[str]:
    keys = (
        "role nouns", "abstract/metaphor", "bare position",
        "language_profile is required", "not allowed under input_mode",
        "missing required active alias", "physical performance",
    )
    return [e for e in _prompt_semantic_errors(rec, REPO) if any(k in e for k in keys)]


def test_validator_clean_v07_record_passes():
    assert _strict_hits(_gen("02")) == []


def test_validator_role_noun_fails():
    rec = _gen("02")
    rec["prompt_text"] += " the infant rests with the mother."
    assert any("role nouns" in e for e in _strict_hits(rec))


def test_validator_metaphor_fails():
    rec = _gen("02")
    rec["prompt_text"] += " protected center; she is about to lose everything."
    assert any("abstract/metaphor" in e for e in _strict_hits(rec))


def test_validator_bare_center_fails():
    rec = _gen("02")
    rec["prompt_text"] += " @C01_NADIA center."
    assert any("bare position" in e for e in _strict_hits(rec))


def test_validator_missing_profile_fails():
    rec = _gen("02")
    rec["generation_params"].pop("language_profile")
    assert any("language_profile is required" in e for e in _strict_hits(rec))


def test_validator_text_only_seed_lock_fails():
    rec = _gen("02")
    rec["generation_params"]["visual_input_budget"] = {"total": 7}
    assert any("not allowed under input_mode" in e for e in _strict_hits(rec))


def test_validator_missing_required_alias_fails():
    rec = _gen("02")
    rec["generation_params"]["required_element_aliases"] = ["@C99_MISSING"]
    assert any("missing required active alias" in e for e in _strict_hits(rec))


# ---------------------------------------------------------------- coverage --

def test_deprecated_still_contact_do_not_trigger_anchor_animate_coverage():
    # SC0014's active route is text_only literal; the retired v06 still/contact
    # records are deprecated, so the anchor-animate coverage contract is skipped.
    assert validate_shot_still_coverage(REPO, "SC0014") == []
