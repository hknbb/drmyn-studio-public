# Template — Non-Character Scale-Angle Pack (ChatGPT Images 2)

**Stage:** 2 of 2 (non-character chain)
**Element types:** location, prop, wardrobe, style
**Model:** ChatGPT Images 2 (`gpt-image-2`)
**Model guide:** `docs/model_guides/chatgpt_image.yaml`
**Snapshot:** `evidence/model_guidance_snapshots/20260504T113000Z_chatgpt_image.yaml`

## Purpose

From the Stage 1 first reference, generate the three production reference views
of the `three_view_scale_angle_v2` policy:

- `front_reference`
- `three_quarter_medium_reference`
- `three_quarter_close_reference`

No left/right directional prompts. Views differ by **camera angle and framing
scale** only.

## Input

- The Stage 1 first reference (`source_reference_id`,
  `CHATGPTIMG_ELEMENT_*`), uploaded as the strict identity source.

## Prompt skeleton (one per view)

```
Use the uploaded first reference as the strict identity source.

Generate one [front_reference | three_quarter_medium_reference |
three_quarter_close_reference] production reference image of the same element.

Preserve:
- form and proportion
- material and palette
- scale and spatial relationships
- defining production features

Change only:
- camera angle
- framing scale

No left/right or profile instruction. No people unless explicitly required.
No extra objects. No text, no watermark, no logo.
```

## View intent

- `front_reference` — front-facing identity read.
- `three_quarter_medium_reference` — three-quarter angle, medium framing.
- `three_quarter_close_reference` — three-quarter angle, detail/close framing.

## Notes from the model guide

- Full natural-language sentences with labeled segments; no `--` flags.
- Use the preserve list to prevent identity drift across the three views.

## Handoff

Register the three outputs as the `prompts` of a
`gpt_images_perspective_pack.yaml` record with
`perspective_policy: three_view_scale_angle_v2`.
