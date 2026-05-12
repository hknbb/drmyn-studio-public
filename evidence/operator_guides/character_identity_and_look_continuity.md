# Character Identity And Look Continuity (Metadata-Only)

This guide defines identity continuity doctrine for character generation records.

## Role Separation
- Midjourney reference sheet: identity source for multi-angle exploration.
- GPT Images 2 FRONT HERO LOCK: single clean identity lock image.
- GPT Images 2 perspective pack: front, three-quarter-left, three-quarter-right, rear/side.
- Kling element reference: animation-facing continuity reference package.

## Reference Sheet Rule
Use uploaded reference as identity source, not as layout source.
Do not recreate a contact sheet.
Produce one single character image only for FRONT HERO LOCK.

## Lock Chain Doctrine
`reference_sheet -> FRONT HERO LOCK -> four-perspective pack -> kling_element_reference`

Each step must use the previous step as required input metadata.

## Identity Anchor vs Look Variant
- `character_identity_anchor`: fixed identity truth (facial topology, silhouette, fixed features).
- `character_look_variant`: scene-dependent appearance state (wardrobe and condition).

A new scene does not generate a new character identity by default; it selects an
appropriate look variant derived from the same identity anchor.

## Look Change Rules
A look change requires an explicit `change_reason`, especially for:
- day-to-night or morning-to-night transitions
- private-to-public social role shifts
- pre-event to post-event damage/wetness/dirt states
- sequence continuity breaks

## Forbidden Drift
Do not introduce:
- a different face
- a different body-type silhouette
- fashion-editorial redesign unrelated to narrative continuity
- wardrobe worlds unrelated to continuity state

## Registration Boundary
Generated image binaries stay outside this repository.
Only metadata refs are stored in production records.

Perspective QC remains null/pending until human review completes.
No selected/canonical, approved/locked, or materialized promotion is allowed in
identity/look continuity seed records.

## Omni shot prompt alias rule

- Per shot, use one active look alias per character: `@C##_LOOK_ROLE`.
- Do not mix two look aliases of the same character in the same shot.
- Wardrobe is baked into the character-look element; do not pass `@WD_*` wardrobe elements to Omni in parallel.
- If a scene requires an in-shot wardrobe change, escalate to a future shot-level look map workflow. Do not solve it inside a scene-level alias hint.
- The operator should use `scene_character_look_map -> kling_character_look_element -> kling_element_alias` as the prompt source chain.
