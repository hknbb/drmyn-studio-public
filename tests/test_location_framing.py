from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_location_framing import check_location_framing  # noqa: E402


def _pack(prompts: list[dict]) -> dict:
    return {
        "record_type": "gpt_images_perspective_pack",
        "prompt_pack_id": "GPTIMG2_LOC001_PACK_V001",
        "element_type": "location",
        "prompts": prompts,
    }


def test_wide_master_with_depth_and_blocking_passes() -> None:
    pack = _pack([
        {
            "prompt_id": "P01",
            "prompt_text": "Wide establishing interior, 24mm lens, deep foreground-to-background, "
            "floor and negative space for actor blocking.",
            "expected_output": {"asset_type": "still", "aspect_ratio": "16:9"},
        }
    ])
    assert check_location_framing(pack) == []


def test_no_wide_master_warns() -> None:
    pack = _pack([
        {
            "prompt_id": "P01",
            "prompt_text": "Close detail of a crib, 24mm, floor space for blocking, depth.",
            "expected_output": {"asset_type": "still", "aspect_ratio": "3:4"},
        }
    ])
    warns = check_location_framing(pack)
    assert any("no WIDE establishing" in w for w in warns)


def test_wide_but_narrow_aspect_warns() -> None:
    pack = _pack([
        {
            "prompt_id": "P01",
            "prompt_text": "Wide establishing room, depth, floor space for blocking.",
            "expected_output": {"asset_type": "still", "aspect_ratio": "3:4"},
        }
    ])
    warns = check_location_framing(pack)
    assert any("without a 16:9" in w for w in warns)


def test_missing_depth_and_blocking_warns() -> None:
    pack = _pack([
        {
            "prompt_id": "P01",
            "prompt_text": "Wide establishing interior of the room.",
            "expected_output": {"asset_type": "still", "aspect_ratio": "2.39:1"},
        }
    ])
    warns = check_location_framing(pack)
    assert any("depth/lens cue" in w for w in warns)
    assert any("actor-blocking" in w for w in warns)


def test_non_location_pack_ignored() -> None:
    pack = _pack([{"prompt_id": "P01", "prompt_text": "x", "expected_output": {"asset_type": "still"}}])
    pack["element_type"] = "character"
    assert check_location_framing(pack) == []
