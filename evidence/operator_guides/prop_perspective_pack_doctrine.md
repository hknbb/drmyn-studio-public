# Prop Perspective Pack Doctrine (PROD-LINE-15A-7 Scaffold)

This doctrine defines the first framework scaffold for prop perspective packs.

Status:
- Framework-only, metadata-only scaffold
- No lifecycle promotion
- No materialized visual outputs
- No binary registration

## Scope
- Element type: `prop`
- Stage family: GPT Images 2 perspective expansion for prop continuity
- This scaffold does not create or lock production prop pack records.

## Core Rules
1. Generate exactly one perspective per GPT Images 2 call.
2. Use landmark-anchored wording; do not use camera-frame left/right terms.
3. Use the prop hero/reference lock as continuity anchor.
4. Do not request opposing mirror-mate views in a single call.
5. Do not redesign prop identity while changing perspective.

Forbidden camera-frame terms in prompt body:
- `camera left`
- `camera right`
- `screen left`
- `screen right`

## Landmark Anchor Set (Prop)
Use prop-specific landmarks to disambiguate orientation and preserve continuity:
- handle
- logo/marking
- asymmetric edge
- material feature
- scale reference

## Candidate Perspective Set (Scaffold)
These are candidate keys for future schema review and are not activated by this scaffold:
- `ortho_front`
- `ortho_side`
- `ortho_rear`
- `top_orthographic`

## Schema Impact Note
- Current `gpt_images_perspective_pack` schema supports `element_type: prop`.
- No enum or validator change is introduced in this scaffold PR.
- Any future prop-specific perspective enums must be additive and backward compatible.

## Backward Compatibility Note
- Historical perspective enums remain valid and unchanged.
- This scaffold introduces no migration and no replacement of existing records.

## Lifecycle and Safety
- Keep prop pack records in `draft` / `review` until explicit human approval.
- Do not set `approved`, `locked`, `canon_lock`, or `materialized` in this scaffold.
- Do not register binaries in-repo.

## Out of Scope
- No schema edits
- No validator edits
- No perspective pack YAML creation
- No QC score population
- No Stage output registration

## Next Step
After framework review, follow with a dedicated implementation PR for:
- additive schema enum proposal (if approved)
- first PROPXX perspective-pack metadata record
- validator/test updates only as needed
