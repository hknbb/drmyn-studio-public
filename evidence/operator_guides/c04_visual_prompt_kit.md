# C04 Dimitri Koss - Visual Prompt Kit

> Doctrine reference: [character_visual_prompt_kit_doctrine.md](character_visual_prompt_kit_doctrine.md)
> Identity anchor: `C04_IDENTITY_ANCHOR_V001` (`visual_dev/elements/characters/C04/character_identity_anchor.yaml`)
> Look variants:
> - `C04_LOOK_OPERATIONAL_V001` (SC0002-SC0009)

## Character Source (Truth)
From `planning/characters/C04.yaml`:
- Age range: 40s
- Screen presence: controlled, precise, hard-edged without theatricality
- Costume logic: operational executive tailoring, functional and disciplined
- Silhouette: lean instrument silhouette
- Color bias: dark corporate neutrals with functional contrast
- Hair/makeup notes: professional polish, not fashion-forward

## Seed Registry
- Character seed: `45`
- Midjourney V8.1 tail (Stage 1 and Stage 5):
`--v 8.1 --raw --ar 2:3 --s 100 --seed 45 --chaos 5 --no text logo watermark`
- Midjourney V7 tail (Stage 2 only â€” requires Omni Reference URL from Stage 1 winner):
`--v 7 --style raw --ar 2:3 --s 100 --seed 45 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout`

## Stage 1 - Identity Exploration Prompt (Midjourney)

```text
/imagine prompt: C04 Dimitri Koss cinematic identity exploration, man in his 40s, lean instrument silhouette, controlled hard-edged precision, no overt menace, no action-hero posing, dark corporate neutrals with functional contrast, operational executive tailoring, no flashy styling, no glamour retouching, no cyberpunk, no neon, clean single-subject production image, full body with face readability, single frame --v 8.1 --raw --ar 2:3 --s 100 --seed 45 --chaos 5 --no text logo watermark
```

## Stage 2 - Identity Exploration 2 (Midjourney V7 + Omni Reference)
Run after selecting the Stage 1 identity direction. Paste Stage 1 winner URL as `--oref`. Three separate `/imagine` calls.

### 2A â€” Identity Portrait Probe
```text
/imagine prompt: Dimitri Koss cinematic identity portrait, single frame, head and shoulders close framing, man in his 40s, controlled hard-edged precision, no theatrical menace, professional polish, realistic skin texture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed 45 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2B â€” Identity Full-Body Probe
```text
/imagine prompt: Dimitri Koss cinematic identity full body, single frame, full-body standing pose, lean instrument silhouette, same face geometry as identity source, dark corporate neutrals with functional contrast, neutral grounded posture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed 45 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2C â€” Identity Expression Band Probe
```text
/imagine prompt: Dimitri Koss cinematic identity variant, single frame, watchful assessment expression within calm procedural neutrality range, same face geometry and lean instrument silhouette as identity source, realistic texture, clean neutral backdrop, one image only, expression variant not angle variant --v 7 --style raw --ar 2:3 --s 100 --seed 45 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

## Stage 3 - GPT Images 2 FRONT HERO LOCK Prompt

```text
Use the uploaded C04 Dimitri Koss reference image as identity source only, not as layout source. Generate one single full-body FRONT hero lock image with identical face geometry, age read, body proportions, and lean instrument silhouette. Keep controlled hard-edged precision without theatrical menace. Neutral clean background, realistic texture, no contact sheet, no redesign, no text, no logo, no watermark, no extra characters.
```

## Stage 4 - GPT Images 2 Four-Perspective Pack
Rule: one look per pack, no look mixing.

### Perspective 1: Front Hero
```text
Using the locked C04 identity source, generate one full-body FRONT view. Preserve identical face geometry, body proportions, silhouette, and exact same look styling.
```

### Perspective 2: Three-Quarter Left
```text
Using the locked C04 identity source, generate one full-body three-quarter LEFT view (about 45 degrees). Preserve identical identity anchors and exact same look styling as Perspective 1.
```

### Perspective 3: Three-Quarter Right
```text
Using the locked C04 identity source, generate one full-body three-quarter RIGHT view (about 45 degrees). Preserve identical identity anchors and exact same look styling as Perspectives 1-2.
```

### Perspective 4: Rear or Side
```text
Using the locked C04 identity source, generate one full-body REAR view (or strict SIDE if rear fails). Preserve identity anchors and exact same look styling as Perspectives 1-3.
```

## Stage 5 - Per-Look-Variant Lock Prompts (Midjourney)

### Look: OPERATIONAL (`C04_LOOK_OPERATIONAL_V001`, SC0002-SC0009)

```text
/imagine prompt: C04 Dimitri Koss look lock OPERATIONAL, preserve established C04 identity source exactly, field operational context cues, tactical-tailored mix, dark corporate neutrals with functional contrast, same lean instrument silhouette, no overt menace, no redesign, no drift --v 8.1 --raw --ar 2:3 --s 100 --seed 45 --chaos 5 --no text logo watermark
```

## Aesthetic Pack References
No dedicated character-specific aesthetic pack found; use `planning/aesthetic_bible.yaml` project-level packs and scene-level context.

## Operator Notes
- Binaries stay external; repository keeps metadata only.
- Stage sequence is mandatory: Stage 1 -> Stage 2 -> Stage 3 -> Stage 4 -> Stage 5.
- Keep look continuity strictly within `C04_LOOK_OPERATIONAL_V001` scope.
- Use [gpt_images_external_ref_replacement_checklist.md](gpt_images_external_ref_replacement_checklist.md) for real external-ref registration workflow.
