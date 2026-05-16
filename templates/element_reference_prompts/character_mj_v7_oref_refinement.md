# Template — Character Omni-Reference Refinement (Midjourney V7 `--oref`)

**Stage:** 2 of 3 (character chain)
**Model:** Midjourney V7 (use `--v 7`)
**Model guide:** `docs/model_guides/midjourney.yaml`
**Snapshot:** `evidence/model_guidance_snapshots/20260507T140000Z_midjourney.yaml`

## Purpose

Take the Stage 1 narrative identity reference and refine it into a **stable
Omni Reference identity lock** suitable as a downstream identity anchor. V7 is
required here because `--oref` (Omni Reference) is not available in V8.1.

The output is the locked reference handed to ChatGPT Images 2 in Stage 3.

## Input

- The selected Stage 1 image (`stage_1.output_ref`), uploaded as the Omni
  Reference.

## Prompt skeleton

```
Use the uploaded character reference as the strict Omni Reference.
Preserve the same face geometry, age read, hair silhouette, body presence,
wardrobe-world, and restrained performance identity. Refine only for stable
production reference clarity. No redesign, no fashion spread, no extra props,
no text, no watermark --v 7 --oref [uploaded image] --ow [weight] --style raw --ar 2:3
```

## Notes from the model guide

- `--oref` replaces the removed `--cref`; pair with `--ow <1-1000>` to set Omni
  Reference weight. Higher `--ow` = stricter identity lock.
- Keep `--style raw` for production realism.
- Do not redesign: no costume drift, no style drift, no aesthetic reinterpretation.

## QC focus

- identity consistency vs Stage 1
- reference lock strength
- no redesign

## Handoff

Select the refined output. Register it as `stage_2.output_ref` and as the
`handoff.source_reference_id` on the character `reference_chain.yaml`. This is
the `source_reference_id` the ChatGPT Images 2 scale-angle pack consumes in
Stage 3.
