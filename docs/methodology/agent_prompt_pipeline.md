# Multi-Agent Prompt Transformation Pipeline
## NexusZeroClosingPriceProduction — Production-Grade Film Architecture

---

## Core Principle

**This is not an "AI film generator." It is an auditable, reproducible, academically defensible film production management system that uses AI at each stage.** Every AI-assisted decision (prompt, image selection, shot composition, video take) is traceable to a planning record, validated against a schema, and advanced through human-approved lifecycle stages.

### Three Non-Negotiable Invariants

1. **Controlled model guidance:** Agents may refresh model guidance through a controlled Research Snapshot step. Prompt adapters never use unlogged live internet directly. Every model-specific prompt must cite either a locked model guide or a run-specific guidance snapshot with URLs, retrieval timestamps, and hashes.

2. **Draft-only agent output:** Agents may write only to `prompts/draft/`, `evidence/`, and explicitly allowed metadata-only review/suggestion files under `visual_dev/` (e.g. `image_selection.yaml`, `pack_manifest_update_suggestion.yaml`, `storyboard_options.yaml`, `video_takes.yaml`). Agents never commit binaries, never update `pack_status`/`canon_lock`/`approved`/`locked` fields directly, and never promote lifecycle stages without a human PR.

3. **One prompt record per model:** No shared `prompt_text` across Midjourney, ChatGPT Image, Nano Banana, and Kling Omni.

---

## Branch & Workflow Model (Non-Negotiable)

**`main` is always clean — merge-ready, release-ready.** No direct commits to main from Claude Code or Codex.

### Per-Batch Workflow

```
1. Open feature branch:  feat/batch-{N}-{slug}
2. Claude Code implements only that batch's files (nothing else)
3. PR opened:            feat/batch-{N}-{slug} → main
4. Codex reviews PR:     audits for repo-faithfulness, path correctness, schema drift,
                          fake validation claims, storage policy compliance
5. Patches (if any):     go to the same feature branch (not a separate Codex branch)
6. CI passes → merge to main
7. Next batch: new feature branch
```

### Rules

| Rule | Detail |
|---|---|
| One batch = one feature branch | Never implement two batches in the same branch |
| Claude Code = implementor | Writes all code, schemas, tests, scaffolds |
| Codex = reviewer | Reviews same PR; never writes separate parallel implementation |
| No `claude/batch-*` or `codex/batch-*` permanent branches | Those diverge schemas and create unresolvable conflicts |
| Experiment branches only | `experiment/claude-batch-*` and `experiment/codex-batch-*` used only for architecture comparison |
| Patch commits on same branch | Codex-requested fixes go to same `feat/batch-*` branch, not a new one |

## Human-Agent Copilot Layer (HA-0+)

The HA batch series adds a file-based human-agent copilot layer above the
existing metadata-only pipeline. It does not renumber or replace the earlier
batch sequence.

The layer follows the same production boundaries as the rest of the repo:

- `operator_next_step.py` stays a read-only recommender.
- `copilot_command.py` performs human-triggered write actions.
- `agent_handoff` records in `evidence/agent_handoffs/` let Claude Code, Codex,
  Gemini Code Assist, and the human operator pass context without external
  APIs.
- The canonical Producer/Critic/Director role contract is documented in
  `docs/operator_guides/agent_role_contract.md`.
- The human operator still owns external generation, PR approval, lifecycle
  promotion, and final merges.
- Agents still must not commit binaries, write credentials, use Google Drive
  APIs, or directly edit `pack_status`, `canon_lock`, `approved`, or `locked`.

HA-3a starts with the smallest command surface: `switch` only. `yes`, `no`, and
`revise` remain planned follow-up commands.

HA-2.5 adds a model guidance refresh gate before prompt generation. Dynamic
snapshot prompts must use human-verified, current snapshots; placeholder,
expired, or unverified snapshots are rejected by the critic. The operator flow
is documented in `docs/operator_guides/model_guidance_refresh_playbook.md`.

### Branch Naming Convention

```
feat/batch-0.1-model-guidance-snapshot
feat/batch-0.25-model-guidance-logs
feat/batch-0.5-model-guidance-registry
feat/batch-1-prompt-record-validation
feat/batch-1.5-prop-continuity-normalization
feat/batch-2-context-continuity-utils
feat/batch-3-neutral-brief-generator
feat/batch-4-model-adapters-run-records
feat/batch-5-critic-writer
feat/batch-5.5-image-review-clearance
feat/batch-5.6-production-record-validation
feat/batch-5.75-storyboard-options
feat/batch-5.8-production-dashboard
feat/batch-5.85-operator-guidance
feat/batch-6-pipeline-cli
feat/batch-7-langgraph-orchestration
feat/batch-7.5-shot-list-omni-suggestion
feat/batch-8-kling-omni-adapter
feat/batch-8.5-video-take-review
feat/batch-9-scene-clip-locking
```

### Already Implemented

- **Batch 0.75** — committed to `main` (`78c81a8`): `.gitattributes` storyboard LFS, `.gitignore` video/proxy protections, `docs/methodology/storage_policy.md`
- **Batch 0.1** — committed to `feat/batch-0.1-model-guidance-snapshot` (`9eac2cb`): model guidance snapshot schema, capability matrix, deterministic research scaffold, snapshot evidence directory, tests
- **Batch 0.25** — committed to `feat/batch-0.25-model-guidance-logs` (`ba963c3`): human-curated model guidance source logs
- **Batch 0.5** — committed to `feat/batch-0.5-model-guidance-registry` (`5164a0a`): locked model guidance registry files and model guidance schema
- **Batch 1** — committed to `feat/batch-1-prompt-record-validation` (`0cdf2b6`): prompt record validator, CI update, tests
- **Batch 1.5** — committed to `feat/batch-1.5-prop-continuity-normalization` (`e9b0cb0`): prop state_changes normalization and resolver tests
- **Batch 2** — committed to `feat/batch-2-context-continuity-utils` (`81c8e0f`): source context agent, continuity resolver, tests
- **Batch 3** — committed to `feat/batch-3-neutral-brief-generator` (`618a0e3`): neutral T2I element brief generation, source-cited visual anchors, readiness flags, tests
- **Batch 4** — committed to `feat/batch-4-model-adapters-run-records` (`c2e2a6a`): model adapters, prompt run schema, run cost header, tests
- **Batch 5** — committed to `feat/batch-5-critic-writer` (`ea59ae3`): prompt QA critic, draft writer, prompt/run evidence updates, tests
- **Branches**: `agent/claude-code` and `agent/codex` already exist on origin; **do not use for batch implementation** — they were created before this workflow was defined. Use `feat/batch-*` naming going forward.

### Current Batch State

```
merged to main = fa4c559 (PR #8, 2026-05-01)
implemented through = Batch 9
next phase = post-Batch-9 review / pilot production hardening / clean scientific extraction
```

Batch 9 adds metadata-only final scene clip locking. It reads
`visual_dev/omni_sets/SC####/video_takes.yaml`, verifies exactly one selected
external take, then writes `selected_take.yaml` and
`evidence/scene_clip_map.csv`. It does not run external video tools, copy
video/proxy binaries, modify `video_takes.yaml`, modify scene cards, modify
prompt records, modify pack manifests, or promote unrelated lifecycle state.

---

## Complete Production Pipeline

```
Planning YAML (scene cards, character sheets, locations, props, wardrobe)
  ↓
[Batch 0.1] Dynamic Model Research Snapshot
  → evidence/model_guidance_snapshots/{timestamp}_{model}.yaml
  → docs/model_guides/model_capability_matrix.yaml
  ↓
[Batch 0.5] Model Guidance Registry
  → docs/model_guides/{model}.yaml (locked versioned guides)
  ↓
Source Context + Continuity Resolver + Neutral Brief Agent
  ↓
T2I Model Adapters (reads snapshot or locked guide)
  → prompts/draft/SC####__t2i-{element}-{model}__v##.yaml
  → evidence/prompt_runs/{run_id}.yaml
  ↓ human PR → approved
External generation (Midjourney / ChatGPT Image / Nano Banana)
  ↓ user uploads outputs
Image Review Agent
  → visual_dev/elements/{type}/{id}/image_selection.yaml
  → visual_dev/elements/{type}/{id}/pack_manifest_update_suggestion.yaml (human applies)
  → evidence/asset_clearance/{asset_id}.yaml
  ↓ human PR → pack_status: seeded → approved → locked
Storyboard / Shot Option Agent
  → visual_dev/storyboards/SC####/storyboard_options.yaml
  ↓ human selects composition
Scene Still Prompts (approved direction)
  ↓
Kling Omni Prompt Adapter (Phase 3 only; requires locked element packs + shot_list_omni)
  → prompts/draft/SC####__omni-{slug}-kling-omni__v##.yaml
  ↓ external Kling generation
Video Take Review Agent
  → visual_dev/omni_sets/SC####/video_takes.yaml
  → (needs_prompt_revision → Kling adapter v02)
  ↓ selected
Scene Clip Locking (Batch 9)
  → visual_dev/omni_sets/SC####/selected_take.yaml
  → evidence/scene_clip_map.csv
  → post/edit/proxies/SC####/ (external storage refs, no binary commits)
```

