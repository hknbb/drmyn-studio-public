# Changelog

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
