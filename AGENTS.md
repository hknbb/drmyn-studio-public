# Human-Agent Production Copilot

This repository is a metadata-only film production management system. Agents
help draft records, review metadata, and hand work between tools, but human PR
review remains the approval boundary.

## Session Memory — First Action (mandatory)

**Read `PROJECT_STATE.md` at the repo root before anything else.** It is the
single source of "where we are": active milestone, per-character pipeline
status, active scene work, next steps, and blockers. Do NOT re-explore the repo
from scratch to reconstruct the current state — the dashboard already holds it.
This applies to every agent/CLI that opens this repo (Claude Code reads this
file via the `CLAUDE.md` stub; Codex and Antigravity read it natively).

### Update Contract (the heart of cross-session memory)

After **every** promotion, lock, stage completion, or significant decision:

1. **Update `PROJECT_STATE.md`**: the relevant pipeline-table row, the
   `Last updated` line, the Türkçe summary if the headline changed, and one new
   line at the top of the Session Log (keep the log to ~10 lines, drop the
   oldest).
2. **Keep the existing conventions**: write an operator session record
   (`evidence/operator_sessions/OP-YYYY-MM-DD-<topic>.yaml`) and use the commit
   pattern `feat(M5): <action> + promote @CHAR_ID to created (SC####, QC>=85)`.
3. A session that changed pipeline state but did not update `PROJECT_STATE.md`
   is an incomplete session — fix it before ending.

`PROJECT_STATE.md` is an allowed metadata-only **status mirror**: it never
holds lifecycle authority (manifests/YAML records stay canonical) and updating
it does not count as a lifecycle promotion under the invariants below.

### Key Locations

| Path | What it holds |
|---|---|
| `PROJECT_STATE.md` | Living status dashboard (read first, keep updated) |
| `planning/manifests/` | `character_index.csv`, `scene_index.csv` rosters + status flags |
| `planning/characters/C##.yaml` | Per-character canonical metadata |
| `planning/scenes/SC####/` | Scene cards, beat plans, dialogue beats, golden reference plans |
| `visual_dev/elements/characters/C##/` | Identity anchors, look sheets, perspective packs, Kling refs |
| `evidence/operator_sessions/OP-*.yaml` | Per-session operator decision records |
| `evidence/perspective_qc/PQC_*.yaml` | QC reports for generated perspective packs |
| `evidence/local_media_indices/` | Index of locally archived binaries (`archive/` is git-ignored) |
| `schemas/` | JSON Schemas validating all record types |
| `source/` | Canonical screenplay, dossiers, bibles |

### Working Language

The human operator works in Turkish. End substantive responses with a brief
Türkçe özet. Repo artifacts (YAML, commits, dashboards) stay in English;
`PROJECT_STATE.md` carries a Turkish summary block at the top.

## Roles

The canonical role contract lives in
`docs/operator_guides/agent_role_contract.md`. This table is the short form.

| Actor | Role |
|---|---|
| `human_operator` | Owns decisions, external tools, lifecycle promotion, and PR approval. |
| `claude_code` | Primary implementation agent for scoped batch work. |
| `codex` | Review and repair agent for repo-faithfulness, tests, validators, and safety gates. |
| `gemini_code_assist` | Second-opinion reviewer, long-form planning/research, and pinch-hitter implementor when Claude and Codex are unavailable. |

## Non-Negotiable Invariants

1. **Controlled model guidance:** Agents may refresh model guidance through a controlled Research Snapshot step. Prompt adapters never use unlogged live internet directly. Every model-specific prompt must cite either a locked model guide or a run-specific guidance snapshot with URLs, retrieval timestamps, and hashes.

2. **Draft-only agent output:** Agents may write only to `prompts/draft/`, `evidence/`, and explicitly allowed metadata-only review/suggestion files under `visual_dev/` (e.g. `image_selection.yaml`, `pack_manifest_update_suggestion.yaml`, `storyboard_options.yaml`, `video_takes.yaml`). Agents may also edit canonical `planning/` records (scene cards, element sheets, aesthetic registry fields) when the edit is explicitly scoped in an approved plan batch and gated by human PR review. Agents never commit binaries, never update `pack_status`/`canon_lock`/`approved`/`locked` fields directly, and never promote lifecycle stages without a human PR.

3. **One prompt record per model:** No shared `prompt_text` across Midjourney, ChatGPT Image, Nano Banana, and Kling Omni.

## Copilot Commands

The human operator may use a small command vocabulary:

| Command | Meaning |
|---|---|
| `yes` | Approve the next recommended metadata-only action and write an operator session. |
| `no` | Reject the recommendation and write a skipped operator session with a required note. |
| `revise` | Request a text-only revision loop through a prompt brief or operator revision note. |
| `switch` | Write an `agent_handoff` record so another agent can continue from the current state. Implemented in HA-3a. |

`operator_next_step.py` remains a read-only recommender. Write actions live in
`scripts/agents/copilot_command.py` and are always human-triggered.

## Handoff Discipline

- Use `evidence/agent_handoffs/HO-*.yaml` for Claude, Codex, Gemini, or human
  handoffs.
- Handoff records are repo-relative and metadata-only.
- Do not place tokens, API keys, Google Drive credentials, or GitHub secrets in
  handoff records, notes, docs, logs, or environment files.
- Do not run Google Drive APIs or automatic PR/merge actions from this layer.
- Do not commit image, video, proxy, audio, or other binary production outputs.

See `docs/operator_guides/human_agent_copilot.md` for the full operating
doctrine.
