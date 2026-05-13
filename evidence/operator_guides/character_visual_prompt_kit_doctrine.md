# Character Visual Prompt Kit Doctrine (PROD-LINE-15A-0)

This guide defines the operator-facing prompt artifact doctrine for character visual lock workflows.

Authority note:
- Primary continuity authority remains [character_identity_and_look_continuity.md](character_identity_and_look_continuity.md).
- This document does not override that guide. It operationalizes it into copy-paste prompt stages.

## Scope
- Characters: C01, C02, C03, C04, C05
- Canon window for look-lock usage: SC0001-SC0009 (KNOWN canon)
- Stage context: pre-PROD-LINE-15A external-ref registration write pass

## Six-Stage Pipeline

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
- Three separate `/imagine` calls (2A, 2B, 2C)  never merged into one prompt.
- "sheet", "reference sheet", "character design", "turnaround", "collage", "multi-panel", "grid", "contact sheet" are FORBIDDEN in the positive prompt body. They may appear only as hyphenated terms in the `--no` clause.
- Stage 1 winner URL must be attached as Omni Reference (`--oref`) to each Stage 2 call.
- Stage 2C is an expression band variant, NOT an angle variant (angle variants belong to Stage 4).

### Stage 2.5 - Identity Evidence Set Selection
Goal: before GPT Images 2, operator declares which identity evidence images will be uploaded.

Output intent:
- One operator-selected evidence set with 1-4 images.
- Each included image has a slot id, source stage, role, inclusion flag, and optional exclusion reason.
- This is operator-facing metadata doctrine, not a production record in this PR.

Allowed evidence slots:
- `E01_STAGE1_WINNER`
  Source: Stage 1 Identity Exploration winner
  Role: primary_identity_direction
- `E02_STAGE2A_PORTRAIT`
  Source: Stage 2A Identity Portrait Probe
  Role: face_topology_anchor
- `E03_STAGE2B_FULL_BODY`
  Source: Stage 2B Identity Full-Body Probe
  Role: silhouette_body_proportion_anchor
- `E04_STAGE2C_EXPRESSION_BAND`
  Source: Stage 2C Identity Expression Band Probe
  Role: expression_range_check

Evidence count rule:
- Minimum: 1 image
- Recommended: 2-4 images
- Maximum for this workflow: 4 images

Recommended input sets:
- 1 image: best single identity source if other images drift
- 2 images: E01 + strongest E02 or E03
- 3 images: E01 + E02 + E03
- 4 images: E01 + E02 + E03 + E04, only if all are identity-consistent

Outlier rule:
Do not upload a source image if it causes:
- face drift
- age drift
- hair silhouette drift
- body proportion drift
- wardrobe/material-world drift
- expression outside anchor range

### Stage 3 - GPT Images 2 FRONT HERO LOCK from Identity Evidence Set
Goal: produce one clean, single full-body front hero lock from the selected Stage 2.5 identity evidence set.

Output intent:
- One single image only
- Identity lock image for downstream pack and look continuity

### Stage 4 - GPT Images 2 Four-Perspective Pack (sequential separate-call, anatomy-anchored)
Goal: produce four non-front perspective outputs from the Stage 3 FRONT HERO LOCK identity anchor while avoiding mirror-mate ambiguity.

Required slots (each generated in a separate GPT Images 2 call):
1. Rear view (`rear_or_side`)
2. Three-quarter left (`three_quarter_left`)
3. Right profile side (`right_profile_side`)
4. Left profile side (`left_profile_side`)

Anatomy-anchored descriptors are mandatory for left/right prompts. Use character-frame language such as:
- "character's left shoulder closer to camera"
- "character's right cheek dominant"
- "character's left ear partially visible"
- "character's right ear hidden behind head"

Front view is not generated in Stage 4. Front hero lock belongs to Stage 3.

### Stage 5 - Per-Look-Variant Lock Prompts (Midjourney)
Goal: enforce look-specific continuity while preserving the same identity anchor.

Output intent:
- One prompt block per look variant
- Explicitly tied to continuity scope and appearance_state

