# Release Runbook v0.15.3

This runbook is the operator checklist for publishing the `v0.15.3` checkpoint to the public snapshot repository and archiving it in Zenodo.

## Target
- Git tag: `v0.15.3-non-character-perspective-pack-framework`
- GitHub release title: `DRMYN Studio v0.15.3 - Non-Character Perspective Pack Framework Checkpoint`
- Zenodo title: `DRMYN Studio: Non-Character Perspective Pack Framework for AI-Assisted Production Metadata Governance`

## Preconditions
1. `main` includes merge commit `e2a3268` (`PR #175`).
2. Working tree is clean.
3. Validation baseline already documented in:
   - `docs/publication/repository_hygiene_audit_v0.15.3.md`
   - `docs/publication/RELEASE_NOTES_v0.15.3.md`

## Step 1 - Prepare Public Snapshot Repository
1. Sync public snapshot repo `main`.
2. Apply only the v0.15.3 include set defined in:
   - `docs/publication/PUBLIC_SNAPSHOT_MANIFEST_v0.15.3.md`
3. Exclude binaries, local artifacts, private media, and secrets.
4. Verify release docs exist in public snapshot:
   - `docs/publication/RELEASE_NOTES_v0.15.3.md`
   - `docs/publication/repository_hygiene_audit_v0.15.3.md`
   - `docs/publication/TAG_SUGGESTION_v0.15.3.md`
   - `docs/publication/CITATION_CHECK_v0.15.3.md`

## Step 2 - Create Tag and GitHub Release (Public Repo)
1. Create annotated tag:
   - `v0.15.3-non-character-perspective-pack-framework`
2. Create GitHub release from this tag.
3. Use the release title:
   - `DRMYN Studio v0.15.3 - Non-Character Perspective Pack Framework Checkpoint`
4. Use release notes body template below.

### GitHub Release Body (Template)
```markdown
## Summary
- Metadata-only scientific software checkpoint after PROD-LINE-15A-8.
- Captures non-character perspective pack framework coverage for wardrobe, prop, and location governance.
- Includes first draft non-character records where available (WD001, PROP003) and location framework scaffolding.

## Scope
- docs/metadata checkpoint only
- no schema edits in this release-hygiene cut
- no validator edits in this release-hygiene cut
- no lifecycle promotion
- no binary/media registration

## Validation
- `python scripts/validate_production_records.py --repo-root .` -> 83 scanned, 83 valid, 0 invalid
- `python -m pytest -q` -> 1368 passed
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed

## Boundary
- After PROD-LINE-15A-8 location scaffold merge.
- Before first LOCXXX draft perspective-pack record.
- Before real location generation, QC score population, lifecycle promotion, and materialized output registration.
```

## Step 3 - Zenodo Archive
1. Wait for Zenodo GitHub integration to ingest the new release.
2. Open Zenodo record and verify:
   - Version record created
   - DOI minted
   - Metadata/title is correct
3. Record both:
   - Concept DOI
   - Version DOI (for v0.15.3)

## Step 4 - DOI Metadata Patch (Public Repo)
After DOI is minted, open a small metadata PR in the public repo:
1. Update `CITATION.cff` with released version DOI/version/date.
2. Update `.zenodo.json` DOI/version metadata.
3. Update README DOI badge/link only if needed.
4. Add short citation check note under `docs/publication/`.

Suggested PR title:
- `chore(citation): apply v0.15.3 minted DOI metadata`

## Step 5 - Resume Production Line
After DOI patch is merged:
1. Resume C01 Nadia checkpoint work.
2. Optional next production-line PR:
   - `PROD-LINE-15A-8B` first `LOCXXX` draft perspective-pack metadata record
   - only after location intake status reconciliation

## Operator Notes
- Zenodo DOI is minted after release ingestion; do not write placeholder DOI as final value.
- Keep release and DOI patch separated to maintain clean audit trace.
