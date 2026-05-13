# DRMYN Studio v0.15.2

## Identity Evidence Set Metadata Checkpoint

Release type: metadata-only scientific software checkpoint.

Date: 2026-05-13
Proposed tag: `v0.15.2-identity-evidence-set-metadata-checkpoint`

## Scope
This checkpoint captures completion of:
- PROD-LINE-15A-3A (Stage 2.5 doctrine/template/kit standardization)
- PROD-LINE-15A-3B (identity evidence set schema + validator scaffold)

This release captures the transition from operator-only guidance to machine-validated metadata tracking for Stage 2.5 identity evidence selection before GPT Images 2 Stage 3 FRONT HERO LOCK.

This is not a final film/output release.

## Key Metadata Change
- New `identity_evidence_set` schema added.
- Validator discovery added for:
  - `visual_dev/elements/characters/*/identity_evidence_sets/*.yaml`
- New C01 draft scaffold record:
  - `C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001`
- Evidence slot standard enforced:
  - `E01_STAGE1_WINNER`
  - `E02_STAGE2A_PORTRAIT`
  - `E03_STAGE2B_FULL_BODY`
  - `E04_STAGE2C_EXPRESSION_BAND`
- Gates enforced:
  - `upload_count` consistency
  - included/excluded_reason consistency
  - slot/source_stage consistency
  - slot/role consistency
  - character/look prefix consistency
  - look and alias existence checks
  - pending_external scaffold refs allowed at draft/review stage

## Release Boundary
- After PROD-LINE-15A-3B.
- Before real external-ref replacement.
- Before GPT Images 2 FRONT HERO LOCK output registration.
- Before QC score population.
- Before lifecycle promotion.

## Validation Evidence
- `python scripts/validate_production_records.py --repo-root .`
  - 77 files scanned, 77 valid, 0 invalid
- `python -m pytest -q`
  - 1368 passed
- `python scripts/validate_prompt_records.py --repo-root .`
  - 7 files validated successfully
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available`
  - 3/3 targets passed

## Governance Confirmation
- Documentation-only and metadata-only release hygiene checkpoint
- No binary/media files committed
- No production record mutation in this release hygiene PR
- No schema/validator/test changes in this release hygiene PR
- No lifecycle promotion
- No real external-ref replacement

## Recommended Release Titles
- Git tag: `v0.15.2-identity-evidence-set-metadata-checkpoint`
- GitHub release title: `DRMYN Studio v0.15.2 - Identity Evidence Set Metadata Checkpoint`
- Zenodo title: `DRMYN Studio: Metadata Scaffold for Identity Evidence Set Selection in AI-Assisted Character Prompt Governance`

## Next Recommended Step
Produce/register actual C01_HOME_MORNING identity evidence external refs, rerun PROD-LINE-15A preflight, then proceed only if READY.
