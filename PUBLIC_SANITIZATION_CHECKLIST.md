# Public Sanitization Checklist — v0.17.0

This checklist must be reviewed and confirmed by the operator before publishing to the public repository and minting the Zenodo DOI.

---

## Security and Privacy

- [ ] No API keys, tokens, or secrets are committed anywhere in the repository.
- [ ] No `.env` files or credential files are present in the repository.
- [ ] `gh auth login` and all authentication actions were performed manually by the human operator; no credentials were handled by any agent.
- [ ] Personal data is limited to ORCID identifiers and institutional affiliations that are already publicly registered (see `CITATION.cff` and `.zenodo.json`).

## Binary Media

- [ ] No raw image files (JPG, PNG, WEBP, etc.) are committed.
- [ ] No video files (MP4, MOV, etc.) are committed.
- [ ] No audio files (WAV, MP3, AAC, etc.) are committed.
- [ ] All generated media outputs are stored externally and referenced only by metadata records.

## External Reference URLs

- [ ] **C02, C03, C04, C05** character records: all `source_reference_id` fields use `pending_external://` placeholders — confirmed, no live URLs.
- [ ] **C01 identity evidence set** (`visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml`): slot `E01_STAGE1_WINNER` contains a live `https://cdn.midjourney.com/...` URL. Before syncing to `drmyn-studio-public`, this file **must** either:
  - (a) be excluded from the public sync entirely, OR
  - (b) have the CDN URL replaced with `pending_external://C01_E01_STAGE1_WINNER` before pushing.
  - [ ] Confirm action taken: ___________________________
- [ ] `external://local_manual/...` refs in C01 evidence slots E02–E04 reference private local storage paths (not live URLs) — acceptable as-is or can be excluded with the file above.
- [ ] No other real image hosting URLs, CDN links, or storage service URLs are committed. (Verified: only one `https://` external_ref exists in the repo — the C01 CDN URL above.)
- [ ] No external API response payloads or image generation service outputs are committed.

## Screenplay and Story Content

- [ ] Scene excerpts in `planning/scenes/*/scene_excerpt.md` are research scaffolds only. No full screenplay or commercially sensitive story content is included.
- [ ] Character names and scene descriptions are research identifiers only.

## Schema and Code Hygiene

- [ ] All schema changes in v0.17.0 are additive only (no breaking changes, no enum removals, no required-field additions to existing schemas).
- [ ] No lifecycle-promoting keys (`approved`, `locked`, `canon_lock`, `materialized`, `selected`) appear in newly created records.
- [ ] All new character records (`C02`, `C03`, `C04`, `C05`) use `status: draft` with `pending_external://` source references.
- [ ] `python scripts/validate_production_records.py --repo-root .` passes (98/98 valid).
- [ ] `python -m pytest -q` passes (1441 tests).

## Public Repository Sync Scope

Before pushing to `drmyn-studio-public`, confirm the following are excluded from the sync:
- [ ] Any files listed under `Excluded` in `PUBLIC_SNAPSHOT_MANIFEST.md`.
- [ ] Any operator session logs containing personal annotations or internal production notes not intended for public release.
- [ ] Any working files or scratch documents not part of the formal methodology.

## Release Actions (Human-Gated)

The following actions must be performed manually by the human operator and are NOT performed by any agent:

- [ ] Push to `drmyn-studio-public` repository.
- [ ] Create Git tag `v0.17.0-public-methodology-checkpoint` on the public repository.
- [ ] Create GitHub Release on `drmyn-studio-public` using `RELEASE_NOTES_v0.17.0.md` as the release body.
- [ ] Confirm Zenodo webhook fires and DOI is minted.
- [ ] Update `CITATION.cff` `doi` field and `.zenodo.json` with the real minted DOI.
- [ ] Commit the DOI update as PR-PUB-2.

---

## Operator Sign-off

Operator: ___________________________
Date: ___________________________
Zenodo DOI (after minting): ___________________________
