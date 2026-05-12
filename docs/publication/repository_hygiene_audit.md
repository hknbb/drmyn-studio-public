# Repository Hygiene Audit

**Conducted:** 2026-05-02  
**Branch:** docs/scientific-clean-release  
**Purpose:** Pre-publication verification that no binaries, credentials, local artifacts, or accidental generated outputs are tracked in the repository.

---

## Commands Run

```bash
git ls-files | grep -Ei '\.(mp4|mov|mkv|wav|png|jpg|jpeg|webp|zip|7z|rar)$'
git ls-files | grep -Ei '(token|secret|credential|\.env|settings\.local|PR_BODY|\.claude/worktree)'
python -m pytest -q
python scripts/validate_production_records.py --repo-root .
python scripts/validate_prompt_records.py --repo-root .
```

---

## Results

### Binary / media files tracked in git

```text
Result: NONE
```

No `.mp4`, `.mov`, `.mkv`, `.wav`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.zip`,
`.7z`, or `.rar` files are tracked in the repository. Git LFS covers canonical
element images under `visual_dev/elements/` per the `.gitattributes` rules, but
no generated image or video binaries are committed.

### Secret / credential / local artifact indicators

```text
Finding: .claude/settings.local.json was tracked (FIXED in this PR)
```

`.claude/settings.local.json` was present in git history and contained
machine-specific local Windows absolute paths
(e.g. `Read(//mnt/c/Users/babac/**)` and `C:\\Users\\babac\\...` style
`Bash()` permission entries). This file is the Claude Code local settings file
and is specific to one operator's machine. It contains no credentials or tokens,
only local permission allowlist entries.

**Action taken:** Added `.claude/settings.local.json` and `PR_BODY_*.md` to
`.gitignore` and removed `.claude/settings.local.json` from git tracking
(`git rm --cached`). The file remains on the operator's local disk.

No tokens, API keys, secrets, GitHub credentials, or password-equivalent data
were found in any tracked file.

### Temporary PR body files

```text
Result: NONE tracked
```

Temporary `PR_BODY_HA_*.md` files were used during development to pass PR body
text to `gh pr create --body-file`. These were deleted from disk after each PR
was opened and were never committed to git. This is now enforced via
`.gitignore`.

### `.claude/` directory

```text
.claude/settings.json   — tracked (project-level agent settings, no secrets)
.claude/settings.local.json — REMOVED from tracking in this PR
```

`settings.json` contains only tool permission allowlists and is safe to track.
`settings.local.json` contained machine-specific operator paths and has been
untracked.

### Worktrees and local agent state

```text
Result: No .claude/worktrees/ or similar agent working tree artifacts tracked.
```

### Validation results

```text
python -m pytest -q                          → 328 passed
validate_production_records.py               → valid: 2, invalid: 0
validate_prompt_records.py                   → 0 files
```

---

## Accepted Exceptions

| Item | Justification |
|---|---|
| `evidence/agent_handoffs/HO-20260502-125535.yaml` | Real operational handoff committed to main by the operator; schema-valid; no credentials or sensitive data. |
| `evidence/scene_clip_map.csv` | Production pipeline output; 1 scene, schema-valid. |

---

## Final Verdict

```text
Binary / media commit:    NONE found ✅
Credential / token leak:  NONE found ✅
Local machine path leak:  FIXED — settings.local.json removed from tracking ✅
Temp artifact commit:     NONE found ✅
Validation:               PASS (328 tests, clean validators) ✅
```

Repository is clean for scientific publication submission.