---

## 1. Three-Phase Pipeline

### Phase 1 — T2I Element Prompt Pipeline
**When:** `intake_status=not_yet_collected` or `pack_status=metadata_only`.
**Produces:** Per-model prompt records for character/location/prop/style element packs.
**Target models:** Midjourney, ChatGPT Image, Nano Banana.
**Ends when:** `image_selection.yaml` complete + `pack_status=locked` for all scene elements.

### Phase 2 — Scene Still + Storyboard Pipeline
**When:** Element packs seeded/approved.
**Produces:** Storyboard option boards (≥5 compositions per scene) + scene still prompt records for selected compositions.
**Target models:** Midjourney, ChatGPT Image, Nano Banana.
**Ends when:** Visual direction selected; still prompt locked.

### Phase 3 — Kling Omni Prompt Pipeline
**When:** Element packs locked + storyboard visual direction selected + `shot_list_omni` populated **AND every required element for the shot has passed the element-first gate (see section 1A).**
**Produces:** `omni_instruction`, `video_generation`, `lipsync_shot`, `lipsync_audio`.
**Target model:** Kling only. Passive until Phase 1 and 2 complete AND the per-shot `shot_element_manifest.yaml` reports `gate_status: all_elements_ready`.
**Ends when:** `selected_take.yaml` locked + clip in `post/edit/proxies/`.

---

## 1A. Element-First Gate for Phase 3 (Kling Omni 3)

Phase 3 prompt synthesis is gated. Kling Omni 3 prompts may reference visual elements **only through registered `@alias` values**, never through raw repo-canonical ids or raw human-language names, and never through "text-described scene context" / "prompt-described action" fallbacks. This is the contract the operator depends on: when the prompt is pasted into Kling Omni 3, the substitution layer composites the registered element images into the generated video. Anything that is only described in English text is left to Kling to hallucinate.

### Required pipeline order, per element, per shot

```
Script              Scene script + shot list
   ↓
Element identity    Required visual elements identified (character, location,
                    location_sub_area, prop, wardrobe, style)
   ↓
Midjourney          Hero render. Recorded as a midjourney_prompt.yaml in the
                    element's directory; external generation produces a
                    selected output recorded via external://local_manual/...
                    in image_selection.yaml.
   ↓
ChatGPT Images 2    Three-view expansion that anchors the element's
                    identity across angles. Newly authored element-first
                    records use exactly front_reference, left_reference,
                    and right_reference; rear/back views are not authored.
                    Recorded as gpt_images_perspective_pack.yaml with
                    downstream_use: [kling_omni_3_shot_prompt].
   ↓
Perspective QC      Each perspective scored on five axes (identity_preservation,
                    perspective_usefulness, material_palette_continuity,
                    production_reference_cleanliness, hallucination_absence);
                    all three required views must score >=85 and the
                    operator must approve.
   ↓
Kling element       Element registered in the Kling Omni UI under its
                    @alias. element_bindings.yaml binding_status promoted
                    from planned → created (or higher); provenance
                    activated_by / activated_at populated.
   ↓
Kling reference     kling_element_reference.yaml authored, linking the
                    Midjourney source + three GPT Images 2 perspectives +
                    approval_gate (operator_approved: true,
                    all_perspectives_score_85_plus: true), status
                    promoted draft → review.
   ↓
Shot manifest gate  visual_dev/omni_sets/SC####/shot_element_manifests/<SHOT_ID>.yaml
                    lists the shot's required_elements; the
                    validate_shot_element_manifest validator computes the
                    gate from records: binding_status is created or higher,
                    gpt_images_perspective_pack.status is review or higher,
                    kling_element_reference.status is review or higher,
                    operator_approved is true, all_perspectives_score_85_plus
                    is true, and the required @alias is active.
   ↓
gate_status flip    Operator promotes the manifest's declared
                    gate_status from blocked → all_elements_ready.
   ↓
Prompt synthesis    KlingOmniAdapter.generate_from_clip_manifest() called
                    with shot_element_manifest_ref. Adapter enters strict
                    element-first mode: refuses to emit a prompt if the
                    manifest gate is not all_elements_ready, refuses if
                    required_element_ids resolve to zero active aliases,
                    and refuses if any repo-canonical element id leaks
                    into the synthesized prompt_text.
   ↓
Prompt validation   validate_prompt_records.py enforces the same gate
                    against the emitted prompt YAML: active prompts in
                    prompts/draft/ that target kling_omni must carry a
                    shot_element_manifest_ref, the referenced manifest must
                    compute to gate_status: all_elements_ready, and
                    prompt_text/model-facing text must use registered
                    @alias values rather than raw element names or
                    canonical ids.
```

The pipeline applies the same way to every element type the script requires the viewer to see: **characters, locations, location sub-areas, props, wardrobe.** A location is not exempt from Midjourney → ChatGPT Images 2 → Kling registration just because it is a setting; a prop is not exempt because it is "only a visual cue." The three-view policy applies to newly authored element-first records after PR-0; legacy four-view records are kept only in git history or outside the active clean SC0001 baseline.

### Element readiness is observable

`python scripts/agents/operator_next_step.py --scene SC####` prints a structured report of every shot manifest under `visual_dev/omni_sets/<scene_id>/shot_element_manifests/`. For each required element it shows: element_binding.binding_status, active @alias, presence and status of pack_manifest.yaml / gpt_images_perspective_pack.yaml / kling_element_reference.yaml, approval_gate booleans, whether the slot is `[READY]` or `[BLOCKING]`, and a concrete ordered next-step list for each blocker. The orchestrator writes nothing; it is the canonical "what is missing" view for a scene.

### `not_attached_as_kling_elements` is deprecated

The earlier draft taxonomy let a Kling Omni prompt list elements under `generation_params.not_attached_as_kling_elements` to mean "this element appears in the script but we are not attaching a Kling element for it in this draft; describe it in English instead." That escape hatch is now closed:

- Active Kling Omni prompts must carry a `shot_element_manifest_ref` and may not carry `not_attached_as_kling_elements`; `validate_prompt_records.py` rejects the escape hatch.
- The shot_element_manifest's `environmental_only_allowed_ids` field is the only sanctioned route for text-described elements, and it is reserved for genuinely environmental flourishes (ambient lighting palette notes, soundscape character) that the script does not require the viewer to identify.
- Prompts that script-require an element to be visually present (e.g. a location passage, an off-angle photo frame whose dust-shadow signals intrusion) must register that element through the full pipeline above; they may not be listed in `environmental_only_allowed_ids`.

### Why this exists

Kling Omni 3 is an element-composition model. Telling it "treat the Vale Residence kitchen passage as text-described scene context with pale stone corridor depth, threshold geometry, and filtered early daylight" and "include the intrusion cue as prompt-described action: a Vardova skyline photo frame hanging subtly off-angle, with visible dust-shadow mismatch" leaves Kling to invent both the kitchen and the frame from English, with no continuity to anchor them across shots. The element-first gate forces the registered element to exist before the prompt is written, so the substitution layer composes a deterministic, continuity-locked frame for every required element on every shot.

---

## 2. Complete File Structure

```
docs/
  model_guides/
    sources/
      midjourney_research_log.md      ← Batch 0.25
      chatgpt_image_research_log.md   ← Batch 0.25
      nano_banana_research_log.md     ← Batch 0.25
      kling_omni_research_log.md      ← Batch 0.25
    midjourney.yaml                   ← Batch 0.5 (locked guide)
    chatgpt_image.yaml                ← Batch 0.5
    nano_banana.yaml                  ← Batch 0.5
    kling_omni.yaml                   ← Batch 0.5 stub; Batch 8
    model_capability_matrix.yaml      ← Batch 0.1
  methodology/
    agent_prompt_pipeline.md
    storage_policy.md                 ← Batch 0.75

schemas/
  model_guidance.schema.json          ← Batch 0.5
  model_guidance_snapshot.schema.json ← Batch 0.1
  prompt_run.schema.json              ← Batch 4 (alongside adapters)
  asset_clearance.schema.json         ← Batch 5.5
  prompt_review.schema.json           ← Batch 5.5
  image_selection.schema.json         ← Batch 5.5
  storyboard_option.schema.json       ← Batch 5.75
  video_take.schema.json              ← Batch 8.5
  video_review.schema.json            ← Batch 8.5

scripts/
  validate_prompt_records.py          ← Batch 1
  agents/
    __init__.py
    state.py
    context.py
    orchestrator.py
    source_context.py
    continuity.py
    neutral_brief.py
    model_research.py                 ← Batch 0.1
    adapters/
      __init__.py
      midjourney.py
      chatgpt_image.py
      nano_banana.py
      kling_omni.py                   ← Batch 8
    critic.py
    writer.py
    review_outputs.py                 ← Batch 5.5
    storyboard_options.py             ← Batch 5.75
    video_take_review.py              ← Batch 8.5
    run_pipeline.py
    graph.py                          ← Batch 7 (LangGraph)

evidence/
  model_guidance_snapshots/
    {timestamp}_{model}.yaml          ← Batch 0.1 runtime output
  prompt_runs/
    {run_id}.yaml                     ← Batch 4 output
  prompt_reviews/
    {prompt_id}_review.md             ← user-authored
    {prompt_id}_v##_brief.yaml        ← Review Agent output
  asset_clearance/
    {asset_id}.yaml                   ← Batch 5.5 output
  storyboard_reviews/                 ← Batch 5.75
  video_reviews/                      ← Batch 8.5
  run_costs.csv                       ← Batch 4 (credit tracking)
  scene_clip_map.csv                  ← Batch 9

visual_dev/
  elements/{type}/{id}/
    image_selection.yaml              ← Review Agent writes (Batch 5.5)
    pack_manifest_update_suggestion.yaml ← Review Agent writes; human applies
  storyboards/SC####/
    storyboard_options.yaml           ← Batch 5.75
    frames/                           ← LFS if repo-hosted (see storage policy)
  omni_sets/SC####/
    video_takes.yaml                  ← Batch 8.5
    selected_take.yaml                ← Batch 9

post/
  edit/proxies/SC####/                ← external storage refs, no binary commits (Batch 9)
```

