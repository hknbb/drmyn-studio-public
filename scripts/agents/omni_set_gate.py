"""
Audit the metadata-only Omni set production gate for a scene.

This module reads scene cards, Omni element sets, element descriptors, and pack
manifests. It does not mutate lifecycle fields, run external tools, or create
media binaries.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REQUIRED_PACK_STATUS = "locked"
DEFAULT_STORAGE_POLICY = "no_binary_commits"


class OmniSetGateError(RuntimeError):
    """Raised when the gate audit cannot be written safely."""


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _shot_list_summary(scene_card: dict[str, Any]) -> dict[str, Any]:
    shot_list = scene_card.get("shot_list_omni")
    if not isinstance(shot_list, list) or not shot_list:
        return {
            "ready": False,
            "shot_count": 0,
            "total_duration_seconds": 0,
        }
    durations = [
        shot.get("duration_seconds")
        for shot in shot_list
        if isinstance(shot, dict)
    ]
    valid_durations = [duration for duration in durations if isinstance(duration, int)]
    return {
        "ready": len(valid_durations) == len(shot_list),
        "shot_count": len(shot_list),
        "total_duration_seconds": sum(valid_durations),
    }


def _element_entry(
    *,
    repo_root: Path,
    element_ref: str,
) -> tuple[dict[str, Any], list[str]]:
    descriptor_path = repo_root / element_ref
    descriptor = _read_yaml(descriptor_path)
    issues: list[str] = []

    entry: dict[str, Any] = {
        "element_ref": element_ref,
        "descriptor_exists": isinstance(descriptor, dict),
        "pack_path_expected": None,
        "pack_manifest_ref": None,
        "pack_manifest_exists": False,
        "pack_status": None,
        "ready": False,
    }
    if not isinstance(descriptor, dict):
        issues.append(f"missing element descriptor: {element_ref}")
        return entry, issues

    pack_path = _text(descriptor.get("pack_path_expected"))
    entry["pack_path_expected"] = pack_path or None
    if not pack_path:
        issues.append(f"missing pack_path_expected in {element_ref}")
        return entry, issues

    pack_manifest_path = repo_root / pack_path / "pack_manifest.yaml"
    entry["pack_manifest_ref"] = _relative(pack_manifest_path, repo_root)
    pack_manifest = _read_yaml(pack_manifest_path)
    entry["pack_manifest_exists"] = isinstance(pack_manifest, dict)
    if not isinstance(pack_manifest, dict):
        issues.append(f"missing pack_manifest.yaml at {pack_path}")
        return entry, issues

    pack_status = pack_manifest.get("pack_status")
    entry["pack_status"] = pack_status
    entry["ready"] = pack_status == REQUIRED_PACK_STATUS
    if pack_status != REQUIRED_PACK_STATUS:
        issues.append(
            f"{pack_path} pack_status is {pack_status!r}, expected {REQUIRED_PACK_STATUS!r}"
        )
    return entry, issues


def _pack_summary(elements: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_elements": len(elements),
        "ready_packs": sum(1 for item in elements if item.get("ready") is True),
        "metadata_only_packs": sum(
            1 for item in elements if item.get("pack_status") == "metadata_only"
        ),
        "missing_pack_manifests": sum(
            1 for item in elements if item.get("pack_manifest_exists") is False
        ),
        "missing_descriptors": sum(
            1 for item in elements if item.get("descriptor_exists") is False
        ),
    }


def audit_omni_set_gate(
    repo_root: str | Path,
    scene_id: str,
    *,
    generated_at: str = "2026-05-04T19:30:00Z",
) -> dict[str, Any]:
    """Return a deterministic metadata-only Omni set gate report."""

    root = Path(repo_root)
    scene_card_path = root / "planning" / "scenes" / scene_id / "scene_card.yaml"
    scene_card = _read_yaml(scene_card_path)
    if not isinstance(scene_card, dict):
        raise OmniSetGateError(f"Missing scene card: {_relative(scene_card_path, root)}")

    blocking_reasons: list[str] = []
    shot_list = _shot_list_summary(scene_card)
    if not shot_list["ready"] or shot_list["shot_count"] == 0:
        blocking_reasons.append("scene_card.shot_list_omni is missing or invalid")

    omni_set_ref = _text(scene_card.get("omni_set_ref"))
    element_set_ref = f"{omni_set_ref.rstrip('/')}/element_set.yaml" if omni_set_ref else None
    element_set = _read_yaml(root / element_set_ref) if element_set_ref else None
    elements: list[dict[str, Any]] = []
    element_issues: list[str] = []
    if not omni_set_ref:
        blocking_reasons.append("scene_card.omni_set_ref is missing")
    elif not isinstance(element_set, dict):
        blocking_reasons.append(f"missing element_set.yaml for {scene_id}")
    else:
        refs = element_set.get("element_refs")
        if not isinstance(refs, list) or not refs:
            blocking_reasons.append("element_set.element_refs is missing or empty")
        else:
            for ref in refs:
                entry, issues = _element_entry(repo_root=root, element_ref=str(ref))
                elements.append(entry)
                element_issues.extend(issues)

    blocking_reasons.extend(element_issues)
    pack_summary = _pack_summary(elements)
    if pack_summary["total_elements"] > 0 and pack_summary["ready_packs"] == 0:
        gate_status = "blocked_pending_locked_element_packs"
    elif blocking_reasons:
        gate_status = "blocked_missing_or_invalid_omni_set_metadata"
    else:
        gate_status = "ready_for_kling_prompt_generation"

    return {
        "scene_id": scene_id,
        "generated_at": generated_at,
        "gate_status": gate_status,
        "ready_for_kling_prompt_generation": not blocking_reasons,
        "scene_card_ref": _relative(scene_card_path, root),
        "omni_set_ref": omni_set_ref or None,
        "element_set_ref": element_set_ref,
        "shot_list_gate": shot_list,
        "element_pack_gate": {
            "required_pack_status": REQUIRED_PACK_STATUS,
            "summary": pack_summary,
            "elements": elements,
        },
        "blocking_reasons": blocking_reasons,
        "storage_policy": DEFAULT_STORAGE_POLICY,
        "external_generation_performed": False,
        "binary_outputs_created": False,
        "lifecycle_promotion_performed": False,
    }


def write_omni_set_gate_report(
    repo_root: str | Path,
    scene_id: str,
    *,
    output_path: str | Path | None = None,
    generated_at: str = "2026-05-04T19:30:00Z",
) -> Path:
    """Write a metadata-only gate report for one scene."""

    root = Path(repo_root)
    report = audit_omni_set_gate(root, scene_id, generated_at=generated_at)
    out_path = (
        Path(output_path)
        if output_path is not None
        else root / "evidence" / "omni_set_gates" / f"{scene_id}_gate.yaml"
    )
    _write_yaml(out_path, report)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--output-path")
    parser.add_argument("--generated-at", default="2026-05-04T19:30:00Z")
    args = parser.parse_args(argv)

    write_omni_set_gate_report(
        args.repo_root,
        args.scene_id,
        output_path=args.output_path,
        generated_at=args.generated_at,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
