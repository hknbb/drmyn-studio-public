# DRMYN Studio v0.15.3

## Non-Character Perspective Pack Framework Checkpoint

Release type: metadata-only scientific software checkpoint.

Date: 2026-05-13
Proposed tag: `v0.15.3-non-character-perspective-pack-framework`

## Scope
This checkpoint captures completion of:
- PROD-LINE-15A-4A (non-character perspective generalization notes)
- PROD-LINE-15A-5 (character downstream perspective key harmonization)
- PROD-LINE-15A-6 (wardrobe perspective pack framework)
- PROD-LINE-15A-6B (first WD001 draft perspective pack record)
- PROD-LINE-15A-7 (prop perspective pack framework)
- PROD-LINE-15A-7B (first ready PROP003 draft perspective pack record)
- PROD-LINE-15A-8 (location perspective pack framework)

This release captures the transition from character-only perspective governance to a documented, schema-compatible framework for wardrobe, prop, and location perspective pack workflows.

This is not a final film/output release.

## Key Metadata Change
- Non-character perspective pack generalization notes added.
- Wardrobe, prop, and location framework doctrines added.
- GPT Images 2 wardrobe, prop, and location perspective pack templates added.
- First draft wardrobe perspective pack record added for WD001.
- First ready draft prop perspective pack record added for PROP003.
- Existing schema-compatible perspective mapping retained for non-character records:
  - `front_hero`
  - `side_depth`
  - `rear_or_side`
  - `detail_or_threshold`
  - `reverse_angle`
  - `usage_angle`
- Location support remains framework-only at this checkpoint; no LOCXXX production perspective pack record is created.

## Release Boundary
- After PROD-LINE-15A-8.
- Before first LOCXXX draft perspective pack record.
- Before real location perspective generation.
- Before generated binary/media registration.
- Before QC score population.
- Before lifecycle promotion.

## Validation Evidence
- `python scripts/validate_production_records.py --repo-root .`
  - 83 files scanned, 83 valid, 0 invalid
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
- Git tag: `v0.15.3-non-character-perspective-pack-framework`
- GitHub release title: `DRMYN Studio v0.15.3 - Non-Character Perspective Pack Framework Checkpoint`
- Zenodo title: `DRMYN Studio: Non-Character Perspective Pack Framework for AI-Assisted Production Metadata Governance`

## Next Recommended Step
Resume C01 Nadia production work from the current checkpoint, or create a dedicated PROD-LINE-15A-8B PR for the first LOCXXX draft perspective-pack metadata record only after location reference intake status is reconciled.
