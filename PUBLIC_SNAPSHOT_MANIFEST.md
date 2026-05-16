# Public Snapshot Manifest — v0.17.0

This document enumerates the methodology artifacts included in the v0.17.0 public methodology checkpoint and explicitly lists what is excluded.

---

## Included: Methodology Documentation

| File | Description |
|------|-------------|
| `docs/methodology/element_reference_generation_policy.md` | Element Reference Generation Policy v2 doctrine |
| `docs/methodology/agent_prompt_pipeline.md` | Agent prompt pipeline methodology |
| `docs/methodology/artifact_policy.md` | Artifact lifecycle policy |
| `docs/methodology/data_management_plan.md` | Data management plan |
| `docs/methodology/kling_native_audio_pass_policy.md` | Native audio pass policy |
| `docs/methodology/omni_prompt_component_model.md` | Omni prompt component model |
| `docs/methodology/omni_prompt_variant_policy.md` | Omni prompt variant policy |
| `docs/methodology/provenance_policy.md` | Provenance policy |
| `docs/methodology/reproducibility_statement.md` | Reproducibility statement |
| `docs/methodology/storage_policy.md` | Storage policy |
| `docs/methodology/STAGE_A_CLOSURE_SUMMARY.md` | Stage A closure summary |
| `docs/methodology/STAGE_B_PR1_SCHEMA_NOTE.md` | Schema additive-only convention note |

## Included: Operator Guides

| File | Description |
|------|-------------|
| `docs/operator_guides/element_reference_prompting_v2.md` | Element reference prompting v2 operator guide |
| `docs/operator_guides/gpt_images_perspective_output_registration.md` | GPT Images 2 perspective output registration guide |
| `docs/operator_guides/agent_handoff_playbook.md` | Agent handoff playbook |
| `docs/operator_guides/agent_role_contract.md` | Agent role contract |
| `docs/operator_guides/canonical_asset_storage_policy.md` | Canonical asset storage policy |
| `docs/operator_guides/human_agent_copilot.md` | Human-agent copilot guide |
| `docs/operator_guides/kling_omni_cinematic_prompting.md` | Kling Omni cinematic prompting guide |
| `docs/operator_guides/kling_omni_generation_playbook.md` | Kling Omni generation playbook |
| `docs/operator_guides/local_manual_storage_playbook.md` | Local manual storage playbook |
| `docs/operator_guides/model_guidance_refresh_playbook.md` | Model guidance refresh playbook |
| `docs/operator_guides/production_operator_runbook.md` | Production operator runbook |
| `docs/operator_guides/review_and_approval_playbook.md` | Review and approval playbook |
| `docs/operator_guides/storyboard_selection_playbook.md` | Storyboard selection playbook |
| `docs/operator_guides/t2i_image_generation_playbook.md` | T2I image generation playbook |

## Included: Prompt Templates

| File | Description |
|------|-------------|
| `templates/element_reference_prompts/character_mj_v8_narrative_identity.md` | Stage 1 character prompt: MJ V8.1 narrative identity |
| `templates/element_reference_prompts/character_mj_v7_oref_refinement.md` | Stage 2 character prompt: MJ V7 --oref refinement |
| `templates/element_reference_prompts/character_gptimg2_scale_angle_pack.md` | Stage 3 character prompt: GPT Images 2 scale-angle pack |
| `templates/element_reference_prompts/non_character_gptimg2_first_reference.md` | Non-character first reference prompt |
| `templates/element_reference_prompts/non_character_gptimg2_scale_angle_pack.md` | Non-character scale-angle pack prompt |

## Included: Schemas (JSON Schema Draft 2020-12)

All 58 schemas in `schemas/`, including:

| Schema | Notes |
|--------|-------|
| `character_reference_chain.schema.json` | New in v0.17.0 |
| `gpt_images_perspective_pack.schema.json` | Extended in v0.17.0 (v2 branch added) |
| `perspective_qc_report.schema.json` | Extended in v0.17.0 (v2 QC fields added) |
| `kling_element_reference_record.schema.json` | Extended in v0.17.0 (v2 branch added) |
| All other schemas | Unchanged from prior releases |

## Included: Model Guides

| File | Description |
|------|-------------|
| `docs/model_guides/midjourney.yaml` | Midjourney model guide (policy v2 rule added) |
| `docs/model_guides/chatgpt_image.yaml` | ChatGPT Image / GPT Images 2 model guide (policy v2 rule added) |
| All other model guides | Unchanged |

## Included: Validation Scripts and Tests

- `scripts/validate_production_records.py`
- `scripts/validate_prompt_records.py`
- `scripts/validators/` (all validators)
- `scripts/agents/` (all agent scripts)
- `tests/` (all test files, including 4 new test modules added in v0.17.0)

---

## Excluded: What Is NOT in This Release

| Category | Reason |
|----------|---------|
| Raw image files (JPG, PNG, WEBP) | Binary media; stored externally, referenced by metadata only |
| Video files (MP4, MOV) | Binary media; stored externally, referenced by metadata only |
| Audio files (WAV, MP3, AAC) | Binary media; stored externally, referenced by metadata only |
| Real external reference URLs | C02–C05 and most records use `pending_external://` placeholders. **Exception:** `visual_dev/elements/characters/C01/identity_evidence_sets/C01_STAGE3_IDENTITY_EVIDENCE_SET_HOME_MORNING_V001.yaml` slot E01 contains a live `https://cdn.midjourney.com/...` URL. This file must be excluded or the URL redacted before syncing to the public repo — see `PUBLIC_SANITIZATION_CHECKLIST.md`. |
| API keys or credentials | Never committed; all auth is human-gated |
| Personal data | Only ORCID identifiers and affiliations that are already publicly registered |
| Unpublished screenplay content | Scene excerpts are research scaffolds only; full screenplay not committed |
| Private production notes | Operator session logs with personal annotations are excluded |

---

## Record Counts at Checkpoint

- Production records scanned: 98
- Valid: 98 / Invalid: 0
- Test suite: 1441 passed
