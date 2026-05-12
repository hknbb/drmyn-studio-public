# DRMYN Studio v0.14.0

## Continuity and Omni Alias Governance Checkpoint

Release type: metadata-only scientific software checkpoint.

Date: 2026-05-12
Proposed tag: `v0.14.0-continuity-alias-checkpoint`

## Scope
This checkpoint captures completion of PROD-LINE-14A through PROD-LINE-14H:
- character identity anchor governance
- character look variant continuity governance
- pilot-canon scene look mapping (SC0001-SC0009)
- look-specific Kling/Omni alias layer
- scene -> look -> alias resolver and operator hint reporting

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
- Metadata-only changes
- No binary/media files committed
- No lifecycle promotion
- No real external-ref replacement
- No perspective QC score population

## Canon/Phase Boundary
- Pilot-canon window remains SC0001-SC0009 only.
- SC0010+ remains deferred to PROD-LINE-16+ canon hydration.

## Next Recommended Step
PROD-LINE-15A preflight only (no write-pass):
- verify four GPT Images 2 perspective outputs exist externally
- verify image_selection/local_media_index consistency
- verify single look target alignment (do not mix HOME_MORNING and NIGHT_TIRED in one pack)

## Citation Positioning
This checkpoint should be published as a software/research artifact checkpoint before external generated media registration.
