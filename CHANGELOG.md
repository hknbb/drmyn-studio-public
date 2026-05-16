# Changelog

## v0.16.2-native-audio-dialogue-rendering (2026-05-16)

### Summary

Scientific checkpoint completing the element-first SC0001 production baseline and introducing
readiness-gated Kling Omni 3 native-audio dialogue rendering infrastructure.

### Added

- **Kling Omni guidance snapshot** (`model_guidance_snapshots/kling/20260516T000000Z_kling_omni_video_best_available.yaml`):
  Refreshed and human-verified guidance snapshot. Key addition: verified native-audio
  dialogue syntax — dialogue is in-prompt text only, action-first, `@alias (tone): "line"` format,
  temporal connectors between speakers.
- **`audio_plan` component renderer** in `KlingOmniAdapter.generate_from_clip_manifest()`:
  New helper `_build_audio_plan_component()` inserts dialogue at component position #8.
  When all speaking elements are `native_audio_readiness: ready`, renders verified
  Omni 3 `@alias`-keyed dialogue. When any speaker is blocked, emits exact suppression note.
- **`_strip_screenplay_dialogue()`**: Removes raw `SPEAKER: "..."` screenplay cues from
  `prompt_action` when a shot carries `dialogue_line_ids` (audio_plan owns spoken content).
- **`_load_dialogue_beats_lines()`**: Loads `dialogue_lines[]` from `dialogue_beats.yaml`.
- **Explicit dialogue_line_ids scoping**: When a shot has explicit IDs, those are used exclusively
  (beat-overlap fallback only when no explicit IDs given — prevents split-beat over-inclusion).
- **`omni_prompt_component_model.md`** updated: full `audio_plan` rendering spec, readiness gate,
  suppression note, verified syntax, clip scoping, and action stripping rules.
- **SC0001 SH001 canon record** (`evidence/operator_sessions/OP-PROD-SC0001-SH001-TAKE002-CANON-2026-05-16.yaml`):
  TAKE002 (QC score 88/100) selected as canon over TAKE001 (80/100); locked_metadata_only.
- **SC0001 suppressed-path proof** (`evidence/operator_sessions/OP-PROD-SC0001-DIALOGUE-SUPPRESSED-PATH-2026-05-16.yaml`):
  Dry-run synthesis of CLIP_SC0001_04 confirms suppression note present, zero line text,
  zero canonical ID leak.
- **Perspective QC records** for C01, LOC001, PROP003 perspective packs.
- **GPT Images perspective pack** for PROP003 (`visual_dev/elements/props/PROP003/`).
- **New schemas**: `gpt_images_perspective_pack`, `shot_element_manifest`,
  `perspective_qc_report`, `kling_element_reference_record`.
- **8 new tests** in `TestAudioPlanComponent`: blocked path, ready path, mixed readiness,
  screenplay cue stripping, canonical-ID leak guard, missing beats file, implied-line exclusion,
  explicit line-ID scoping.

### Changed

- `docs/model_guides/kling_omni.yaml`: guide_version 0.2.0 → 0.3.0; added verified
  `native_audio_dialogue_format` rule; updated `snapshot_ref` to 20260516 snapshot.
- `evidence/scene_clip_map.csv`: SC0001 TAKE002 external_storage_ref added.
- `planning/scenes/SC0001/scene_card.yaml`: updated with element-first shot list.

### Validation Evidence

- `python scripts/validate_production_records.py --repo-root .` → 98 files scanned, 98 valid, 0 invalid.
- `python -m pytest -q` → 1408 passed.
- `python scripts/validators/validate_model_research_gate.py --targets kling_omni_video_best_available` → 1/1 passed.

### Policy Confirmation

- No binary image/video/audio outputs committed.
- `repo_binary_committed: false` for all takes; SC0001 TAKE002 stored in external local media.
- No API keys or private local paths in committed files.
- Suppression note contains no raw character names, canonical IDs, or planning aliases.

### Next Step

- C03 Birta full element production → C01/C03 `native_audio_readiness: ready` →
  dialogue-bearing SC0001 prompt generation → full v0.17.0 scene production trial.

## v0.15.3-non-character-perspective-pack-framework (2026-05-13)

### Summary
- Scientific checkpoint after PROD-LINE-15A-8.
- Scope remains documentation-only and metadata-only release hygiene.
- Non-character perspective pack governance now covers wardrobe, prop, and location framework scaffolding.

