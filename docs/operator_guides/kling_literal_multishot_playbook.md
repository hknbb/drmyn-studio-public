# Kling Literal Multi-Shot Playbook (text_only, v07)

This is the **current** SC0014 production route. It replaces the Anchor & Animate
(still → contact-sheet → `anchored_i2v`) loop, which is now historical
(`shot_photography_contact_sheet.md`).

## 1. Why

Kling Omni parses **concrete, literal, camera-led** description. The earlier prompts
spoke author-facing prose — abstract metaphor ("protected center", "about to lose"),
role nouns standing in for aliases ("infant"/"mother" instead of `@C08_JIN`/`@C01_NADIA`),
and bare position labels ("center", which Kling reads as a framing command). The model
"thinks" in a different language than the prompt was written in, producing wrong results.

The root cause was that this language lived in the **canonical YAML**, and the renderer
faithfully printed it. So the fix is a data fix, not just a renderer fix.

## 2. The dual-field split

Each manifest/ledger keeps its human-readable poetic fields **and** carries new
model-facing literal `render_*` fields. Under `language_profile: kling_literal_alias_locked`
the renderer prints **only** the `render_*` fields and never the poetic/bookkeeping ones.

| Poetic (human-only, never printed) | Model-facing literal (printed) |
|---|---|
| `shots[].prompt_action`, `performance_note` | `shots[].render_action` |
| `shots[].camera.lens_bias` | `shots[].render_camera` |
| `shots[].diegetic_audio` | `shots[].render_diegetic_audio` |
| `figures[].action`, `role` | `figures[].render_action` |
| `figures[].distinguishing_detail` | `figures[].render_label` (neutral, no role nouns) |
| ledger `entry/exit_state.summary`, `key_positions`, `screen_position` | ledger `render_start_state` / `render_end_state` |

## 3. The grammar (`kling_literal_alias_locked`)

- **Alias-only.** Every subject is an `@alias` (`@C01_NADIA`, `@C08_JIN`, `@LOC001_NURSERY`).
  Never raw names, canonical ids, or role nouns.
- **Camera-led, one move per shot** (`render_camera`: "Medium two-shot, static.").
- **Emotion via physical performance**, never abstraction:
  `@C01_NADIA keeps her face still, eyes lowered to @C08_JIN, jaw tight` — not
  "as if holding something she is about to lose".
- **No bare position labels.** Use literal blocking ("beside the crib", "screen-right"),
  never "center"/"centered".
- **Self-contained shots.** Each shot establishes its own state; the seam (`Start state:`
  from `render_start_state`) is a short literal hint, not relied on.
- **Dialogue** stays inline, alias-tagged, literal: `— @C04_DIMITRI (Flat): "Mrs. Vale."`

### Banlist (validator-enforced when profile is literal)
Raw names · canonical ids (`C01`/`LOC001`) · role nouns
(infant/child/mother/man/woman/baby/enforcer…) · abstract/metaphor
(protected center / about to lose / means something / already elsewhere…) · bare
`center`/`centered`. Each active alias must appear; each character clip must carry ≥1
physical performance cue. `@aliases` and quoted dialogue are masked before the scan.

## 4. Continuity = text_only + optional last-frame seed

- `input_mode: text_only`. Identity rests on Kling Element Library bindings (`@aliases`).
- No 22-still pass, no contact sheets. The anchored triplet
  (`start_frame_ref` / `contact_sheet_ref` / `visual_input_budget`) is **forbidden**
  under `text_only` (validator-enforced).
- Optional `generation_params.continuity_seed_ref`: an *extracted* last-frame, used only
  if the operator provides one. On a cold first pass there is no seed — identity then
  rests fully on Element bindings.

## 5. Operator flow

```
1. Author render_* literal fields in the 8 clip manifests + ledger render seams.
2. python -m scripts.generate_sc0014_v07_text_only
     → 8 prompts/draft/SC0014__omni-...-safe__v07.yaml (text_only, literal)
     → deprecates the v06 still/contact/anchored records + library + map rows
3. python -m scripts.validate_prompt_records      # literal bans enforced
4. In Kling: bind @aliases to Element Library uploads, run each clip as text_only.
```

## 6. Rollout

`kling_literal_alias_locked` is the default grammar for new Kling generation. Every
**active** Kling record must declare a `language_profile`; not-yet-migrated records must
declare `legacy_prose` explicitly (no silent pass). Deprecated records are exempt.
