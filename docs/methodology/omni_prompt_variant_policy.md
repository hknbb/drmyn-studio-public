# Omni Prompt Variant Policy

This document defines the canonical variant and render-pass policy for Kling Omni prompt generation.

## 1) Variant Modes

`variant_mode` enum:

- `safe`
- `creative`
- `aggressive`

Semantics:

- `safe`: conservative direction, reduced stylistic risk, strict source-bound behavior.
- `creative`: controlled atmospheric enrichment while preserving source facts.
- `aggressive`: stronger cinematic expression (camera/style intensity) without inventing new story facts.

## 2) Render Passes

`render_pass` enum:

- `visual_test`
- `performance_test`
- `final_candidate`
- `final_locked`

Pass intent:

- `visual_test`: continuity, identity, camera, and artifact screening.
- `performance_test`: speech/performance validation under audio policy gates.
- `final_candidate`: candidate assembled after successful prior pass notes.
- `final_locked`: human-reviewed final lock state through PR workflow.

## 3) Quality Tiers

`quality_tier` enum:

- `test_720p`
- `final_1080p`

Usage:

- `test_720p` for iteration speed in test passes.
- `final_1080p` only for approved final-candidate path.

## 4) Prompt Count Policy (N-prompting)

Recommended variant set sizes by scene risk:

- Transition scene: `N=3`
- Normal scene: `N=6`
- Critical scene: `N=9`

Dialogue-heavy scenes should run in this order:

1. `visual_test`
2. `performance_test`

Do not run `final_candidate` before pass evidence is recorded.

## 5) Prompt ID and Lifecycle Compliance

Prompt IDs must remain schema-compatible with the existing repository pattern.

Example IDs:

- `SC0001__omni-kling-clip-sc0001-01-safe__v01`
- `SC0001__omni-kling-clip-sc0001-01-creative__v01`
- `SC0001__omni-kling-clip-sc0001-01-aggressive__v01`

Lifecycle policy:

- All generated variants start at `lifecycle_stage: draft`.
- Promotion to `approved`/`locked` remains human-PR-gated.

## 6) Required Metadata in Generation Params

Variant-generated prompt records should include:

- `variant_mode`
- `render_pass`
- `quality_tier`
- `prompt_component_model` (reference path)

## 7) Boundary Rules

- No variant may introduce new characters, events, or story facts.
- Canonical planning IDs must not leak into `prompt_text`.
- `required_element_aliases` must be preserved when present.

## 8) Scope

This is a policy document only.

- No schema changes in this PR.
- No adapter/runtime changes in this PR.
- No prompt regeneration in this PR.
