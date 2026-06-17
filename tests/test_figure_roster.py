from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_figure_roster import (  # noqa: E402
    collect_figures_from_manifest,
    validate_figure_roster,
)


def _fig(figure_id: str, base: str, alias: str, role: str) -> dict:
    return {"figure_id": figure_id, "base_element_id": base, "kling_alias": alias, "role": role}


def _manifest(shots: list[dict]) -> dict:
    return {"record_type": "omni_clip_manifest", "shots": shots}


def test_two_distinct_aliases_same_base_passes() -> None:
    figs = [
        ("SHOT_A", _fig("FIG_HOLDER", "C10", "@C10_HOLDER", "restrains Nadia")),
        ("SHOT_A", _fig("FIG_CARRIER", "C10", "@C10_CARRIER", "carries the infant")),
    ]
    errs = validate_figure_roster("SC0014", figs, {"@C10_HOLDER", "@C10_CARRIER"})
    assert errs == []


def test_one_alias_two_figures_fails() -> None:
    figs = [
        ("SHOT_A", _fig("FIG_HOLDER", "C10", "@C10_ENFORCER", "restrains Nadia")),
        ("SHOT_B", _fig("FIG_CARRIER", "C10", "@C10_ENFORCER", "carries the infant")),
    ]
    codes = [e.error_code for e in validate_figure_roster("SC0014", figs, {"@C10_ENFORCER"})]
    assert "ALIAS_MULTIPLE_FIGURES" in codes


def test_alias_reused_in_same_shot_fails() -> None:
    figs = [
        ("SHOT_A", _fig("FIG_HOLDER", "C10", "@C10_OP", "a")),
        ("SHOT_A", _fig("FIG_CARRIER", "C10", "@C10_OP", "b")),
    ]
    codes = [e.error_code for e in validate_figure_roster("SC0014", figs, {"@C10_OP"})]
    assert "ALIAS_REUSED_IN_SHOT" in codes


def test_figure_with_two_aliases_fails() -> None:
    figs = [
        ("SHOT_A", _fig("FIG_HOLDER", "C10", "@C10_HOLDER", "r")),
        ("SHOT_B", _fig("FIG_HOLDER", "C10", "@C10_OTHER", "r")),
    ]
    codes = [e.error_code for e in validate_figure_roster("SC0014", figs, {"@C10_HOLDER", "@C10_OTHER"})]
    assert "FIGURE_MULTIPLE_ALIASES" in codes


def test_unbound_alias_fails() -> None:
    figs = [("SHOT_A", _fig("FIG_HOLDER", "C10", "@C10_HOLDER", "r"))]
    codes = [e.error_code for e in validate_figure_roster("SC0014", figs, set())]
    assert "ALIAS_NOT_BOUND" in codes


def test_no_binding_check_when_bound_is_none() -> None:
    figs = [("SHOT_A", _fig("FIG_HOLDER", "C10", "@C10_HOLDER", "r"))]
    assert validate_figure_roster("SC0014", figs, None) == []


def test_collect_figures_from_manifest() -> None:
    manifest = _manifest([
        {"shot_id": "SHOT_A", "figures": [_fig("FIG_H", "C10", "@C10_HOLDER", "r")]},
        {"shot_id": "SHOT_B", "figures": []},
        {"shot_id": "SHOT_C"},
    ])
    collected = collect_figures_from_manifest(manifest)
    assert len(collected) == 1
    assert collected[0][0] == "SHOT_A"
    assert collected[0][1]["kling_alias"] == "@C10_HOLDER"
