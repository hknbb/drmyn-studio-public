# Scientific Clean Release Manifest

**Project:** DRMYN Studio  
**Case study:** *Closing Price* AI-assisted film project  
**Release state:** v0.4.0 — Three-agent orchestration + movie development and production process scope  
**Verified date:** 2026-05-06  
**Tests:** 505 passed  
**Validators:** clean  

This document is the authoritative reference for what is and is not included in
the scientific clean release of this repository. It is intended for journal
reviewers, editors, dataset curators, and reproducibility auditors.

For authorship and contributor roles, see [AUTHORS.md](../../AUTHORS.md),
[CONTRIBUTORS.md](../../CONTRIBUTORS.md), and
[docs/publication/contributor_roles.md](contributor_roles.md).

---

## 1. Purpose

DRMYN Studio is a **metadata-only, schema-validated, human-gated** research
software framework for AI-assisted **movie development and movie production
process** design, documentation, validation, and reproducibility.
Demonstrated through the *Closing Price* film project, its primary scientific
contributions are:

- A reproducible, auditable methodology for source-grounded AI-assisted movie
  development and movie production process governance.
- Schema-validated metadata records for every decision point (scene cards,
  prompt records, storyboard options, image selection, video takes, agent
  handoffs, operator sessions).
- A three-agent autonomous orchestration layer (Claude Code / Codex / Gemini
  Code Assist) with auto-handoff and pickup mode enabling structured
  multi-agent coordination without external APIs, automatic merges, or
  credential exposure.
- A lifecycle promotion gate ensuring that no record reaches `approved` or
  `locked` status without a human pull-request review.
- A Film Aesthetic Bible system that injects deterministic, scene-grounded
  visual keywords into T2I prompts via named aesthetic packs.

The repository does **not** contain generated image or video outputs. Those are
stored externally per the storage policy and referenced by metadata-only records.

The repository is not limited to screenplay generation. Screenplay-related files,
when present, are treated as one source component within the broader movie
development process.

The software citation author is Hakan Babacan. Ra. Dr. Serra Çelik and
Assoc. Prof. Dr. Gizem Parlayandemir Sayan are recorded as software contributors
in `.zenodo.json` and in [docs/publication/contributor_roles.md](contributor_roles.md).
The related article is authored by all three researchers.

---

## 2. Included Components

| Component | Location | Description |
|---|---|---|
| Development source package | `source/` | Canonical source records for the movie development process; screenplay files are one source component |
| Planning records | `planning/` | Scene, character, location, continuity, aesthetic, and production-planning metadata |
| Prompt governance records | `prompts/` | Prompt lifecycle: draft → review → approved → locked |
| JSON Schemas | `schemas/` | 20+ schemas, all `additionalProperties: false`, draft 2020-12 |
| Validators | `scripts/validate_*.py` | Production, prompt, phase1, referential integrity |
| Three-agent copilot layer | `scripts/agents/` | `operator_next_step.py`, `copilot_command.py`, `pr_helper.py`; auto-handoff + pickup mode |
| Streamlit dashboard | `tools/copilot_dashboard/` | Read-only + command + review + PR suggestion panels |
| Evidence records | `evidence/` | Agent handoffs, operator sessions, local media indices, validation reports |
| Model guidance | `model_guidance_snapshots/` | Human-verified model capability snapshots |
| Docs | `docs/` | Methodology, operator guides, publication docs |
| Tests | `tests/` | 505 tests; all use `tmp_path` only |
| AGENTS.md | `AGENTS.md` | Agent role definitions for CLI agent probe |
| CITATION.cff | `CITATION.cff` | Machine-readable citation metadata |
| `.zenodo.json` | `.zenodo.json` | Zenodo archive metadata |
| AUTHORS.md | `AUTHORS.md` | Software creator and article authorship |
| CONTRIBUTORS.md | `CONTRIBUTORS.md` | Contributor role table |
| AI_USE_DISCLOSURE.md | `AI_USE_DISCLOSURE.md` | AI tool use disclosure |
| codemeta.json | `codemeta.json` | Machine-readable software metadata (Schema.org / CodeMeta 2.0) |

---

## 3. Excluded Components

