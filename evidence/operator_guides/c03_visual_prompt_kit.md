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

## Stage 4 - GPT Images 2 Four-Perspective Pack (sequential separate-call, anatomy-anchored)
Rule: run 4 separate GPT Images 2 calls. Front is owned by Stage 3 and is not regenerated here.

### Perspective 1: Rear View (`rear_or_side`)
```text
Use the registered C03 Birta FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body rear view image of the same character. Full rear view, back of head and shoulders centered toward the camera, no facial features visible, preserve hair silhouette, body proportions, and wardrobe-world continuity.

Keep facial geometry continuity, age read continuity, body proportions, hair silhouette, and wardrobe-world consistency locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround. Do not add text, logos, watermark, or panel labels.

Output exactly one clean full-body image for character continuity use.
```

### Perspective 2: Three-Quarter Left (`three_quarter_left`)
```text
Use the registered C03 Birta FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body three-quarter-left image of the same character. Three-quarter angle where the character's left shoulder is closer to the camera and rotated slightly toward it; the character's right cheek is the dominant facial plane in frame; the character's left ear is partially visible at frame edge; right ear hidden behind the head.

Keep facial geometry, age read, body proportions, hair silhouette, and controlled support-role expression range locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not use ambiguous camera-frame directional wording. Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround.

Output exactly one clean full-body image for character continuity use.
```

### Perspective 3: Right Profile Side (`right_profile_side`)
```text
Use the registered C03 Birta FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body strict 90-degree right-profile image of the same character. The character's right ear is closest to the camera; the character's left ear is fully hidden behind the head; one full side facial plane is visible.

Keep facial geometry, age read, body proportions, hair silhouette, and wardrobe-world continuity locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not use ambiguous camera-frame directional wording. Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround.

Output exactly one clean full-body image for character continuity use.
```

### Perspective 4: Left Profile Side (`left_profile_side`)
```text
Use the registered C03 Birta FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body strict 90-degree left-profile image of the same character. The character's left ear is closest to the camera; the character's right ear is fully hidden behind the head; one full side facial plane is visible.

Keep facial geometry, age read, body proportions, hair silhouette, and wardrobe-world continuity locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not use ambiguous camera-frame directional wording. Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround.

Output exactly one clean full-body image for character continuity use.
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

