# Changelog

## element-reference-policy-v2-c0205-migration (2026-05-16)

### Summary
- PR-REF-5: migrates the draft characters C02, C03, C04, C05 to Element Reference Generation Policy v2.
- First proof of policy v2 on real character records. Grandfathered records (C01, LOC001, PROP003) untouched.

### Changed
- Rewrote `gpt_images_perspective_pack.yaml` for C02/C03/C04/C05 to `perspective_policy: three_view_scale_angle_v2`: three scale-angle views (`front_reference`, `three_quarter_medium_reference`, `three_quarter_close_reference`), no left/right directional prompts, `full_body_visible: false`, prompt text free of canonical IDs.
- Added `reference_chain.yaml` for C02/C03/C04/C05 recording the two-stage Midjourney chain (V8.1 narrative identity -> V7 `--oref` refinement) and the ChatGPT Images 2 handoff.
- `source_reference_id` now points at the chain handoff (`pending_external://MJ_OMNI_REF_C0x_V001`); stage outputs remain `pending_external` until real generation.

### Validation Evidence
- `python -m pytest -q` -> 1441 passed.
- `python scripts/validate_production_records.py --repo-root .` -> 98 files scanned, 98 valid, 0 invalid.

### Policy Confirmation
- No binary outputs committed. No lifecycle promotion — all records remain `status: draft`.
- Grandfathered C01/LOC001/PROP003 records unchanged.

### Next Step
- Operator generates real C03 Birta images per the prompt templates, then promotes the chain and perspective pack from draft -> review.

## element-reference-policy-v2 (2026-05-16)

### Summary
- PR-REF-0: defines Element Reference Generation Policy v2 (doctrine + additive schema + operator prompt templates).
- Forward-only policy. Existing records (C01, LOC001, PROP003) are grandfathered, not migrated.
- This entry is the v2 cutoff: records authored after it must use `perspective_policy: three_view_scale_angle_v2`.

### Changed
- Added doctrine `docs/methodology/element_reference_generation_policy.md` (two-stage character chain, non-character routing, scale-angle three-view, full-body-not-a-gate, grandfather rule).
- Added operator guide `docs/operator_guides/element_reference_prompting_v2.md` and prompt templates under `templates/element_reference_prompts/` (5 stage templates, each citing the active model guide + snapshot).
- `schemas/gpt_images_perspective_pack.schema.json`: added `three_view_scale_angle_v2` to `perspective_policy` enum and a new `prompts` `oneOf` branch (`front_reference`, `three_quarter_medium_reference`, `three_quarter_close_reference`). Legacy enum values and branches retained for grandfathered records.
- Added `tests/test_gpt_images_perspective_pack_schema.py`.
- Added `element_reference_policy_v2` policy notes to `docs/model_guides/midjourney.yaml` and `docs/model_guides/chatgpt_image.yaml`.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 98 files scanned, 98 valid, 0 invalid.
- `python -m pytest -q` -> 1416 passed.

### Policy Confirmation
- No binary outputs committed.
- No lifecycle promotion. No production record mutation — schema changes are strictly additive.
- Existing C01/LOC001/PROP003 records unchanged (grandfathered).

### Next Step
- PR-REF-1: add the `character_reference_chain` schema.

## v0.15.3-non-character-perspective-pack-framework (2026-05-13)

### Summary
- Scientific checkpoint after PROD-LINE-15A-8.
- Scope remains documentation-only and metadata-only release hygiene.
- Non-character perspective pack governance now covers wardrobe, prop, and location framework scaffolding.

### Changed
- Added non-character perspective generalization notes for wardrobe, prop, and location workflows.
- Added wardrobe, prop, and location perspective pack doctrine/template scaffolds.
- Added first draft wardrobe perspective pack record for WD001.
- Added first ready draft prop perspective pack record for PROP003.
- Preserved schema-compatible perspective mappings without adding new enums in this release hygiene checkpoint.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 83 files scanned, 83 valid, 0 invalid.
- `python -m pytest -q` -> 1368 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation in this release hygiene PR.
- No schema, validator, or test changes in this release hygiene PR.

