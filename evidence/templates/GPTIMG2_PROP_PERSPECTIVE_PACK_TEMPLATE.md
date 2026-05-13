# Prop GPT Images 2 Perspective Pack Template (Scaffold)

Use this template only after framework approval.

```yaml
schema_version: "0.x-draft"
record_type: gpt_images_perspective_pack
prompt_pack_id: GPTIMG2_PROPXXX_PERSPECTIVE_PACK_V001
status: draft
source_reference_id: PROPXXX_HERO_REFERENCE_V001
target_model: gpt_images_2
target_role: multi_perspective_element_expander
element_id: PROPXXX
element_type: prop
shared_preservation_instruction: >
  Preserve prop identity anchors (handle, logo/marking, asymmetric edge,
  material feature, scale reference), material behavior, and geometry.

prompts:
  - prompt_id: GPTIMG2_PROPXXX_P01_ORTHO_FRONT_V001
    perspective: front_hero
    prompt_text: >
      Generate ONE single strict orthographic front prop view on a neutral clean background.
      Keep logo/marking placement, anchor edges, and front-plane proportions unchanged.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "1:1"

  - prompt_id: GPTIMG2_PROPXXX_P02_ORTHO_SIDE_V001
    perspective: side_depth
    prompt_text: >
      Generate ONE single strict orthographic side prop view.
      Keep asymmetric landmark orientation and material edge transitions fixed.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "1:1"

  - prompt_id: GPTIMG2_PROPXXX_P03_ORTHO_REAR_V001
    perspective: rear_or_side
    prompt_text: >
      Generate ONE single strict orthographic rear prop view.
      Preserve rear-side seams, feature boundaries, and silhouette thickness.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "1:1"

  - prompt_id: GPTIMG2_PROPXXX_P04_TOP_ORTHOGRAPHIC_V001
    perspective: detail_or_threshold
    prompt_text: >
      Generate ONE single strict top orthographic prop view.
      Preserve top-plane proportions, handle orientation, and scale cues.
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
  - prop_continuity_reference
```

Notes:
- This scaffold template intentionally maps candidate prop perspectives to currently available schema enums.
- No lifecycle promotion is authorized by this template.
- No binary registration is authorized by this template.
