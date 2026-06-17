# Scene Continuity System (Production System v2)

End-to-end method for producing Kling Omni (O3) scenes with reliable multi-shot
continuity and no character-clone artifacts. This is the canonical path; new scenes
follow it from the start.

## Canonical pipeline

```
screenplay
  → scene_beat_plan.yaml        (semantic beats; optional figures[] per beat)
  → dialogue_beats.yaml         (lines mapped to beats + speaker @aliases)
  → omni_clip_planner.py        (deterministic packer: beats → shots → clips)
  → omni_clip_plan.yaml + manifests/CLIP_*.yaml   (CLIP = one Kling Omni job, ≤15s, ≤6 shots)
  → scene_continuity_ledger.yaml (inter-clip hand-off: camera + action + screen direction)
  → KlingOmniAdapter.generate_from_clip_manifest()  → O3 multi-shot prompt
  → external Kling generation → video_takes → selected_take → scene_clip_map.csv
```

- **Multi-shot WITHIN a clip** = `omni_clip_manifest.shots[]` (one Kling generation).
- **Continuity BETWEEN clips** = `scene_continuity_ledger.clip_chain[]`.

## Kling Omni (O3) multi-shot prompt rules

Calibrated to the official Kling VIDEO 3.0 Omni guide (see
`model_guidance_snapshots/kling/…_kling_omni_video_best_available.yaml`):

- Single generation: **≤ 6 shots (cuts), ≤ 15s total**; repo-authored shots may be **2–15s**. Use 2–4s cutaways/close-ups for reaction, reveal, prop, or pressure beats; reserve one long take only when the beat truly needs continuous performance.
- **Goro-style timecode-first blocks** (calibrated to the official VIDEO 3.0 Omni examples + the user-supplied reference prompt). Each shot is:
  `[MM:SS - MM:SS] <Framing label>: <action + @Element + performance>. <natural camera sentence>. Audio: <diegetic cue>. — @Alias (tone): "verbatim line"`
  - **No `Shot N (Xs):` prefix and no added "Cut to"** — the timecode block *is* the cut.
  - Framing label comes from `coverage_role` first (so a reaction reads "Cutaway", a detail "Insert", a reverse "Reverse angle"), else from `camera.framing` ("Wide shot", "Medium shot", "Close-up", …).
  - Camera/movement/lens and `performance_note` are **woven into prose**, never dumped as `Camera:/Lighting:/Motion: subject 0.1` telemetry. Numeric intensities and structured camera/lighting/motion stay in the manifest for QC only.
  - `diegetic_audio` renders as a per-shot `Audio:` line (non-speech sound design); thread continuity ("continues", "softens").
- **Coverage, not same-frame splits (director pass).** A long beat is covered by **distinct** shots — establish → reaction/insert → reverse → resolve, with `focus_alias` choosing each shot's subject — authored in `omni_clip_manifest.shots[]` (or hinted on the beat). The deterministic packer no longer fabricates two identical wide shots from one hold; coverage is an authored, human-PR-gated decision that adds **no new story facts**.
- **Dialogue is verbatim, alias-tagged, and decoupled from audio.** The speaker's exact `line_text` renders inline in the speaking shot as `— @Alias (tone): "…"` (sequenced with "Immediately,"). This is **always** present as on-screen dialogue text; `native_audio_readiness`/`render_pass` only gate whether Kling also generates spoken **voice** (`audio_gate_status`), never whether the text appears. Enforced by `validate_dialogue_coverage` (every `dialogue_required`, non-`implied` line whose beat is covered must be assigned to exactly one shot).
- **Positions chain across cuts (entry/exit state).** Each shot opens by restating the
  carried world state — who/what is where as the shot begins (the prior shot's settled
  end) — **before** the new action, so Kling keeps positions instead of resetting them at
  the cut. Authored in `omni_clip_manifest.shots[].entry_state` / `exit_state` (a rich
  `world_state`: `summary`, `key_positions{subject @alias, screen_position, posture,
  relation, gaze_target, visibility}`, `props_state`), chained so `exit_state(N) ==
  entry_state(N+1)` within a clip and matching the `scene_continuity_ledger` entry/exit at
  the **clip seam**. Subjects in prompt-facing state are `@alias` only (canonical ids stay
  in `figures[].base_element_id`). The renderer prints the carried state as the shot's
  opening clause.
- **One action per character (multi-figure disambiguation).** In a shot with ≥2 on-frame
  figures (or any dialogue), each figure carries its own `shots[].figures[].action` clause
  so the model never confuses who does what (Kling/FAL.ai: bind the action to a unique
  `@alias`, avoid pronouns); `prompt_action` stays environment-only. Around a protected
  subject, the action states non-contact explicitly (e.g. "does not touch @C08_JIN").
