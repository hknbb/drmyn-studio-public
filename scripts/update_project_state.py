#!/usr/bin/env python3
"""
scripts/update_project_state.py
Auto-updates PROJECT_STATE.md from git log + operator session records.
Called by .git/hooks/post-commit after every commit.
Works with Claude Code, Codex CLI, and Antigravity (tool-agnostic).

Sections it rewrites (delimited by HTML comment markers in PROJECT_STATE.md):
  <!-- AUTO:PIPELINE:START --> ... <!-- AUTO:PIPELINE:END -->
  <!-- AUTO:SESSION_LOG:START --> ... <!-- AUTO:SESSION_LOG:END -->
Also updates the "| Last updated |" row in the Status table.
"""

import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone


# ── repo root ──────────────────────────────────────────────────────────────────
def find_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve().parent]
    for base in candidates:
        for p in [base, *base.parents]:
            if (p / ".git").exists():
                return p
    raise RuntimeError("Cannot find git repo root from cwd or script location")


REPO     = find_repo_root()
STATE    = REPO / "PROJECT_STATE.md"
SESSIONS = REPO / "evidence" / "operator_sessions"


# ── character metadata ─────────────────────────────────────────────────────────
CHARS = {
    "C01": "Nadia Vale",
    "C02": "Roman Vale",
    "C03": "Birta",
    "C04": "Dimitri",
    "C05": "Marcus",
    "C06": "Zara",
    "C07": "Sera",
    "C08": "Jin",
    "C09": "Otto",
    "C10": "Carrier+Holder",
}

NOTES = {
    "C01": "4 look bindings created: base, field-night, transit, battle-worn",
    "C03": "Needs PR-BATCH-KEYCHAR-1 registration",
    "C05": "Needs PR-BATCH-KEYCHAR-1 registration",
    "C07": "Queued after key-character batch",
    "C10": "Two enforcer figures (Carrier + Holder), per-figure packs",
}


# ── YAML field reader (no third-party dependency) ──────────────────────────────
def yaml_field(text: str, key: str) -> str:
    m = re.search(rf'^{re.escape(key)}:\s*(.+)$', text, re.MULTILINE)
    if not m:
        return ""
    v = m.group(1).strip().strip('"').strip("'")
    return "" if v.lower() in ("null", "~", "") else v


# ── parse operator sessions ────────────────────────────────────────────────────
# Filename pattern: OP-YYYY-MM-DD-C##-name-stage#-type.yaml
_FILE_RE = re.compile(r'OP-\d{4}-\d{2}-\d{2}-(C\d+)-[^-]+-stage(\d+)-', re.IGNORECASE)


def get_sessions() -> dict:
    """Returns {char_id: {s1, s2, s3, scenes: set}}"""
    data: dict = {}
    if not SESSIONS.is_dir():
        return data
    for f in SESSIONS.glob("OP-*.yaml"):
        m = _FILE_RE.match(f.stem)
        if not m:
            continue
        cid   = m.group(1).upper()
        stage = int(m.group(2))
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if yaml_field(text, "status") != "complete":
            continue
        entry = data.setdefault(cid, {"s1": False, "s2": False, "s3": False, "scenes": set()})
        entry[f"s{stage}"] = True
        scene = yaml_field(text, "scene_id")
        if scene:
            entry["scenes"].add(scene)
    return data


# ── parse git log ──────────────────────────────────────────────────────────────
def get_git_log(n: int = 80) -> list:
    result = subprocess.run(
        ["git", "log", f"--max-count={n}", "--format=%as\x1f%s"],
        cwd=REPO, capture_output=True, text=True
    )
    entries = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\x1f", 1)
        if len(parts) == 2:
            entries.append({"date": parts[0], "subject": parts[1]})
    return entries


_CHAR_RE  = re.compile(r'@?C(\d+)', re.IGNORECASE)
_SCENE_RE = re.compile(r'\(SC(\d+)', re.IGNORECASE)


