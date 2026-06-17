"""
Cross-record scene status-consistency validator.

Catches the SC0014-class contradiction where a shot_element_manifest declares
``gate_status: all_elements_ready`` while one of its required elements has no
active element_binding at (or above) the required registration state. Status
claimed in one record must not contradict the bindings the scene actually has.

Read-only; operates on parsed records so it is reusable from the production
validator and from tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Ordered registration states: a binding satisfies a requirement if its status is
# at the same level or higher.
_REGISTRATION_ORDER = {"planned": 0, "created": 1, "voice_capable": 2, "voice_locked": 3}


@dataclass
class SceneStatusConsistencyError(ValueError):
    scene_id: str
    error_code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.scene_id}] {self.error_code}: {self.message}"


def _binding_satisfies(binding_status: str | None, required: str | None) -> bool:
    have = _REGISTRATION_ORDER.get(str(binding_status), -1)
    need = _REGISTRATION_ORDER.get(str(required), 0)
    return have >= need


def validate_scene_status_consistency(
    scene_id: str,
    manifests: list[dict[str, Any]],
    binding_status_by_element: dict[str, str],
) -> list[SceneStatusConsistencyError]:
    errors: list[SceneStatusConsistencyError] = []
    for manifest in manifests:
        if not isinstance(manifest, dict):
            continue
        if manifest.get("gate_status") != "all_elements_ready":
            continue
        shot_id = manifest.get("shot_id", manifest.get("manifest_id", "?"))
        env_only = set(manifest.get("environmental_only_allowed_ids") or [])
        for req in manifest.get("required_elements") or []:
            if not isinstance(req, dict):
                continue
            eid = req.get("element_id")
            if not isinstance(eid, str) or eid in env_only:
                continue
            required_state = req.get("registration_state_required")
            status = binding_status_by_element.get(eid)
            if status is None:
                errors.append(
                    SceneStatusConsistencyError(
                        scene_id, "STATUS_CONTRADICTION",
                        f"{shot_id}: gate_status=all_elements_ready but required element "
                        f"{eid} has no element_binding.",
                    )
                )
            elif not _binding_satisfies(status, required_state):
                errors.append(
                    SceneStatusConsistencyError(
                        scene_id, "STATUS_CONTRADICTION",
                        f"{shot_id}: gate_status=all_elements_ready but element {eid} binding "
                        f"status {status!r} does not meet required {required_state!r}.",
                    )
                )
    return errors


def _load_yaml_docs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [d for d in yaml.safe_load_all(f) if isinstance(d, dict)]


def validate_scene_status_consistency_for_scene(
    repo_root: str | Path, scene_id: str
) -> list[SceneStatusConsistencyError]:
    repo_root = Path(repo_root)
    manifests_dir = (
        repo_root / "visual_dev" / "omni_sets" / scene_id / "shot_element_manifests"
    )
    manifests: list[dict[str, Any]] = []
    for mpath in sorted(manifests_dir.glob("*.yaml")):
        data = _load_yaml_docs(mpath)
        manifests.extend(
            d for d in data if d.get("record_type") == "shot_element_manifest"
        )

    bindings_path = (
        repo_root / "visual_dev" / "omni_sets" / scene_id / "element_bindings.yaml"
    )
    status_by_elem: dict[str, str] = {}
    for doc in _load_yaml_docs(bindings_path):
        eid = doc.get("element_id")
        status = doc.get("binding_status")
        if isinstance(eid, str) and isinstance(status, str):
            # Keep the highest binding status seen for an element (multiple figure
            # bindings can share an element_id).
            prev = status_by_elem.get(eid)
            if prev is None or _REGISTRATION_ORDER.get(status, -1) > _REGISTRATION_ORDER.get(prev, -1):
                status_by_elem[eid] = status

    return validate_scene_status_consistency(scene_id, manifests, status_by_elem)
