# C03 Birta - Visual Prompt Kit

> Doctrine reference: [character_visual_prompt_kit_doctrine.md](character_visual_prompt_kit_doctrine.md)
> Identity anchor: `C03_IDENTITY_ANCHOR_V001` (`visual_dev/elements/characters/C03/character_identity_anchor.yaml`)
> Look variants:
> - `C03_LOOK_DOMESTIC_STAFF_V001` (SC0001)

## Character Source (Truth)
From `planning/characters/C03.yaml`:
- Age range: 70s
- Screen presence: compact, work-shaped, quietly authoritative, observant
- Costume logic: practical domestic workwear, no stylized nostalgia
- Silhouette: compact working silhouette
- Color bias: muted domestic/service neutrals
- Hair/makeup notes: age and use read honestly, no caricature

## Seed Registry
- Character seed: `44`
- Midjourney V8.1 tail (Stage 1 and Stage 5):
`--v 8.1 --raw --ar 2:3 --s 100 --seed 44 --chaos 5 --no text logo watermark`
- Midjourney V7 tail (Stage 2 only  requires Omni Reference URL from Stage 1 winner):
`--v 7 --style raw --ar 2:3 --s 100 --seed 44 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout`

## Stage 1 - Identity Exploration Prompt (Midjourney)

```text
/imagine prompt: C03 Birta cinematic identity exploration, woman in her 70s, compact work-shaped silhouette, quietly authoritative and observant practical domestic presence, muted service neutrals, practical domestic workwear logic, realistic skin texture, realistic fabric texture, no stylized nostalgia, no grandmother trope, no period drama styling, no romanticized housekeeper aesthetic, no fashion editorial exaggeration, clean single-subject production image, full body with face readability, single frame --v 8.1 --raw --ar 2:3 --s 100 --seed 44 --chaos 5 --no text logo watermark
```

## Stage 2 - Identity Exploration 2 (Midjourney V7 + Omni Reference)
Run after selecting the Stage 1 identity direction. Paste Stage 1 winner URL as `--oref`. Three separate `/imagine` calls.

### 2A  Identity Portrait Probe
```text
/imagine prompt: Birta cinematic identity portrait, single frame, head and shoulders close framing, woman in her 70s, compact work-shaped presence, quietly authoritative and observant, age and use read honestly, realistic skin texture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed 44 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2B  Identity Full-Body Probe
```text
/imagine prompt: Birta cinematic identity full body, single frame, full-body standing pose, compact working silhouette, same face geometry as identity source, muted service neutrals, neutral grounded posture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed 44 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2C  Identity Expression Band Probe
```text
/imagine prompt: Birta cinematic identity variant, single frame, quiet watchful assessment expression within still domestic authority range, same face geometry and compact working silhouette as identity source, realistic texture, clean neutral backdrop, one image only, expression variant not angle variant --v 7 --style raw --ar 2:3 --s 100 --seed 44 --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

## Stage 2.5 - Identity Evidence Set Selection
Recommended default: E01 + E02 + E03. Add E04 only if expression-band probe preserves the same identity.

```yaml
stage3_identity_evidence_set:
  evidence_set_id: C03_STAGE3_IDENTITY_EVIDENCE_SET_V001
  target_character: C03
  target_stage: GPT_IMAGES_2_FRONT_HERO_LOCK
  upload_count: <1-4>
  uploaded_slots:
    - slot_id: E01_STAGE1_WINNER
      source_stage: STAGE_1_IDENTITY_EXPLORATION
      role: primary_identity_direction
      included: true
      external_ref: <operator_external_ref_or_note>
    - slot_id: E02_STAGE2A_PORTRAIT
      source_stage: STAGE_2A_IDENTITY_PORTRAIT_PROBE
      role: face_topology_anchor
      included: <true_or_false>
      external_ref: <operator_external_ref_or_note>
      excluded_reason: <required_if_included_false>
    - slot_id: E03_STAGE2B_FULL_BODY
      source_stage: STAGE_2B_IDENTITY_FULL_BODY_PROBE
      role: silhouette_body_proportion_anchor
      included: <true_or_false>
      external_ref: <operator_external_ref_or_note>
      excluded_reason: <required_if_included_false>
    - slot_id: E04_STAGE2C_EXPRESSION_BAND
      source_stage: STAGE_2C_IDENTITY_EXPRESSION_BAND_PROBE
      role: expression_range_check
      included: <true_or_false>
      external_ref: <operator_external_ref_or_note>
      excluded_reason: <required_if_included_false>
