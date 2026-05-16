# Omni Prompt Component Model

This document defines how Kling Omni `prompt_text` is composed from structured components rather than free-form single-block text.

## Canonical component order

1. `goal`
2. `duration_format`
3. `scene_context`
4. `active_elements`
5. `shot_plan`
6. `action_timeline`
7. `camera_grammar`
8. `audio_plan`
9. `negative_constraints`
10. `style_color`
11. `expected_outcome`
12. `retry_rule`

## Component to source mapping

- `goal` -> `planning/scenes/SC####/scene_card.yaml` (`purpose`) + beat role
- `duration_format` -> `planning/scenes/SC####/manifests/*_manifest.yaml` (`total_duration_seconds`)
- `scene_context` -> `scene_card` + `planning/locations/*.yaml`
- `active_elements` -> `visual_dev/omni_sets/SC####/element_bindings.yaml` + `required_element_ids`
- `shot_plan` -> `omni_clip_manifest.shots[]`
- `action_timeline` -> `shots[].duration_seconds` + `shots[].prompt_action`
- `camera_grammar` -> `shots[].camera`
- `audio_plan` -> `kling_native_audio` + `planning/scenes/SC####/dialogue_beats.yaml`
- `negative_constraints` -> model-guide defaults + prompt record negative constraints
- `style_color` -> `planning/aesthetic_bible.yaml` + shot lighting
- `expected_outcome` -> `prompt_record.expected_output`
- `retry_rule` -> QC record or next-pass note

## Rendering rule

The adapter renders `prompt_text` in this fixed order. Component ordering is not randomized.

## audio_plan component (position #8)

The `audio_plan` component renders Kling Omni 3 native-audio dialogue inline in `prompt_text`. There is no separate audio/voice API parameter — dialogue is injected as structured text that the model converts into synchronized speech and lip movement.

### Source data

- `planning/scenes/SC####/dialogue_beats.yaml` → `dialogue_lines[]`
- `visual_dev/omni_sets/SC####/element_bindings.yaml` → `native_audio_readiness` per element

### Readiness gate

Before rendering any dialogue line text, the adapter checks every speaking element referenced in the clip's shots against `native_audio_readiness` in `element_bindings.yaml`:

- If **all** speaking elements are `native_audio_readiness: ready` → render in verified Omni 3 syntax (see below).
- If **any** speaking element is not `ready` → emit the suppression note and omit all line text:

```
Audio plan suppressed: one or more speaking elements are not native_audio_readiness: ready. Dialogue line text omitted from prompt_text.
```

The suppression note must not contain raw character names, canonical IDs (C01, C03), or planning aliases.

### Verified Omni 3 native-audio dialogue syntax (source: `docs/model_guides/kling_omni.yaml` rule `native_audio_dialogue_format`)

- Write each spoken line **action-first**: physical action sentence → speaker clause (`@alias (tone)`) → quoted line.
- Tag every line with the character's Kling element `@alias`, optionally followed by a parenthesised tone/delivery descriptor derived from `delivery_note`.
- Place a temporal connector (`Immediately,`) between consecutive speakers so the model does not merge speech.
- Skip lines where `line_type: implied` (these are subtext only, not rendered audio).
- Prepend the block with `Audio plan: `.

Example:
```
Audio plan: @Nadia (controlled, low voice): "I slept." Immediately, @Birta (warm, knowing tone): "You slept the way you fold laundry."
```

### Clip scoping

Only lines whose `target_beat_id` overlaps the shot's `source_beat_ids`, or whose `line_id` appears in the shot's `dialogue_line_ids`, are included in the clip's `audio_plan`. Lines from other beats in the same `dialogue_beats.yaml` are excluded.

### Action component stripping

When a shot carries `dialogue_line_ids`, raw screenplay cues in `prompt_action` (e.g. `NADIA: "..."`) are stripped before the shot text is rendered. The `audio_plan` component owns all spoken content; the action component covers physical movement only.

## Policy constraints

- Canonical planning IDs must not leak into `prompt_text`.
- `required_element_aliases` must be preserved and visible in prompt text.
- Apply hard guard when prompt character limits are exceeded.
- Do not invent new story facts.

## Variant compatibility

The same component skeleton must work across:

- `safe`
- `creative`
- `aggressive`

Variants may change expression intensity, not source-grounded facts.
