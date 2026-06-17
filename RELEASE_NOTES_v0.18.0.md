# DRMYN Studio v0.18.0 — Public Methodology Checkpoint

**Release date:** 2026-06-17
**Tag:** `v0.18.0-kling-literal-multishot-pipeline`
**Zenodo DOI:** _pending mint_

---

## Summary

This checkpoint introduces the **Kling Literal Multi-Shot Pipeline**, a principled
production-language architecture for AI video generation that enforces a strict separation
between human-readable narrative prose and model-facing literal prompts. It also records
the first complete evidence set from the M5 Element Production phase, where the Element
Reference Policy v2 (introduced in v0.17.0) was applied to real characters, locations,
and props through the full operator-generation-QC-binding chain.

---

## Changes

### 1. Kling Literal Multi-Shot Pipeline (`kling_literal_alias_locked`)

The core problem solved here: AI video generators (Kling Omni) fail when prompt text
carries narrative abstractions ("as if holding something she is about to lose"), role
nouns that create new subjects ("infant", "mother"), or bare positional labels
("center") that get misread as framing commands. The root cause was that this language
was authored into canonical YAML records, not added by the renderer — so fixing the
renderer was the wrong lever.

**Solution — dual-field split:**
- Existing poetic/bookkeeping fields (`action`, `role`, `performance_note`,
  `screen_position`, `summary`) remain in records for human use and are **never**
  sent to the model under `kling_literal_alias_locked`.
- New `render_*` fields (`render_action`, `render_camera`, `render_diegetic_audio`,
  `render_label`) carry only literal, camera-led, alias-locked text. The renderer
  emits exactly these fields and nothing else.

**Validator-enforced grammar** (gated by `language_profile: kling_literal_alias_locked`):
- **Role-noun ban**: "infant", "child", "mother", "man", "woman", "baby", "enforcer"
  and similar create duplicate subjects in Kling — forbidden in model-facing text.
- **Metaphor/abstract ban**: poetic language that describes emotional meaning rather
  than physical action is blocked.
- **Bare-center ban**: `center`/`centered` as bare positional labels are blocked
  (left/right framing in thirds is allowed).
- **Alias-present check**: every active `@ALIAS` must appear in the `render_action`
  field for its clip.
- **Physical performance cue required**: when a `@C…` character alias is active,
  at least one literal physical action must be present in model-facing text.
- **`anchored_i2v` triplet forbidden under `text_only`**: `start_frame_ref`,
  `contact_sheet_ref`, `visual_input_budget` are blocked when `input_mode: text_only`;
  only `continuity_seed_ref` (extracted last-frame) is permitted.
- **`language_profile` required**: every active Kling Omni prompt record must declare
  a `language_profile`; records without one fail validation.

**Aliases and quoted dialogue are masked before ban scans** so that `@C01_NADIA`
tokens and in-dialogue occurrences of banned words do not trigger false positives.

**Legacy records** are backfilled with `language_profile: legacy_prose` in the same
migration; the validator emits a migration report listing them as a known backlog
without failing CI.

**Anchor & Animate (v06) retired:** the prior SC0014 route (22 designed stills →
8 contact sheets → `anchored_i2v`) is marked deprecated/historical. The
`text_only` literal multi-shot route with an optional last-frame seed is the new
canonical production default for all scenes.

### 2. Schema Extensions (all additive)

| Schema | Change |
|--------|--------|
| `prompt_record.schema.json` | Added `language_profile` enum; `continuity_seed_ref`; hard ban on `anchored_i2v` triplet under `text_only` |
| `omni_clip_manifest.schema.json` | Added `render_action`, `render_camera`, `render_diegetic_audio` (shot-level); `render_action`, `render_label` (figure-level) |
| `scene_continuity_ledger.schema.json` | Added `render_start_state`, `render_end_state` (alias-only seam fields) |
| `extracted_frame_reference.schema.json` | New — last-frame continuity seed reference |
| `image_selection.schema.json` | New — per-element perspective QC selection record |
| `golden_reference_plan.schema.json` | New |
| `omni_set_gate.schema.json` | New |
| `shot_list_omni_suggestion.schema.json` | New |
| `system_character_element.schema.json` | New |

