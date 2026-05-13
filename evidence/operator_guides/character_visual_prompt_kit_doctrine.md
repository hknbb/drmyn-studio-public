# Character Visual Prompt Kit Doctrine (PROD-LINE-15A-0)

This guide defines the operator-facing prompt artifact doctrine for character visual lock workflows.

Authority note:
- Primary continuity authority remains [character_identity_and_look_continuity.md](character_identity_and_look_continuity.md).
- This document does not override that guide. It operationalizes it into copy-paste prompt stages.

## Scope
- Characters: C01, C02, C03, C04, C05
- Canon window for look-lock usage: SC0001-SC0009 (KNOWN canon)
- Stage context: pre-PROD-LINE-15A external-ref registration write pass

## Five-Stage Pipeline

### Stage 1 - Identity Exploration Prompt (Midjourney)
Goal: discover a stable identity source before wardrobe-specific lock attempts.

Output intent:
- One candidate identity direction for the character
- Face geometry, silhouette, expression band, and age read
- No heavy look-specific styling dependency

Midjourney parameter tail standard:
- `--v 8.1 --raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --no text logo watermark`

### Stage 2 - Identity Exploration 2 (Midjourney V7 + Omni Reference)
Goal: deepen identity confidence by generating three single-image variant probes from the Stage 1 winner, without producing a sheet or panel layout.

Output intent:
- Three separately-run single-frame images per character (2A portrait, 2B full body, 2C expression band)
- Identity anchor band (face geometry, silhouette, expression range) confirmed across independent frames
- Still metadata-facing, not final scene output

Midjourney parameter tail standard (Stage 2 only):
- `--v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout`

IMPORTANT: `--v 8.1` and `--oref` are incompatible. V8.1 does not support Omni Reference as of 2026-05 (on roadmap; not live). Use V7 for Stage 2 when identity adherence via `--oref` is required. Source of truth: `docs/model_guides/midjourney.yaml` (`omni_reference` rule).

Stage 2 hard rules:
- Three separate `/imagine` calls (2A, 2B, 2C) — never merged into one prompt.
- "sheet", "reference sheet", "character design", "turnaround", "collage", "multi-panel", "grid", "contact sheet" are FORBIDDEN in the positive prompt body. They may appear only as hyphenated terms in the `--no` clause.
- Stage 1 winner URL must be attached as Omni Reference (`--oref`) to each Stage 2 call.
- Stage 2C is an expression band variant, NOT an angle variant (angle variants belong to Stage 4).

### Stage 3 - GPT Images 2 FRONT HERO LOCK Prompt
Goal: produce one clean, single full-body front hero lock from the selected identity source.

Output intent:
- One single image only
- Identity lock image for downstream pack and look continuity

### Stage 4 - GPT Images 2 Four-Perspective Pack
Goal: expand one locked identity/look into four angle slots.

Required slots:
1. Front
2. Three-quarter left
3. Three-quarter right
4. Rear or side

### Stage 5 - Per-Look-Variant Lock Prompts (Midjourney)
Goal: enforce look-specific continuity while preserving the same identity anchor.

Output intent:
- One prompt block per look variant
- Explicitly tied to continuity scope and appearance_state

## Hard Rules
- Stage 2 is a single-image variant probe, not a sheet or panel layout.
- Stage 2 outputs are three independent single frames (2A, 2B, 2C) — not one merged sheet.
- FRONT HERO LOCK is a single image, not a contact sheet recreation.
- Same look only per perspective pack.
- Identity anchor invariants are non-negotiable.
- `mutable_appearance_allowed` defines the only allowed appearance drift.
- Positive prompt bodies must not contain: sheet, reference sheet, character design, turnaround, collage, multi-panel, grid, contact sheet. Use `--no` hyphenated forms only.

## Chain Discipline
Sequential lock chain (do not parallelize shortcuts):

`identity exploration 1 (V8.1) -> identity exploration 2 / single-image variant probe (V7 + oref) -> FRONT HERO LOCK -> four-perspective pack -> per-look lock`

Skipping Stage 1 collapses identity into wardrobe semantics and increases drift risk.
Skipping Stage 2 removes independent frame evidence for the identity anchor band.

## Schema Crosswalk
This doctrine maps prompt stages to existing metadata contracts.

- Stage 1-2 outputs map to:
  - `character_identity_anchor.source_reference_sheet_ref`

  > Field name `source_reference_sheet_ref` is preserved for historical stability. Its semantic meaning is the single identity-source image selected from the Stage 2 Identity Exploration 2 probe set. This field does not point to a sheet image; sheet output is forbidden (`contact_sheet_layout_forbidden_as_lock: true`). Schema field rename is deferred to a future PR (PROD-LINE-15A-3 recommended).
- Stage 3 output maps to:
  - `character_identity_anchor.front_hero_lock_ref`
- Stage 4 outputs map to:
  - `gpt_images_perspective_pack` (four perspective slots)
- Stage 5 outputs map operationally to:
  - `character_look_variant` continuity usage
  - `kling_character_look_element.source_reference_chain.wardrobe_ids` continuity expectations

## Field Notes
- Identity exploration is metadata-first: the model must learn who the person is before wardrobe-specific lock prompts.
- Stage 2 uses V7 + Omni Reference (`--oref`) because V8.1 does not support `--oref` as of 2026-05. Operatör must switch to V7 in Midjourney UI for Stage 2 calls.
- Stage 2 Omni Reference URL: paste the Stage 1 winner URL into `--oref`. `--ow 100` enforces maximum identity adherence.
- Lock chain is sequential, not parallel: each stage consumes the previous stage's validated identity source.
- The workflow is designed to reduce face/silhouette drift across look variants and scene transitions.

## What This Guide Is Not
- Not a prompt record file (`prompts/draft/` remains unchanged).
- Not a lifecycle gate implementation (`approved`/`locked` status promotion is out of scope).
- Not a binary registration policy (see [gpt_images_external_ref_replacement_checklist.md](gpt_images_external_ref_replacement_checklist.md)).

## Operator Safety Notes
- Do not commit generated binaries to the repository.
- Do not promote lifecycle statuses from this guide alone.
- Do not rewrite continuity records while running prompt kit stages.
- Keep external references pending until controlled replacement workflow is completed.