**Dependencies — `pyproject.toml` only:**
```toml
langgraph>=0.2.0
```

---

## 3. Dynamic Model Research Snapshot Layer (Batch 0.1)

**Purpose:** Satisfy the need for current model prompt approaches without breaking reproducibility. Agents do not access the internet per-prompt. Instead, a controlled Research Snapshot step runs once per production batch.

**Workflow:**
```bash
# Step 1: Run research snapshot (before any prompt generation)
python scripts/agents/run_pipeline.py \
  --mode refresh-model-guidance \
  --models midjourney,chatgpt-image,nano-banana,kling-omni \
  --save-snapshot

# Step 2: Generate prompts — pass snapshot directory (one snapshot per model inside)
python scripts/agents/run_pipeline.py \
  --mode generate-prompts \
  --scene-id SC0001 \
  --models midjourney,chatgpt-image,nano-banana \
  --model-guidance-snapshot-dir evidence/model_guidance_snapshots/2026-04-29T153000Z/
# Each prompt record stores its own model's snapshot path in generation_params.model_guidance_snapshot
```

**Snapshot format (`schemas/model_guidance_snapshot.schema.json`):**
```yaml
model_id: midjourney
snapshot_taken_at: "2026-04-29T15:30:00Z"
snapshot_hash: sha256:...
sources:
  - url: "https://docs.midjourney.com/..."
    retrieved_at: "2026-04-29T15:29:50Z"
    http_status: 200
    content_hash: sha256:...
    human_verified: false
    notes: "official docs current parameter reference"
extracted_rules:
  - "Use compact visual clauses"
  - "Lead with subject and dominant quality"
confidence: medium
do_not_use_without_verification:
  - "Any stylistic shorthand not from official docs"
```

**Prompt record provenance when using snapshot:**
```yaml
generation_params:
  model_guidance_mode: dynamic_snapshot
  model_guidance_snapshot: evidence/model_guidance_snapshots/2026-04-29T153000Z_midjourney.yaml
  model_guidance_ref: docs/model_guides/midjourney.yaml
  adapter_name: midjourney
```

**Model Capability Matrix (`docs/model_guides/model_capability_matrix.yaml`):**
```yaml
models:
  midjourney:
    output_type: image
    supports_negative_prompt: limited
    supports_image_reference: true
    supports_seed: true
    supports_consistency_reference: false
    max_prompt_length: unlimited
  chatgpt_image:
    output_type: image
    supports_natural_language_revision: true
    supports_image_editing: true
    supports_negative_prompt: false
  nano_banana:
    output_type: image
    supports_identity_consistency: true
    supports_variation_prompting: true
  kling_omni:
    output_type: video
    supports_elements: true
    supports_camera_motion: true
    supports_video_generation: true
    max_duration_seconds: 10
```

---

## 4. Known Repo Drift — Fix in Batch 1.5

`schemas/prop_record.schema.json` requires `scene_id` + `new_state` in each `state_changes` entry.
Current `planning/props/PROP001.yaml` uses `transition` (text) instead of `scene_id`.

**Target format:**
```yaml
continuity_state:
  initial_state: "White plastic hospital bracelet; Nadia listed as registrant."
  state_changes:
    - scene_id: SC0010
      transition_note: "Between SC0003 and SC0010 (source does not specify exact scene)"
      new_state: "Pale blue band from a later check-up..."
```

Schema change: add optional `transition_note` to `state_changes` items. Keep `additionalProperties: false` otherwise.

**Resolver algorithm:**
```python
def resolve_prop_state_at_scene(prop_id, target_scene_id):
    prop = read_yaml(f"planning/props/{prop_id}.yaml")
    resolved = prop["continuity_state"]["initial_state"]
    changes = sorted(
        prop["continuity_state"].get("state_changes", []),
        key=lambda c: int(c["scene_id"][2:])
    )
    target_num = int(target_scene_id[2:])
    for change in changes:
        if int(change["scene_id"][2:]) <= target_num:
            resolved = change["new_state"]
        else:
            break
    # props_state.yaml overlay (note only)
    ledger = read_yaml("planning/continuity/props_state.yaml") or {}
    note = (f"NOTE: props_state.yaml override: {ledger[target_scene_id][prop_id]}"
            if ledger.get(target_scene_id, {}).get(prop_id) else None)
    if any(m in str(resolved) for m in ("UNRESOLVED", "TODO", "EVIDENCE_THIN")):
        return resolved, "WARNING: unresolved state — do not use in prompt"
    return resolved, note
```

---

## 5. Storage Policy Reconciliation (Batch 0.75)

**Problem:** Plan introduces `visual_dev/storyboards/SC####/frames/` and references to video takes. Current `.gitattributes` only covers `visual_dev/elements/**` for LFS. `visual_dev/omni_sets/README.md` and `post/README.md` explicitly prohibit large binary commits.

**Policy after Batch 0.75:**

