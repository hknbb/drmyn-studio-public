# GPT Images 2 External Ref Replacement Checklist (Metadata-Only)

This checklist defines a controlled human workflow for replacing
`pending_external://...` references after real GPT Images 2 outputs exist
outside the repository.

This is a metadata-only process. It does not authorize or require binary
commits.

## Scope
- Applies to SC0001 / C01 GPT Images 2 perspective outputs.
- Applies to these four prompt IDs only:
  - `GPTIMG2_C01_P01_FRONT_V001`
  - `GPTIMG2_C01_P02_LEFT_V001`
  - `GPTIMG2_C01_P03_RIGHT_V001`
  - `GPTIMG2_C01_P04_REAR_V001`

## Storage Rule
Generated image binaries must stay outside this repository.

Do not commit:
- png
- jpg/jpeg
- webp
- psd
- tiff
- zip
- screenshots
- platform-export image files

## Controlled Replacement Steps
1. Confirm all four outputs exist in external/operator-controlled storage.
2. Fill `evidence/templates/GPTIMG2_C01_EXTERNAL_REF_REGISTRATION_TEMPLATE.yaml`.
3. Verify each slot has:
   - non-pending `replacement_external_storage_ref`
   - `repo_binary_committed: false`
   - `operator_verified: true` only when manually confirmed
4. In a dedicated follow-up PR, copy only approved external refs into:
   - `visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml`
   - `evidence/local_media_indices/LOCAL_MEDIA_INDEX_C01_GPTIMG2_PERSPECTIVES_V001.yaml`
5. Keep candidate status as `candidate` during registration; do not set
   `selected`/`canonical` in this step.
6. Keep perspective QC scores null and decisions pending until human image
   review is completed.
7. Keep `can_advance_to_kling_reference: false` until refs are non-pending and
   QC requirements are actually satisfied.

## Gate Reminder
`pending_external://` refs are valid only for scaffold/not-advancing states.
Advancement gating requires real non-pending external refs in both
`image_selection` and `local_media_index` metadata.

## Template Status
`evidence/templates/*.yaml` files are operator templates only. They are not
applied production records and are not interpreted as lifecycle promotions.