```

## Stage 3 - GPT Images 2 FRONT HERO LOCK from Identity Evidence Set

```text
Use the uploaded C03 Birta identity evidence set strictly as identity evidence, not as layout references.

The uploaded set may contain 1 to 4 images selected from these slots:
E01_STAGE1_WINNER: primary identity direction
E02_STAGE2A_PORTRAIT: face topology anchor
E03_STAGE2B_FULL_BODY: silhouette and body proportion anchor
E04_STAGE2C_EXPRESSION_BAND: expression range check

Consolidate only the shared identity features across the uploaded images into one single full-body FRONT hero lock image of the same character. Preserve consistent facial geometry, age read, body proportions, hair silhouette, body silhouette, and expression range.

Do not average into a new face. Do not mix conflicting details. If one uploaded image conflicts with the others, prioritize the most consistent shared identity features and ignore the outlier.

Generate one single full-body front-facing character image only. Neutral clean background, natural cinematic realism, no text, no logos, no watermark, no contact sheet, no collage, no multi-panel output.
```

## Stage 4 - GPT Images 2 Four-Perspective Pack
Rule: one look per pack, no look mixing.

### Perspective 1: Front Hero
```text
Using the locked C03 identity source, generate one full-body FRONT view. Preserve identical face geometry, body proportions, silhouette, and exact same look styling.
```

### Perspective 2: Three-Quarter Left
```text
Using the locked C03 identity source, generate one full-body three-quarter LEFT view (about 45 degrees). Preserve identical identity anchors and exact same look styling as Perspective 1.
```

### Perspective 3: Three-Quarter Right
```text
Using the locked C03 identity source, generate one full-body three-quarter RIGHT view (about 45 degrees). Preserve identical identity anchors and exact same look styling as Perspectives 1-2.
```

### Perspective 4: Rear or Side
```text
Using the locked C03 identity source, generate one full-body REAR view (or strict SIDE if rear fails). Preserve identity anchors and exact same look styling as Perspectives 1-3.
```

## Stage 5 - Per-Look-Variant Lock Prompts (Midjourney)

### Look: DOMESTIC_STAFF (`C03_LOOK_DOMESTIC_STAFF_V001`, SC0001)

```text
/imagine prompt: C03 Birta look lock DOMESTIC_STAFF, preserve established C03 identity source exactly, LOC001 Vale residence domestic context, service apron over practical work garments when consistent with wardrobe metadata, same compact work-shaped silhouette, same quietly authoritative presence, muted service neutrals, no redesign, no drift --v 8.1 --raw --ar 2:3 --s 100 --seed 44 --chaos 5 --no text logo watermark
```

## Aesthetic Pack References
No dedicated character-specific aesthetic pack found; use `planning/aesthetic_bible.yaml` project-level packs and scene-level context.

## Operator Notes
- Binaries stay external; repository keeps metadata only.
- Stage sequence is mandatory: Stage 1 -> Stage 2 -> Stage 2.5 -> Stage 3 -> Stage 4 -> Stage 5.
- Keep look continuity strictly within `C03_LOOK_DOMESTIC_STAFF_V001` scope.
- Use [gpt_images_external_ref_replacement_checklist.md](gpt_images_external_ref_replacement_checklist.md) for real external-ref registration workflow.
