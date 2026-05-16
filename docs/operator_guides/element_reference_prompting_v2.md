# Element Reference Prompting v2 (Operator Guide)

This guide is the **single operator-facing source** for manually generating
element reference images under Element Reference Generation Policy v2. It tells
the operator which prompt to copy, into which model, at which stage, and what QC
evaluates afterwards.

This workflow is metadata-only. Operators generate images outside this
repository; the repository stores only prompt IDs, registration metadata, and
review scores.

## Policy v2 in one paragraph

Characters get a **two-stage Midjourney chain** — Midjourney V8/V8.1 produces a
narrative identity reference, then Midjourney V7 `--oref` refines it into a
stable Omni Reference identity lock. Non-character elements (location / prop /
wardrobe / style) get their **first reference from ChatGPT Images 2** directly.
In both cases, the locked reference is handed to ChatGPT Images 2, which
produces a three-view **scale/angle** pack: `front_reference`,
`three_quarter_medium_reference`, `three_quarter_close_reference`. Left/right
directional prompts are not used.

## Stage map

| Stage | Element type | Model | Template |
|-------|--------------|-------|----------|
| 1. Narrative identity | character | Midjourney V8/V8.1 | [character_mj_v8_narrative_identity.md](../../templates/element_reference_prompts/character_mj_v8_narrative_identity.md) |
| 2. Omni-reference refine | character | Midjourney V7 `--oref` | [character_mj_v7_oref_refinement.md](../../templates/element_reference_prompts/character_mj_v7_oref_refinement.md) |
| 3. Scale-angle pack | character | ChatGPT Images 2 | [character_gptimg2_scale_angle_pack.md](../../templates/element_reference_prompts/character_gptimg2_scale_angle_pack.md) |
| 1. First reference | non-character | ChatGPT Images 2 | [non_character_gptimg2_first_reference.md](../../templates/element_reference_prompts/non_character_gptimg2_first_reference.md) |
| 2. Scale-angle pack | non-character | ChatGPT Images 2 | [non_character_gptimg2_scale_angle_pack.md](../../templates/element_reference_prompts/non_character_gptimg2_scale_angle_pack.md) |

## Model guide / snapshot binding

Every template cites the active model guide and its `snapshot_ref`. Adapters and
operators read rules from the guide — never hardcode prompt rules.

- Midjourney: [docs/model_guides/midjourney.yaml](../model_guides/midjourney.yaml)
  — snapshot `evidence/model_guidance_snapshots/20260507T140000Z_midjourney.yaml`.
- ChatGPT Images 2: [docs/model_guides/chatgpt_image.yaml](../model_guides/chatgpt_image.yaml)
  — snapshot `evidence/model_guidance_snapshots/20260504T113000Z_chatgpt_image.yaml`.

When a record is authored, its `source_refs.model_guidance_snapshot_ref` must
point at the snapshot in effect at generation time.

## Full body is not a hard gate

Under v2 the character first reference is judged on identity readability, not
head-to-toe coverage. Full body is **optional metadata** (`full_body_visible`),
never a QC pass/fail criterion. See PR-REF-3 QC rubric for scoring criteria.

## What QC evaluates

- Character chain: identity readability, face geometry clarity, age/body read,
  silhouette/hair read, wardrobe-world continuity, expression/performance
  readability, no redesign/no stylization.
- Scale-angle pack: `view_distinction`, `scale_distinction`,
  `identity_preservation`, `no_directional_confusion`. Left/right accuracy is
  no longer a QC criterion.

## Grandfather note

Records authored before the `element-reference-policy-v2` CHANGELOG entry may
use the legacy directional three-view (`three_view_no_rear`) or
`legacy_four_view` policy. C01, LOC001, PROP003 stay on their legacy policy and
are not migrated. Newly authored records use `three_view_scale_angle_v2`.
