"""
Location framing soft-check.

ChatGPT Images 2 location references tend to come out narrow / box-like, leaving
no floor or negative space for actor blocking. This soft-check flags location
gpt_images_perspective_pack prompts that lack cinematic-width cues so the operator
can widen them before generating. It returns WARNINGS, never hard failures — it is
intentionally not wired as a blocking gate in the production validator.

A location reference pack should have at least one WIDE establishing prompt that:
  - states wide / establishing framing,
  - uses a 16:9 or 2.39:1 aspect ratio,
  - and ideally cites depth, a lens (e.g. 24mm), and explicit actor blocking /
    coverage space (floor + negative space).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_WIDE_CUES = ("wide", "establishing", "full room", "full set", "expansive")
_DEPTH_CUES = ("depth", "deep", "foreground", "background", "mm", "lens")
_BLOCKING_CUES = ("blocking", "coverage", "room to move", "floor", "negative space", "space for")
_WIDE_AR = ("16:9", "2.39", "2.39:1", "21:9")


def _has(text: str, cues: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(c in low for c in cues)


def check_location_framing(pack: dict[str, Any]) -> list[str]:
    """Return warnings for a location gpt_images_perspective_pack. Empty == fine."""
    warnings: list[str] = []
    if pack.get("element_type") != "location":
        return warnings
    prompts = pack.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        return warnings

    pack_id = pack.get("prompt_pack_id", "?")
    has_wide_master = False
    for p in prompts:
        if not isinstance(p, dict):
            continue
        text = str(p.get("prompt_text", ""))
        ar = str((p.get("expected_output") or {}).get("aspect_ratio", ""))
        wide = _has(text, _WIDE_CUES)
        wide_ar = any(a in ar for a in _WIDE_AR)
        if wide and wide_ar:
            has_wide_master = True
        if wide and not wide_ar:
            warnings.append(
                f"{pack_id}/{p.get('prompt_id', '?')}: wide framing without a 16:9 or 2.39:1 "
                "aspect ratio; widen the frame for actor blocking."
            )

    if not has_wide_master:
        warnings.append(
            f"{pack_id}: no WIDE establishing prompt at a 16:9/2.39:1 aspect ratio; "
            "location may render narrow/box-like with no room for actor blocking."
        )

    # Recommend depth + blocking cues somewhere in the pack.
    joined = " ".join(str(p.get("prompt_text", "")) for p in prompts if isinstance(p, dict))
    if not _has(joined, _DEPTH_CUES):
        warnings.append(
            f"{pack_id}: no depth/lens cue (e.g. '24mm', 'deep foreground-to-background'); "
            "add spatial depth for cinematic width."
        )
    if not _has(joined, _BLOCKING_CUES):
        warnings.append(
            f"{pack_id}: no actor-blocking/coverage space cue (e.g. 'floor and negative space "
            "for blocking'); reference may not leave room for performers."
        )
    return warnings


def check_location_framing_file(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return []
    return check_location_framing(data)
