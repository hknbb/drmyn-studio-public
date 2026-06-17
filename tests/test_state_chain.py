"""Tests for the state-chain validator (intra-clip continuity + per-figure action)."""

from __future__ import annotations

from typing import Any

from scripts.validators.validate_state_chain import (
    StateChainIssue,
    _normalize_relation,
    validate_state_chain,
)


def _codes(issues: list[StateChainIssue]) -> set[str]:
    return {i.error_code for i in issues}


def _fig(alias: str, base: str, action: str | None = None, visibility: str = "on_frame") -> dict[str, Any]:
    f: dict[str, Any] = {
        "figure_id": f"FIG_{alias.strip('@')}",
        "base_element_id": base,
        "kling_alias": alias,
        "role": "role",
        "visibility": visibility,
    }
    if action is not None:
        f["action"] = action
    return f


def _state(subjects: list[tuple[str, str]] | None = None, props: list[tuple[str, str]] | None = None,
           summary: str = "") -> dict[str, Any]:
    s: dict[str, Any] = {}
    if summary:
        s["summary"] = summary
    if subjects:
        s["key_positions"] = [
            {"subject": a, "screen_position": "center", "relation": rel} if rel else
            {"subject": a, "screen_position": "center"}
            for a, rel in subjects
        ]
    if props:
        s["props_state"] = [{"prop": p, "state": st} for p, st in props]
    return s


def _manifest(clip_id: str, shots: list[dict[str, Any]]) -> dict[str, Any]:
    return {"record_type": "omni_clip_manifest", "clip_id": clip_id, "shots": shots}


