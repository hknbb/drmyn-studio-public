# DRMYN Studio — Metadata-Only AI-Assisted Movie Development and Production Workflow

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20534124.svg)](https://doi.org/10.5281/zenodo.20534124)
[![GitHub release](https://img.shields.io/github/v/release/hknbb/drmynstudio-public)](https://github.com/hknbb/drmynstudio-public/releases/tag/v0.18.0)

This repository contains the canonical source records, planning metadata, prompt-governance, validation, and reproducibility infrastructure for **DRMYN Studio**, demonstrated through the *Closing Price* AI-assisted film project.

> **v0.18.0 — Scene Continuity System (Kling 3.0 Omni / O3).** This release adds a deterministic
> beat→clip packer, an inter-clip continuity ledger (camera/action/screen-direction hand-off), an
> anti-clone figure roster (one distinct on-screen figure per `@alias`), a four-view scale-angle
> character reference policy with full-body look sheets, a local-only media archive, and a single
> canonical clip-manifest prompt path. See
> [`docs/methodology/scene_continuity_system.md`](docs/methodology/scene_continuity_system.md).

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
| `source/` | Canonical human-authored source files (screenplay) |
| `planning/` | Scene cards, beat plans, dialogue beats, continuity ledgers, character/location/prop/wardrobe sheets |
| `prompts/` | Prompt lifecycle and library |
| `schemas/` | JSON Schemas for machine validation (draft 2020-12) |
| `scripts/` | Validation, packer, archive, and pipeline scripts (`scripts/validators/` holds per-record semantic validators) |
| `visual_dev/` | Element reference records and per-scene Omni sets (metadata only; no committed binaries) |
| `model_guidance_snapshots/` | Per-model capability/prompt-rule snapshots the engine reads (version-agnostic) |
| `evidence/` | QC reports, operator sessions, local media indices, maps, and validation reports |
| `archive/` | **Local-only** (git-ignored) externally-produced image/video binaries filed by `scripts/archive_media.py` |
| `.github/` | GitHub-native governance and CI files |
| `docs/` | Human-readable workflow, methodology, and policy documentation |

### Scene Continuity System (v0.18.0)

The canonical Kling Omni (O3) pipeline:

```
screenplay → scene_beat_plan → dialogue_beats → omni_clip_planner
  → omni_clip_plan + clip manifests (CLIP = one ≤15s / ≤6-shot Omni job; shots[] = intra-clip)
  → scene_continuity_ledger (inter-clip camera/action/screen-direction hand-off)
  → figures[] roster (anti-clone: one figure → one @alias)
  → KlingOmniAdapter.generate_from_clip_manifest() → O3 multi-shot prompt
  → external Kling generation → video_takes → selected_take
```

Character references use the `four_view_scale_angle_v3` policy (full-body front, three-quarter waist,
close portrait front, profile) plus a `character_look_sheet` (full-body build + head-to-toe wardrobe).
Locations require a wide cinematic master with actor-blocking space. Semantic validators live in
`scripts/validators/` (continuity ledger, figure roster, status consistency, clip manifest, location framing).

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
