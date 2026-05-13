# C01 Nadia - Visual Prompt Kit

> Doctrine reference: [character_visual_prompt_kit_doctrine.md](character_visual_prompt_kit_doctrine.md)
> Identity anchor: `C01_IDENTITY_ANCHOR_V001` (`visual_dev/elements/characters/C01/character_identity_anchor.yaml`)
> Look variants:
> - `C01_LOOK_HOME_MORNING_V001` (SC0001-SC0003)
> - `C01_LOOK_NIGHT_TIRED_V001` (SC0004-SC0009)

## Character Source (Truth)
From `planning/characters/C01.yaml`:
- Age range: early to mid 30s
- Screen presence: controlled, observant, physically exact
- Costume logic: elite domestic presentation with practical mobility
- Silhouette: lean, upright, economical movement
- Color bias: muted neutrals and controlled domestic tones
- Hair/makeup: natural restraint, fatigue legibility allowed

## Seed Registry
- Character seed: `42`
- Midjourney V8.1 tail (Stage 1 and Stage 5):
`--v 8.1 --raw --ar 2:3 --s 100 --seed 42 --chaos 5 --no text logo watermark`
- Midjourney V7 tail (Stage 2 only â€” requires Omni Reference URL from Stage 1 winner):
`--v 7 --style raw --ar 2:3 --s 100 --seed 42 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout`

## Stage 1 - Identity Exploration Prompt (Midjourney)
Use this first, before any look-specific lock attempt.

```text
/imagine prompt: C01 Nadia cinematic identity exploration, woman in early to mid 30s, controlled observant presence, lean upright economical silhouette, short wavy bob, precise stillness and tactical composure, muted domestic neutrals, natural restrained makeup, realistic skin and fabric texture, no fashion editorial exaggeration, no glam retouch, no cyberpunk, full body with face readability, clean neutral backdrop --v 8.1 --raw --ar 2:3 --s 100 --seed 42 --chaos 5 --no text logo watermark
```

## Stage 2 - Identity Exploration 2 (Midjourney V7 + Omni Reference)
Run after selecting the Stage 1 identity direction. Paste Stage 1 winner URL as `--oref`. Three separate `/imagine` calls.

### 2A â€” Identity Portrait Probe
```text
/imagine prompt: Nadia cinematic identity portrait, single frame, head and shoulders close framing, woman in early to mid 30s, controlled observant presence, short wavy bob, precise stillness, natural restrained expression, realistic skin texture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed 42 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2B â€” Identity Full-Body Probe
```text
/imagine prompt: Nadia cinematic identity full body, single frame, full-body standing pose, lean upright economical silhouette, same face geometry as identity source, muted domestic neutrals, neutral grounded posture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed 42 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2C â€” Identity Expression Band Probe
```text
/imagine prompt: Nadia cinematic identity variant, single frame, tired but watchful expression within controlled range, same face geometry and lean upright silhouette as identity source, realistic skin texture, clean neutral backdrop, one image only, expression variant not angle variant --v 7 --style raw --ar 2:3 --s 100 --seed 42 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

## Stage 3 - GPT Images 2 FRONT HERO LOCK Prompt
Use uploaded Stage 2 output as identity source. Do not recreate a sheet layout.

```text
Use the uploaded C01 Nadia reference image strictly as an identity source, not as a layout to recreate. Generate one single full-body FRONT hero lock image of the same character with identical face geometry, age read, body proportions, and short wavy bob silhouette. Keep expression controlled and observant. Neutral clean background, natural cinematic realism, no text, no logos, no watermark, no contact sheet, no multi-panel output.
```

## Stage 4 - GPT Images 2 Four-Perspective Pack
Rule: same identity and same look within one pack.

### Perspective 1: Front Hero
```text
Using the locked C01 identity source, generate a full-body FRONT view. Keep identical face geometry, body proportions, hair silhouette, and the same look styling. Neutral background, realistic texture fidelity, no redesign.
```

### Perspective 2: Three-Quarter Left
```text
Using the locked C01 identity source, generate a full-body three-quarter LEFT view (about 45 degrees). Keep identical identity anchors and the exact same look styling as Perspective 1.
```

### Perspective 3: Three-Quarter Right
```text
Using the locked C01 identity source, generate a full-body three-quarter RIGHT view (about 45 degrees). Keep identical identity anchors and the exact same look styling as Perspectives 1-2.
```

### Perspective 4: Rear or Side
```text
Using the locked C01 identity source, generate a full-body REAR view (or strict SIDE if rear fails). Preserve identity anchors and keep the exact same look styling as Perspectives 1-3.
```

## Stage 5 - Per-Look-Variant Lock Prompts (Midjourney)

### Look: HOME_MORNING (`C01_LOOK_HOME_MORNING_V001`, SC0001-SC0003)
Appearance targets:
- fatigue_level: nominal
- damage_level: none
- hair_state_within_anchor: controlled morning restraint

```text
/imagine prompt: C01 Nadia look lock HOME_MORNING, preserve established C01 identity source exactly, domestic morning continuity, controlled morning restraint styling, nominal fatigue, no damage, short wavy bob controlled within anchor, muted domestic neutrals, practical elite domestic presentation, full-body plus face readability, no identity drift, no wardrobe world change --v 8.1 --raw --ar 2:3 --s 100 --seed 42 --chaos 5 --no text logo watermark
```

### Look: NIGHT_TIRED (`C01_LOOK_NIGHT_TIRED_V001`, SC0004-SC0009)
Appearance targets:
- fatigue_level: tired
- damage_level: none
- hair_state_within_anchor: loosened within short wavy bob anchor

```text
/imagine prompt: C01 Nadia look lock NIGHT_TIRED, preserve established C01 identity source exactly, night continuity with visible fatigue, tired but controlled expression, no damage, short wavy bob loosened within anchor, muted low-key domestic/night palette, same facial topology and body proportions, full-body plus face readability, no redesign --v 8.1 --raw --ar 2:3 --s 100 --seed 42 --chaos 5 --no text logo watermark
```

## Aesthetic Pack References
From `planning/aesthetic_bible.yaml`:
- `VALE_DOMESTIC_RESTRAINT`

Suggested keyword direction:
- controlled domestic restraint cinematography
- muted domestic neutrals
- filtered cold daylight (morning continuity)
- no decorative warmth drift

## Operator Notes
- Store generated binaries externally; repository keeps metadata only.
- Stage 4 pack must not mix `HOME_MORNING` and `NIGHT_TIRED`.
- Stage 1 result informs Stage 2; Stage 3 must consume Stage 2 output.
- For real external-ref registration flow, follow:
  [gpt_images_external_ref_replacement_checklist.md](gpt_images_external_ref_replacement_checklist.md)
- Do not promote lifecycle states from this kit.
