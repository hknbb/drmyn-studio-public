# Location Perspective Pack Doctrine (PROD-LINE-15A-8 Scaffold)

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

This doctrine defines the first framework scaffold for location perspective packs.

Status:
- Framework-only, metadata-only scaffold
- No lifecycle promotion
- No materialized visual outputs
- No binary registration

## Scope
- Element type: `location`
- Stage family: GPT Images 2 perspective expansion for location continuity
- This scaffold does not create or lock production location pack records.

## Core Rules
1. Generate exactly one perspective per GPT Images 2 call.
2. Use landmark-anchored wording; do not use camera-frame left/right terms.
3. Use the location establishing hero/reference lock as continuity anchor.
4. Do not request opposing mirror-mate views in a single call.
5. Do not redesign layout identity while changing perspective.

Forbidden camera-frame terms in prompt body:
- `camera left`
- `camera right`
- `screen left`
- `screen right`

## Landmark Anchor Set (Location)
Use location-specific landmarks to disambiguate orientation and preserve continuity:
- doorway
- window
- fireplace
- furniture placement
- threshold detail

## Candidate Perspective Set (Scaffold)
These are candidate keys for future schema review and are not activated by this scaffold:
- `establishing_hero`
- `reverse_angle_room`
- `side_depth_room`
- `threshold_detail`

## Schema Impact Note
- Current `gpt_images_perspective_pack` schema supports `element_type: location`.
- No enum or validator change is introduced in this scaffold PR.
- Existing perspective enums are sufficient for first location pack implementation.

## Backward Compatibility Note
- Historical perspective enums remain valid and unchanged.
- This scaffold introduces no migration and no replacement of existing records.

## Lifecycle and Safety
- Keep location pack records in `draft` / `review` until explicit human approval.
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
- first LOCXXX perspective-pack metadata record
- validator/test updates only as needed
