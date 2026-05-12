# DRMYN Studio — Metadata-Only AI-Assisted Movie Development and Production Workflow

[![DOI](https://zenodo.org/badge/1227492409.svg)](https://doi.org/10.5281/zenodo.19987410)

This repository contains the canonical source records, planning metadata, prompt-governance, validation, and reproducibility infrastructure for **DRMYN Studio**, demonstrated through the *Closing Price* AI-assisted film project.

## Scope

DRMYN Studio is a metadata-only, schema-validated, human-gated research software framework for AI-assisted **movie development and movie production process** design, documentation, validation, and reproducibility.

The repository is not a generated-media repository and is not limited to screenplay generation. Screenplay-related files, when present, are treated as one component of the broader movie development process.

The repository records source truth, planning metadata, prompt governance, validation evidence, human approval decisions, agent handoffs, and reproducibility artifacts for an AI-assisted film production workflow.

## Purpose

DRMYN Studio governs the **pre-production and production-process metadata layer** of an AI-assisted film production pipeline. It is responsible for:

- defining canonical source truth
- stabilizing scene, character, location, continuity, and prompt records
- enforcing naming and schema rules
- supporting GitHub-based review and approval
- generating reproducible artifacts before downstream runtime generation

This repository is **not** a runtime output repository. Generated image, video, audio, and post-production binaries are stored externally per the storage policy and referenced by metadata-only records.

## Core principles

1. **Source-first** — Canonical project truth begins in `source/`.
2. **Stable identifiers** — Scene, character, sequence, location, prop, and continuity IDs must remain stable across the pipeline.
3. **Schema-first planning** — Planning records are only accepted if they pass machine validation.
4. **Prompt governance** — Prompts move through a strict lifecycle: `draft → review → approved → locked`.
5. **GitHub review before canon** — Nothing becomes canonical without review, validation, and merge to the protected base branch.
6. **Reproducibility by design** — Validation reports, manifests, artifact bundles, and release metadata are treated as first-class research outputs.

## Repository layout

| Directory | Purpose |
|-----------|---------|
| `source/` | Canonical human-authored source files |
| `planning/` | Scene cards, character sheets, location sheets, continuity records |
| `prompts/` | Prompt lifecycle and library |
| `schemas/` | JSON Schemas for machine validation |
| `scripts/` | Validation and artifact scripts |
| `evidence/` | Maps, logs, and reports for publication and supplements |
| `.github/` | GitHub-native governance and CI files |
| `docs/` | Human-readable workflow, methodology, and policy documentation |

## Zone 1 / Phase 1 scope

**In scope:**
- Canonical source package preparation
- Scene-card construction
- Prompt-brief design
- Continuity registration
- GitHub review and approval workflows
- Artifact validation and release

**Out of scope:**
- Runtime graph generation
- Scene drafting
- LLM critique
- Commit-event writing
- Index materialization

## Validation

Run locally:

```bash
pip install -r requirements.txt

python scripts/validate_phase1.py \
  --source-dir source \
  --planning-dir planning \
  --prompts-dir prompts \
  --schemas-dir schemas \
  --evidence-dir evidence \
  --report-json evidence/validation_reports/phase1_validation_report.json \
  --report-md evidence/validation_reports/phase1_validation_report.md

python scripts/check_referential_integrity.py \
  --planning-dir planning \
  --prompts-dir prompts \
  --output evidence/validation_reports/referential_integrity_report.json

python scripts/build_manifests.py \
  --planning-dir planning \
  --output-dir planning/manifests
```

Or use Make:

```bash
make validate
make manifests
make numbered-fountain
make seed-scenes
make hydrate-scenes
make canon-queue
```

## Source spine automation

- `source/screenplay/closing_price.fountain` remains the canonical unnumbered screenplay.
- `planning/manifests/closing_price_scene_retrieval_map.json` is the authoritative 120-scene spine.
- `make numbered-fountain` generates `source/screenplay/closing_price.numbered.fountain` as a derivative artifact.
- `make seed-scenes` scaffolds `planning/scenes/SC0001` through `planning/scenes/SC0120` and refreshes `scene_excerpt.md` from the retrieval-map spans.
- `make hydrate-scenes` conservatively grounds `scene_card.yaml` and `prompt_brief.md` from the retrieval map and each scene's excerpt, then writes `evidence/validation_reports/scene_hydration_report.json`.
- `make canon-queue` builds a deterministic canon hydration work queue plus pilot-scene review packets for the first human canon pass.

## Branching model

- `main` — protected, release-ready only
- Feature branches — short-lived working branches
- No direct commits to `main`

See [docs/workflow/branch_protection_policy.md](docs/workflow/branch_protection_policy.md).

## ID namespace

| Entity | Format | Example |
|--------|--------|---------|
| Scene | `SC0001` | `SC0001` |
| Character | `C01` | `C01` |
| Sequence | `SEQ01` | `SEQ01` |
| Location | `LOC001` | `LOC001` |
| Prop | `PROP001` | `PROP001` |
| Wardrobe | `WD001` | `WD001` |

## Film Aesthetic Bible

The **Film Aesthetic Bible** (`planning/aesthetic_bible.yaml`) is a machine-readable registry of named visual mood-board packs grounded in `source/style_bible.md`. Each pack defines:

- `search_keywords` — curator reference list for Pinterest / Midjourney visual searches
- `element_keyword_map` — deterministic 2-3 keyword sets per element type (character, location, prop, wardrobe, style)
- `do_not_keywords` — negative constraints injected alongside style bible rules

Scene cards and element records declare which packs apply via `aesthetic_pack_refs`. The prompt pipeline resolves keywords deterministically by `(pack_id, element_type)` pair — no randomness, no web fetches. Each adapter injects them in its native idiom:

| Adapter | Injection style |
|---|---|
| Midjourney | Compact comma-tail, ≤80 words |
| ChatGPT Image | `"Visual world: …"` natural-language phrase |
| Nano Banana | `"World consistency: …"` identity anchor |

Pack provenance is recorded in every prompt record under `source_refs.aesthetic_refs` and `generation_params.aesthetic_keywords_injected`.

Starter packs: `VALE_DOMESTIC_RESTRAINT`, `KASPAR_INSTITUTIONAL_SURVEILLANCE`, `MERIN_INDUSTRIAL_DECAY`, `ORACLE_BROADCAST_CLEAN`.

See `docs/publication/aesthetic_bible_overview.md` for pack rationale and `schemas/aesthetic_bible.schema.json` for the registry schema.

## Scientific Clean Release / Reviewer Entrypoint

For journal reviewers and reproducibility auditors, the canonical entrypoint is:

```
docs/publication/scientific_clean_release_manifest.md
```

That document describes what is included, what is excluded, validation commands,
the storage doctrine, AI model provenance, and known limitations.

Quick validation:

```bash
python -m pytest -q
python scripts/validate_production_records.py --repo-root .
python scripts/validate_prompt_records.py --repo-root .
```

## Citation

This private repository is the active development/production repository and is
not the archival citation target.

For publication citation, use the public archived release:

```
Babacan, H. (2026). DRMYN Studio: Metadata-Only AI-Assisted Movie Development and
Production Workflow (Version 0.4.6) [Computer software]. Zenodo.
https://doi.org/10.5281/zenodo.20121045
```

Public release repository:
https://github.com/hknbb/drmyn-studio-public/releases/tag/v0.4.6

For machine-readable citation metadata, see [CITATION.cff](CITATION.cff).
For authorship and contribution details, see [AUTHORS.md](AUTHORS.md), [CONTRIBUTORS.md](CONTRIBUTORS.md),
and [docs/publication/contributor_roles.md](docs/publication/contributor_roles.md).

## Archiving

Tagged releases are archived via Zenodo. Metadata is stored in [.zenodo.json](.zenodo.json).

## License

See [LICENSE](LICENSE).