The following are intentionally absent from this repository:

| Excluded | Reason |
|---|---|
| Generated image candidates (`.png`, `.jpg`, `.webp`) | External storage only; `repo_binary_committed: false` enforced by schema |
| Generated video takes (`.mp4`, `.mov`, `.mkv`) | External storage only; platform asset refs in metadata |
| Audio renders | External storage only |
| Post-production proxies | External storage only |
| GitHub tokens, API keys, credentials | Never written to any repo file, log, or evidence record |
| Google Drive API sync | Manual operator action only; no Drive API in codebase |
| External model API calls | All model usage is manual operator action; no runtime API in pipeline |
| Local absolute media paths (canonical) | `local://` URI convention used for canonical refs; absolute paths are operator-local only |
| Auto-merge logic | All lifecycle promotion requires human PR review |
| `.claude/settings.local.json` | Local agent configuration; not part of reproducible pipeline |
| Generated pilot production outputs | Not yet present; pilot run is post–scientific clean release |

---

## 4. Validation Commands

Run from the repository root to verify reproducibility:

```bash
# Python environment
pip install -r requirements.txt           # or: pip install pyyaml jsonschema

# 1. Full test suite (328 tests, all tmp_path only)
python -m pytest -q

# 2. Production records validator
python scripts/validate_production_records.py --repo-root .

# 3. Prompt records validator
python scripts/validate_prompt_records.py --repo-root .

# 4. Phase 1 structural validator
python scripts/validate_phase1.py \
  --source-dir source \
  --planning-dir planning \
  --prompts-dir prompts \
  --schemas-dir schemas \
  --evidence-dir evidence \
  --report-json evidence/validation_reports/phase1_validation_report.json \
  --report-md evidence/validation_reports/phase1_validation_report.md

# 5. Optional: launch Streamlit dashboard (read-only safe)
python -m streamlit run tools/copilot_dashboard/app.py
```

Expected results for a clean release state:

```text
python -m pytest -q               → N passed (no failures)
validate_production_records.py    → valid: N, invalid: 0
validate_prompt_records.py        → 0 files or N passed
```

---

## 5. Verified Release Status

| Item | Status |
|---|---|
| HA-0 doctrine docs (AGENTS.md, human_agent_copilot.md) | ✅ merged PR #9 |
| HA-1 agent_handoff schema + validator | ✅ merged PR #9 |
| HA-2 storage URI vocabulary | ✅ merged PR #10 |
| HA-2.5 model guidance refresh gate | ✅ merged PR #11 |
| HA-3a/3b/3c copilot commands (switch/yes/no/revise) + pr_helper | ✅ merged PR #9, #12, #13 |
| HA-4a/b-1/b-2/c Streamlit dashboard (read + command + review + PR panel) | ✅ merged PR #14–#18 |
| HA-5 local media index schema + validator | ✅ merged PR #19 |
| HA-6 end-to-end operator loop dry-run test | ✅ merged PR #20 |
| B8-3 recommended_next_agent routing | ✅ merged PR #51 |
| B8-4 auto-handoff + pickup mode | ✅ merged PR #53 |
| B8-5 storage_policy clarification + intake_slot schema | ✅ merged PR #54 |
| v0.4.0 publication metadata (authorship, scope, contributors) | ✅ this batch |
| Full test suite | ✅ 505 passed |
| Production records validator | ✅ valid: 18, invalid: 0 |
| Prompt records validator | ✅ clean |
| No binaries committed | ✅ confirmed |
| No tokens or credentials in repo | ✅ confirmed |

---

## 6. Reproducibility Statement

All production decisions recorded in this repository are:

1. **Schema-validated** at every stage by `scripts/validate_production_records.py`
   and `scripts/validate_prompt_records.py`.
2. **Human-gated**: no lifecycle field (`pack_status`, `canon_lock`, `approved`,
   `locked`) is set without a human pull-request review and merge.
3. **Agent-auditable**: every agent action is recorded in
   `evidence/agent_handoffs/` or `evidence/operator_sessions/` with structured
   YAML.
4. **Binary-free**: `repo_binary_committed: false` is a `const` constraint in all
   relevant schemas; the validator enforces `FORBIDDEN_LIFECYCLE_KEYS`.