## Hard Rules
- Stage 2 is a single-image variant probe, not a sheet or panel layout.
- Stage 2 outputs are three independent single frames (2A, 2B, 2C)  not one merged sheet.
- FRONT HERO LOCK is a single image, not a contact sheet recreation.
- Stage 4 perspectives are produced as four separate GPT Images 2 calls; never request mirror-mate angles in one prompt.
- Stage 4 must not request front view; Stage 3 owns front hero lock generation.
- Anatomy-anchored left/right disambiguation is mandatory for Stage 4 left/right prompts.
- Do not use camera-frame terms in Stage 4 prompt bodies: camera left, camera right, screen left, screen right.
- Same look only per perspective pack.
- Identity anchor invariants are non-negotiable.
- `mutable_appearance_allowed` defines the only allowed appearance drift.
- Positive prompt bodies must not contain: sheet, reference sheet, character design, turnaround, collage, multi-panel, grid, contact sheet. Use `--no` hyphenated forms only.

## Chain Discipline
Sequential lock chain (do not parallelize shortcuts):

`identity exploration 1 (V8.1) -> identity exploration 2 / single-image variant probe (V7 + oref) -> identity evidence set selection (1-4 images) -> FRONT HERO LOCK from identity evidence set -> four-perspective pack (rear + 3q-left + right-profile + left-profile) -> per-look lock`

Skipping Stage 1 collapses identity into wardrobe semantics and increases drift risk.
Skipping Stage 2 removes independent frame evidence for the identity anchor band.
Skipping Stage 2.5 removes explicit evidence selection control before Stage 3.

## Schema Crosswalk
This doctrine maps prompt stages to existing metadata contracts.

- Stage 1-2 outputs map to:
  - `character_identity_anchor.source_reference_sheet_ref`

  > Field name `source_reference_sheet_ref` is preserved for historical stability. It remains the historical primary pointer from the Stage 1-2 identity chain. This field does not point to a sheet image; sheet output is forbidden (`contact_sheet_layout_forbidden_as_lock: true`).
- Stage 2.5 is operator-facing selection context in this PR.
- Stage 3 output maps to:
  - `character_identity_anchor.front_hero_lock_ref`
- Stage 4 outputs map to:
  - `gpt_images_perspective_pack` (four perspective slots generated as separate calls)
  - New perspective enums for new packs: `right_profile_side`, `left_profile_side`
  - Deprecated for new packs (kept for backwards compatibility): `front_hero`, `three_quarter_right`
- Stage 5 outputs map operationally to:
  - `character_look_variant` continuity usage
  - `kling_character_look_element.source_reference_chain.wardrobe_ids` continuity expectations
- Future schema support may add `source_identity_evidence_refs` or an `identity_evidence_set` record type in a later PR.

## Element-Type Generalization (Forward-Looking)

The anatomy-anchored separate-call paradigm of Stage 4 can generalize to non-character element types such as wardrobe, props, and locations.

For every element type, the same production rules apply:

1. Generate one perspective per GPT Images 2 call.
2. Use landmark-anchored disambiguation instead of camera-frame directions.
3. Use the locked hero/reference image for that element type as the identity or continuity anchor.
4. Do not request opposing mirror-mate views in the same prompt.
5. Do not redesign the element while changing perspective.

Element-specific anchors differ by type:

- Character: ear, shoulder, cheek, hair silhouette, body proportions.
- Wardrobe: lapel, cuff, pocket, seam, label, fabric panel, closure direction.
- Prop: handle, logo/marking, asymmetric edge, material feature, scale reference.
- Location: doorway, window, fireplace, furniture placement, threshold, wall geometry.

This repository currently implements the migrated Stage 4 perspective set only for character elements.

Non-character perspective packs are deferred:
- PROD-LINE-15A-6: wardrobe perspective pack framework
- PROD-LINE-15A-7: prop perspective pack framework
- PROD-LINE-15A-8: location perspective pack framework

Until those follow-up PRs land, no wardrobe, prop, or location perspective pack records are created.

See [non_character_perspective_generalization_notes.md](../research_notes/non_character_perspective_generalization_notes.md) for the detailed framework, candidate perspective sets per element type (subject to schema review), and web research findings.

## Field Notes
- Identity exploration is metadata-first: the model must learn who the person is before wardrobe-specific lock prompts.
- Stage 2 uses V7 + Omni Reference (`--oref`) because V8.1 does not support `--oref` as of 2026-05. Operator must switch to V7 in Midjourney UI for Stage 2 calls.
- Stage 2 Omni Reference URL: paste the Stage 1 winner URL into `--oref`. `--ow 100` enforces maximum identity adherence.
- More images are not automatically better.
- Use fewer images if outliers degrade identity.
- Default recommendation is E01 + E02 + E03.
- Add E04 only when expression-band probe preserves identity.
- Downstream records may still use historical perspective keys; migration is deferred to follow-up PROD-LINE-15A-5.
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
