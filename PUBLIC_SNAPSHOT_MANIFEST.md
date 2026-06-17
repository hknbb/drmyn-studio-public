# Public Snapshot Manifest — v0.18.0

This document enumerates the methodology artifacts included in the v0.18.0 public methodology checkpoint and explicitly lists what is excluded.

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
| `docs/methodology/scene_continuity_system.md` | Scene continuity system methodology |
| `docs/methodology/STAGE_A_CLOSURE_SUMMARY.md` | Stage A closure summary |
| `docs/methodology/STAGE_B_PR1_SCHEMA_NOTE.md` | Schema additive-only convention note |

## Included: Operator Guides

| File | Description |
|------|-------------|
| `docs/operator_guides/element_reference_prompting_v2.md` | Element reference prompting v2 operator guide |
| `docs/operator_guides/gpt_images_perspective_output_registration.md` | GPT Images 2 perspective output registration guide |
| `docs/operator_guides/kling_literal_multishot_playbook.md` | **New in v0.18.0** — Kling literal multi-shot grammar, ban-list, dual-field convention |
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
| `docs/operator_guides/shot_photography_contact_sheet.md` | Historical/deprecated for SC0014 (Anchor & Animate retired); retained as reference |
| `docs/operator_guides/storyboard_selection_playbook.md` | Storyboard selection playbook |
| `docs/operator_guides/t2i_image_generation_playbook.md` | T2I image generation playbook |
| `AGENTS.md` | **New in v0.18.0** — cross-CLI session memory contract, operator commands, agent role table, non-negotiable invariants |

## Included: Prompt Templates

| File | Description |
|------|-------------|
| `templates/element_reference_prompts/character_mj_v8_narrative_identity.md` | Stage 1 character prompt: MJ V8.1 narrative identity |
| `templates/element_reference_prompts/character_mj_v7_oref_refinement.md` | Stage 2 character prompt: MJ V7 --oref refinement |
| `templates/element_reference_prompts/character_gptimg2_scale_angle_pack.md` | Stage 3 character prompt: GPT Images 2 scale-angle pack |
| `templates/element_reference_prompts/non_character_gptimg2_first_reference.md` | Non-character first reference prompt |
| `templates/element_reference_prompts/non_character_gptimg2_scale_angle_pack.md` | Non-character scale-angle pack prompt |

## Included: Schemas (JSON Schema Draft 2020-12)

All schemas in `schemas/`, including:

| Schema | Notes |
|--------|-------|
| `prompt_record.schema.json` | Extended in v0.18.0: `language_profile`, `continuity_seed_ref`, `anchored_i2v` triplet ban under `text_only` |
| `omni_clip_manifest.schema.json` | Extended in v0.18.0: `render_action`, `render_camera`, `render_diegetic_audio`, `render_label` |
| `scene_continuity_ledger.schema.json` | Extended in v0.18.0: `render_start_state`, `render_end_state` |
| `extracted_frame_reference.schema.json` | New in v0.18.0 |
| `image_selection.schema.json` | New in v0.18.0 |
| `golden_reference_plan.schema.json` | New in v0.18.0 |
| `omni_set_gate.schema.json` | New in v0.18.0 |
| `shot_list_omni_suggestion.schema.json` | New in v0.18.0 |
| `system_character_element.schema.json` | New in v0.18.0 |
| `character_reference_chain.schema.json` | Added in v0.17.0 |
| `gpt_images_perspective_pack.schema.json` | Extended in v0.17.0 (v2 branch) |
| `perspective_qc_report.schema.json` | Extended in v0.17.0 (v2 QC fields) |
| `kling_element_reference_record.schema.json` | Extended in v0.17.0 (v2 branch) |
| All other schemas | Unchanged from prior releases |

## Included: Model Guides

| File | Description |
|------|-------------|
| `docs/model_guides/kling_omni.yaml` | Kling Omni model guide (literal multi-shot guidance added) |
| `docs/model_guides/midjourney.yaml` | Midjourney model guide (policy v2 rule added in v0.17.0) |
| `docs/model_guides/chatgpt_image.yaml` | ChatGPT Image / GPT Images 2 model guide (policy v2 rule added in v0.17.0) |
| All other model guides | Unchanged |

## Included: Validation Scripts and Tests

- `scripts/validate_production_records.py`
- `scripts/validate_prompt_records.py` — **new in v0.18.0**: strict ban validator
- `scripts/archive_media.py` — **new in v0.18.0**: binary archival tool (metadata-only index writer)
- `scripts/update_project_state.py` — **new in v0.18.0**: session dashboard auto-update hook
- `scripts/validators/` (all validators, including 9 new/updated in v0.18.0)
- `scripts/agents/` (all agent scripts, including `kling_literal_alias_locked` render path)
- `tests/` (all test files; 1520 passed / 3 skipped)

---

## Excluded: What Is NOT in This Release

| Category | Reason |
|----------|---------|
| Raw image files (JPG, PNG, WEBP) | Binary media; stored externally, referenced by metadata only |
| Video files (MP4, MOV) | Binary media; stored externally, referenced by metadata only |
| Audio files (WAV, MP3, AAC) | Binary media; stored externally, referenced by metadata only |
| `planning/scenes/` | Scene cards, beat plans, dialogue — story content, not methodology |
| `planning/characters/`, `planning/locations/`, `planning/props/` | Character/location/prop descriptions — story content |
| `source/` | Screenplay, dossiers, story bibles — excluded entirely |
| `prompts/draft/` | Scene-specific Kling Omni prompts — production content, not methodology |
| `evidence/operator_sessions/` | Operator production session logs — private production records |
| `evidence/local_media_indices/` | Binary archive indices — private production records |
| `evidence/perspective_qc/` | Per-element QC reports referencing private production runs |
| `visual_dev/elements/` | KER records, image_selection.yaml, perspective packs — production content |
| `visual_dev/omni_sets/` | Element binding records referencing specific production outputs |
| `planning/manifests/` | Scene/character rosters referencing story content |
| Real external reference URLs (CDN, oref) | Live in production content paths (excluded above); not present in methodology paths |
| API keys or credentials | Never committed; all auth is human-gated |
| Personal data | Only ORCID identifiers and affiliations already publicly registered |
| `closingpriceclaudecodeanalysisforcode.md` | Internal analysis document, not methodology |
| `drmynstdklingomnideep-research-report.md` | Internal research document, not methodology |

---

## Record Counts at Checkpoint

- Production records scanned: 150
- Valid: 150 / Invalid: 0
- Prompt records validated: 55 / Invalid: 0
- Test suite: 1520 passed / 3 skipped