5. **Credential-free**: no GitHub token, model API key, or Google Drive credential
   is present in any repository file, log, or evidence record.

A reviewer can independently verify these properties by running the validation
commands in Section 4.

---

## 7. Storage Doctrine

```text
Canonical metadata (YAML, CSV, Markdown)    → this repository (git, text)
Locked canonical images (≤ 20/element)      → repository + Git LFS
Generated candidate images (bulk)           → external storage; local:// or gdrive:// URI refs
Video takes (Kling Omni outputs)            → external storage; platform_asset_ref + external_storage_ref
Post-production proxies / audio             → external storage
Model output binaries                       → external storage; never committed
```

External storage references appear in repository metadata as URI strings
(`local://`, `gdrive://`, `kling://`, `dvc://`, `s3://`). The repository
stores references and decisions, not the media itself.

---

## 8. Human Approval and Lifecycle Promotion

Lifecycle promotion in this project is strictly human-gated:

| Field | Promoted by | Mechanism |
|---|---|---|
| `pack_status` | Human operator | Pull request to `main` |
| `canon_lock` | Human operator | Pull request to `main` |
| `approved` | Human operator | Pull request to `main` |
| `locked` | Human operator | Pull request to `main` |

AI agents (Claude Code, Codex, Gemini Code Assist) may draft and write
evidence records in `evidence/`. They may not set the above fields.
The validator (`FORBIDDEN_LIFECYCLE_KEYS`) enforces this at every run.

---

## 9. AI Models Used

### Image generation models

| Canonical ID | Model | Usage |
|---|---|---|
| `midjourney` | Midjourney | Compact visual clause generation |
| `chatgpt_image` | ChatGPT Image | Natural language image editing and generation |
| `nano_banana` | Nano Banana | Identity-consistent variation generation |

### Video generation models

| Canonical ID | Model | Usage |
|---|---|---|
| `kling_omni` | Kling Omni | Scene video generation |

### Agent / code assistant models

| Agent ID | Tool | Role |
|---|---|---|
| `claude_code` | Claude Code (Anthropic) | Implementation, schema/validator authoring |
| `codex` | Codex (OpenAI) | Review, repair, second opinion |
| `gemini_code_assist` | Gemini Code Assist (Google) | Diff review, pinch-hitter implementor, long-form planning/prose drafting |

Exact model version labels are recorded by the human operator in
`agent_handoff.notes` when scientifically relevant. Automatic model version
detection is not implemented.

---

## 10. Known Limitations

1. **No generated media included.** Image candidate and video take binaries are
   stored externally. Reviewers cannot independently reproduce visual outputs
   without access to the same external storage.
2. **Prompt records may be sparse.** Pilot production runs have not yet been
   executed as of this clean release. `validate_prompt_records.py` reports
   0 files.
3. **Local absolute media paths are operator-local.** Any `D:/ClosingPriceMedia/`
   style path in a local media index is the operator's machine path, not a
   canonical reference. Canonical refs use `local://` or `gdrive://` prefixes.
4. **Agent model version provenance is partial.** Agent tool names are recorded
   in handoff records (`claude_code`, `codex`, etc.); exact runtime model
   versions are human-annotated in `notes` fields when recorded. A future
   schema field (`model_label`) may formalize this.
5. **Dashboard requires Streamlit.** `tools/copilot_dashboard/` requires
   `streamlit>=1.30` (optional dependency). Core pipeline tests do not require
   Streamlit.

---

## 11. How to Cite

See [CITATION.cff](../../CITATION.cff) and [.zenodo.json](../../.zenodo.json)
for machine-readable citation metadata.

The software citation author is **Hakan Babacan**.

Ra. Dr. Serra Çelik and Assoc. Prof. Dr. Gizem Parlayandemir Sayan are
recorded as software contributors in `.zenodo.json` and in
[docs/publication/contributor_roles.md](contributor_roles.md).
The related article is authored by all three researchers.

For full authorship details, see [AUTHORS.md](../../AUTHORS.md) and
[CONTRIBUTORS.md](../../CONTRIBUTORS.md).
