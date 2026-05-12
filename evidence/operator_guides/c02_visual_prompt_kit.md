# C02 Roman Vale - Visual Prompt Kit

> Doctrine reference: [character_visual_prompt_kit_doctrine.md](character_visual_prompt_kit_doctrine.md)
> Identity anchor: `C02_IDENTITY_ANCHOR_V001` (`visual_dev/elements/characters/C02/character_identity_anchor.yaml`)
> Look variants:
> - `C02_LOOK_CORPORATE_CONTROL_V001` (SC0002-SC0007)
> - `C02_LOOK_DOMESTIC_AUTHORITY_V001` (SC0008-SC0009)

## Character Source (Truth)
From `planning/characters/C02.yaml`:
- Age range: late 40s to 50s
- Screen presence: controlled institutional gravity, centered composure
- Costume logic: tailored corporate/private-control wardrobe with disciplined construction
- Silhouette: tall or lengthened control silhouette
- Color bias: dark suiting neutrals, controlled whites, muted luxury restraint
- Hair/makeup notes: composure first, no theatrical villain coding

## Seed Registry
- Character seed: `43`
- Midjourney V8.1 tail (all Stage 1/2/5 prompts):
`--v 8.1 --raw --ar 2:3 --s 100 --seed 43 --chaos 5 --no text logo watermark`

## Stage 1 - Identity Exploration Prompt (Midjourney)

```text
/imagine prompt: C02 Roman Vale cinematic identity exploration, man in late 40s to early 50s, tall lengthened upright silhouette, centered controlled composure, watchful institutional reading, no overt aggression, dark suiting neutrals, controlled whites, muted luxury restraint, tailored corporate and private-control wardrobe logic, disciplined construction, no decorative looseness, no fashion editorial exaggeration, no action-hero styling, no glamour retouching, no cyberpunk, no neon, clean character reference composition, full body with face readability --v 8.1 --raw --ar 2:3 --s 100 --seed 43 --chaos 5 --no text logo watermark
```

## Stage 2 - Reference Sheet Prompt (Midjourney)

```text
/imagine prompt: C02 Roman Vale reference sheet for identity source locking, preserve selected identity exactly, same face geometry, same age read, same tall lengthened silhouette, same composed authority posture, full-body cinematic reference composition, clean neutral background, high facial readability, no wardrobe redesign, no decorative styling drift --v 8.1 --raw --ar 2:3 --s 100 --seed 43 --chaos 5 --no text logo watermark
```

## Stage 3 - GPT Images 2 FRONT HERO LOCK Prompt

```text
Use the uploaded C02 Roman Vale reference image as identity source only, not as a layout source. Generate one single full-body FRONT hero lock image with identical face geometry, age read, body proportions, and silhouette. Preserve composed institutional authority. Neutral clean background, realistic cinematic texture, no contact sheet, no redesign, no text, no logo, no watermark, no extra characters.
```

## Stage 4 - GPT Images 2 Four-Perspective Pack
Rule: one look per pack, no look mixing.

### Perspective 1: Front Hero
```text
Using the locked C02 identity source, generate one full-body FRONT view. Preserve identical face geometry, body proportions, silhouette, and exact same look styling.
```

### Perspective 2: Three-Quarter Left
```text
Using the locked C02 identity source, generate one full-body three-quarter LEFT view (about 45 degrees). Preserve identical identity anchors and exact same look styling as Perspective 1.
```

### Perspective 3: Three-Quarter Right
```text
Using the locked C02 identity source, generate one full-body three-quarter RIGHT view (about 45 degrees). Preserve identical identity anchors and exact same look styling as Perspectives 1-2.
```

### Perspective 4: Rear or Side
```text
Using the locked C02 identity source, generate one full-body REAR view (or strict SIDE if rear fails). Preserve identity anchors and exact same look styling as Perspectives 1-3.
```

## Stage 5 - Per-Look-Variant Lock Prompts (Midjourney)

### Look: CORPORATE_CONTROL (`C02_LOOK_CORPORATE_CONTROL_V001`, SC0002-SC0007)

```text
/imagine prompt: C02 Roman Vale look lock CORPORATE_CONTROL, preserve established C02 identity source exactly, corporate boardroom and private institutional control cues, tailored dark suit, same face geometry and body proportions, same composed authority, dark suiting neutrals with controlled whites, no redesign, no drift --v 8.1 --raw --ar 2:3 --s 100 --seed 43 --chaos 5 --no text logo watermark
```

### Look: DOMESTIC_AUTHORITY (`C02_LOOK_DOMESTIC_AUTHORITY_V001`, SC0008-SC0009)

```text
/imagine prompt: C02 Roman Vale look lock DOMESTIC_AUTHORITY, preserve established C02 identity source exactly, domestic authority context inside LOC001 Vale residence, softened collar or private-household authority cues, identical face geometry and body proportions, same institutional composure, no redesign, no drift --v 8.1 --raw --ar 2:3 --s 100 --seed 43 --chaos 5 --no text logo watermark
```

## Aesthetic Pack References
From `planning/aesthetic_bible.yaml`:
- `KASPAR_INSTITUTIONAL_SURVEILLANCE`

## Operator Notes
- Binaries stay external; repository keeps metadata only.
- Stage 4 must not mix `C02_LOOK_CORPORATE_CONTROL_V001` and `C02_LOOK_DOMESTIC_AUTHORITY_V001` in the same pack.
- Stage sequence is mandatory: Stage 1 -> Stage 2 -> Stage 3 -> Stage 4 -> Stage 5.
- Use [gpt_images_external_ref_replacement_checklist.md](gpt_images_external_ref_replacement_checklist.md) for real external-ref registration workflow.