def get_promotions(git_log: list) -> dict:
    """Returns {char_id: {binding, scenes: set}} for commits that promote to 'created'."""
    data: dict = {}
    for entry in git_log:
        subj = entry["subject"]
        if "promot" not in subj.lower() or "created" not in subj.lower():
            continue
        cm = _CHAR_RE.search(subj)
        if not cm:
            continue
        cid = f"C{int(cm.group(1)):02d}"
        entry_data = data.setdefault(cid, {"binding": "**created**", "scenes": set()})
        sm = _SCENE_RE.search(subj)
        if sm:
            entry_data["scenes"].add(f"SC{int(sm.group(1)):04d}")
    return data


# ── build pipeline table ───────────────────────────────────────────────────────
def _tick(flag: bool) -> str:
    return "✅" if flag else "—"


def build_table(sessions: dict, promotions: dict) -> str:
    rows = [
        "Stages: S1 = MJ v8.1 hero · S2 = MJ v7 --oref identity lock · S3 = four-view pack · Binding = lifecycle status",
        "",
        "| ID | Name | S1 | S2 | S3 | Binding | Scene(s) | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cid, name in CHARS.items():
        s = sessions.get(cid, {})
        p = promotions.get(cid, {})
        promoted = bool(p.get("binding"))
        s1 = _tick(s.get("s1") or promoted)
        s2 = _tick(s.get("s2") or promoted)
        s3 = _tick(s.get("s3") or promoted)
        binding  = p.get("binding") or "—"
        all_scenes = sorted(s.get("scenes", set()) | p.get("scenes", set()))
        scene_str  = ", ".join(all_scenes) if all_scenes else "—"
        note = NOTES.get(cid, "")
        rows.append(f"| {cid} | {name} | {s1} | {s2} | {s3} | {binding} | {scene_str} | {note} |")
    return "\n".join(rows)


# ── build session log ──────────────────────────────────────────────────────────
_SKIP_RE = re.compile(r'^(Merge |Revert |chore\(memory\))', re.IGNORECASE)


def build_session_log(git_log: list, keep: int = 10) -> str:
    lines = []
    for entry in git_log:
        subj = entry["subject"]
        if _SKIP_RE.match(subj):
            continue
        short = re.sub(r'^feat\(M5\):\s*', '', subj)
        short = re.sub(r'^fix\(M5\):\s*', '[fix] ', short)
        short = re.sub(r'^chore\(M5\):\s*', '[chore] ', short)
        lines.append(f"- {entry['date']} — {short}")
        if len(lines) >= keep:
            break
    return "\n".join(lines) if lines else "- (no entries yet)"


# ── marker-based section replace ──────────────────────────────────────────────
def replace_marked(text: str, marker: str, new_body: str) -> tuple:
    start = f"<!-- AUTO:{marker}:START -->"
    end   = f"<!-- AUTO:{marker}:END -->"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    replacement = f"{start}\n{new_body}\n{end}"
    result, n = pat.subn(replacement, text)
    return result, n > 0


# ── main ───────────────────────────────────────────────────────────────────────
def main() -> int:
    if not STATE.exists():
        print(f"[update_project_state] {STATE.name} not found — skipping.", file=sys.stderr)
        return 0

    sessions   = get_sessions()
    git_log    = get_git_log()
    promotions = get_promotions(git_log)

    table = build_table(sessions, promotions)
    log   = build_session_log(git_log)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    text = STATE.read_text(encoding="utf-8")

    text, ok_pipeline = replace_marked(text, "PIPELINE", table)
    text, ok_log      = replace_marked(text, "SESSION_LOG", log)

    # Update "| Last updated |" row
    text = re.sub(r'(\| Last updated\s*\|)[^\|]+(\|)', rf'\1 {today} \2', text)

    if not ok_pipeline:
        print("[update_project_state] WARNING: PIPELINE marker not found — table not updated.", file=sys.stderr)
    if not ok_log:
        print("[update_project_state] WARNING: SESSION_LOG marker not found — log not updated.", file=sys.stderr)

    STATE.write_text(text, encoding="utf-8")
    print(f"[update_project_state] PROJECT_STATE.md updated ({today}). "
          f"Characters with created binding: "
          f"{sum(1 for v in promotions.values() if v.get('binding'))}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
