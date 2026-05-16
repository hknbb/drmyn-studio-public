# Kling Omni Cinematic Prompting Guide (Repo-Aligned)

## 1. Scope and validation level

This guide replaces uncontrolled single-prompt generation for long-form work with a controlled chain:

`scene -> clip -> shot -> element -> prompt variant -> QC`

This is an operator guide. It does not perform runtime API calls. It follows the repository's metadata-only doctrine.

## 2. Omni baseline realities

- Shot-first design: one shot = one primary action.
- Duration band: keep each clip in the 3-15 second range.
- Native Audio is a separate pass and must not be mixed with visual validation.

## 3. Repo-aligned working method

Use this mapping:

- instead of `preprod/`: use `source/` + `planning/`
- instead of `elements/`: use `visual_dev/elements/` + `visual_dev/omni_sets/`
- instead of generic `prompts/`: use `prompts/draft/`, `prompts/review/`, `prompts/approved/`, `prompts/locked/`
- instead of `renders/`: use `evidence/prompt_runs/` + external storage references
- instead of `qc/`: use `evidence/omni_qc/` (or `evidence/take_reviews/`)

Do not introduce binary output folders like `renders/tests` or `renders/finals` inside this repository.

## 4. Cinematic prompt architecture

Core rule set:

- Every clip is defined by an `omni_clip_manifest`.
- `shots[]` must keep camera/lighting/motion explicit and reviewable.
- Preserve `required_element_ids -> element_bindings -> @Alias` consistency.

## 5. Master cinematic template (repo language)

Render each prompt from this component order:

1. Goal
2. Duration format
3. Scene context
4. Active elements
5. Shot plan
6. Action timeline
7. Camera grammar
8. Audio plan
9. Negative constraints
10. Style/color
11. Expected outcome
12. Retry rule

## 6. Cinematic Prompter note

Prompting is not free-form prose writing. Component order must remain stable.

- Safe: conservative direction
- Creative: controlled atmospheric enrichment
- Aggressive: stronger cinematic expression while remaining source-bounded

## 7. Variant and pass logic

Render pass split:

- `visual_test`: audio-off by default, focus on camera/identity/continuity
- `performance_test`: audio only with ready speaker bindings
- `final_candidate`: selected candidate after prior pass evidence
- `final_locked`: final lock only through human PR approval

## 8. Troubleshooting matrix (summary)

Typical issues and one-variable retry rule:

- Identity drift -> strengthen element alias use and constraints
- Camera instability -> reduce motion intensity
- Lighting inconsistency -> make lighting source/quality explicit
- Unwanted speech -> audio off or stricter dialogue constraints

Change only one variable per retry.

## 9. Fast execution recipe

1. Finalize scene beat plan.
2. Build clip manifest (3-15s).
3. Generate Safe/Creative/Aggressive draft prompts.
4. Do not proceed to performance pass before visual test passes.
5. Record retry rules in QC metadata.
6. Lock final choice via human PR review.

## 10. Short brief form

- Scene ID:
- Clip ID:
- Primary action:
- Required elements:
- Camera intent:
- Lighting intent:
- Audio requirement:
- Risk (drift/artifact):
- Next pass objective:

## 11. Long-form pipeline note

Long-form scale comes from:

- Scene-based planning
- Clip-based prompt packaging
- Shot-based QC feedback

Single uncontrolled prompts reduce quality and reviewability.

## 12. Official docs vs field practice

- Official model limits/rules: `docs/model_guides/kling_omni.yaml`
- Field tactics: experimental, not absolute rules

Do not treat forum/community heuristics as official constraints.

## 13. Storage doctrine

Repository remains metadata-only. Media files live in external storage.

Preferred reference types:

- `external_storage_ref`
- `platform_asset_ref`
- `local://`
- `gdrive://`
- `kling://`
