# Location GPT Images 2 Perspective Pack Template (Scaffold)

Use this template only after framework approval.

```yaml
schema_version: "0.x-draft"
record_type: gpt_images_perspective_pack
prompt_pack_id: GPTIMG2_LOCXXX_PERSPECTIVE_PACK_V001
status: draft
source_reference_id: LOCXXX_ESTABLISHING_HERO_REFERENCE_V001
target_model: gpt_images_2
target_role: multi_perspective_element_expander
element_id: LOCXXX
element_type: location
shared_preservation_instruction: >
  Preserve location identity anchors (doorway, window, fireplace, furniture placement,
  threshold detail), spatial geometry, and material behavior.

prompts:
  - prompt_id: GPTIMG2_LOCXXX_P01_ESTABLISHING_HERO_V001
    perspective: front_hero
    prompt_text: >
      Generate ONE single establishing hero location view on a neutral clean frame.
      Keep doorway/window/fireplace relationships and primary furniture layout unchanged.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "16:9"

  - prompt_id: GPTIMG2_LOCXXX_P02_REVERSE_ANGLE_V001
    perspective: reverse_angle
    prompt_text: >
      Generate ONE single reverse-angle location view.
      Keep doorway thresholds, furniture depth order, and material continuity fixed.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "16:9"

  - prompt_id: GPTIMG2_LOCXXX_P03_SIDE_DEPTH_V001
    perspective: side_depth
    prompt_text: >
      Generate ONE single side-depth location view.
      Preserve wall openings, furniture placement ratios, and sightline geometry.
    constraints:
      - no text
      - no logo overlay
      - no watermark
      - no collage
      - no multi-panel output
    expected_output:
      asset_type: still
      aspect_ratio: "16:9"

  - prompt_id: GPTIMG2_LOCXXX_P04_THRESHOLD_DETAIL_V001
    perspective: detail_or_threshold
    prompt_text: >
      Generate ONE single threshold detail location view.
      Preserve trim transitions, material edge behavior, and local scale cues.
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
  - location_continuity_reference
```

Notes:
- This scaffold template intentionally maps candidate location perspectives to currently available schema enums.
- No lifecycle promotion is authorized by this template.
- No binary registration is authorized by this template.
