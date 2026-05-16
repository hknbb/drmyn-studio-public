# Kling Native Audio Pass Policy

This document defines pass-level Native Audio behavior for Kling Omni prompt workflows.

## 1) Pass Types

`render_pass` values:

- `visual_test`
- `performance_test`
- `final_candidate`
- `final_locked`

## 2) Native Audio Policy by Pass

### visual_test

- `native_audio.enabled = false` (default)
- Dialogue is represented as metadata intent only
- Primary focus: identity consistency, continuity, camera/lighting stability, artifact detection

### performance_test

- `native_audio.enabled = true` only if all speaking character bindings are audio-ready
- Prefer one speaking character focus per shot
- Keep dialogue short and source-grounded

### final_candidate

- Native Audio may be enabled only after successful `visual_test` and `performance_test` evidence
- Uses selected policy profile from prior pass outcomes

### final_locked

- Requires human PR approval
- Lock decision references pass evidence and policy compliance

## 3) Audio Readiness Gate

For passes that can carry live audio (`performance_test`, `final_candidate`, `final_locked`):

- Every speaking character must have binding-level readiness marked `ready`
- If readiness is not met, generation is blocked or downgraded according to adapter enforcement mode

Recommended adapter behavior:

- strict mode: raise adapter error and block generation
- permissive draft mode: emit warning and set an explicit blocked gate flag in generation params

## 4) Required Evidence Before Audio Promotion

Before promoting from `visual_test` to audio-enabled passes, reviewers should have:

- continuity/identity check status
- camera stability and motion artifact notes
- dialogue intent confirmation against source beats
- a one-variable-only retry record for any failed check

## 5) Metadata Expectations

Prompt/run metadata should record:

- `render_pass`
- Native Audio enabled state
- Gate status (`allowed` / `blocked`)
- Blocking reason when blocked

QC evidence should record:

- speech quality
- lip-sync/performance risk
- unwanted speech artifacts
- retry rule (one variable only)

## 6) Boundary Rules

- Native Audio policy never permits story invention.
- Audio convenience must not override source-grounded continuity constraints.
- Human PR review remains the only lock boundary for final outputs.

## 7) Scope

This is a policy document only.

- No schema changes in this PR
- No adapter/runtime changes in this PR
- No prompt regeneration in this PR
