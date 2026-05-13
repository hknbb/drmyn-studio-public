# [CXX] [Character Name] - Visual Prompt Kit

<!--
Usage:
1. Copy to `evidence/operator_guides/cXX_visual_prompt_kit.md`
2. Replace placeholders:
   - [CXX] -> C01/C02/.../CNN
   - [Character Name] -> planning/characters/CXX.yaml `display_name`
   - [CXX_IDENTITY_ANCHOR_V001] -> anchor id from visual_dev/elements/characters/CXX/character_identity_anchor.yaml
3. Pull truth from:
   - planning/characters/CXX.yaml
   - visual_dev/elements/characters/CXX/look_variants/*.yaml
   - planning/aesthetic_bible.yaml
4. Keep Midjourney V8.1 tail exactly:
   --v 8.1 --raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --no text logo watermark
5. Seed registry:
   C01=42, C02=43, C03=44, C04=45, C05=46
-->

> Doctrine reference: [character_visual_prompt_kit_doctrine.md](../operator_guides/character_visual_prompt_kit_doctrine.md)
> Identity anchor: `[CXX_IDENTITY_ANCHOR_V001]`
> Look variants: `[list look ids from visual_dev/elements/characters/CXX/look_variants/]`

## Character Source (Truth)
- Age range: [from planning/characters/CXX.yaml]
- Screen presence: [from planning/characters/CXX.yaml]
- Costume logic: [from planning/characters/CXX.yaml]
- Silhouette: [from planning/characters/CXX.yaml]
- Color bias: [from planning/characters/CXX.yaml]
- Hair/makeup notes: [from planning/characters/CXX.yaml]

## Seed Registry
- Character seed: `<CHARACTER_SEED>`
- Midjourney V8.1 tail (Stage 1 and Stage 5):
`--v 8.1 --raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --no text logo watermark`
- Midjourney V7 tail (Stage 2 only â€” requires Omni Reference URL from Stage 1 winner):
`--v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout`

## Stage 1 - Identity Exploration Prompt (Midjourney V8.1)
Positive prompt language rules: do NOT use "reference sheet", "character design", "turnaround", "collage", "multi-panel", "grid", "contact sheet", or "character reference composition". Use "clean single-subject production image" or "single frame" instead.
```text
/imagine prompt: [CXX Character identity exploration prompt adapted to truth profile â€” single frame, full body with face readability, clean single-subject production image] --v 8.1 --raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --no text logo watermark
```

## Stage 2 - Identity Exploration 2 (Midjourney V7 + Omni Reference)
Run after selecting the Stage 1 identity direction. Paste Stage 1 winner URL as `--oref`. Three separate `/imagine` calls â€” do NOT merge into one prompt.

### 2A â€” Identity Portrait Probe (close framing, face primacy)
```text
/imagine prompt: [CXX Character] cinematic identity portrait, single frame, head and shoulders close framing, [age + expression band + silhouette descriptors from Stage 1 truth profile], neutral controlled gaze, realistic skin and fabric texture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2B â€” Identity Full-Body Probe (silhouette confirmation, single frame)
```text
/imagine prompt: [CXX Character] cinematic identity full body, single frame, full-body standing pose, [silhouette descriptors], same face geometry as identity source, neutral grounded posture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2C â€” Identity Expression Band Probe (within anchor range, single frame)
```text
/imagine prompt: [CXX Character] cinematic identity variant, single frame, [alternate expression within anchor â€” e.g. alternate between two controlled states], same face geometry and silhouette as identity source, realistic texture, clean neutral backdrop, one image only, expression variant not angle variant --v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

## Stage 3 - GPT Images 2 FRONT HERO LOCK Prompt
```text
Use uploaded [CXX] reference image as identity source, not layout source. Generate one single full-body FRONT hero lock image only. Preserve face geometry, age read, body proportions, and silhouette exactly. No contact sheet recreation.
```

## Stage 4 - GPT Images 2 Four-Perspective Pack
### Perspective 1: Front Hero
```text
[front perspective prompt]
```

### Perspective 2: Three-Quarter Left
```text
[three-quarter left prompt]
```

### Perspective 3: Three-Quarter Right
```text
[three-quarter right prompt]
```

### Perspective 4: Rear or Side
```text
[rear or side prompt]
```

## Stage 5 - Per-Look-Variant Lock Prompts (Midjourney V8.1)
### Look: [LOOK_ID_1] ([scope])
```text
/imagine prompt: [look-specific lock prompt preserving identity source] --v 8.1 --raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --no text logo watermark
```

### Look: [LOOK_ID_2 if exists] ([scope])
```text
/imagine prompt: [look-specific lock prompt preserving identity source] --v 8.1 --raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --no text logo watermark
```

## Aesthetic Pack References
- [pack ids from planning/aesthetic_bible.yaml]

## Operator Notes
- Binaries are external-only.
- Same look only per perspective pack.
- Stage sequence is mandatory (1 -> 2 -> 3 -> 4 -> 5).
- Use external-ref replacement checklist for registration stage.
