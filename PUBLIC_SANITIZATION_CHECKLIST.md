# Public Sanitization Checklist — v0.18.0

This checklist must be reviewed and confirmed by the operator before publishing to the public repository and minting the Zenodo DOI.

---

## Security and Privacy

- [ ] No API keys, tokens, or secrets are committed anywhere in the repository.
- [ ] No `.env` files or credential files are present in the repository.
- [ ] `gh auth login` and all authentication actions were performed manually by the human operator; no credentials were handled by any agent.
- [ ] Personal data is limited to ORCID identifiers and institutional affiliations that are already publicly registered (see `CITATION.cff`).

## Binary Media

- [ ] No raw image files (JPG, PNG, WEBP, etc.) are committed.
- [ ] No video files (MP4, MOV, etc.) are committed.
- [ ] No audio files (WAV, MP3, AAC, etc.) are committed.
- [ ] All generated media outputs are stored externally (git-ignored `archive/` tree) and referenced only by metadata records.

## Content Exclusions (Story / Production Records)

All of the following path categories must be **excluded** from the public sync — they contain story content or private production records, not methodology:

- [ ] `planning/scenes/` — excluded.
- [ ] `planning/characters/`, `planning/locations/`, `planning/props/` — excluded.
- [ ] `source/` — excluded entirely (screenplay, dossiers, story bibles).
- [ ] `prompts/draft/` — excluded (scene-specific Kling Omni prompts).
- [ ] `evidence/operator_sessions/` — excluded.
- [ ] `evidence/local_media_indices/` — excluded.
- [ ] `evidence/perspective_qc/` — excluded.
- [ ] `visual_dev/elements/` — excluded.
- [ ] `visual_dev/omni_sets/` — excluded.
- [ ] `planning/manifests/` — excluded.
- [ ] `closingpriceclaudecodeanalysisforcode.md` — excluded (internal analysis).
- [ ] `drmynstdklingomnideep-research-report.md` — excluded (internal research).
- [ ] `revised_character_batch_to_golden_scene_plan.md` — excluded (internal planning).
- [ ] `generate_workflow_diagram.py`, `preview_diagram.html`, `workflow_diagram.*` — excluded (scratch files).
- [ ] `.claude/` — excluded (local agent memory, not methodology).

## External Reference URLs

- [ ] Scan `docs/`, `schemas/`, `scripts/`, `templates/`, `tests/`, `AGENTS.md` for any `https://cdn`, `https://oaiusercontent`, or other image-hosting URLs. **In v0.18.0: none found in these paths.** Confirm before sync.
- [ ] CDN/oref URLs (`oref_cdn_url`, CDN `https://cdn.midjourney.com/…`) exist only in `prompts/draft/` (excluded above) and `visual_dev/elements/` (excluded above) — they do **not** appear in methodology paths.
- [ ] **C01 identity evidence set** (`visual_dev/elements/characters/C01/identity_evidence_sets/`): this path is excluded (`visual_dev/elements/` is out of scope for v0.18.0 public sync). No action needed beyond confirming exclusion.
- [ ] No `external://local_manual/…` or `pending_external://` refs in methodology files.
- [ ] No external API response payloads are committed.

## Screenplay and Story Content

- [ ] `source/` is fully excluded — no screenplay fragments in any included file.
- [ ] `planning/scenes/*/scene_excerpt.md` paths are excluded.
- [ ] No character names, scene descriptions, or story content appear in methodology files (schemas, scripts, docs, templates, tests).
  - *Note:* Scripts and tests may reference generic placeholder IDs (e.g., `SC0001`, `C01`) as test fixtures — confirm these are structural identifiers only, not story excerpts.

## Schema and Code Hygiene

- [ ] All schema changes in v0.18.0 are additive only (no breaking changes, no enum removals, no required-field additions to existing schemas).
- [ ] `python scripts/validate_production_records.py --repo-root .` passes (150/150 valid).
- [ ] `python scripts/validate_prompt_records.py --repo-root .` passes (55/55 valid).
- [ ] `python -m pytest -q` passes (1520 passed, 3 skipped).
- [ ] `validate_model_research_gate.py` — 3/3 targets pass.
- [ ] `AGENTS.md` contains no API keys, CDN URLs, personal annotations, or story content.

## Public Repository Sync Scope

Before pushing to the public repository, confirm the following are included and excluded:

**Included paths (methodology only):**
- [ ] `schemas/`
- [ ] `scripts/`
- [ ] `tests/`
- [ ] `docs/`
- [ ] `templates/`
- [ ] `AGENTS.md`
- [ ] `CHANGELOG.md`
- [ ] `RELEASE_NOTES_v0.18.0.md`
- [ ] `PUBLIC_SNAPSHOT_MANIFEST.md`
- [ ] `PUBLIC_SANITIZATION_CHECKLIST.md`
- [ ] `README.md`, `LICENSE`, `AUTHORS.md`, `CONTRIBUTORS.md`, `AI_USE_DISCLOSURE.md`
- [ ] `CITATION.cff`, `codemeta.json`
- [ ] `pyproject.toml`, `requirements.txt`, `devcontainer.json`, `Makefile`

**Excluded paths (all content / private production records — see Content Exclusions above).**

## Release Actions (Human-Gated)

The following actions must be performed manually by the human operator and are NOT performed by any agent:

- [ ] Merge PR #247 (`feat/sc0014-scene-production → main`) on the private repository.
- [ ] Create Git tag `v0.18.0-kling-literal-multishot-pipeline` on `main` of the private repository.
- [ ] Sync to public repository (copy methodology paths only; exclude all content paths).
- [ ] Create Git tag `v0.18.0-kling-literal-multishot-pipeline` on the public repository.
- [ ] Create GitHub Release on the public repository using `RELEASE_NOTES_v0.18.0.md` as the release body.
- [ ] Confirm Zenodo webhook fires and DOI is minted.
- [ ] Update `CITATION.cff` `doi` field with the minted DOI.
- [ ] Commit the DOI update.

---

## Operator Sign-off

Operator: ___________________________
Date: ___________________________
Zenodo DOI (after minting): ___________________________
