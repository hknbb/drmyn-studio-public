# Wardrobe GPT Images 2 Perspective Pack Template (Scaffold)

Use this template only after framework approval.

```yaml
schema_version: "0.x-draft"
record_type: gpt_images_perspective_pack
prompt_pack_id: GPTIMG2_WDXXX_PERSPECTIVE_PACK_V001
status: draft
source_reference_id: WDXXX_HERO_REFERENCE_V001
target_model: gpt_images_2
target_role: multi_perspective_element_expander
element_id: WDXXX
element_type: wardrobe
shared_preservation_instruction: >
  Preserve garment identity anchors (lapel, cuff, pocket, seam, label,
  fabric panel, closure direction), material behavior, and silhouette.

prompts:
  - prompt_id: GPTIMG2_WDXXX_P01_FLAT_LAY_V001
    perspective: usage_angle
    prompt_text: >
      Generate ONE single wardrobe flat-lay view on a neutral clean background.
      Keep closure direction, seam paths, and panel boundaries unchanged.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "2:3"

  - prompt_id: GPTIMG2_WDXXX_P02_MANNEQUIN_FRONT_V001
    perspective: front_hero
    prompt_text: >
      Generate ONE single on-mannequin front view.
      Keep lapel geometry, closure direction, pocket placement, and label region fixed.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "2:3"

  - prompt_id: GPTIMG2_WDXXX_P03_MANNEQUIN_BACK_V001
    perspective: rear_or_side
    prompt_text: >
      Generate ONE single on-mannequin back view.
      Keep back seam topology, panel transitions, and hem behavior consistent with anchor.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "2:3"

  - prompt_id: GPTIMG2_WDXXX_P04_MATERIAL_DETAIL_V001
    perspective: detail_or_threshold
    prompt_text: >
      Generate ONE single close material detail preserving weave, texture,
      stitch direction, and trim continuity.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "1:1"

qc_gate:
  minimum_score: 85
  all_perspectives_required: true
  failed_perspective_revision_only: true

downstream_use:
  - wardrobe_continuity_reference
```

Notes:
- This scaffold template intentionally maps candidate wardrobe perspectives to currently available schema enums.
- No lifecycle promotion is authorized by this template.
- No binary registration is authorized by this template.