All existing schemas remain backwards-compatible: no required-field additions,
no enum removals, no breaking changes.

### 3. New Validator: `validate_prompt_records.py`

Standalone strict validator for Kling Omni prompt records. Gated by `language_profile`:
only `kling_literal_alias_locked` records are subject to the full ban suite. Runs
independently of the production record validator and is CI-integrated. Emits a
`legacy_prose` migration report listing records that need to be ported to the new
profile.

### 4. New Validators (production governance)

- `validate_continuity_presence.py` — checks that `render_start_state`/`render_end_state` seams are populated
- `validate_dialogue_coverage.py` — dialogue/audio coverage completeness
- `validate_figure_roster.py` — every figure alias in a clip has a binding
- `validate_location_framing.py` — location framing constraints
- `validate_omni_clip_manifest.py` — manifest structural integrity
- `validate_scene_continuity_ledger.py` — ledger completeness
- `validate_scene_status_consistency.py` — scene status cross-file consistency
- `validate_shot_still_coverage.py` — updated: deprecated still/contact records are excluded from coverage checks; explicit early-skip when scene's active Kling route is `text_only`
- `validate_state_chain.py` — render-field state chain integrity

### 5. Agent Updates

- `scripts/agents/adapters/kling_omni.py` — `kling_literal_alias_locked` render path;
  6-shot / 2500-char guards; `legacy_prose` path unchanged.
- `scripts/agents/run_pipeline.py` — v07 route (`text_only`, `kling_literal_alias_locked`);
  idempotent `prompt_library.yaml` and `scene_prompt_map.csv` upsert.
- `scripts/archive_media.py` — binary archival tool writing metadata-only index entries.
- `scripts/update_project_state.py` — cross-session dashboard auto-update hook.
- `scripts/agents/omni_clip_planner.py`, `omni_set_gate.py` — Kling Omni clip planning agents.

### 6. Cross-CLI Session Memory Architecture

`AGENTS.md` formalises the session memory contract used across Claude Code, Codex CLI,
and Gemini Code Assist:
- `PROJECT_STATE.md` is the single living dashboard (read first, update after every
  promotion/lock/stage completion).
- Operator command vocabulary: `yes` / `no` / `revise` / `switch`.
- Non-negotiable invariants: no binaries committed, no lifecycle promotion without
  human PR, controlled model guidance via Research Snapshot, draft-only agent output.
- `evidence/agent_handoffs/HO-*.yaml` schema for cross-agent task handoff.

### 7. Operator Guide: Kling Literal Multi-Shot Playbook

`docs/operator_guides/kling_literal_multishot_playbook.md` — complete operator reference:
- Grammar rules: camera-led, alias-only, one move per shot, emotion via physical
  performance.
- Ban-list table with examples (before/after).
- Dual-field convention: which fields are human-only vs model-facing.
- Optional last-frame seed protocol (`continuity_seed_ref`).
- `shot_photography_contact_sheet.md` marked historical/deprecated for SC0014.

---

## Validation Evidence

- `python scripts/validate_production_records.py --repo-root .` → 150 files scanned, 0 invalid.
- `python scripts/validate_prompt_records.py --repo-root .` → 55 files validated, 0 invalid.
- `python -m pytest -q` → **1520 passed, 3 skipped** (vs 1441 in v0.17.0).
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` → 3/3 passed.

---

## Policy Confirmation

- No binary image/video/audio outputs committed.
- No screenplay content, scene descriptions, character descriptions, or story content
  included — all content paths are excluded from the public sync.
- No personal data beyond already-public ORCID identifiers and affiliations.
- No API keys, tokens, or credentials in any committed file.
- No real external reference URLs (CDN links, storage service URLs) in methodology files;
  all such URLs live in production content paths that are excluded from the public sync.
- All schema changes strictly additive.
- Lifecycle promotions are human-PR-gated; agent writes to allowed draft/metadata paths
  only.

---

## Next Steps

- SC0047/SC0089/SC0111 Kling Omni clip plan using the v07 text-only literal route.
- PR-BATCH-KEYCHAR-1: C03 Birta + C05 Marcus character element pipeline.
- C07 Sera + Halo Unit element production.
- SC0014 v07 video take QC (8 clips archived, operator review pending).
