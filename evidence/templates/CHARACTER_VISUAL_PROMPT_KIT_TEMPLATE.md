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
- Midjourney V7 tail (Stage 2 only  requires Omni Reference URL from Stage 1 winner):
`--v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout`

## Stage 1 - Identity Exploration Prompt (Midjourney V8.1)
Positive prompt language rules: do NOT use "reference sheet", "character design", "turnaround", "collage", "multi-panel", "grid", "contact sheet", or "character reference composition". Use "clean single-subject production image" or "single frame" instead.
```text
/imagine prompt: [CXX Character identity exploration prompt adapted to truth profile  single frame, full body with face readability, clean single-subject production image] --v 8.1 --raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --no text logo watermark
```

## Stage 2 - Identity Exploration 2 (Midjourney V7 + Omni Reference)
Run after selecting the Stage 1 identity direction. Paste Stage 1 winner URL as `--oref`. Three separate `/imagine` calls  do NOT merge into one prompt.

### 2A  Identity Portrait Probe (close framing, face primacy)
```text
/imagine prompt: [CXX Character] cinematic identity portrait, single frame, head and shoulders close framing, [age + expression band + silhouette descriptors from Stage 1 truth profile], neutral controlled gaze, realistic skin and fabric texture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2B  Identity Full-Body Probe (silhouette confirmation, single frame)
```text
/imagine prompt: [CXX Character] cinematic identity full body, single frame, full-body standing pose, [silhouette descriptors], same face geometry as identity source, neutral grounded posture, clean neutral backdrop, one image only --v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

### 2C  Identity Expression Band Probe (within anchor range, single frame)
```text
/imagine prompt: [CXX Character] cinematic identity variant, single frame, [alternate expression within anchor  e.g. alternate between two controlled states], same face geometry and silhouette as identity source, realistic texture, clean neutral backdrop, one image only, expression variant not angle variant --v 7 --style raw --ar 2:3 --s 100 --seed <CHARACTER_SEED> --chaos 5 --oref <STAGE1_WINNER_URL> --ow 100 --no text, logo, watermark, sheet, contact-sheet, multi-panel, collage, turnaround, character-design, grid, layout
```

## Stage 2.5 - Identity Evidence Set Selection

Recommended default: E01 + E02 + E03. Add E04 only if expression-band probe preserves the same identity.

```yaml
stage3_identity_evidence_set:
  evidence_set_id: [CXX]_STAGE3_IDENTITY_EVIDENCE_SET_V001
  target_character: [CXX]
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
Use the uploaded [CXX] identity evidence set strictly as identity evidence, not as layout references.

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
Rule: run 4 separate GPT Images 2 calls. Do not request multiple directional views in a single call.

### Perspective 1: Rear View (`rear_or_side`)
```text
Use the registered [CXX] FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body rear view image of the same character. Full rear view, back of head and shoulders centered toward the camera, no facial features visible, hair silhouette and back-of-neck continuity preserved.

Keep facial geometry continuity, age read continuity, body proportions, hair silhouette, and wardrobe-world continuity locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround. Do not add text, logos, watermark, or panel labels.

Output exactly one clean full-body image for character continuity use.
```

### Perspective 2: Three-Quarter Left (`three_quarter_left`)
```text
Use the registered [CXX] FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body three-quarter-left image of the same character. Three-quarter angle where the character's left shoulder is closer to the camera and rotated slightly toward it; the character's right cheek is the dominant facial plane in the frame; the character's left ear is partially visible at the frame edge; right ear hidden behind the head.

Keep facial geometry, age read, body proportions, hair silhouette, and wardrobe-world continuity locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not use ambiguous camera-frame directional wording. Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround.

Output exactly one clean full-body image for character continuity use.
```

### Perspective 3: Right Profile Side (`right_profile_side`)
```text
Use the registered [CXX] FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body strict 90-degree right-profile image of the same character. The character's right ear is closest to the camera; the character's left ear is fully hidden behind the head; one full side facial plane is visible.

Keep facial geometry, age read, body proportions, hair silhouette, and wardrobe-world continuity locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not use ambiguous camera-frame directional wording. Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround.

Output exactly one clean full-body image for character continuity use.
```

### Perspective 4: Left Profile Side (`left_profile_side`)
```text
Use the registered [CXX] FRONT HERO LOCK as the strict identity anchor.

Generate ONE single full-body strict 90-degree left-profile image of the same character. The character's left ear is closest to the camera; the character's right ear is fully hidden behind the head; one full side facial plane is visible.

Keep facial geometry, age read, body proportions, hair silhouette, and wardrobe-world continuity locked to the anchor. Keep lighting and lens feel consistent with the anchor.

Do not use ambiguous camera-frame directional wording. Do not redesign the character. Do not stylize into illustration. Do not produce a contact sheet, collage, multi-panel layout, or turnaround.

Output exactly one clean full-body image for character continuity use.
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
- Stage sequence is mandatory (1 -> 2 -> 2.5 -> 3 -> 4 -> 5).
- Use external-ref replacement checklist for registration stage.

