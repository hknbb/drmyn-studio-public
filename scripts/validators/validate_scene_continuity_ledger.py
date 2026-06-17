"""
Semantic validator for scene_continuity_ledger records.

Enforces inter-clip (package-to-package) continuity rules that JSON Schema cannot
express:

1. clip_chain.order is a 1..N contiguous, unique sequence.
2. clip_chain clip_ids match the source omni_clip_plan clip_summaries exactly
   (same set, same order). Referenced plan file must exist.
3. Across every consecutive cut, exit_state -> entry_state must be continuous:
   - screen_direction must not flip (180-degree / screen-direction rule);
   - any subject present in BOTH the exit and the next entry must keep the same
     screen_position (no teleporting across the cut).
4. frame_continuity.continuity_input_mode == frame_input_active requires at least
   one of from_clip_id / to_clip_id (aligns with omni_clip_manifest Rule 5).

This validator is read-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SceneContinuityLedgerError(ValueError):
    ledger_id: str
    error_code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.ledger_id}] {self.error_code}: {self.message}"


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _plan_clip_ids_in_order(repo_root: Path, ref: str) -> list[str] | None:
    data = _load_yaml(Path(repo_root) / ref)
    if not isinstance(data, dict):
        return None
    summaries = data.get("clip_summaries")
    if not isinstance(summaries, list):
        return []
    ids: list[str] = []
    for item in summaries:
        if isinstance(item, dict) and isinstance(item.get("clip_id"), str):
            ids.append(item["clip_id"])
    return ids


def _positions_map(state: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for kp in state.get("key_positions") or []:
        if isinstance(kp, dict):
            subject = kp.get("subject")
            pos = kp.get("screen_position")
            if isinstance(subject, str) and isinstance(pos, str):
                out[subject] = pos
    return out


def validate_scene_continuity_ledger(
    record: dict[str, Any], repo_root: str | Path
) -> list[SceneContinuityLedgerError]:
    errors: list[SceneContinuityLedgerError] = []
    ledger_id = record.get("scene_continuity_ledger_id", "UNKNOWN")
    repo_root = Path(repo_root)

    chain = record.get("clip_chain")
    if not isinstance(chain, list) or not chain:
        return errors  # schema layer reports structural problems

    # Rule 1: order is 1..N contiguous + unique.
    orders = [c.get("order") for c in chain if isinstance(c, dict)]
    if orders != list(range(1, len(chain) + 1)):
        errors.append(
            SceneContinuityLedgerError(
                ledger_id,
                "ORDER_NOT_CONTIGUOUS",
                f"clip_chain.order must be 1..{len(chain)} in sequence; got {orders}.",
            )
        )

    chain_ids = [c.get("clip_id") for c in chain if isinstance(c, dict)]
    if len(set(chain_ids)) != len(chain_ids):
        errors.append(
            SceneContinuityLedgerError(
                ledger_id, "DUPLICATE_CLIP_ID", f"clip_chain has duplicate clip_ids: {chain_ids}."
            )
        )

    # Rule 2: clip_ids match the omni_clip_plan exactly, in order.
    plan_ref = record.get("source_omni_clip_plan_ref")
    if isinstance(plan_ref, str) and plan_ref:
        plan_ids = _plan_clip_ids_in_order(repo_root, plan_ref)
        if plan_ids is None:
            errors.append(
                SceneContinuityLedgerError(
                    ledger_id,
                    "MISSING_OMNI_CLIP_PLAN",
                    f"source_omni_clip_plan_ref points to missing/invalid file: {plan_ref}",
                )
            )
        elif chain_ids != plan_ids:
            errors.append(
                SceneContinuityLedgerError(
                    ledger_id,
                    "CLIP_CHAIN_PLAN_MISMATCH",
                    f"clip_chain {chain_ids} must match omni_clip_plan clip order {plan_ids}.",
                )
            )

    # Rule 3: continuity across each cut.
    for i in range(len(chain) - 1):
        cur = chain[i]
        nxt = chain[i + 1]
        if not (isinstance(cur, dict) and isinstance(nxt, dict)):
            continue
        exit_state = cur.get("exit_state") or {}
        entry_state = nxt.get("entry_state") or {}
        cur_id = cur.get("clip_id", f"[{i}]")
        nxt_id = nxt.get("clip_id", f"[{i + 1}]")

        exit_dir = exit_state.get("screen_direction")
        entry_dir = entry_state.get("screen_direction")
        if exit_dir and entry_dir and exit_dir != entry_dir:
            errors.append(
                SceneContinuityLedgerError(
                    ledger_id,
                    "SCREEN_DIRECTION_FLIP",
                    f"screen_direction flips across cut {cur_id}->{nxt_id} "
                    f"({exit_dir} -> {entry_dir}); 180-degree continuity violated.",
                )
            )

        exit_pos = _positions_map(exit_state)
        entry_pos = _positions_map(entry_state)
        for subject in set(exit_pos) & set(entry_pos):
            if exit_pos[subject] != entry_pos[subject]:
                errors.append(
                    SceneContinuityLedgerError(
                        ledger_id,
                        "SUBJECT_POSITION_DISCONTINUITY",
                        f"{subject} jumps from {exit_pos[subject]!r} to {entry_pos[subject]!r} "
                        f"across cut {cur_id}->{nxt_id}.",
                    )
                )

    # Rule 4: frame_input_active requires a frame reference.
    for c in chain:
        if not isinstance(c, dict):
            continue
        fc = c.get("frame_continuity")
        if isinstance(fc, dict) and fc.get("continuity_input_mode") == "frame_input_active":
            if not fc.get("from_clip_id") and not fc.get("to_clip_id"):
                errors.append(
                    SceneContinuityLedgerError(
                        ledger_id,
                        "FRAME_INPUT_ACTIVE_NO_REFS",
                        f"clip {c.get('clip_id')}: frame_input_active requires from_clip_id "
                        "or to_clip_id.",
                    )
                )

    return errors


def validate_scene_continuity_ledger_file(
    path: str | Path, repo_root: str | Path
) -> list[SceneContinuityLedgerError]:
    data = _load_yaml(Path(path))
    if not isinstance(data, dict):
        return []
    return validate_scene_continuity_ledger(data, repo_root)