- Enforced by `validate_state_chain` (`ENTRY_STATE_MISSING_AFTER_FIRST_SHOT`,
  `SHOT_EXIT_STATE_MISSING`, `CARRIED_SUBJECT_DROPPED`, `CARRIED_PROP_DROPPED`,
  `RELATION_BROKEN_WITHOUT_ACTION`, `CLIP_SEAM_MISMATCH`, `FIGURE_ACTION_MISSING`,
  `DIALOGUE_SPEAKER_NOT_ON_FRAME_OR_OFFSCREEN_MARKED`, plus render-aware
  `PROMPT_RENDER_OMITS_ENTRY_STATE` / `PROMPT_RENDER_OMITS_FIGURE_ACTION` via the adapter's
  pure `render_prompt_text_only`). The 2500-char API cap is render_pass-aware: a warning on
  `visual_test`, fatal on `final_candidate`/`final_locked`.
- **Describe action and camera, not appearance** — identity/wardrobe/look are carried by the attached `@elements`.
- `short_insert` beats merge into neighboring action by default. Mark `standalone_insert: true`
  only for load-bearing 2s cutaways such as a prop reveal, reaction detail, or irreversible state
  change that must be reviewed as its own camera beat.
- Enforced by `validate_omni_clip_manifest` (≤6 shots, sum==total), `validate_dialogue_coverage` (no dropped line), and the golden test `tests/agents/test_prompt_golden_format.py`.

## Anti-clone: one figure ⇒ one alias

Kling collapses two distinct figures sharing a description into one (or clones them).
Rule: **every distinct on-screen figure gets its own `@alias`.** A base character (e.g.
C10) appearing as two figures uses two aliases (`@C10_HOLDER`, `@C10_CARRIER`), each
with a `distinguishing_detail`.

- Authored in `scene_beat_plan.source_beats[].figures[]` / `omni_clip_manifest.shots[].figures[]`.
- Enforced by `scripts/validators/validate_figure_roster.py` (one alias ↔ one figure/role;
  distinct aliases for same base; aliases must be bound; no alias reused in a shot).
- The adapter attaches figure aliases directly (never collapsed by element_id), and the
  prompt enumerates the exact figures + a "no additional/duplicated people" negative.

## Inter-clip continuity ledger

`scene_continuity_ledger.yaml` chains the scene's clips in order and declares each clip's
`entry_state` / `exit_state` (summary, key_positions, props_state, action_state,
camera_state, screen_direction). `validate_scene_continuity_ledger.py` checks the chain
matches the clip plan and that screen direction / shared-subject positions stay continuous
across each cut (180-degree rule). The adapter injects this hand-off into the prompt
("Continue from previous clip…", "End state for next clip…").

## Element references: four-view scale+angle (v3) + look sheet

- Character hero = **Midjourney 8.1**; 4-view expansion + all non-character elements = **ChatGPT Images 2**.
- `gpt_images_perspective_pack` policy **`four_view_scale_angle_v3`**: `full_body_front`,
  `three_quarter_waist`, `close_portrait_front`, `profile_full` — scale ladder + profile for a
  3D identity lock that does not crop. (`perspective_qc_report` and
  `kling_element_reference_record` accept these names; QC already accepts 3 or 4 views.)
- **`character_look_sheet`** captures full-body build/height/physical + head-to-toe wardrobe
  (top, bottom, footwear, outerwear, accessories) + palette, so scale views never invent or crop garments.

## Locations: cinematic width

ChatGPT Images 2 rooms tend to render narrow/box-like. Location packs must include a WIDE
establishing prompt at **16:9 or 2.39:1** with depth/lens cues and explicit **actor blocking /
coverage space** (floor + negative space). Soft-checked by
`scripts/validators/validate_location_framing.py`.

## Local media archive (local-only)

External image/video binaries are filed by `scripts/archive_media.py` into a git-ignored
`archive/<project>/<scene|_elements>/<element>/stage{1,2,3}/{images|video}/…` tree and
registered in a metadata-only `local_media_index` under `evidence/`. Binaries are never
committed (`repo_binary_committed: false`).

## Non-destructive versioning

Change = new `V00N`; the old record is **not deleted** — set `status: deprecated`, add a
`continuity_note`, and (where the schema allows) a `superseded_by` pointer.

## Model guidance

The engine reads model capabilities/rules from the model guidance snapshot; it is
version-agnostic. Current model: **Kling 3.0 Omni / O3**. Update the snapshot (not the
adapter) when the model changes.

## Status / open items

- Prompt generation is canonical via `generate_from_clip_manifest`. New Kling prompt work must be
  driven by `omni_clip_manifest` records, not storyboard options or `shot_list_omni` gates. Some
  legacy hooks may remain for older artifacts, but they must not control new Kling prompt generation.
  The `KlingOmniAdapter.generate()` method is retained as the shared adapter contract; build new
  scenes on the clip-manifest path only.
- Scene teardown + rebuild of SC0001/SC0014 under this system is a separate, operator-gated step
  (irreversible deletes; requires operator-produced media + real QC scores).
