# Element Reference Generation Policy v2

## Why this policy exists

Before v2, element reference packs used a **directional** three-view layout
(`front_reference`, `left_reference`, `right_reference`). In operator practice
the left/right directional prompts produced inconsistent results, and the
character first reference carried an implicit "full body" expectation that added
quality pressure without serving the actual goal — reading the character as a
correct dramatic identity.

Policy v2 standardizes a **scale/angle** three-view layout and a two-stage
Midjourney chain for characters. It is a **forward-only** policy: existing
records are grandfathered, not migrated.

## The chains

### Character

```
Stage 1  Midjourney V8/V8.1   narrative identity reference
Stage 2  Midjourney V7 --oref omni-reference identity refinement
Stage 3  ChatGPT Images 2     scale-angle three-view pack
```

Stage 1 produces a narrative identity reference. Stage 2 refines it into a
stable Omni Reference identity lock (V7 is required — `--oref` is not available
in V8.1). Stage 3 expands the locked reference into three production views.

### Non-character (location / prop / wardrobe / style)

```
Stage 1  ChatGPT Images 2  first identity reference
Stage 2  ChatGPT Images 2  scale-angle three-view pack
```

Non-character elements do not use Midjourney. Their first reference and their
view pack are both produced by ChatGPT Images 2.

### Routing table

| Element type | First reference | View pack |
|--------------|-----------------|-----------|
| character | Midjourney V8/V8.1 -> V7 `--oref` | ChatGPT Images 2 |
| location | ChatGPT Images 2 | ChatGPT Images 2 |
| prop | ChatGPT Images 2 | ChatGPT Images 2 |
| wardrobe | ChatGPT Images 2 | ChatGPT Images 2 |
| style | ChatGPT Images 2 | ChatGPT Images 2 |

Non-character `source_reference_id` values follow the `CHATGPTIMG_ELEMENT_*`
pattern.

## The three views

All element types use one standard set of views — `three_view_scale_angle_v2`:

- `front_reference`
- `three_quarter_medium_reference`
- `three_quarter_close_reference`

Views differ by **camera angle and framing scale**, never by which side of the
subject faces the camera. Left/right directional prompts are not used.

## Full body is not a hard gate

The character first reference is judged on identity readability, not head-to-toe
coverage. There is **no `full_body` hard gate** in any validator. `full_body_visible`
exists only as optional metadata on the perspective pack. Useful when it occurs;
never a QC pass/fail criterion.

Character QC scoring criteria:

- character description strength
- identity readability
- face geometry clarity
- age / body read
- silhouette / hair read
- wardrobe-world continuity
- expression / performance readability
- no redesign / no stylization

Scale-angle pack QC criteria: `view_distinction`, `scale_distinction`,
`identity_preservation`, `no_directional_confusion`. Left/right accuracy is no
longer a QC criterion.

## Operator prompting

The prompt templates and copy/paste workflow live in
[docs/operator_guides/element_reference_prompting_v2.md](../operator_guides/element_reference_prompting_v2.md)
and `templates/element_reference_prompts/`. Each template cites the active model
guide and `model_guidance_snapshot_ref`; adapter code never hardcodes prompt
rules.

## Grandfather rule (cutoff)

> Records authored before the `element-reference-policy-v2` CHANGELOG entry may
> use legacy directional (`three_view_no_rear`) or `legacy_four_view` policy.
> Newly authored records after that entry must use `three_view_scale_angle_v2`.

C01, LOC001, and PROP003 stay on their existing policy and are **not migrated**.
Their canon chains remain valid; reauthoring closed audit records would be
unnecessary risk.

## Schema impact

All schema changes for this policy are **additive** (per
`STAGE_B_PR1_SCHEMA_NOTE.md`): new enum values and new `oneOf` branches only — no
removals, no required-field changes. The legacy `legacy_four_view` and
`three_view_no_rear` enum values are retained as the grandfather buckets.
