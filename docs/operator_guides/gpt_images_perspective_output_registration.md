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

## Required Four Outputs
- `GPTIMG2_C01_P01_FRONT_V001`
- `GPTIMG2_C01_P02_LEFT_V001`
- `GPTIMG2_C01_P03_RIGHT_V001`
- `GPTIMG2_C01_P04_REAR_V001`

## Safe Registration Sequence
1. Generate outputs externally from the locked Midjourney reference.
2. Store binaries in external or operator-controlled storage outside this repository.
3. Record external references in `evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml`.
4. Add candidate metadata entries in `visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml`.
5. Populate perspective QC scores only after human review of real outputs.
6. Keep `can_advance_to_kling_reference: false` until all four perspective scores meet threshold.

## Warning
Do not commit image binaries to this repository.
