# GPT Images 2 Perspective Output Registration (Metadata-Only)

This workflow is metadata-only.

Human operators generate GPT Images 2 perspective outputs outside this repository. The repository stores only registration and review metadata.

## What The Repository Stores
- Prompt IDs used for generation.
- `external_storage_ref` or manual/platform reference strings.
- Quality scores after human review.
- `local_media_index` metadata entries.
- `image_selection` metadata entries.

## What The Repository Does Not Store
- Raw generated images.
- Preview image binaries.
- Platform downloads.
- Screenshots.
- Zipped image batches.

## Required Outputs

Under Element Reference Generation Policy v2
(`perspective_policy: three_view_scale_angle_v2`), each pack has **three**
scale-angle outputs — no rear view, no left/right directional views:

- `front_reference`
- `three_quarter_medium_reference`
- `three_quarter_close_reference`

Records authored before the `element-reference-policy-v2` cutoff are
grandfathered and may keep their legacy directional or four-view outputs. See
`docs/methodology/element_reference_generation_policy.md`.

## Full body is not a gate

`full_body_visible` is optional metadata on the perspective pack record. Full
body / head-to-toe coverage is **not** a QC pass/fail criterion — character
references are scored on identity readability.

## Safe Registration Sequence
1. Generate outputs externally from the locked reference (for characters, the
   Stage 2 V7 `--oref` refined reference; for non-character elements, the
   ChatGPT Images 2 first reference).
2. Store binaries in external or operator-controlled storage outside this repository.
3. Record external references in the element's `evidence/local_media_indices/` index.
4. Add candidate metadata entries in the element's `image_selection.yaml`.
5. Populate perspective QC scores only after human review of real outputs.
6. Keep `can_advance_to_kling_reference: false` until all three perspective scores meet threshold.

## Warning
Do not commit image binaries to this repository.
