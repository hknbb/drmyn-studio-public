# DRMYN Studio v0.15.0

## Character Visual Prompt Kit Checkpoint

Release type: metadata-only scientific software checkpoint.

Date: 2026-05-12
Proposed tag: `v0.15.0-character-visual-prompt-kit-checkpoint`

## Scope
This checkpoint captures completion of:
- PROD-LINE-15A-0 (doctrine + template + C01 visual prompt kit)
- PROD-LINE-15A-1 (C02-C05 visual prompt kits)

This release closes the operator-facing prompt kit gap for C01-C05 and documents the five-stage identity-to-look prompt workflow.

This is not a final film/output release.

## Validation Evidence
- `python scripts/validate_production_records.py --repo-root .`
  - 76 files scanned, 76 valid, 0 invalid
- `python -m pytest -q`
  - 1357 passed
- `python scripts/validate_prompt_records.py --repo-root .`
  - 7 files validated successfully
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available`
  - 3/3 targets passed
- `make validate`
  - not run because `make` is unavailable in this shell environment

## Governance Confirmation
- Documentation-only and metadata-only checkpoint
- No binary/media files committed
- No production record mutation
- No schema/validator/test changes
- No lifecycle promotion
- No real external-ref replacement

## Boundary
- After PROD-LINE-15A-1
- Before PROD-LINE-15A real GPT Images 2 external-ref registration write-pass

## Next Recommended Step
Operator-side external generation for a single look target:
- Recommended first target: `C01_LOOK_HOME_MORNING_V001` / `@C01_HOME_MORNING`
- Required external outputs: front, three-quarter-left, three-quarter-right, rear/side
- Keep outputs outside repo, then rerun 15A preflight

## Citation Positioning
This checkpoint should be published as an operator-facing prompt governance artifact before any real external media reference registration.