### Changed
- Added non-character perspective generalization notes for wardrobe, prop, and location workflows.
- Added wardrobe, prop, and location perspective pack doctrine/template scaffolds.
- Added first draft wardrobe perspective pack record for WD001.
- Added first ready draft prop perspective pack record for PROP003.
- Preserved schema-compatible perspective mappings without adding new enums in this release hygiene checkpoint.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 83 files scanned, 83 valid, 0 invalid.
- `python -m pytest -q` -> 1368 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation in this release hygiene PR.
- No schema, validator, or test changes in this release hygiene PR.

### Next Step
- Resume C01 Nadia production work from the checkpoint, or open a dedicated PROD-LINE-15A-8B PR for the first LOCXXX draft perspective-pack record after location intake status reconciliation.

## v0.15.2-identity-evidence-set-metadata-checkpoint (2026-05-13)

### Summary
- Scientific checkpoint after PROD-LINE-15A-3B.
- Scope remains documentation-only and metadata-only release hygiene.
- Stage 2.5 Identity Evidence Set Selection is now machine-validated through schema + validator wiring.

### Changed
- Added formal `identity_evidence_set` metadata contract to the validated production model set.
- Added validator discovery for `visual_dev/elements/characters/*/identity_evidence_sets/*.yaml`.
- Added C01 HOME_MORNING draft scaffold for Stage 3 identity evidence selection.
- Standardized evidence slot semantics: `E01_STAGE1_WINNER`, `E02_STAGE2A_PORTRAIT`, `E03_STAGE2B_FULL_BODY`, `E04_STAGE2C_EXPRESSION_BAND`.
- Added enforcement gates for upload_count consistency, included/excluded_reason coupling, slot-to-source/role matching, look/alias consistency, and pending_external scaffold safety.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 77 files scanned, 77 valid, 0 invalid.
- `python -m pytest -q` -> 1368 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation in this release hygiene PR.
- No schema, validator, or test changes in this release hygiene PR.

### Next Step
- Produce/register actual C01_HOME_MORNING identity evidence external refs, rerun PROD-LINE-15A preflight, and proceed only if READY.

## v0.15.1-identity-exploration-probe-checkpoint (2026-05-13)

### Summary
- Scientific checkpoint after PROD-LINE-15A-2 doctrine correction.
- Scope remains documentation-only and metadata-only.
- Stage 2 prompt doctrine was corrected before C01 operator-side image generation and before real GPT Images 2 external-ref registration write-pass.

### Changed
- Stage 2 `Reference Sheet Prompt` workflow removed from operator doctrine/prompt-kit materials.
- Stage 2 replaced with `Identity Exploration 2 / Single-Image Variant Probe`.
- Stage 2 standardized to Midjourney V7 with `--oref` and `--ow 100`.
- Explicit guardrail documented: do not combine `--v 8.1` with `--oref`.
- Positive prompt sheet/layout language removed from Stage 2 prompt bodies.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation.
- No schema, validator, or test changes.

### Next Step
- Produce C01 GPT Images 2 outputs externally (`C01_HOME_MORNING`) and rerun PROD-LINE-15A preflight before any write-pass.

## v0.15.0-character-visual-prompt-kit-checkpoint (2026-05-12)

### Summary
- Scientific checkpoint for PROD-LINE-15A-0 and PROD-LINE-15A-1.
- Scope is documentation-only and metadata-only, before real GPT Images 2 external-ref registration.

### Added
- Character visual prompt kit doctrine guide.
- Character visual prompt kits for C01, C02, C03, C04, C05.
- Reusable character visual prompt kit template.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation.

### Next Step
- PROD-LINE-15A write-pass after real C01 GPT Images 2 perspective outputs are available externally and preflight is READY.
## v0.14.0-continuity-alias-checkpoint (2026-05-12)

### Summary
- Scientific checkpoint for PROD-LINE-14A through PROD-LINE-14H.
- Scope is metadata-only governance architecture before PROD-LINE-15 external-output registration.

### Added
- Look-specific Kling element alias architecture and records (`kling_character_look_element`).
- Scene-to-Kling alias resolver and operator hint report export.
- Operator guide append for Omni alias usage rule (`@C##_LOOK_ROLE`).

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.

### Next Step
- PROD-LINE-15A: C01 GPT Images 2 real external-ref registration preflight (look-target aware).
