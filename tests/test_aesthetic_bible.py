from __future__ import annotations

import json
import socket
import sys
import urllib.request
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agents.aesthetic_bible import (  # noqa: E402
    AestheticBibleError,
    AestheticPack,
    get_pack_ids_from_records,
    load_aesthetic_bible,
    resolve_pack_keywords,
    resolve_pack_negatives,
)
from scripts.validate_production_records import run_validation  # noqa: E402


SCHEMA_PATH = REPO_ROOT / "schemas" / "aesthetic_bible.schema.json"
BIBLE_PATH = REPO_ROOT / "planning" / "aesthetic_bible.yaml"


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_schema(tmp_path: Path) -> None:
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "aesthetic_bible.schema.json",
        "image_selection.schema.json",
        "asset_clearance.schema.json",
        "batch_job.schema.json",
    ):
        (schemas_dir / name).write_text(
            (REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _valid_pack(pack_id: str = "TEST_PACK_ALPHA") -> dict:
    return {
        "pack_id": pack_id,
        "name": "Test pack alpha",
        "visual_thesis": "A test visual thesis with enough words to be meaningful.",
        "derived_from": {
            "style_bible_sections": ["Palette rules"],
        },
        "search_keywords": [
            "kw1", "kw2", "kw3", "kw4",
            "kw5", "kw6", "kw7", "kw8",
        ],
        "element_keyword_map": {
            "t2i_character_element": ["char_kw_1", "char_kw_2"],
            "t2i_location_element": ["loc_kw_1", "loc_kw_2"],
            "t2i_prop_element": ["prop_kw_1", "prop_kw_2"],
            "t2i_wardrobe_element": ["wd_kw_1", "wd_kw_2"],
        },
        "do_not_keywords": ["bad_kw_1", "bad_kw_2"],
    }


def _valid_bible_payload(pack_ids: list[str] | None = None) -> dict:
    if pack_ids is None:
        pack_ids = ["TEST_PACK_ALPHA"]
    return {
        "schema_version": 1,
        "packs": [_valid_pack(pid) for pid in pack_ids],
    }


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_canonical_aesthetic_bible_passes_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = yaml.safe_load(BIBLE_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert errors == []


def test_canonical_aesthetic_bible_has_four_initial_packs() -> None:
    payload = yaml.safe_load(BIBLE_PATH.read_text(encoding="utf-8"))
    pack_ids = [pack["pack_id"] for pack in payload["packs"]]
    assert pack_ids == [
        "VALE_DOMESTIC_RESTRAINT",
        "KASPAR_INSTITUTIONAL_SURVEILLANCE",
        "MERIN_INDUSTRIAL_DECAY",
        "ORACLE_BROADCAST_CLEAN",
    ]


def test_aesthetic_bible_rejects_invalid_pack_id_lowercase() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = _valid_bible_payload()
    payload["packs"][0]["pack_id"] = "vale_domestic"
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert any("pack_id" in str(e.absolute_path) for e in errors)


def test_aesthetic_bible_rejects_invalid_pack_id_with_hyphen() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = _valid_bible_payload()
    payload["packs"][0]["pack_id"] = "VALE-DOMESTIC"
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert any("pack_id" in str(e.absolute_path) for e in errors)


def test_aesthetic_bible_rejects_invalid_pack_id_with_space() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = _valid_bible_payload()
    payload["packs"][0]["pack_id"] = "VALE DOMESTIC"
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert any("pack_id" in str(e.absolute_path) for e in errors)


def test_aesthetic_bible_rejects_missing_required_element_type() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = _valid_bible_payload()
    del payload["packs"][0]["element_keyword_map"]["t2i_prop_element"]
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert any(
        "t2i_prop_element" in e.message or "element_keyword_map" in str(e.absolute_path)
        for e in errors
    )


def test_aesthetic_bible_rejects_extra_top_level_field() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = _valid_bible_payload()
    payload["unexpected_field"] = "x"
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert errors


# ---------------------------------------------------------------------------
# Validator dispatch
# ---------------------------------------------------------------------------

def test_validator_accepts_aesthetic_bible(tmp_path: Path) -> None:
    _copy_schema(tmp_path)
    _write_yaml(tmp_path / "planning" / "aesthetic_bible.yaml", _valid_bible_payload())

    report = run_validation(tmp_path)

    assert report.by_record_type.get("aesthetic_bible") == 1
    assert report.invalid_files == 0
    assert report.issues == []


def test_validator_rejects_invalid_aesthetic_bible(tmp_path: Path) -> None:
    _copy_schema(tmp_path)
    payload = _valid_bible_payload()
    payload["packs"][0]["pack_id"] = "lowercase_id"
    _write_yaml(tmp_path / "planning" / "aesthetic_bible.yaml", payload)

    report = run_validation(tmp_path)

    assert report.invalid_files == 1
    assert any(
        issue.record_type == "aesthetic_bible"
        and "pack_id" in issue.field_path
        for issue in report.issues
    )


def test_validator_skips_when_aesthetic_bible_absent(tmp_path: Path) -> None:
    _copy_schema(tmp_path)

    report = run_validation(tmp_path)

    assert report.by_record_type.get("aesthetic_bible") == 0
    assert report.invalid_files == 0


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def test_load_aesthetic_bible_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_aesthetic_bible(tmp_path) is None


def test_load_aesthetic_bible_parses_canonical_file() -> None:
    bible = load_aesthetic_bible(REPO_ROOT)
    assert bible is not None
    assert bible.schema_version == 1
    assert [p.pack_id for p in bible.packs] == [
        "VALE_DOMESTIC_RESTRAINT",
        "KASPAR_INSTITUTIONAL_SURVEILLANCE",
        "MERIN_INDUSTRIAL_DECAY",
        "ORACLE_BROADCAST_CLEAN",
    ]
    vale = bible.get_pack("VALE_DOMESTIC_RESTRAINT")
    assert vale is not None
    assert vale.element_keyword_map["t2i_character_element"]
    assert vale.do_not_keywords


def test_load_aesthetic_bible_raises_on_wrong_schema_version(tmp_path: Path) -> None:
    payload = _valid_bible_payload()
    payload["schema_version"] = 2
    _write_yaml(tmp_path / "planning" / "aesthetic_bible.yaml", payload)

    with pytest.raises(AestheticBibleError, match="schema_version"):
        load_aesthetic_bible(tmp_path)


def test_load_aesthetic_bible_raises_on_non_mapping_root(tmp_path: Path) -> None:
    path = tmp_path / "planning" / "aesthetic_bible.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(AestheticBibleError, match="mapping"):
        load_aesthetic_bible(tmp_path)


# ---------------------------------------------------------------------------
# Resolver helpers — determinism + dedupe
# ---------------------------------------------------------------------------

def _make_pack(
    pack_id: str,
    *,
    char: tuple[str, ...] = ("char_a", "char_b"),
    loc: tuple[str, ...] = ("loc_a", "loc_b"),
    do_not: tuple[str, ...] = ("bad_a", "bad_b"),
) -> AestheticPack:
    return AestheticPack(
        pack_id=pack_id,
        name=pack_id,
        visual_thesis="thesis",
        derived_from={"style_bible_sections": ("Palette rules",)},
        search_keywords=tuple(f"sk{n}" for n in range(8)),
        element_keyword_map={
            "t2i_character_element": char,
            "t2i_location_element": loc,
            "t2i_prop_element": ("prop_a", "prop_b"),
            "t2i_wardrobe_element": ("wd_a", "wd_b"),
        },
        do_not_keywords=do_not,
    )


def test_get_pack_ids_merges_scene_and_element_refs_in_order() -> None:
    scene = {"visual_targets": {"aesthetic_pack_refs": ["A", "B"]}}
    element = {"aesthetic_pack_refs": ["B", "C"]}

    result = get_pack_ids_from_records(scene, element)

    assert result == ["A", "B", "C"]


def test_get_pack_ids_handles_missing_sources() -> None:
    assert get_pack_ids_from_records(None, None) == []
    assert get_pack_ids_from_records({}, None) == []
    assert get_pack_ids_from_records({"visual_targets": {}}, None) == []
    assert get_pack_ids_from_records(None, {"aesthetic_pack_refs": ["X"]}) == ["X"]


def test_get_pack_ids_is_deterministic_across_calls() -> None:
    scene = {"visual_targets": {"aesthetic_pack_refs": ["A", "B", "A"]}}
    element = {"aesthetic_pack_refs": ["B"]}

    first = get_pack_ids_from_records(scene, element)
    second = get_pack_ids_from_records(scene, element)

    assert first == second == ["A", "B"]


def test_resolve_pack_keywords_picks_first_n_in_order() -> None:
    packs = [
        _make_pack("PACK_A", char=("a1", "a2", "a3")),
        _make_pack("PACK_B", char=("b1", "b2", "b3")),
    ]

    result = resolve_pack_keywords(
        packs, ["PACK_A", "PACK_B"], "t2i_character_element", limit_per_pack=2
    )

    assert result == ["a1", "a2", "b1", "b2"]


def test_resolve_pack_keywords_dedupes_across_packs() -> None:
    packs = [
        _make_pack("PACK_A", char=("shared", "a2")),
        _make_pack("PACK_B", char=("shared", "b2")),
    ]

    result = resolve_pack_keywords(
        packs, ["PACK_A", "PACK_B"], "t2i_character_element", limit_per_pack=2
    )

    assert result == ["shared", "a2", "b2"]


def test_resolve_pack_keywords_skips_unknown_pack_ids() -> None:
    packs = [_make_pack("PACK_A")]
    assert (
        resolve_pack_keywords(packs, ["PACK_A", "MISSING"], "t2i_character_element", 2)
        == ["char_a", "char_b"]
    )


def test_resolve_pack_keywords_skips_packs_without_prompt_type() -> None:
    pack = AestheticPack(
        pack_id="MIN_PACK",
        name="min",
        visual_thesis="thesis",
        derived_from={"style_bible_sections": ("x",)},
        search_keywords=("a",),
        element_keyword_map={"t2i_character_element": ("only_char",)},
        do_not_keywords=("bad",),
    )

    result = resolve_pack_keywords([pack], ["MIN_PACK"], "t2i_location_element", 2)

    assert result == []


def test_resolve_pack_keywords_is_deterministic() -> None:
    packs = [_make_pack("PACK_A"), _make_pack("PACK_B")]
    pack_ids = ["PACK_A", "PACK_B"]

    runs = [
        resolve_pack_keywords(packs, pack_ids, "t2i_character_element", 2)
        for _ in range(5)
    ]

    assert all(run == runs[0] for run in runs)


def test_resolve_pack_keywords_rejects_negative_limit() -> None:
    packs = [_make_pack("PACK_A")]
    with pytest.raises(ValueError, match="limit_per_pack"):
        resolve_pack_keywords(packs, ["PACK_A"], "t2i_character_element", -1)


def test_resolve_pack_negatives_unions_all_packs() -> None:
    packs = [
        _make_pack("PACK_A", do_not=("a1", "shared")),
        _make_pack("PACK_B", do_not=("shared", "b1")),
    ]

    result = resolve_pack_negatives(packs, ["PACK_A", "PACK_B"])

    assert result == ["a1", "shared", "b1"]


def test_resolve_pack_negatives_skips_unknown() -> None:
    packs = [_make_pack("PACK_A", do_not=("a1",))]
    assert resolve_pack_negatives(packs, ["MISSING"]) == []
    assert resolve_pack_negatives(packs, ["PACK_A", "MISSING"]) == ["a1"]


# ---------------------------------------------------------------------------
# Network-isolation guard
# ---------------------------------------------------------------------------

def test_aesthetic_bible_helpers_make_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_urlopen(*args: object, **kwargs: object) -> object:
        raise AssertionError("aesthetic_bible helpers must not call urllib.request.urlopen")

    def _fail_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("aesthetic_bible helpers must not open sockets")

    monkeypatch.setattr(urllib.request, "urlopen", _fail_urlopen)
    monkeypatch.setattr(socket, "create_connection", _fail_socket)

    bible = load_aesthetic_bible(REPO_ROOT)
    assert bible is not None

    pack_ids = get_pack_ids_from_records(
        {"visual_targets": {"aesthetic_pack_refs": ["VALE_DOMESTIC_RESTRAINT"]}},
        None,
    )
    keywords = resolve_pack_keywords(
        bible.packs, pack_ids, "t2i_character_element", 2
    )
    negatives = resolve_pack_negatives(bible.packs, pack_ids)

    assert keywords
    assert negatives
