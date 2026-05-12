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

### Stage 2 - Reference Sheet Prompt (Midjourney)
Goal: freeze the selected identity source in a reusable format for downstream locking.

Output intent:
- Identity-source-aware reference image
- Consistent geometry and silhouette with Stage 1
- Still metadata-facing, not final scene output

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
- Reference sheet is identity source, not layout source.
- FRONT HERO LOCK is a single image, not a contact sheet recreation.
- Same look only per perspective pack.
- Identity anchor invariants are non-negotiable.
- `mutable_appearance_allowed` defines the only allowed appearance drift.

## Chain Discipline
Sequential lock chain (do not parallelize shortcuts):

`identity exploration -> reference sheet -> FRONT HERO LOCK -> four-perspective pack -> per-look lock`

Skipping Stage 1 collapses identity into wardrobe semantics and increases drift risk.

## Schema Crosswalk
This doctrine maps prompt stages to existing metadata contracts.

- Stage 1-2 outputs map to:
  - `character_identity_anchor.source_reference_sheet_ref`
- Stage 3 output maps to:
  - `character_identity_anchor.front_hero_lock_ref`
- Stage 4 outputs map to:
  - `gpt_images_perspective_pack` (four perspective slots)
- Stage 5 outputs map operationally to:
  - `character_look_variant` continuity usage
  - `kling_character_look_element.source_reference_chain.wardrobe_ids` continuity expectations

## Field Notes
- Identity exploration is metadata-first: the model must learn who the person is before wardrobe-specific lock prompts.
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
