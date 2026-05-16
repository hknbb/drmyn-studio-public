# Template — Non-Character First Reference (ChatGPT Images 2)

**Stage:** 1 of 2 (non-character chain)
**Element types:** location, prop, wardrobe, style
**Model:** ChatGPT Images 2 (`gpt-image-2`)
**Model guide:** `docs/model_guides/chatgpt_image.yaml`
**Snapshot:** `evidence/model_guidance_snapshots/20260504T113000Z_chatgpt_image.yaml`

## Purpose

Produce the **first identity reference** for a non-character element. Under
policy v2, non-character elements do not use the Midjourney character chain —
their first reference is generated directly by ChatGPT Images 2.

This first reference is the input to Stage 2
(`non_character_gptimg2_scale_angle_pack.md`).

## Prompt skeleton

ChatGPT Images 2 has no `--` parameters and no negative-prompt field. Use
labeled segments and embed prohibitions as positive constraints.

```
Scene: [setting / context the element belongs to]
Subject: [location / prop / wardrobe / style element], described from its
canonical element sheet and scene function.
Details: [material, scale, defining features, production-relevant cues].
Constraints: Prioritize identity clarity, production usability, material/space
readability, and downstream consistency. No people unless explicitly required.
No extra objects. No text, no watermark, no logo.
```

## Notes from the model guide

- Prompt order: background/scene -> subject -> key details -> constraints.
- Use full sentences; no Midjourney comma clauses, no `--` flags, no seed.
- Never include canonical IDs (LOC001, PROP003) or character full display names
  in prompt text.

## Handoff

Select one output. It becomes the `source_reference_id` (a
`CHATGPTIMG_ELEMENT_*` reference) consumed by the Stage 2 scale-angle pack.
