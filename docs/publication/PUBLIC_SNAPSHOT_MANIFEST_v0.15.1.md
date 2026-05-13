# Public Snapshot Manifest v0.15.1

## Include (public scientific snapshot)
- `schemas/`
- `scripts/`
- `tests/`
- `planning/`
- `prompts/` (draft/review/approved/locked metadata prompt records)
- `visual_dev/` metadata YAML records
- `evidence/` metadata records (including operator sessions, handoffs, indices, QC reports, guides, and reports)
- `model_guidance_snapshots/`
- `README.md`
- `LICENSE`
- `CITATION.cff`
- `CHANGELOG.md`
- `docs/publication/RELEASE_NOTES_v0.15.1.md`
- `docs/publication/repository_hygiene_audit_v0.15.1.md`

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
This snapshot is a metadata-only operator prompt governance checkpoint after PROD-LINE-15A-2 and before C01_HOME_MORNING operator-side image generation and real GPT Images 2 external-reference registration.
