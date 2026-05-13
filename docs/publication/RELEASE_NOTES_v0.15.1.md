# DRMYN Studio v0.15.1

## Identity Exploration Probe Checkpoint

Release type: metadata-only scientific software checkpoint.

Date: 2026-05-13
Proposed tag: `v0.15.1-identity-exploration-probe-checkpoint`

## Scope
This checkpoint captures completion of:
- PROD-LINE-15A-2 (Identity Exploration 2 probe correction)

This release corrects the Stage 2 methodology in the character visual prompt kit doctrine before any C01 operator-side image generation and before real GPT Images 2 external-reference registration write-pass.

This is not a final film/output release.

## Key Doctrine Change
- Removed Stage 2 `Reference Sheet Prompt`.
- Added Stage 2 `Identity Exploration 2 / Single-Image Variant Probe`.
- Stage 2 is now three separate single-image calls (2A portrait, 2B full-body, 2C expression band).
- Stage 2 uses Midjourney V7 + Omni Reference: `--oref` with `--ow 100`.
- `--v 8.1` and `--oref` are not combined.
- Positive prompt sheet/layout terms were removed from Stage 2 bodies; sheet-like terms are only allowed in `--no` clauses.

## Release Boundary
- After PROD-LINE-15A-2.
- Before C01_HOME_MORNING operator-side image generation.
- Before real GPT Images 2 external-reference registration write-pass.

## Validation Evidence
- `python scripts/validate_production_records.py --repo-root .`
  - 76 files scanned, 76 valid, 0 invalid
- `python -m pytest -q`
  - 1357 passed
- `python scripts/validate_prompt_records.py --repo-root .`
  - 7 files validated successfully
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available`
  - 3/3 targets passed

## Governance Confirmation
- Documentation-only and metadata-only checkpoint
- No binary/media files committed
- No production record mutation
- No schema/validator/test changes
- No lifecycle promotion
- No real external-ref replacement

## Recommended Release Titles
- Git tag: `v0.15.1-identity-exploration-probe-checkpoint`
- GitHub release title: `DRMYN Studio v0.15.1 - Identity Exploration Probe Checkpoint`
- Zenodo title: `DRMYN Studio: Single-Image Identity Exploration Probe for AI-Assisted Character Prompt Governance`

## Next Recommended Step
Produce C01_HOME_MORNING GPT Images 2 outputs externally, then rerun PROD-LINE-15A preflight before any external-reference write-pass.
