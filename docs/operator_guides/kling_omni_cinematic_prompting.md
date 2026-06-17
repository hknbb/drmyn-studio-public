# Kling Omni Cinematic Prompting Guide (Repo-Aligned)

## 1. Scope and validation level

This guide replaces uncontrolled single-prompt generation for long-form work with a controlled chain:

`scene -> clip -> shot -> element -> prompt variant -> QC`

This is an operator guide. It does not perform runtime API calls. It follows the repository's metadata-only doctrine.

## 2. Omni baseline realities

- Shot-first design: one shot = one primary action.
- Duration band: keep each clip at 15 seconds or less, with no more than 6 shots.
- Repo-authored shots may be 2-15 seconds. Use 2-4 second cutaways/close-ups for reaction, reveal, prop, or pressure beats; use a single long static shot only when the scene explicitly needs a long take.
- Native audio is written inline in prompt text when used, but visual-test prompts should keep audio disabled until identity/camera/continuity pass.

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
- `shots[]` keep camera/lighting/motion explicit and reviewable **in the manifest** (for QC);
  the prompt itself reads as director's prose, not telemetry.
- Render shot blocks **Goro-style, timecode-first**:
  `[MM:SS - MM:SS] <Framing label>: <action + @Element + performance>. <camera sentence>. Audio: <diegetic cue>. — @Alias (tone): "line"`.
  No `Shot N (Xs):` prefix; no added "Cut to" (the timecode block is the cut). Framing label
  is chosen from `coverage_role` (Insert / Cutaway / Reverse angle) then `camera.framing`.
- **Coverage over duplication:** cover a long beat with *distinct* shots (establish → reaction/insert
  → reverse → resolve), each with its own `framing`/`focus_alias`/`performance_note`/`diegetic_audio`.
  Never split one hold into two identical same-framing shots.
- **Dialogue:** put the speaker's verbatim `line_text` inline in the speaking shot as
  `— @Alias (tone): "…"` (tone from `delivery_note`; sequence with "Immediately,"). It always
  appears as on-screen text; the audio gate (`render_pass`, `native_audio_readiness`) only controls
  whether spoken **voice** is generated. `validate_dialogue_coverage` fails the build if a required
  line is never assigned to a shot.
- **Carried-state anchor (continuity chain):** open every shot by restating where each
  subject/prop is as it begins — the prior shot's settled end — **before** the new action, so
  positions don't reset at the cut. Author `shots[].entry_state` / `exit_state` (rich
  `world_state` with `@alias` subjects + `posture`/`relation`/`visibility` + `props_state`),
  chained `exit_state(N) == entry_state(N+1)` and matched to the `scene_continuity_ledger` at the
  clip seam. The renderer prints it as the shot's opening clause.
- **One action per character:** in any shot with ≥2 on-frame figures (or dialogue), give each
  figure its own `figures[].action` clause (bind to the `@alias`, avoid pronouns); keep
  `prompt_action` environment-only. State non-contact explicitly around a protected subject.
- **Budget:** the 2500-char API cap is render_pass-aware — a warning on `visual_test`, **fatal**
  on `final_candidate`/`final_locked`. `validate_state_chain` (incl. render-aware checks) guards
  the chain and per-figure action.
- Keep ordinary `short_insert` beats merged, but mark load-bearing cutaways with
  `standalone_insert: true` so they render as explicit 2 second shots.
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
2. Build clip manifest (<=15s, <=6 shots).
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