# --------------------------------------------------------------------------- #
# Clean baseline
# --------------------------------------------------------------------------- #
def test_clean_chain_passes() -> None:
    shots = [
        {
            "shot_id": "S_A",
            "figures": [_fig("@C01_NADIA", "C01", "stays seated"),
                        _fig("@C04_DIMITRI", "C04", "enters the room")],
            "exit_state": _state([("@C01_NADIA", "holding @C08_JIN"), ("@C04_DIMITRI", "")]),
        },
        {
            "shot_id": "S_B",
            "entry_state": _state([("@C01_NADIA", "in her arms @C08_JIN"), ("@C04_DIMITRI", "")]),
            "figures": [_fig("@C01_NADIA", "C01", "looks up"),
                        _fig("@C04_DIMITRI", "C04", "speaks")],
            "exit_state": _state([("@C01_NADIA", "holding @C08_JIN")]),
        },
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_SC0014_03", shots)])
    assert [i for i in issues if i.severity == "error"] == []


# --------------------------------------------------------------------------- #
# Structural failures
# --------------------------------------------------------------------------- #
def test_entry_state_missing_after_first_shot() -> None:
    shots = [
        {"shot_id": "S_A", "figures": [_fig("@C01_NADIA", "C01", "sits")],
         "exit_state": _state([("@C01_NADIA", "")])},
        {"shot_id": "S_B", "figures": [_fig("@C01_NADIA", "C01", "stands")],
         "exit_state": _state([("@C01_NADIA", "")])},
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "ENTRY_STATE_MISSING_AFTER_FIRST_SHOT" in _codes(issues)


def test_shot_exit_state_missing() -> None:
    shots = [{"shot_id": "S_A", "figures": [_fig("@C01_NADIA", "C01")]}]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "SHOT_EXIT_STATE_MISSING" in _codes(issues)


def test_figure_action_missing_in_multi_figure_shot() -> None:
    shots = [{
        "shot_id": "S_A",
        "figures": [_fig("@C01_NADIA", "C01", "sits"), _fig("@C04_DIMITRI", "C04")],  # Dimitri no action
        "exit_state": _state([("@C01_NADIA", "")]),
    }]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "FIGURE_ACTION_MISSING" in _codes(issues)


def test_off_frame_figure_exempt_from_action_requirement() -> None:
    shots = [{
        "shot_id": "S_A",
        "figures": [_fig("@C01_NADIA", "C01", "sits"),
                    _fig("@C04_DIMITRI", "C04", visibility="off_frame")],
        "exit_state": _state([("@C01_NADIA", "")]),
    }]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "FIGURE_ACTION_MISSING" not in _codes(issues)


def test_carried_subject_dropped() -> None:
    shots = [
        {"shot_id": "S_A", "figures": [_fig("@C01_NADIA", "C01", "sits"), _fig("@C08_JIN", "C08", "rests")],
         "exit_state": _state([("@C01_NADIA", ""), ("@C08_JIN", "")])},
        {"shot_id": "S_B", "entry_state": _state([("@C01_NADIA", "")]),  # Jin dropped
         "figures": [_fig("@C01_NADIA", "C01", "looks down")],
         "exit_state": _state([("@C01_NADIA", "")])},
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "CARRIED_SUBJECT_DROPPED" in _codes(issues)


def test_carried_prop_dropped() -> None:
    shots = [
        {"shot_id": "S_A", "figures": [_fig("@C01_NADIA", "C01", "sits")],
         "exit_state": _state([("@C01_NADIA", "")], props=[("@PROP001_BRACELET", "on wrist")])},
        {"shot_id": "S_B", "entry_state": _state([("@C01_NADIA", "")]),  # bracelet dropped
         "figures": [_fig("@C01_NADIA", "C01", "waits")],
         "exit_state": _state([("@C01_NADIA", "")])},
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "CARRIED_PROP_DROPPED" in _codes(issues)


def test_relation_change_explained_by_action_passes() -> None:
    shots = [
        {"shot_id": "S_A", "figures": [_fig("@C01_NADIA", "C01", "holds the child")],
         "exit_state": _state([("@C01_NADIA", "holding @C08_JIN")])},
        {"shot_id": "S_B",
         "entry_state": _state([("@C01_NADIA", "empty hands")]),
         "figures": [_fig("@C01_NADIA", "C01", "@C01_NADIA's arms are emptied as the child is lifted")],
         "exit_state": _state([("@C01_NADIA", "empty hands")])},
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "RELATION_BROKEN_WITHOUT_ACTION" not in _codes(issues)


def test_relation_change_without_action_flags() -> None:
    shots = [
        {"shot_id": "S_A", "figures": [_fig("@C01_NADIA", "C01", "holds the child")],
         "exit_state": _state([("@C01_NADIA", "holding @C08_JIN")])},
        {"shot_id": "S_B",
         "entry_state": _state([("@C01_NADIA", "empty hands")]),
         "figures": [_fig("@C01_NADIA", "C01", "waits")],  # no mention of the change
         "exit_state": _state([("@C01_NADIA", "empty hands")])},
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "RELATION_BROKEN_WITHOUT_ACTION" in _codes(issues)


def test_relation_paraphrase_not_flagged() -> None:
    # "holding @C08_JIN" vs "@C08_JIN in her arms" are the same relation family.
    shots = [
        {"shot_id": "S_A", "figures": [_fig("@C01_NADIA", "C01", "holds")],
         "exit_state": _state([("@C01_NADIA", "holding @C08_JIN")])},
        {"shot_id": "S_B", "entry_state": _state([("@C01_NADIA", "@C08_JIN in her arms")]),
         "figures": [_fig("@C01_NADIA", "C01", "looks up")],
         "exit_state": _state([("@C01_NADIA", "holding @C08_JIN")])},
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    assert "RELATION_BROKEN_WITHOUT_ACTION" not in _codes(issues)


def test_clip_seam_mismatch() -> None:
    ledger = {"CLIP_X": (_state([("@C01_NADIA", ""), ("@C08_JIN", "")]),
                         _state([("@C01_NADIA", "")]))}
    shots = [
        {"shot_id": "S_A",
         "entry_state": _state([("@C01_NADIA", "")]),  # missing @C08_JIN from ledger entry
         "figures": [_fig("@C01_NADIA", "C01", "sits")],
         "exit_state": _state([("@C01_NADIA", "")])},
    ]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)], ledger_states=ledger)
    assert "CLIP_SEAM_MISMATCH" in _codes(issues)


def test_dialogue_speaker_not_in_shot_flags() -> None:
    speakers = {"DLG_1": {"alias": "@C04_DIMITRI", "line_type": "spoken"}}
    shots = [{
        "shot_id": "S_A",
        "dialogue_line_ids": ["DLG_1"],
        "figures": [_fig("@C01_NADIA", "C01", "listens")],  # Dimitri absent
        "exit_state": _state([("@C01_NADIA", "")]),
    }]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)], speakers=speakers)
    assert "DIALOGUE_SPEAKER_NOT_ON_FRAME_OR_OFFSCREEN_MARKED" in _codes(issues)


def test_character_action_duplicated_is_warning_only() -> None:
    shots = [{
        "shot_id": "S_A",
        "prompt_action": "@C04_DIMITRI enters the room as the door opens",
        "figures": [_fig("@C01_NADIA", "C01", "sits"),
                    _fig("@C04_DIMITRI", "C04", "enters the room")],
        "exit_state": _state([("@C01_NADIA", "")]),
    }]
    issues = validate_state_chain("SC0014", [_manifest("CLIP_X", shots)])
    dup = [i for i in issues if i.error_code == "CHARACTER_ACTION_DUPLICATED_IN_PROMPT_ACTION"]
    assert dup and all(i.severity == "warning" for i in dup)


def test_normalize_relation_families() -> None:
    assert _normalize_relation("holding @C08_JIN") == _normalize_relation("@C08_JIN in her arms")
    assert _normalize_relation("cradling the infant") == "holding"
    assert _normalize_relation("restrains @C01_NADIA") == "restraining"
