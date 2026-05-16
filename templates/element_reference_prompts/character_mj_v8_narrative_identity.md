# Template — Character Narrative Identity Reference (Midjourney V8/V8.1)

**Stage:** 1 of 3 (character chain)
**Model:** Midjourney V8.1 (use `--v 8.1`)
**Model guide:** `docs/model_guides/midjourney.yaml`
**Snapshot:** `evidence/model_guidance_snapshots/20260507T140000Z_midjourney.yaml`

## Purpose

Produce the first **narrative identity reference** for a character — an image
that reads the character correctly as a dramatic presence. This image is the
input to Stage 2 (V7 `--oref` refinement), not a final production view.

The goal is identity, not coverage. Evaluate the output on:
- character description strength (does it read as the intended person)
- face geometry / identity cues
- age and body read
- silhouette and hair read
- wardrobe-world fit
- expression / performance register
- restrained realism, no redesign

## Not required

- full body / head-to-toe / feet visible
- turntable
- left/right profile

These are not quality criteria at Stage 1. `full_body_visible` is optional
metadata only.

## Prompt skeleton

Replace bracketed slots. Use the character first name only — never canonical IDs
(C01, SC0001) or full display names (see `no_canonical_ids_in_prompt` in the
model guide).

```
[FIRST NAME], [age read], [body / silhouette], [hair], [face / identity cues],
[wardrobe-world], [emotional register], cinematic production character reference,
neutral clean background, identity readability, restrained realism, no redesign,
no fashion spread, no text, no watermark --v 8.1 --style raw --ar 2:3 --seed [seed]
```

## Notes from the model guide

- `--style raw` is the production standard for character work (strips aesthetic
  bias). Always include it.
- V8.1 has a ~74-token cap; target 40-50 meaningful words, no padding.
- V8.1 does not support `--oref` — that is Stage 2 on V7.
- Record the `--seed` value so the variant is reproducible.
- `--ar 2:3` is the standard character/portrait aspect ratio.

## Handoff

Select one output. It becomes the **input image** for Stage 2
(`character_mj_v7_oref_refinement.md`). Register the selected image as the
`stage_1.output_ref` on the character `reference_chain.yaml` record.
