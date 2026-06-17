from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.reports.export_scene_alias_hints import build_report
from scripts.resolvers.scene_to_kling_alias import (
    SceneAliasResolverError,
    resolve_scene_aliases,
)


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_scene_to_kling_alias_fails_when_look_has_no_alias(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/scene_character_look_map.yaml",
        {
            "scene_id": "SC0001",
            "characters": [
                {
                    "character_id": "C01",
                    "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
                    "look_id": "C01_LOOK_HOME_MORNING_V001",
                    "required": True,
                }
            ],
        },
    )
    with pytest.raises(SceneAliasResolverError, match="no active kling alias record"):
        resolve_scene_aliases(tmp_path, "SC0001")


def test_scene_to_kling_alias_fails_on_duplicate_active_alias_for_same_look(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "visual_dev/omni_sets/SC0001/scene_character_look_map.yaml",
        {
            "scene_id": "SC0001",
            "characters": [
                {
                    "character_id": "C01",
                    "identity_anchor_id": "C01_IDENTITY_ANCHOR_V001",
                    "look_id": "C01_LOOK_HOME_MORNING_V001",
                    "required": True,
                }
            ],
        },
    )
    base = {
        "status": "draft",
        "character_id": "C01",
        "look_id": "C01_LOOK_HOME_MORNING_V001",
        "kling_element_alias": "@C01_HOME_MORNING",
        "kling_character_look_element_id": "KLING_ELEM_C01_HOME_MORNING_V001",
    }
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V001.yaml",
        base,
    )
    _write_yaml(
        tmp_path
        / "visual_dev/elements/characters/C01/kling_elements/KLING_ELEM_C01_HOME_MORNING_V002.yaml",
        {
            **base,
            "kling_element_alias": "@C01_HOME_MORNING_ALT",
            "kling_character_look_element_id": "KLING_ELEM_C01_HOME_MORNING_V002",
        },
    )
    with pytest.raises(SceneAliasResolverError, match="ambiguous active alias"):
        resolve_scene_aliases(tmp_path, "SC0001")


def test_scene_to_kling_alias_fails_when_scene_map_missing(tmp_path: Path) -> None:
    with pytest.raises(SceneAliasResolverError, match="scene map not found"):
        resolve_scene_aliases(tmp_path, "SC0001")


