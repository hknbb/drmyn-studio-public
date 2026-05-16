# Template — Character Scale-Angle Pack (ChatGPT Images 2)

**Stage:** 3 of 3 (character chain)
**Model:** ChatGPT Images 2 (`gpt-image-2`)
**Model guide:** `docs/model_guides/chatgpt_image.yaml`
**Snapshot:** `evidence/model_guidance_snapshots/20260504T113000Z_chatgpt_image.yaml`

## Purpose

From the Stage 2 V7-refined identity lock, generate the three production
reference views of the `three_view_scale_angle_v2` policy:

- `front_reference`
- `three_quarter_medium_reference`
- `three_quarter_close_reference`

No left/right directional prompts. Views differ by **camera angle and framing
scale**, not by which side of the subject faces the camera.

## Input

- The Stage 2 refined character reference (`handoff.source_reference_id`),
  uploaded as the strict identity source.

## Prompt skeleton (one per view)

ChatGPT Images 2 has no `--` parameters and no negative-prompt field. Embed all
constraints as positive prohibitions in natural language.

```
Use the uploaded refined character reference as the strict identity source.

Generate one [front_reference | three_quarter_medium_reference |
three_quarter_close_reference] production reference image of the same character.

Preserve:
- face geometry
- age read
- hair silhouette
- body presence
- wardrobe-world
- expression / performance identity

Change only:
- camera angle
- framing scale

No left/right or profile instruction. No props, no furniture, no extra people,
no text, no watermark, no logo.
```

## View intent

- `front_reference` — front-facing, full identity read.
- `three_quarter_medium_reference` — three-quarter angle, medium framing.
- `three_quarter_close_reference` — three-quarter angle, closer framing.

## Notes from the model guide

- Use full natural-language sentences, not Midjourney comma clauses.
- Use the preserve list to prevent identity drift across the three views.
- First name only; never canonical IDs or full display names.

## Handoff

Register the three outputs as the `prompts` of a
`gpt_images_perspective_pack.yaml` record with
`perspective_policy: three_view_scale_angle_v2`. These feed the Kling element
reference (PR-REF-4).