| Asset type | Storage |
|---|---|
| Canonical element images (C##, LOC###, PROP###) | Repo + Git LFS (`visual_dev/elements/**`) |
| Storyboard candidate stills | External storage; repo stores metadata/path only |
| Locked storyboard keyframes | Repo + Git LFS if `visual_dev/storyboards/` added to `.gitattributes` |
| Kling video takes (full MP4) | External DVC-style storage; never committed to repo |
| Post-production proxies | External storage; repo stores `external_storage_ref` and `platform_asset_ref` only |

**`video_takes.yaml` correct format (no `local_path` for full MP4):**
```yaml
takes:
  - take_id: SC0001_TAKE001
    platform_asset_ref: "kling://[platform-job-id]"
    external_storage_ref: "dvc://closing-price/SC0001/take001.mp4"
    local_proxy_ref: null           # no binary in repo
    repo_binary_committed: false
    status: rejected
    reason: "Camera drifted away from object evidence"
  - take_id: SC0001_TAKE002
    platform_asset_ref: "kling://[platform-job-id]"
    external_storage_ref: "dvc://closing-price/SC0001/take002.mp4"
    repo_binary_committed: false
    status: selected
    reason: "Best route clarity"
selected_take: SC0001_TAKE002
```

---

## 6. Agent Personas & Responsibilities

### 6A. Orchestrator

Reads scene_card + image pack manifests. Phase detection source priority:
1. `visual_dev/elements/{type}/{id}/image_intake_manifest.yaml` (primary)
2. `visual_dev/elements/{type}/{id}/pack_manifest.yaml` (fallback)
3. Contradictory → `escalate`

Readiness rules: scaffolded/deprecated → skip; TBD visual_targets → skip; promptability < 3 → skip; missing character/location records → escalate.

---

### 6B. Source Context Agent

Reads scene_card, excerpt, brief, character sheets, location, props, wardrobe, style_bible sections (verbatim). Carries UNRESOLVED/EVIDENCE_THIN/TODO_REVIEW as warnings. Never fills missing values.

---

### 6C. Continuity Resolver

Primary source: `planning/props/PROPxxx.yaml`. Overlay: `props_state.yaml`. Chronological numeric sort of `state_changes`. Flags unresolved markers; never injects them into prompts.

---

### 6D. Neutral Brief Agent

Produces model-agnostic briefs with:
- Cited `visual_anchors` (each entry includes source field path)
- Resolved wardrobe state from Continuity Resolver (not raw initial_state)
- Complete `negative_constraints` from do_not_invent_notes + style_bible.do_not_do
- `model_guidance_required: true`
- `is_ready: false` if any continuity state is UNRESOLVED

---

### 6E. Model Research Agent (Batch 0.1)

**Role:** Collects current model guidance and writes a reproducibility-preserving snapshot. Runs once per production batch, not per-prompt.

**Reads:** Official model documentation URLs, release notes, known model behavior docs.

**Writes:** `evidence/model_guidance_snapshots/{timestamp}_{model}.yaml` with:
- Source URLs + retrieval timestamps + content hashes
- Extracted prompt rules
- Confidence level
- Human verification status

**System prompt:**
```
You are the Model Research Agent. Your job is to produce a reproducible snapshot
of current model prompt guidance — not to write prompts.

For each requested model:
1. Search official documentation and verified sources only.
2. Record source URL, retrieval timestamp, and note what the source is.
3. Extract concrete prompt-writing rules.
4. Do NOT use forum posts, unofficial tip threads, or unverifiable sources.
5. Set confidence level: high (official docs), medium (verified 3rd party),
   low (community-reported, flagged for human review).
6. Do NOT invent rules not found in sources.

OUTPUT: one snapshot YAML per model, following model_guidance_snapshot.schema.json.
```

---

### 6F. Model Adapter Agents

**One adapter per model. One record per element per model.** Adapters read either the locked guide or the run's snapshot — whichever is specified in `--model-guidance-snapshot`.

**Prompt ID:** `SC####__[slug]-[model-slug]__v##`

**Required `generation_params`:**
```yaml
model_guidance_mode: dynamic_snapshot | locked_guide
model_guidance_snapshot: evidence/model_guidance_snapshots/...yaml  # if dynamic
model_guidance_ref: docs/model_guides/midjourney.yaml
adapter_name: midjourney
```

**Per-adapter style:**

| Adapter | Style | Notes |
|---|---|---|
| Midjourney | Compact visual clauses, ≤80 words | Reads capability: `supports_negative_prompt: limited` |
| ChatGPT Image | Natural language, task framing | `supports_negative_prompt: false` — embed constraints in positive prompt |
| Nano Banana | Variation/consistency logic | `supports_identity_consistency: true` |
| Kling Omni | Multimodal instruction spec | Phase 3; reads `max_duration_seconds` from capability matrix |

**Prompt Run Record (written by adapter alongside prompt record):**
```yaml
run_id: RUN_SC0001_MJ_0001
prompt_id: SC0001__t2i-char-nadia-midjourney__v01
model: midjourney
model_guidance_snapshot: evidence/model_guidance_snapshots/2026-04-29T153000Z_midjourney.yaml
run_at: "2026-04-29T..."
outputs_expected: 4
cost:
  unit: credits
  value: 1
status: pending   # pending | complete | error
```

---

### 6G. Critic / QA Agent (v1)

**Hard checks:** schema validation, prompt_id pattern, lifecycle_stage="draft", source_refs, no canonical ID in prompt_text, exactly 1 target_model, `model_guidance_ref` file exists and `model_id` matches `target_model`, `model_guidance_snapshot` file exists if `mode=dynamic_snapshot`.

**Negative prompt rule (conditional on model capability):**
- If `supports_negative_prompt: true/limited` → `negative_prompt` must be non-empty.
- If `supports_negative_prompt: false` (e.g. ChatGPT Image) → `generation_params.constraint_strategy` must equal `"embedded_positive_constraints"` and `negative_prompt` may be omitted or null.

**Soft checks (keyword-based, v1):**
- Prop continuity state contradiction (color/material keywords)
- do_not_invent_notes keyword violations
- style_bible.do_not_do keyword violations
- UNRESOLVED/TODO/EVIDENCE_THIN markers in prompt_text or negative_prompt

**Deferred to v2:** Full semantic source-grounding.

---

### 6H. Writer Agent

**Writes:** `prompts/draft/`, appends to `evidence/scene_prompt_map.csv` and `evidence/prompt_runs/`, updates `prompts/prompt_library.yaml`.

**Does NOT** update `pack_manifest.yaml` directly — that is human-gated.

**`scene_prompt_map.csv` row:**
```csv
SC0001,SC0001__t2i-char-nadia-midjourney__v01,t2i_character_element,draft,midjourney,pending_generation,,agent-generated draft; no image asset yet
```

**`evidence/run_costs.csv` row:**
```csv
RUN_SC0001_MJ_0001,SC0001,midjourney,t2i_character_element,4,1,credits,pending
```

---

### 6I. Image Review Agent

**Trigger:** User uploads candidate images + review notes.

**Writes:**
- `visual_dev/elements/{type}/{id}/image_selection.yaml` (selection decisions)
- `visual_dev/elements/{type}/{id}/pack_manifest_update_suggestion.yaml` — **agent writes suggestion; human applies to `pack_manifest.yaml` via PR**
- `evidence/asset_clearance/{asset_id}.yaml` (rights/copyright/clearance)
- `evidence/prompt_reviews/{prompt_id}_v##_brief.yaml` (corrected brief for v02)

**`image_selection.yaml`:**
```yaml
element_id: C01
selection_round: 1
source_prompt_ids:
  - SC0001__t2i-char-nadia-midjourney__v01
candidate_images:
  - path: visual_dev/elements/characters/C01/candidates/nadia_front_v01.png
    status: selected      # candidate | selected | rejected | canonical | deprecated
    reason: "Best identity consistency; correct silhouette"
  - path: visual_dev/elements/characters/C01/candidates/nadia_alt_v01.png
    status: rejected
    reason: "Too fashion editorial"
canonical_images:
  - visual_dev/elements/characters/C01/nadia_front_v01.png
round_status: complete
pack_manifest_sync: pending   # pending | applied (human sets to applied after PR)
```

**`pack_manifest_update_suggestion.yaml`:**
```yaml
element_id: C01
suggested_field: pack_status
suggested_value: seeded
reason: "image_selection.yaml complete with canonical_images non-empty"
applied_by: null      # human fills in after PR
applied_at: null
```

**`asset_clearance` format:**
```yaml
asset_id: C01_nadia_front_v01
source_model: midjourney
commercial_use_allowed: pending_review   # pending_review | allowed | restricted | rejected
actor_likeness_risk: false
style_imitation_risk: false
watermark_detected: false
face_identity_drift: false
review_notes: ""
```

---

### 6J. Storyboard / Shot Option Agent (Batch 5.75)

Generates ≥5 distinct composition options per scene grounded in `visual_targets` (lens_bias, framing_bias, movement_bias). No invented compositions allowed.

**`storyboard_options.yaml`:**
```yaml
scene_id: SC0001
round: 1
source_refs:
  scene_card: planning/scenes/SC0001/scene_card.yaml
  scene_excerpt: planning/scenes/SC0001/scene_excerpt.md
options:
  - option_id: SC0001_OPT_A
    purpose: "Establish surveillance geometry through corridor depth"
    camera_angle: corridor-depth restrained
    framing: thresholds, doorways, Vardova frame off-angle
    movement: minimal, exact
    lighting: filtered early daylight, low-key practicals
    source_field: visual_targets.framing_bias
    prompt_ids: []   # generated after human selects
    status: candidate
  - option_id: SC0001_OPT_B
    purpose: "Object-evidence insert — tilted frame discovery"
    camera_angle: tight object detail
    framing: fingertips, dust-shadow, frame angle
    movement: static / observational
    source_field: scene_excerpt (PROP003 state description)
    status: candidate
selected_option: null
review_status: pending
storage_policy: no_binary_commits   # frame stills in external storage
```

---

### 6K. Video Take Review Agent (Batch 8.5)

**`video_takes.yaml`:**
```yaml
scene_id: SC0001
prompt_id: SC0001__omni-corridor-discovery-kling-omni__v01
takes:
  - take_id: SC0001_TAKE001
    platform_asset_ref: "kling://..."
    external_storage_ref: "dvc://closing-price/SC0001/take001.mp4"
    repo_binary_committed: false
    status: rejected
    reason: "Camera drifted away from object evidence"
  - take_id: SC0001_TAKE002
    platform_asset_ref: "kling://..."
    external_storage_ref: "dvc://closing-price/SC0001/take002.mp4"
    repo_binary_committed: false
    status: selected
    reason: "Best route clarity and object deviation visibility"
selected_take: SC0001_TAKE002
round_status: complete
needs_prompt_revision: false
```

If `needs_prompt_revision: true` → Kling Omni Adapter v02 triggered.

---

## 7. Implementation Batches (Final Ordered Sequence)

> **Storage policy must be reconciled before any binary output paths are designed.**
> Batch 0.75 is first; everything else depends on knowing where binaries go.

| # | Batch | Goal | Key files | Commit prefix |
|---|---|---|---|---|
| **0.75** | Storage policy | Binary/LFS/external decision for all output types | `.gitattributes`, `docs/methodology/storage_policy.md`, `.gitignore` additions | `docs(storage): define production output storage policy` |
| **0.1** | Dynamic model research snapshot | Controlled web research → snapshot YAML | `scripts/agents/model_research.py`, `schemas/model_guidance_snapshot.schema.json`, `evidence/model_guidance_snapshots/`, `docs/model_guides/model_capability_matrix.yaml` | `feat(prompting): add dynamic model guidance snapshot workflow` |
| **0.25** | Model guidance research logs | Human-curated source logs | `docs/model_guides/sources/*.md` | `docs(model-guides): add prompt guidance research logs` |
| **0.5** | Model guidance registry YAML | Locked versioned guide files + skeleton operator runbook | `docs/model_guides/*.yaml`, `schemas/model_guidance.schema.json`, `docs/operator_guides/production_operator_runbook.md` (skeleton) | `feat(prompting): add model guidance registry` |
| **1** | Prompt record validation | CI validates prompt YAML against schema | `scripts/validate_prompt_records.py`, CI update, tests | `feat(validation): add prompt record schema validation` |
| **1.5** | Prop continuity normalization | Fix `state_changes` format drift | `planning/props/PROP001.yaml`, `schemas/prop_record.schema.json`, tests | `fix(continuity): normalize prop state_changes to schema format` |
| **2** | Context & continuity utilities | Source reading + resolver functions | `source_context.py`, `continuity.py`, tests | `feat(agents): add grounded context and continuity resolution` |
| **3** | Neutral brief generator | Model-agnostic element briefs | `neutral_brief.py`, tests | `feat(agents): generate neutral t2i element briefs` |
| **4** | Model adapters + run records | Per-model prompt records + cost tracking | `adapters/*.py`, `schemas/prompt_run.schema.json`, `evidence/run_costs.csv`, tests | `feat(agents): add model-specific t2i prompt adapters and run records` |
| **5** | Critic v1 + writer | Schema QA + file I/O | `critic.py`, `writer.py`, tests | `feat(agents): add prompt QA and draft writer` |
| **5.5** | Image review + clearance | Human output review loop | `review_outputs.py`, `schemas/image_selection.schema.json`, `schemas/asset_clearance.schema.json`, tests | `feat(review): add human-in-loop image review, selection, and clearance` |
| **5.6** | Production record validation | CI validates all non-prompt production YAMLs against their schemas | `scripts/validate_production_records.py`, tests | `feat(validation): add production record schema validation` |
| **5.75** | Storyboard options | ≥5 composition options per scene | `storyboard_options.py`, `schemas/storyboard_option.schema.json`, tests | `feat(storyboard): add shot option board generation` |
| **5.8** | Production dashboard + batch queue | Per-scene status tracking | `evidence/production_status.csv`, `schemas/batch_job.schema.json`, `evidence/batch_jobs/` | `feat(tracking): add production status dashboard and batch job queue` |
| **5.85** | Operator guidance layer | Human user step-by-step runbook and next-step CLI | `docs/operator_guides/*.md`, `scripts/agents/operator_next_step.py`, `evidence/operator_sessions/.gitkeep` | `feat(operator): add human production guidance layer` |
| **6** | CLI pilot run | All 5 modes wired up | `run_pipeline.py`, `docs/methodology/agent_prompt_pipeline.md` | `feat(agents): add full pipeline CLI` |
| **7** | LangGraph wrapper | Graph-based orchestration | `graph.py`, `state.py` | `feat(agents): add LangGraph orchestration wrapper` |
| **7.5** | Shot list omni suggestion | Generate `shot_list_omni` suggestion from selected storyboard direction | `visual_dev/storyboards/SC####/shot_list_omni_suggestion.yaml`, tests | `feat(storyboard): add shot_list_omni hydration suggestion layer` |
| **8** | Kling Omni adapter | Video instruction prompts | `adapters/kling_omni.py` | `feat(agents): add kling omni instruction prompt adapter` |
| **8.5** | Video take review | Take selection + revision loop | `video_take_review.py`, `schemas/video_take.schema.json`, tests | `feat(review): add kling video take review and selection` |
| **9** | Scene clip locking | Final clip evidence chain | `evidence/scene_clip_map.csv`, `schemas/video_review.schema.json` (metadata only in repo) | `feat(post): add scene clip locking and evidence tracking` |

---

## 8. Batch 0.75 — Storage Policy (Runs First)

**Why first:** Every output path in every subsequent batch depends on knowing where binaries go. If this is wrong, path assumptions propagate everywhere.

**Policy decisions (to be confirmed in `docs/methodology/storage_policy.md`):**

| Asset type | Storage location | Rationale |
|---|---|---|
| Canonical element images (`visual_dev/elements/{type}/{id}/`) | Repo + Git LFS (already configured) | Existing `.gitattributes` covers `visual_dev/elements/**/*.{png,jpg,jpeg,webp}` |
| Storyboard candidate stills | External storage; metadata/path in YAML | Volume too high for LFS |
| Locked storyboard keyframes | Repo + Git LFS (add `visual_dev/storyboards/**` to `.gitattributes`) | Only selected keyframes, low count |
| Kling video takes (full MP4/MOV) | External DVC-style storage only | Already mandated in `visual_dev/omni_sets/README.md` |
| Post-production proxies | External storage only | Already mandated in `post/README.md` |
| Selected candidate images (in `candidates/`) | Repo + LFS if ≤20 per element; external beyond that | Balance audit trail vs. repo size |
| Rejected bulk outputs | External storage | No repo commit |

**`.gitignore` additions to prevent accidental binary commits:**
```
post/edit/proxies/**/*.mp4
post/edit/proxies/**/*.mov
post/edit/proxies/**/*.mkv
post/edit/proxies/**/*.wav
visual_dev/omni_sets/**/takes/*.mp4
visual_dev/omni_sets/**/takes/*.mov
visual_dev/storyboards/**/candidates/
```

**`.gitattributes` additions (if locked storyboard keyframes go to repo):**
```
visual_dev/storyboards/**/*.png  filter=lfs diff=lfs merge=lfs -text
visual_dev/storyboards/**/*.jpg  filter=lfs diff=lfs merge=lfs -text
visual_dev/storyboards/**/*.jpeg filter=lfs diff=lfs merge=lfs -text
visual_dev/storyboards/**/*.webp filter=lfs diff=lfs merge=lfs -text
```

---

## 8.1. Batch 0.1 — Dynamic Model Research Snapshot

**Key constraint for model research agent:**
```yaml
allowed_source_classes:
  - official_docs
  - official_release_notes
  - official_help_center
  - verified_platform_blog
blocked_source_classes:
  - forum_threads
  - prompt_hack_blogs
  - unsourced_social_media
  - paid_prompt_packs
```

**Snapshot freshness policy (in `schemas/model_guidance_snapshot.schema.json`):**
```yaml
snapshot_validity:
  max_age_days:
    image_models: 14    # Midjourney, ChatGPT Image, Nano Banana
    video_models: 7     # Kling — faster release cadence
  require_refresh_before:
    - batch_prompt_generation
    - model_version_change
    - failed_output_rate_above_threshold: 0.5
```

**Model version capture in every snapshot:**
```yaml
model_version_observed: "Midjourney 6.1"   # or "unknown_ui_current" if not surfaced
model_version_confidence: high | medium | low
```

---

## 8.2. Quality Score Rubric & Failure Taxonomy

**Add to `schemas/image_selection.schema.json` and `schemas/video_take.schema.json`:**

```yaml
# Per-candidate quality scores (1–5)
scores:
  identity_consistency: 3    # Does it match the character/location/prop identity?
  source_grounding: 4        # Is it grounded in the source planning data?
  style_compliance: 5        # Does it comply with style_bible rules?
  continuity: 4              # Correct prop/wardrobe state for this scene?
  production_usability: 3    # Can this be used in the final production?
```

**Standard failure taxonomy (enum in all review schemas):**
```yaml
failure_reason_enum:
  - source_missing           # planning record not found or incomplete
  - continuity_unresolved    # prop/wardrobe state has UNRESOLVED marker
  - model_guidance_stale     # snapshot expired or guidance version mismatch
  - output_too_stylized      # style_bible violation in output
  - identity_drift           # character identity not preserved
  - camera_drift             # Kling camera moved off intended framing
  - storage_policy_violation # binary committed where not allowed
  - schema_validation_error  # record doesn't pass schema validation
  - unsourced_assertion      # visual claim not traceable to planning data
  - continuity_contradiction # visual contradicts resolved state
```

---

## 8.3. Production Dashboard & Batch Queue (Batch 5.8)

**`evidence/production_status.csv`** — per-scene progress tracker:
```csv
scene_id,element_packs_status,storyboard_status,still_prompt_status,omni_prompt_status,takes_status,selected_clip_status,overall_status
SC0001,metadata_only,not_started,not_started,not_started,not_started,not_started,phase1_pending
SC0003,metadata_only,not_started,not_started,not_started,not_started,not_started,phase1_pending
```

**`schemas/batch_job.schema.json`:**
```yaml
job_id: BATCH_SC0001_MJ_001
job_type: generate_prompts | review_outputs | generate_storyboard | review_takes
scenes: [SC0001, SC0003]
models: [midjourney, chatgpt-image]
prompt_types: [t2i_character_element, t2i_location_element]
model_guidance_snapshot: evidence/model_guidance_snapshots/...yaml
expected_outputs: 8
cost_limit:
  unit: credits
  max: 20
retry_limit: 2
priority: high | normal | low
status: queued | running | complete | failed | partial
created_at: "ISO-8601"
```

---

## 8.4. Batch 5.85 — Operator Guidance Layer

**Goal:** Human user knows exactly what to do at each production step — which file to open, which prompt to paste into which external tool, where to save outputs, and which CLI command to run next.

**Key file: `scripts/agents/operator_next_step.py`**

Reads repo state (`image_intake_manifest.yaml`, `pack_manifest.yaml`, `production_status.csv`, `storyboard_options.yaml`, `video_takes.yaml`) and outputs the next human task:

```text
Current task: C01 Nadia image seeding
Open:
- visual_dev/elements/characters/C01/source_notes.md
- planning/characters/C01.yaml
- prompts/draft/SC0001__t2i-char-nadia-midjourney__v01.yaml

Do:
1. Copy the Midjourney prompt.
2. Generate 4 candidate images in Midjourney.
3. Save selected candidates under:
   visual_dev/elements/characters/C01/candidates/
4. Write review notes to:
   evidence/prompt_reviews/SC0001__t2i-char-nadia-midjourney__v01_review.md
5. Run:
   python scripts/agents/run_pipeline.py --mode review-outputs \
     --prompt-id SC0001__t2i-char-nadia-midjourney__v01 \
     --images visual_dev/elements/characters/C01/candidates/
```

**Key docs:**
```
docs/operator_guides/
  production_operator_runbook.md         ← full pipeline guide
  t2i_image_generation_playbook.md       ← Phase 1 step-by-step
  storyboard_selection_playbook.md       ← Phase 2 step-by-step
  kling_omni_generation_playbook.md      ← Phase 3 step-by-step
  review_and_approval_playbook.md        ← PR/approval process
```

**Agent writes:** `evidence/operator_sessions/SESSION_YYYYMMDD_SC####.yaml` (audit log of operator actions, read-only for agents after creation).

**Human does:** reads runbook, executes external generation, uploads outputs, runs agent commands.

---

## 8.5. Batch 7.5 — Shot List Omni Suggestion Layer

**Goal:** After storyboard direction is selected, generate a `shot_list_omni_suggestion.yaml` from the selected composition. Human applies to `scene_card.yaml` via PR. Kling Omni adapter is blocked until `shot_list_omni` is non-empty.

**Why required:** All pilot scene cards have `shot_list_omni: []`. Kling Omni cannot run without populated shot list. This batch creates the bridge between storyboard selection (Batch 5.75) and video generation (Batch 8).

**Output:** `visual_dev/storyboards/SC####/shot_list_omni_suggestion.yaml`

```yaml
scene_id: SC0001
source_storyboard_option: SC0001_OPT_A
suggested_shot_list:
  - shot_id: SHOT_01
    type: establishing
    subject: "Vardova at corridor threshold, surveillance geometry"
    camera_movement: static
    duration_seconds: 5
    source_field: storyboard_options.SC0001_OPT_A.framing
suggested_by: storyboard_agent
applied_to_scene_card: false    # human sets to true after PR
applied_at: null
```

**Human step:** Review suggestion → update `planning/scenes/SC####/scene_card.yaml` `shot_list_omni` array via PR → then Batch 8 Kling Omni adapter unblocks.

---

## 8.6. Model Alias Map (for all adapters)

**Problem:** CLI uses kebab-case (`kling-omni`, `chatgpt-image`, `nano-banana`); Python files and YAML keys use snake_case (`kling_omni.py`, `chatgpt_image.yaml`).

**Resolution:** Add a canonical alias map in `scripts/agents/adapters/__init__.py`:

```python
MODEL_ALIAS_MAP = {
    "kling-omni":    {"guide_file": "docs/model_guides/kling_omni.yaml",   "adapter": "kling_omni"},
    "chatgpt-image": {"guide_file": "docs/model_guides/chatgpt_image.yaml", "adapter": "chatgpt_image"},
    "nano-banana":   {"guide_file": "docs/model_guides/nano_banana.yaml",   "adapter": "nano_banana"},
    "midjourney":    {"guide_file": "docs/model_guides/midjourney.yaml",    "adapter": "midjourney"},
}
```

**Rule:** CLI args and prompt ID suffixes always use kebab-case canonical ID. File names always use snake_case. Adapter resolves via `MODEL_ALIAS_MAP`.

---

## 9. Batch 1 — First Implementation Target

**Goal:** Close the validation gap. No prompt YAML files are currently validated against `schemas/prompt_record.schema.json`.

**Create:** `scripts/validate_prompt_records.py`
- Scans `prompts/{draft,review,approved,locked}/*.yaml`
- Validates each via Draft202012Validator against `schemas/prompt_record.schema.json`
- Returns nonzero on errors
- Writes `evidence/validation_reports/prompt_records_validation_report.json`

**Update:** `.github/workflows/validate-phase1.yml` — new step; empty `prompts/` must not fail.

**Tests (`tests/test_prompt_record_validation.py`) — use `tmp_path`, never write to real `prompts/`:**
- Valid minimal record → passes
- Missing `prompt_text` → fails
- Invalid `prompt_id` pattern → fails
- Invalid `prompt_type` enum → fails
- `lifecycle_stage="production"` → fails
- Empty directory → exit 0, "0 files validated"

**Constraints:** No agents, no LangGraph, no prompt generation, no planning data changes.

---

## 9. Batch 1.5 — Prop Continuity Normalization

**Update:** `planning/props/PROP001.yaml` — add `scene_id: SC0010`, rename `transition` → `transition_note`.
**Update:** `schemas/prop_record.schema.json` — add optional `transition_note` to state_changes items.
**Scan:** all other `planning/props/*.yaml` for same drift.

**Tests (`tests/test_prop_continuity_state.py`) — use `tmp_path`:**
- PROP001 in SC0003 → `"white plastic hospital bracelet"`
- PROP001 in SC0010 → `"pale blue band"`
- PROP001 in SC0014 → `"pale blue band"` (no further changes)
- Prop with no state_changes → initial_state always
- `validate_phase1.py` still passes

---

## 10. CLI Modes (Batch 6)

```bash
# Batch 0.1: refresh model guidance
python scripts/agents/run_pipeline.py \
  --mode refresh-model-guidance \
  --models midjourney,chatgpt-image,nano-banana,kling-omni \
  --save-snapshot

# Phase 1: generate t2i prompts (pass a per-model snapshot directory)
python scripts/agents/run_pipeline.py \
  --mode generate-prompts \
  --scene-id SC0001 \
  --models midjourney,chatgpt-image,nano-banana \
  --model-guidance-snapshot-dir evidence/model_guidance_snapshots/2026-04-29T153000Z/
# or per-model mapping:
#  --model-guidance-snapshots \
#    midjourney=evidence/model_guidance_snapshots/..._midjourney.yaml,\
#    chatgpt-image=evidence/model_guidance_snapshots/..._chatgpt_image.yaml,\
#    nano-banana=evidence/model_guidance_snapshots/..._nano_banana.yaml

# After external generation: review images
python scripts/agents/run_pipeline.py \
  --mode review-outputs \
  --prompt-id SC0001__t2i-char-nadia-midjourney__v01 \
  --images visual_dev/elements/characters/C01/candidates/ \
  --review-notes evidence/prompt_reviews/SC0001__t2i-char-nadia-midjourney__v01_review.md

# Phase 2: storyboard compositions
python scripts/agents/run_pipeline.py \
  --mode generate-storyboard-options \
  --scene-id SC0001

# Operator guidance
python scripts/agents/run_pipeline.py \
  --mode operator-next-step \
  --format text
```

Batch 6 deliberately does not expose `review-video-takes`, Kling Omni
generation, scene clip locking, or LangGraph graph execution. Those remain
future batches.

### Batch 7 Graph Wrapper

Batch 7 exposes a serializable `PipelineState` and a graph/fallback runner:

```python
from scripts.agents.graph import run_graph
from scripts.agents.state import PipelineState

state = PipelineState(
    repo_root=".",
    mode="operator-next-step",
)
result = run_graph(state)
```

The graph wrapper supports the same production-safe modes as Batch 6:

- `refresh-model-guidance`
- `generate-prompts`
- `review-outputs`
- `generate-storyboard-options`
- `generate-shot-list-omni-suggestion`
- `generate-kling-omni-prompts`
- `review-video-takes`
- `lock-scene-clip`
- `operator-next-step`

It is a control-flow layer only. Existing agent boundaries remain authoritative:
critic checks still gate prompt writing, review output still writes metadata
only, storyboard selection remains human-gated, and lifecycle fields remain
untouched.

### Batch 7.5 Shot List Omni Suggestion

After a human has selected a storyboard option, run:

```bash
python scripts/agents/run_pipeline.py \
  --mode generate-shot-list-omni-suggestion \
  --scene-id SC0001
```

Input:

- `visual_dev/storyboards/SC####/storyboard_options.yaml`
- `selected_option` must reference an existing option id

Output:

- `visual_dev/storyboards/SC####/shot_list_omni_suggestion.yaml`

The suggestion file is metadata-only and contains `applied_to_scene_card:
false` and `applied_at: null`. A human later applies the suggested
`shot_list_omni` to `planning/scenes/SC####/scene_card.yaml` through PR review.
Batch 7.5 does not unlock Kling by itself.

### Batch 8 Kling Omni Adapter

Kling prompt metadata is generated only after a human PR has applied
`shot_list_omni` to the scene card:

```bash
python scripts/agents/run_pipeline.py \
  --mode generate-kling-omni-prompts \
  --scene-id SC0001
```

The adapter blocks if `shot_list_omni` is empty, if `omni_set_ref` is missing,
or if existing element pack metadata shows packs are not `locked`. The output
is limited to:

- `prompts/draft/SC####__omni-kling-omni__v01.yaml`
- `evidence/prompt_runs/RUN_SC####_KO_0001.yaml`
- normal writer-managed CSV/library metadata

External Kling generation remains a manual platform step. Selected take locking
and scene clip mapping remain future batches.

#### Element-First Gate (SC0001 fix lineage)

Kling Omni prompt synthesis now follows a strict attached-element gate:

- Each shot must have a `shot_element_manifest` record under
  `visual_dev/omni_sets/SC####/shot_element_manifests/`.
- Every required element must resolve to a scene `element_binding` with
  `binding_status` at least `created`.
- Every required element must also have `pack_manifest.yaml`,
  `gpt_images_perspective_pack.yaml`, and `kling_element_reference.yaml`
  with `status` at least `review`.
- When `shot_element_manifest_ref` is present in a prompt, legacy
  `not_attached_as_kling_elements` is disallowed.
- Prompt text must stay alias-first: use `@alias` placeholders and avoid
  canonical ID leakage in `prompt_text`.

### Batch 8.5 Video Take Review

After a human generates Kling takes externally and records the platform/storage
references, review metadata may be written with:

```bash
python scripts/agents/run_pipeline.py \
  --mode review-video-takes \
  --scene-id SC0001 \
  --prompt-id SC0001__omni-kling-omni__v01 \
  --takes-metadata handoff/SC0001_takes.yaml \
  --review-notes evidence/video_reviews/SC0001_review_notes.md
```

The input is YAML/JSON metadata only. Video files remain external. The mode may
write:

- `visual_dev/omni_sets/SC####/video_takes.yaml`
- `evidence/video_reviews/SC####_take_review.yaml`
- optional `evidence/prompt_reviews/*_brief.yaml` when prompt revision is needed

Batch 8.5 does not create `selected_take.yaml` or `evidence/scene_clip_map.csv`;
those remain Batch 9 clip locking outputs.

### Batch 9 Scene Clip Locking

After `video_takes.yaml` contains exactly one selected take, lock final scene
clip metadata with:

```bash
python scripts/agents/run_pipeline.py \
  --mode lock-scene-clip \
  --scene-id SC0001 \
  --locked-by human_operator \
  --locked-at 2026-04-30T00:00:00Z
```

The mode writes:

- `visual_dev/omni_sets/SC####/selected_take.yaml`
- `evidence/scene_clip_map.csv`

The selected take must keep `repo_binary_committed: false` and must provide an
`external_storage_ref`. No video or proxy binary is created or copied.

---

## 11. Requirements Satisfaction Matrix

Status is evaluated against the active batch branch `feat/batch-8.5-video-take-review`, not the final target architecture.

| Requirement | Status |
|---|---|
| Model-specific prompt per model | implemented through Batch 4 adapters; one target model per prompt record |
| Flux support | ❌ Removed — no repo guide/adapter/capability entry; not part of production model set |
| Current model guidance (dynamic) | implemented in Batch 0.1 scaffold |
| Snapshot source quality control | implemented: `allowed_source_classes` / `blocked_source_classes` enum |
| Snapshot freshness policy | implemented: 14-day image / 7-day video policy fields |
| Model version capture | implemented: `model_version_observed` + confidence |
| Human image review loop | planned Batch 5.5 |
| Pack status human-gated | planned Batch 5.5; invariant already documented |
| Prompt v02/v03 iteration | partly supported by adapter versioning and writer; review loop planned later |
| Storyboard composition options | planned Batch 5.75 |
| Kling video take multi-selection | implemented in Batch 8.5 as metadata-only review |
| Video review loop → prompt v02 | implemented in Batch 8.5 via corrected brief metadata |
| Storage policy (no large binary commits) | implemented in Batch 0.75 |
| Candidate image storage limit | documented in storage policy; production validator planned later |
| Prompt schema validation | implemented in Batch 1 |
| Production record validation | planned Batch 5.6 |
| Prop continuity drift | implemented in Batch 1.5 |
| Asset clearance / rights tracking | planned Batch 5.5 |
| Quality score rubric | planned Batch 5.5 + 8.5 |
| Standard failure taxonomy | planned across review schemas |
| Cost / credit tracking | implemented in Batch 4/5: `run_costs.csv` + prompt run records |
| Per-scene production dashboard | planned Batch 5.8 |
| Batch job queue | planned Batch 5.8 |
| Reproducibility / audit trail | partially implemented through snapshots, prompt run records, and writer outputs |
| Scene clip locking evidence | planned Batch 9 |
| Operator step-by-step guidance | planned Batch 5.85 |
| Shot list omni hydration bridge | planned Batch 7.5 |
| Model CLI/file alias normalization | implemented in Batch 4 |

---

## 12. Critical Files for Implementation

| File | Purpose |
|---|---|
| `schemas/prompt_record.schema.json` | Primary schema for Engineer output and Critic validation |
| `schemas/prop_record.schema.json` | Needs `transition_note` in Batch 1.5 |
| `planning/props/PROP001.yaml` | Needs `scene_id` in state_changes (Batch 1.5) |
| `visual_dev/elements/props/PROP001/image_intake_manifest.yaml` | Pack status for phase detection |
| `.gitattributes` | LFS scope — needs Batch 0.75 storage policy decision |
| `evidence/scene_prompt_map.csv` | Output: `asset_ref=pending_generation` until linked |
| `prompts/prompt_library.yaml` | Master index output |
| `source/style_bible.md` | do_not_do constraints in every NeutralBrief |
| `scripts/validate_phase1.py` | Pattern for new `validate_prompt_records.py` |
| `pyproject.toml` | Dependency target (not `requirements.txt`) |
| `scripts/agents/operator_next_step.py` | Reads repo state → outputs next human task (Batch 5.85) |
| `visual_dev/storyboards/SC####/shot_list_omni_suggestion.yaml` | Bridge from storyboard → Kling Omni (Batch 7.5); human applies to scene_card via PR |
| `scripts/agents/adapters/__init__.py` | `MODEL_ALIAS_MAP` — resolves kebab CLI args to snake_case file names (Batch 4) |

---

## 13. Verification Plan

1. **Batch 0.75:** `docs/methodology/storage_policy.md` created; `.gitignore` blocks `post/edit/proxies/**/*.mp4` and `visual_dev/omni_sets/**/takes/*.mp4`. Confirm `.gitattributes` is updated for storyboard LFS scope decision.

2. **Batch 0.1:** `python scripts/agents/run_pipeline.py --mode refresh-model-guidance --save-snapshot` → snapshot files in `evidence/model_guidance_snapshots/` with `snapshot_hash`, `sources[*].retrieved_at`, `model_version_observed`, and `confidence` fields. Blocked source classes not used.

3. **Batch 1:** `python scripts/validate_prompt_records.py --repo-root .` → exit 0, "0 files validated". `pytest tests/test_prompt_record_validation.py`. PR → `validate-phase1.yml` passes with empty `prompts/`.

4. **Batch 1.5:** `pytest tests/test_prop_continuity_state.py` — PROP001 white in SC0003, pale blue in SC0010. `validate_phase1.py` still passes.

5. **Batch 6 integration pilot:**
   ```bash
   # First: refresh snapshots for all three T2I models
   python scripts/agents/run_pipeline.py \
     --mode refresh-model-guidance \
     --models midjourney,chatgpt-image,nano-banana \
     --save-snapshot
   # Then: generate prompts using snapshot directory
   python scripts/agents/run_pipeline.py \
     --mode generate-prompts \
     --scene-ids SC0001,SC0003,SC0006,SC0008,SC0009 \
     --models midjourney,chatgpt-image,nano-banana \
     --model-guidance-snapshot-dir evidence/model_guidance_snapshots/2026-04-29T153000Z/
   ```
   Assert: YAML in `prompts/draft/`, no canonical IDs in prompt_text, all pass `validate_prompt_records.py`, `asset_ref=pending_generation` in CSV, `evidence/run_costs.csv` updated, `generation_params.model_guidance_snapshot` points to correct per-model snapshot file in each record.

6. **Batch 5.5:** Upload mock candidate images; run `--mode review-outputs`; assert `image_selection.yaml` has quality scores (5 dimensions) and failure_reason if rejected; `pack_manifest_update_suggestion.yaml` written (NOT `pack_manifest.yaml` directly); `asset_clearance/{id}.yaml` generated.

7. **Batch 5.6:** `python scripts/validate_production_records.py --repo-root .` → exit 0, "0 files validated" on clean repo. Provide sample `image_selection.yaml` and `asset_clearance/*.yaml` from Batch 5.5 output → script validates against schemas and reports any violations. PR → `validate-phase1.yml` adds `validate_production_records.py` as a CI step for `visual_dev/**/*.yaml` and `evidence/**/*.yaml` changes.

8. **Batch 5.75:** `--mode generate-storyboard-options` for SC0001 → `storyboard_options.yaml` with ≥5 options, all with `source_field` citations from `visual_targets`, `selected_option: null`, `storage_policy: no_binary_commits` on frames.

9. **Snapshot freshness check:** Run `validate_prompt_records.py` against a prompt with a snapshot older than `max_age_days` → Critic flags `model_guidance_stale`.

---

## 14. Verified Current State vs Target State

> **This plan describes a target architecture. `main` is intentionally still at Batch 0.75; the active batch branch `feat/batch-5-critic-writer` has implemented through Batch 5.**

### Branch State

| Component | Status |
|---|---|
| `main` | Batch 0.75 only: storage policy, storyboard LFS scope, binary protections |
| `feat/batch-0.1-model-guidance-snapshot` | Batch 0.1 implemented and pushed |
| `feat/batch-0.25-model-guidance-logs` | Batch 0.25 implemented and pushed |
| `feat/batch-0.5-model-guidance-registry` | Batch 0.5 implemented and pushed |
| `feat/batch-1-prompt-record-validation` | Batch 1 implemented and pushed |
| `feat/batch-1.5-prop-continuity-normalization` | Batch 1.5 implemented and pushed |
| `feat/batch-2-context-continuity-utils` | Batch 2 implemented and pushed |
| `feat/batch-3-neutral-brief-generator` | Batch 3 implemented and pushed |
| `feat/batch-4-model-adapters-run-records` | Batch 4 implemented and pushed |
| `feat/batch-5-critic-writer` | Batch 5 implemented and pushed |

Batch branch ancestry has been checked: `feat/batch-5-critic-writer` contains the prior Batch 0.1 through Batch 4 commits in order. `scripts/agents/run_pipeline.py` is intentionally absent until Batch 6, so CLI examples are target commands, not current executable entrypoints.

### What exists on `feat/batch-5-critic-writer`

| Component | Status |
|---|---|
| `docs/methodology/storage_policy.md` | implemented in Batch 0.75 |
| `visual_dev/storyboards/` LFS scope | configured in `.gitattributes` |
| `.gitignore` video/proxy binary protections | added in Batch 0.75 |
| `schemas/model_guidance_snapshot.schema.json` | implemented in Batch 0.1 |
| `docs/model_guides/model_capability_matrix.yaml` | implemented in Batch 0.1 |
| `evidence/model_guidance_snapshots/.gitkeep` | implemented in Batch 0.1 |
| `docs/model_guides/sources/*.md` | implemented in Batch 0.25 |
| locked `docs/model_guides/*.yaml` files | implemented in Batch 0.5 |
| `scripts/validate_prompt_records.py` | implemented in Batch 1 |
| prompt validation CI step | implemented in Batch 1 |
| `scripts/agents/model_research.py` | implemented in Batch 0.1 |
| `scripts/agents/source_context.py` | implemented in Batch 2 |
| `scripts/agents/continuity.py` | implemented in Batch 2 |
| `scripts/agents/neutral_brief.py` | implemented in Batch 3 |
| model adapters for Midjourney, ChatGPT Image, Nano Banana | implemented in Batch 4 |
| `schemas/prompt_run.schema.json` | implemented in Batch 4 |
| `scripts/agents/critic.py` | implemented in Batch 5 |
| `scripts/agents/writer.py` | implemented in Batch 5 |
| `evidence/run_costs.csv` | header implemented in Batch 4 |
| `evidence/scene_prompt_map.csv` updates | writer-supported in Batch 5 |
| image review and asset clearance | not implemented; next batch |
| production record validation | not implemented; Batch 5.6 |
| storyboard/video review/operator pipeline | not implemented; later batches |
| `evidence/production_status.csv`, `evidence/batch_jobs/` | not implemented |

### Target state this plan builds toward

```
planning records
  → Dynamic Model Research Snapshot (controlled web → versioned YAML)
    → model capability matrix
      → source context + continuity resolution
        → neutral brief (model-agnostic)
          → model adapter (Midjourney / ChatGPT Image / Nano Banana)
            → prompt record (prompts/draft/)
              ↓ human PR → approved
                → external image generation
                  ↓ user uploads
                  → image review + quality scores + asset clearance
                    → pack_manifest_update_suggestion (human applies)
                      ↓ pack_status: locked
                      → storyboard options (≥5 compositions per scene)
                        ↓ human selects direction
                        → scene still prompts (approved composition)
                          → Kling Omni prompt adapter
                            ↓ external Kling generation
                            → video take review
                              → selected_take.yaml
                                → scene_clip_map.csv
                                  → film assembly
```

---

## 15. Open Risks & Pending Decisions

| Risk / Decision | Status | Notes |
|---|---|---|
| Storyboard keyframes: Repo+LFS vs. external only | **Decided in Batch 0.75** | Plan default: locked keyframes → LFS; candidate stills → external |
| DVC/external storage: convention vs. real setup | **Convention first** | `external_storage_ref: dvc://...` is a placeholder until DVC remote is configured |
| Web-capable agent environment for snapshots | **Execution-time concern** | Claude Code / Codex must have web access when running `--mode refresh-model-guidance` |
| Production record validator (`validate_production_records.py`) | **Batch 5.6** | Covers `image_selection.yaml`, `asset_clearance`, `storyboard_options`, `video_takes`, `prompt_runs`, `batch_jobs` |
| Agent yetki sınırı | **Non-negotiable** | Agents never write `pack_status`, `canon_lock`, `approved`, `locked` fields directly |
| Candidate image limit (≤20 per element in LFS) | **Enforced by storage policy doc** | Beyond 20 → external storage |
| Prompt text ID leakage | **Critic v1 soft check** | C01/LOC001 IDs must not appear in `prompt_text`; only in `source_refs` |
| Flux | **Removed** | Not in repo guide set; Phase 2 uses Midjourney + ChatGPT Image + Nano Banana |
| `shot_list_omni` populated gate | **Batch 7.5** | All pilot scene cards have `shot_list_omni: []`; suggestion layer generates hydration YAML; human applies |
| Operator guidance | **Batch 5.85** | Without step-by-step runbook, human user doesn't know which prompt to paste, where to save outputs, or which command to run |
| Model alias map (CLI↔file naming) | **Batch 4** | `kling-omni` CLI → `kling_omni.yaml` file; resolved via `MODEL_ALIAS_MAP` in `adapters/__init__.py` |

---

## 16. Batch 0.75 — Implementation Prompts

### Claude Code Prompt

```text
Role: You are Claude Code operating repo-faithfully on NexusZeroClosingPriceProduction.

Task: Implement Batch 0.75 only — production output storage policy reconciliation.

Inspect first:
- .gitattributes
- visual_dev/elements/README.md
- visual_dev/omni_sets/README.md
- post/README.md
- existing visual_dev/ and post/ scaffold

Goal:
Define where all production binaries and metadata belong before any agent pipeline writes output paths.

Required changes:
1. Create docs/methodology/storage_policy.md
2. Document storage policy for:
   - canonical element images (visual_dev/elements/)
   - candidate images (visual_dev/elements/{type}/{id}/candidates/)
   - rejected bulk outputs
   - storyboard candidate stills (visual_dev/storyboards/)
   - locked storyboard keyframes
   - Kling full video takes (visual_dev/omni_sets/)
   - post-production proxies (post/edit/proxies/)
   - metadata records (YAML files)
3. Add .gitignore protections for:
   - post/edit/proxies/**/*.mp4
   - post/edit/proxies/**/*.mov
   - post/edit/proxies/**/*.mkv
   - post/edit/proxies/**/*.wav
   - visual_dev/omni_sets/**/takes/*.mp4
   - visual_dev/omni_sets/**/takes/*.mov
   - visual_dev/storyboards/**/candidates/
4. Decide and document whether locked storyboard keyframes are repo+LFS or external only.
5. If repo+LFS: add path-scoped LFS rules in .gitattributes for
   visual_dev/storyboards/**/*.png|jpg|jpeg|webp
6. Do not add any binary files.
7. Do not implement agents.
8. Do not modify schemas, scene cards, planning records, or prompt files.

End with:
- changed paths
- storage decisions made
- LFS patterns added or not added
- confirmation no binaries were committed
```

### Codex Review Prompt

```text
Role: You are ChatGPT Codex acting as repository auditor.

Review Batch 0.75 — production output storage policy.

Check:
1. No binary files were added.
2. .gitignore blocks accidental video/proxy commits.
3. .gitattributes remains path-scoped and not overbroad.
4. visual_dev/elements LFS behavior remains intact.
5. Generated video and proxy outputs remain external storage only.
6. Storyboard keyframe storage policy is explicit and documented.
7. No schemas, planning records, prompt files, or agent code changed.

Verdict: safe / safe with corrections / unsafe.
```
