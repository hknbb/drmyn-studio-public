# DRMYN Studio v0.17.0 — Public Methodology Checkpoint

**Release date:** 2026-05-16
**Tag:** `v0.17.0-public-methodology-checkpoint`
**Zenodo DOI:** [10.5281/zenodo.20241807](https://doi.org/10.5281/zenodo.20241807)

---

## Summary

This checkpoint formalizes the **Element Reference Generation Policy v2**, which establishes a principled, reproducible workflow for producing visual reference elements used in AI-assisted film production. The policy replaces ad-hoc directional perspective prompts with a structured two-stage character chain and a universal scale-angle three-view vocabulary.

---

## Changes

### Element Reference Generation Policy v2 (PR-REF-0 through PR-REF-5)

**Doctrine and operator guides**
- New: `docs/methodology/element_reference_generation_policy.md` — full v2 doctrine covering the two-stage character reference chain, non-character routing, the scale-angle three-view vocabulary, full-body-not-a-gate rule, and grandfather rule for pre-policy records.
- New: `docs/operator_guides/element_reference_prompting_v2.md` — stage map table, model guide binding, QC criteria, grandfather note.
- Updated: `docs/operator_guides/gpt_images_perspective_output_registration.md` — replaced "Required Four Outputs" section with v2 three-view output language; documented that full-body visibility is optional metadata, not a hard QC gate.
- Updated: `evidence/operator_guides/location_perspective_pack_doctrine.md`, `prop_perspective_pack_doctrine.md`, `wardrobe_perspective_pack_doctrine.md` — added policy v2 addendum superseding legacy candidate perspective sets.
- Updated: `evidence/research_notes/non_character_perspective_generalization_notes.md` — superseded-by-v2 note.

**Prompt templates**
New directory `templates/element_reference_prompts/` with five operator-facing prompt templates:
- `character_mj_v8_narrative_identity.md` — Stage 1: Midjourney V8/V8.1 narrative identity reference (`--style raw --ar 2:3 --seed`; full body not required).
- `character_mj_v7_oref_refinement.md` — Stage 2: Midjourney V7 `--oref` Omni Reference refinement from Stage 1 winner.
- `character_gptimg2_scale_angle_pack.md` — Stage 3: GPT Images 2 three-view scale-angle pack from Stage 2 anchor.
- `non_character_gptimg2_first_reference.md` — Non-character first identity reference via GPT Images 2.
- `non_character_gptimg2_scale_angle_pack.md` — Non-character scale-angle three-view pack.

**Model guides updated**
- `docs/model_guides/midjourney.yaml` — added `element_reference_policy_v2` rule: Midjourney used only for character first-reference chain.
- `docs/model_guides/chatgpt_image.yaml` — added `element_reference_policy_v2` rule: GPT Images 2 used for scale-angle pack across all element types and for non-character first reference.

**Schema changes (additive only)**
- `schemas/gpt_images_perspective_pack.schema.json`:
  - Added `three_view_scale_angle_v2` to `perspective_policy` enum (legacy values retained).
  - Added `$defs`: `scaleAngleThreeViewPrompt`, `threeQuarterMediumReferencePrompt`, `threeQuarterCloseReferencePrompt`.
  - Added third `prompts` oneOf branch for v2 three-view packs.
  - Added optional `full_body_visible` boolean property.
- `schemas/character_reference_chain.schema.json` — **new schema**: records the two-stage Midjourney reference chain per character (stage_1 V8/V8.1 narrative identity, stage_2 V7 Omni Reference refinement, handoff to GPT Images 2).
- `schemas/perspective_qc_report.schema.json`:
  - Added `three_quarter_medium_reference` and `three_quarter_close_reference` to perspective enum (11 values total, 9 legacy retained).
  - Added 8 optional QC scoring fields: `character_description_strength`, `identity_readability`, `silhouette_readability`, `wardrobe_world_fit`, `expression_performance_readability`, `view_distinction`, `scale_distinction`, `no_directional_confusion`.
- `schemas/kling_element_reference_record.schema.json`:
  - Added 4th oneOf branch to `gpt_images_2_perspectives` for v2 key set (`front_reference`, `three_quarter_medium_reference`, `three_quarter_close_reference`). Previous 3 branches retained.

**Validator and agent updates**
- `scripts/agents/scene_readiness.py` — updated next-step hint to reference v2 view names.

**New tests**
- `tests/test_gpt_images_perspective_pack_schema.py` — 8 tests for v2 branch.
- `tests/test_character_reference_chain_schema.py` — 12 tests.
- `tests/test_perspective_qc_report_schema.py` — 6 tests for v2 QC fields.
- `tests/test_kling_element_reference_record_schema.py` — 7 tests for v2 branch.

**Character draft record migration (PR-REF-5)**
- `visual_dev/elements/characters/C02/`, `C03/`, `C04/`, `C05/`:
  - `gpt_images_perspective_pack.yaml` migrated to `perspective_policy: three_view_scale_angle_v2` with three-view prompts.
  - `reference_chain.yaml` created per character (draft, `pending_external://` placeholders).
- Grandfather rule: `C01`, `LOC001`, `PROP003` remain on `three_view_no_rear` — unchanged.

---

## Non-character routing clarification (PR-REF-2)

Routing table established in `element_reference_generation_policy.md`:
- Characters → Midjourney V8/V8.1 → V7 Omni Reference → GPT Images 2 three-view pack.
- Locations, props, wardrobe, style → GPT Images 2 first reference + GPT Images 2 three-view pack.
- Legacy non-character records with `MJ_ELEMENT_*` source IDs remain grandfathered.

---

## Validation Evidence

- `python scripts/validate_production_records.py --repo-root .` → 98 files scanned, 98 valid, 0 invalid.
- `python -m pytest -q` → 1441 passed.

---

## Policy Confirmation

- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed — all new character records use `pending_external://` placeholders.
- All schema changes strictly additive (no required-field additions, no enum removals, no breaking changes).
- Existing C01/LOC001/PROP003 records unchanged (grandfathered).

---

## Next Steps

- **Phase 2:** C03 Birta character visual production (MJ V8.1 → V7 --oref → GPT Images 2 → Kling binding).
- **Phase 3:** SC0001 golden reference scene — first end-to-end produced scene with full shot coverage.
