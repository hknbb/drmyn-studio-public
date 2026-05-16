# Wardrobe Perspective Pack Doctrine (PROD-LINE-15A-6 Scaffold)

> **Policy v2 update (`element-reference-policy-v2`).** This scaffold predates
> Element Reference Generation Policy v2. Under v2, non-character elements
> (location / prop / wardrobe / style) route through ChatGPT Images 2 for BOTH
> the first identity reference and the scale-angle three-view pack. The
> `source_reference_id` follows the `CHATGPTIMG_ELEMENT_*` pattern. The
> candidate perspective set below is superseded by the single standard triple:
> `front_reference`, `three_quarter_medium_reference`,
> `three_quarter_close_reference` (`perspective_policy: three_view_scale_angle_v2`).
> Views differ by camera angle and framing scale — no left/right directional
> wording. See `docs/methodology/element_reference_generation_policy.md` and the
> operator prompt templates in `templates/element_reference_prompts/`. Records
> authored before the v2 cutoff are grandfathered and not migrated.

This doctrine defines the first framework scaffold for wardrobe perspective packs.

Status:
- Framework-only, metadata-only scaffold
- No lifecycle promotion
- No materialized visual outputs
- No binary registration

## Scope
- Element type: `wardrobe`
- Stage family: GPT Images 2 perspective expansion for wardrobe continuity
- This scaffold does not create or lock production wardrobe pack records.

## Core Rules
1. Generate exactly one perspective per GPT Images 2 call.
2. Use landmark-anchored wording; do not use camera-frame left/right terms.
3. Use the wardrobe hero/reference lock as continuity anchor.
4. Do not request opposing mirror-mate views in a single call.
5. Do not redesign garment identity while changing perspective.

Forbidden camera-frame terms in prompt body:
- `camera left`
- `camera right`
- `screen left`
- `screen right`

## Landmark Anchor Set (Wardrobe)
Use garment landmarks to disambiguate orientation and preserve continuity:
- lapel
- cuff
- pocket
- seam
- label
- fabric panel
- closure direction

## Candidate Perspective Set (Scaffold)
These are candidate keys for future schema review and are not activated by this scaffold:
- `flat_lay`
- `on_mannequin_front`
- `on_mannequin_back`
- `material_detail`

## Schema Impact Note
- Current `gpt_images_perspective_pack` schema supports `element_type: wardrobe`.
- No enum or validator change is introduced in this scaffold PR.
- Any future wardrobe-specific perspective enums must be additive and backward compatible.

## Backward Compatibility Note
- Historical perspective enums remain valid and unchanged.
- This scaffold introduces no migration and no replacement of existing records.

## Lifecycle and Safety
- Keep wardrobe pack records in `draft` / `review` until explicit human approval.
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
- first WDXX perspective-pack metadata record
- validator/test updates only as needed
