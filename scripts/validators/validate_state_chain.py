"""
State-chain validator: intra-clip continuity chaining + per-character action.

Closes two failure modes the other validators miss:

1. "Positions reset between cuts." Each shot after the first in a clip must
   restate the carried world state (``entry_state``) so the prompt re-anchors
   where each subject/prop is BEFORE the new action, instead of letting Kling
   reset positions at every cut. ``exit_state`` records where the shot leaves
   things, so the chain has explicit before/after evidence
   (entry_state(K) <-> exit_state(K-1)) and ties to the scene_continuity_ledger
   at the clip seam.

2. "Multi-character action confusion." In a shot with two or more on-frame
   figures (or any dialogue), each on-frame figure must carry its own ``action``
   so the model never has to guess who does what (Kling/FAL.ai: bind action to a
   unique character).

Error codes
-----------
ENTRY_STATE_MISSING_AFTER_FIRST_SHOT   - shot after the first lacks entry_state.
SHOT_EXIT_STATE_MISSING                - shot lacks exit_state (needed for chain/seam).
CARRIED_SUBJECT_DROPPED                - on-frame subject in exit_state(K-1) missing from entry_state(K).
CARRIED_PROP_DROPPED                   - prop in exit_state(K-1) missing from entry_state(K).
RELATION_BROKEN_WITHOUT_ACTION         - a subject's relation changed across the cut but no figure action explains it.
CLIP_SEAM_MISMATCH                     - first-shot entry / last-shot exit inconsistent with the ledger for the clip.
FIGURE_ACTION_MISSING                  - on-frame figure in a multi-figure or dialogue shot has no action.
DIALOGUE_SPEAKER_NOT_ON_FRAME_OR_OFFSCREEN_MARKED - a line's speaker is neither a figure nor a key_position in the shot.
CHARACTER_ACTION_DUPLICATED_IN_PROMPT_ACTION (warning) - prompt_action repeats a figure's action; keep it environment-only.
PROMPT_RENDER_OMITS_ENTRY_STATE        - (render-aware) authored entry_state.summary is not present in the rendered prompt.
PROMPT_RENDER_OMITS_FIGURE_ACTION      - (render-aware) a figure action is not present in the rendered prompt.
PROMPT_OVER_2500                       - (render-aware, warning) rendered prompt exceeds the 2500-char API limit.

Read-only. Render-aware checks call the adapter's pure ``render_prompt_text_only``
helper (no files written) and are skipped gracefully if it is unavailable.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ON_FRAME = {"on_frame", "partial_frame", "occluded"}
_ALIAS_RE = re.compile(r"@[A-Z0-9_]+")

# Relation verb families mapped to a canonical token so paraphrases of the same
# relation ("holding" / "in her arms" / "cradling") are not flagged as broken.
_RELATION_SYNONYMS: dict[str, str] = {
    "holding": "holding",
    "holds": "holding",
    "held": "holding",
    "cradling": "holding",
    "cradled": "holding",
    "in arms": "holding",
    "in her arms": "holding",
    "in his arms": "holding",
    "restraining": "restraining",
    "restrains": "restraining",
    "restrained": "restraining",
    "holds her": "restraining",
    "beside": "beside",
    "next to": "beside",
    "at the side of": "beside",
}


@dataclass
class StateChainIssue(ValueError):
    scene_id: str
    clip_id: str
    shot_id: str
    error_code: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        loc = f"{self.clip_id}/{self.shot_id}" if self.shot_id else self.clip_id
        return f"[{self.scene_id}:{loc}] {self.error_code}: {self.message}"


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _strip_aliases(text: str) -> str:
    return _norm(_ALIAS_RE.sub("", text or ""))


def _normalize_relation(text: str) -> str:
    """Canonicalise a relation phrase so paraphrases compare equal."""
    base = _strip_aliases(text)
    base = re.sub(r"[^a-z0-9 ]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    for phrase, canon in _RELATION_SYNONYMS.items():
        if phrase in base:
            return canon
    return base


def _aliases_in(text: str) -> set[str]:
    return set(_ALIAS_RE.findall(text or ""))


# --------------------------------------------------------------------------- #
# State accessors
# --------------------------------------------------------------------------- #
def _key_positions(state: Any) -> list[dict[str, Any]]:
    if not isinstance(state, dict):
        return []
    return [p for p in (state.get("key_positions") or []) if isinstance(p, dict)]


def _props(state: Any) -> list[dict[str, Any]]:
    if not isinstance(state, dict):
        return []
    return [p for p in (state.get("props_state") or []) if isinstance(p, dict)]


def _on_frame_subjects(state: Any) -> dict[str, dict[str, Any]]:
    """alias -> position dict, for on-frame subjects only."""
    out: dict[str, dict[str, Any]] = {}
    for pos in _key_positions(state):
        subj = pos.get("subject")
        vis = pos.get("visibility", "on_frame")
        if isinstance(subj, str) and subj.startswith("@") and vis in _ON_FRAME:
            out[subj] = pos
    return out


def _all_subjects(state: Any) -> set[str]:
    return {
        p.get("subject")
        for p in _key_positions(state)
        if isinstance(p.get("subject"), str) and p.get("subject", "").startswith("@")
    }


def _prop_keys(state: Any) -> set[str]:
    return {p.get("prop") for p in _props(state) if isinstance(p.get("prop"), str)}


def _figures(shot: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in (shot.get("figures") or []) if isinstance(f, dict)]


def _figure_actions_text(shot: dict[str, Any]) -> str:
    return " ".join(
        f.get("action", "") for f in _figures(shot) if isinstance(f.get("action"), str)
    )


# --------------------------------------------------------------------------- #
# Per-clip structural checks
# --------------------------------------------------------------------------- #
def _validate_clip(
    scene_id: str,
    manifest: dict[str, Any],
    ledger_states: dict[str, tuple[Any, Any]],
    speakers: dict[str, dict[str, str]],
) -> list[StateChainIssue]:
    issues: list[StateChainIssue] = []
    clip_id = manifest.get("clip_id", "UNKNOWN")
    shots = [s for s in (manifest.get("shots") or []) if isinstance(s, dict)]
    n = len(shots)

    for idx, shot in enumerate(shots):
        shot_id = shot.get("shot_id", f"[{idx}]")
        entry = shot.get("entry_state")
        exit_ = shot.get("exit_state")
        figs = _figures(shot)
        has_dialogue = bool(shot.get("dialogue_line_ids"))

        # entry_state required after the first shot (first shot inherits the
        # clip's ledger entry_state).
        if idx > 0 and not isinstance(entry, dict):
            issues.append(
                StateChainIssue(
                    scene_id, clip_id, shot_id,
                    "ENTRY_STATE_MISSING_AFTER_FIRST_SHOT",
                    "shot after the first has no entry_state; it cannot restate the "
                    "carried positions and the chain breaks.",
                )
            )

        # exit_state required on every shot (chain + clip seam evidence).
        if not isinstance(exit_, dict):
            issues.append(
                StateChainIssue(
                    scene_id, clip_id, shot_id, "SHOT_EXIT_STATE_MISSING",
                    "shot has no exit_state; the next shot's entry cannot be verified "
                    "and the clip seam has no settled end.",
                )
            )

        # Per-figure action in multi-figure or dialogue shots.
        if len(figs) >= 2 or has_dialogue:
            for fig in figs:
                vis = fig.get("visibility", "on_frame")
                if vis not in _ON_FRAME:
                    continue
                if not (isinstance(fig.get("action"), str) and fig["action"].strip()):
                    issues.append(
                        StateChainIssue(
                            scene_id, clip_id, shot_id, "FIGURE_ACTION_MISSING",
                            f"on-frame figure {fig.get('kling_alias', fig.get('figure_id'))} "
                            "has no action; give every character its own action so the "
                            "model never confuses who does what.",
                        )
                    )

        # prompt_action should stay environment-only (warning if it repeats a figure action).
        prompt_action = shot.get("prompt_action", "")
        if isinstance(prompt_action, str):
            for fig in figs:
                act = fig.get("action")
                alias = fig.get("kling_alias")
                if not (isinstance(act, str) and act.strip() and isinstance(alias, str)):
                    continue
                act_core = _strip_aliases(act)
                first_words = " ".join(act_core.split()[:3])
                if alias in prompt_action and first_words and first_words in _norm(prompt_action):
                    issues.append(
                        StateChainIssue(
                            scene_id, clip_id, shot_id,
                            "CHARACTER_ACTION_DUPLICATED_IN_PROMPT_ACTION",
                            f"prompt_action repeats {alias}'s action; keep prompt_action "
                            "environment-only and let figures[].action carry character action.",
                            severity="warning",
                        )
                    )

        # Dialogue speaker must be referenced in the shot (figure or key_position).
        shot_aliases = {f.get("kling_alias") for f in figs}
        shot_aliases |= _all_subjects(entry)
        for lid in shot.get("dialogue_line_ids") or []:
            spk = speakers.get(lid)
            if not spk:
                continue
            alias = spk.get("alias")
            if alias and alias not in shot_aliases:
                issues.append(
                    StateChainIssue(
                        scene_id, clip_id, shot_id,
                        "DIALOGUE_SPEAKER_NOT_ON_FRAME_OR_OFFSCREEN_MARKED",
                        f"line {lid} speaker {alias} is neither a figure nor a "
                        "key_position in the shot; add the figure or mark it "
                        "off_frame/heard_offscreen in entry_state.",
                    )
                )

        # Chain: entry_state(K) vs exit_state(K-1).
        if idx > 0 and isinstance(entry, dict):
            prev_exit = shots[idx - 1].get("exit_state")
            if isinstance(prev_exit, dict):
                issues.extend(
                    _check_chain(scene_id, clip_id, shot_id, prev_exit, entry, shot)
                )

    # Clip seam: first-shot entry vs ledger entry; last-shot exit vs ledger exit.
    if shots and clip_id in ledger_states:
        led_entry, led_exit = ledger_states[clip_id]
        issues.extend(
            _check_seam(scene_id, clip_id, shots[0], shots[-1], led_entry, led_exit)
        )

    return issues


def _check_chain(
    scene_id: str, clip_id: str, shot_id: str,
    prev_exit: dict[str, Any], entry: dict[str, Any], shot: dict[str, Any],
) -> list[StateChainIssue]:
    issues: list[StateChainIssue] = []
    prev_on = _on_frame_subjects(prev_exit)
    cur_all = _all_subjects(entry)

    for alias, prev_pos in prev_on.items():
        if alias not in cur_all:
            issues.append(
                StateChainIssue(
                    scene_id, clip_id, shot_id, "CARRIED_SUBJECT_DROPPED",
                    f"{alias} was on-frame at the previous shot's exit but is absent "
                    "from this shot's entry_state.key_positions; restate it (or mark it "
                    "off_frame) so the position chains instead of resetting.",
                )
            )
            continue
        # Relation change must be explained by some figure action this shot.
        cur_pos = next(
            (p for p in _key_positions(entry) if p.get("subject") == alias), {}
        )
        prev_rel = _normalize_relation(prev_pos.get("relation", ""))
        cur_rel = _normalize_relation(cur_pos.get("relation", ""))
        if prev_rel and cur_rel and prev_rel != cur_rel:
            actions = _figure_actions_text(shot)
            if alias not in _aliases_in(actions):
                issues.append(
                    StateChainIssue(
                        scene_id, clip_id, shot_id, "RELATION_BROKEN_WITHOUT_ACTION",
                        f"{alias}'s relation changed ('{prev_rel}' -> '{cur_rel}') across "
                        "the cut but no figure action in this shot references it.",
                    )
                )

    for prop in _prop_keys(prev_exit) - _prop_keys(entry):
        issues.append(
            StateChainIssue(
                scene_id, clip_id, shot_id, "CARRIED_PROP_DROPPED",
                f"prop {prop!r} was in the previous shot's exit_state but is absent "
                "from this shot's entry_state.props_state.",
            )
        )
    return issues


def _check_seam(
    scene_id: str, clip_id: str,
    first_shot: dict[str, Any], last_shot: dict[str, Any],
    led_entry: Any, led_exit: Any,
) -> list[StateChainIssue]:
    issues: list[StateChainIssue] = []

    def _ledger_aliases(state: Any) -> set[str]:
        # Only compare alias-shaped subjects; legacy name-based ledgers are skipped.
        return {s for s in _all_subjects(state)}

    first_entry = first_shot.get("entry_state")
    led_in = _ledger_aliases(led_entry)
    if led_in and isinstance(first_entry, dict):
        missing = led_in - _all_subjects(first_entry)
        if missing:
            issues.append(
                StateChainIssue(
                    scene_id, clip_id, first_shot.get("shot_id", "?"),
                    "CLIP_SEAM_MISMATCH",
                    f"first shot entry_state is missing ledger entry subjects "
                    f"{sorted(missing)}; the clip opening must match the ledger hand-off.",
                )
            )

    last_exit = last_shot.get("exit_state")
    led_out = _ledger_aliases(led_exit)
    if led_out and isinstance(last_exit, dict):
        missing = led_out - _all_subjects(last_exit)
        if missing:
            issues.append(
                StateChainIssue(
                    scene_id, clip_id, last_shot.get("shot_id", "?"),
                    "CLIP_SEAM_MISMATCH",
                    f"last shot exit_state is missing ledger exit subjects "
                    f"{sorted(missing)}; the clip ending must match the ledger hand-off.",
                )
            )
    return issues


# --------------------------------------------------------------------------- #
# Render-aware checks (pure dry-run; skipped if the adapter helper is absent)
# --------------------------------------------------------------------------- #
def _render_checks(
    repo_root: Path, scene_id: str, manifests: list[dict[str, Any]]
) -> list[StateChainIssue]:
    try:
        from scripts.agents.adapters.kling_omni import KlingOmniAdapter
    except Exception:
        return []
    adapter = KlingOmniAdapter(repo_root)
    render = getattr(adapter, "render_prompt_text_only", None)
    if render is None:
        return []

    issues: list[StateChainIssue] = []
    for manifest in manifests:
        clip_id = manifest.get("clip_id", "UNKNOWN")
        try:
            text = render(scene_id, clip_id)
        except Exception:
            continue
        if not isinstance(text, str):
            continue
        # Compare against an alias-stripped, lowercased copy so a probe whose
        # words straddle an @alias still matches (the rendered text keeps aliases).
        low = _strip_aliases(text)

        if len(text) > 2500:
            issues.append(
                StateChainIssue(
                    scene_id, clip_id, "", "PROMPT_OVER_2500",
                    f"rendered prompt is {len(text)} chars (>2500 API limit).",
                    severity="warning",
                )
            )

        shots = [s for s in (manifest.get("shots") or []) if isinstance(s, dict)]
        for idx, shot in enumerate(shots):
            shot_id = shot.get("shot_id", f"[{idx}]")
            entry = shot.get("entry_state")
            if idx > 0 and isinstance(entry, dict):
                summary = entry.get("summary")
                if isinstance(summary, str) and summary.strip():
                    probe = " ".join(_strip_aliases(summary).split()[:5])
                    if probe and probe not in low:
                        issues.append(
                            StateChainIssue(
                                scene_id, clip_id, shot_id,
                                "PROMPT_RENDER_OMITS_ENTRY_STATE",
                                "authored entry_state.summary is not present in the "
                                "rendered prompt; the carried-state anchor was dropped.",
                            )
                        )
            for fig in _figures(shot):
                act = fig.get("action")
                if not (isinstance(act, str) and act.strip()):
                    continue
                probe = " ".join(_strip_aliases(act).split()[:4])
                if probe and probe not in low:
                    issues.append(
                        StateChainIssue(
                            scene_id, clip_id, shot_id,
                            "PROMPT_RENDER_OMITS_FIGURE_ACTION",
                            f"action of {fig.get('kling_alias')} is not present in the "
                            "rendered prompt.",
                        )
                    )
    return issues


# --------------------------------------------------------------------------- #
# Loading + scene entry point
# --------------------------------------------------------------------------- #
def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _ledger_states(scene_dir: Path) -> dict[str, tuple[Any, Any]]:
    ledger = _load_yaml(scene_dir / "scene_continuity_ledger.yaml")
    out: dict[str, tuple[Any, Any]] = {}
    for entry in ledger.get("clip_chain") or []:
        if isinstance(entry, dict) and isinstance(entry.get("clip_id"), str):
            out[entry["clip_id"]] = (entry.get("entry_state"), entry.get("exit_state"))
    return out


def _speakers(scene_dir: Path) -> dict[str, dict[str, str]]:
    dialogue = _load_yaml(scene_dir / "dialogue_beats.yaml")
    out: dict[str, dict[str, str]] = {}
    for line in dialogue.get("dialogue_lines") or []:
        if not isinstance(line, dict):
            continue
        lid = line.get("line_id")
        if isinstance(lid, str):
            out[lid] = {
                "alias": line.get("speaker_kling_alias", ""),
                "line_type": line.get("line_type", "spoken"),
            }
    return out


def validate_state_chain(
    scene_id: str,
    manifests: list[dict[str, Any]],
    ledger_states: dict[str, tuple[Any, Any]] | None = None,
    speakers: dict[str, dict[str, str]] | None = None,
) -> list[StateChainIssue]:
    """Validate intra-clip state chaining + per-figure action over parsed records."""
    ledger_states = ledger_states or {}
    speakers = speakers or {}
    issues: list[StateChainIssue] = []
    for manifest in manifests:
        if isinstance(manifest, dict):
            issues.extend(
                _validate_clip(scene_id, manifest, ledger_states, speakers)
            )
    return issues


def validate_scene_state_chain(
    repo_root: str | Path, scene_id: str, render_check: bool = True
) -> list[StateChainIssue]:
    """Load a scene's manifests + ledger + dialogue and validate the state chain."""
    repo_root = Path(repo_root)
    scene_dir = repo_root / "planning" / "scenes" / scene_id
    manifests: list[dict[str, Any]] = []
    for mpath in sorted((scene_dir / "manifests").glob("CLIP_*.yaml")):
        doc = _load_yaml(mpath)
        if doc.get("record_type") == "omni_clip_manifest":
            manifests.append(doc)

    issues = validate_state_chain(
        scene_id,
        manifests,
        ledger_states=_ledger_states(scene_dir),
        speakers=_speakers(scene_dir),
    )
    if render_check:
        issues.extend(_render_checks(repo_root, scene_id, manifests))
    return issues


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate intra-clip state chaining + per-character action."
    )
    parser.add_argument("scene_ids", nargs="+")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--no-render-check", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    errors = 0
    for scene_id in args.scene_ids:
        for issue in validate_scene_state_chain(
            repo_root, scene_id, render_check=not args.no_render_check
        ):
            print(f"{issue.severity.upper()}: {issue}")
            if issue.severity == "error":
                errors += 1
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
