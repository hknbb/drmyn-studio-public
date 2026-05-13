# Public Snapshot Manifest v0.15.3

## Include (public scientific snapshot)
- `schemas/`
- `scripts/`
- `tests/`
- `planning/`
- `prompts/` (draft/review/approved/locked metadata prompt records)
- `visual_dev/` metadata YAML records
- `evidence/` metadata records (including operator sessions, handoffs, indices, QC reports, guides, templates, and reports)
- `model_guidance_snapshots/`
- `README.md`
- `LICENSE`
- `CITATION.cff`
- `CHANGELOG.md`
- `docs/publication/RELEASE_NOTES_v0.15.3.md`
- `docs/publication/repository_hygiene_audit_v0.15.3.md`

## Exclude (must remain out of public snapshot)
- raw generated images
- raw Kling videos
- platform downloads/export bundles
- local machine paths and local-only config artifacts
- API keys/secrets/tokens
- private media archives and large preview batches
- any binary production outputs

## Reproducibility Note
The include set preserves the inputs needed to reproduce the documented checkpoint validations, including:
- `python scripts/validate_prompt_records.py --repo-root .`
- `python scripts/validate_production_records.py --repo-root .`

## Rationale
This snapshot is a metadata-only checkpoint where non-character perspective pack governance is documented and partially scaffolded for wardrobe, prop, and location workflows after PROD-LINE-15A-8 and before first location perspective-pack record creation.