### Next Step
- Resume C01 Nadia production work from the checkpoint, or open a dedicated PROD-LINE-15A-8B PR for the first LOCXXX draft perspective-pack record after location intake status reconciliation.

## v0.15.2-identity-evidence-set-metadata-checkpoint (2026-05-13)

### Summary
- Scientific checkpoint after PROD-LINE-15A-3B.
- Scope remains documentation-only and metadata-only release hygiene.
- Stage 2.5 Identity Evidence Set Selection is now machine-validated through schema + validator wiring.

### Changed
- Added formal `identity_evidence_set` metadata contract to the validated production model set.
- Added validator discovery for `visual_dev/elements/characters/*/identity_evidence_sets/*.yaml`.
- Added C01 HOME_MORNING draft scaffold for Stage 3 identity evidence selection.
- Standardized evidence slot semantics: `E01_STAGE1_WINNER`, `E02_STAGE2A_PORTRAIT`, `E03_STAGE2B_FULL_BODY`, `E04_STAGE2C_EXPRESSION_BAND`.
- Added enforcement gates for upload_count consistency, included/excluded_reason coupling, slot-to-source/role matching, look/alias consistency, and pending_external scaffold safety.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 77 files scanned, 77 valid, 0 invalid.
- `python -m pytest -q` -> 1368 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation in this release hygiene PR.
- No schema, validator, or test changes in this release hygiene PR.

### Next Step
- Produce/register actual C01_HOME_MORNING identity evidence external refs, rerun PROD-LINE-15A preflight, and proceed only if READY.

## v0.15.1-identity-exploration-probe-checkpoint (2026-05-13)

### Summary
- Scientific checkpoint after PROD-LINE-15A-2 doctrine correction.
- Scope remains documentation-only and metadata-only.
- Stage 2 prompt doctrine was corrected before C01 operator-side image generation and before real GPT Images 2 external-ref registration write-pass.

### Changed
- Stage 2 `Reference Sheet Prompt` workflow removed from operator doctrine/prompt-kit materials.
- Stage 2 replaced with `Identity Exploration 2 / Single-Image Variant Probe`.
- Stage 2 standardized to Midjourney V7 with `--oref` and `--ow 100`.
- Explicit guardrail documented: do not combine `--v 8.1` with `--oref`.
- Positive prompt sheet/layout language removed from Stage 2 prompt bodies.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation.
- No schema, validator, or test changes.

### Next Step
- Produce C01 GPT Images 2 outputs externally (`C01_HOME_MORNING`) and rerun PROD-LINE-15A preflight before any write-pass.

## v0.15.0-character-visual-prompt-kit-checkpoint (2026-05-12)

### Summary
- Scientific checkpoint for PROD-LINE-15A-0 and PROD-LINE-15A-1.
- Scope is documentation-only and metadata-only, before real GPT Images 2 external-ref registration.

### Added
- Character visual prompt kit doctrine guide.
- Character visual prompt kits for C01, C02, C03, C04, C05.
- Reusable character visual prompt kit template.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation.

### Next Step
- PROD-LINE-15A write-pass after real C01 GPT Images 2 perspective outputs are available externally and preflight is READY.
## v0.14.0-continuity-alias-checkpoint (2026-05-12)

### Summary
- Scientific checkpoint for PROD-LINE-14A through PROD-LINE-14H.
- Scope is metadata-only governance architecture before PROD-LINE-15 external-output registration.

### Added
- Look-specific Kling element alias architecture and records (`kling_character_look_element`).
- Scene-to-Kling alias resolver and operator hint report export.
- Operator guide append for Omni alias usage rule (`@C##_LOOK_ROLE`).

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.

### Next Step
- PROD-LINE-15A: C01 GPT Images 2 real external-ref registration preflight (look-target aware).
