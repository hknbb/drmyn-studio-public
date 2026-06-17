"""
Figure roster validator (anti-clone).

Kling Omni collapses two physically distinct figures into one (or hallucinates
clones) when a single element/@alias is reused for more than one on-screen figure.
This validator enforces, per scene, that every distinct figure has its own alias:

1. ALIAS_REUSED_IN_SHOT     - the same kling_alias appears twice in one shot's figures.
2. ALIAS_MULTIPLE_FIGURES   - one kling_alias is bound to >1 distinct figure_id/role
                              across the scene (one alias doing two figures).
3. FIGURE_MULTIPLE_ALIASES  - one figure_id uses >1 distinct kling_alias across the scene.
4. ALIAS_NOT_BOUND          - a figure's kling_alias is not declared in the scene's
                              element_bindings.yaml.

Read-only. Operates on already-parsed records so it is reusable from the
production validator and from tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FigureRosterError(ValueError):
    scene_id: str
    error_code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.scene_id}] {self.error_code}: {self.message}"


def collect_figures_from_manifest(manifest: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return [(shot_id, figure_dict), ...] for one omni_clip_manifest."""
    out: list[tuple[str, dict[str, Any]]] = []
    for shot in manifest.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id", "?")
        for fig in shot.get("figures") or []:
            if isinstance(fig, dict):
                out.append((shot_id, fig))
    return out


def bound_aliases_from_bindings(binding_docs: list[dict[str, Any]]) -> set[str]:
    aliases: set[str] = set()
    for doc in binding_docs:
        if isinstance(doc, dict):
            alias = doc.get("kling_alias")
            if isinstance(alias, str) and alias:
                aliases.add(alias)
    return aliases


def validate_figure_roster(
    scene_id: str,
    shot_figures: list[tuple[str, dict[str, Any]]],
    bound_aliases: set[str] | None,
) -> list[FigureRosterError]:
    errors: list[FigureRosterError] = []

    # Rule 1: no alias repeated within a single shot.
    per_shot: dict[str, list[str]] = {}
    for shot_id, fig in shot_figures:
        alias = fig.get("kling_alias")
        if isinstance(alias, str):
            per_shot.setdefault(shot_id, []).append(alias)
    for shot_id, aliases in per_shot.items():
        dupes = {a for a in aliases if aliases.count(a) > 1}
        for a in sorted(dupes):
            errors.append(
                FigureRosterError(
                    scene_id, "ALIAS_REUSED_IN_SHOT",
                    f"shot {shot_id}: alias {a} attached to more than one figure in the same shot.",
                )
            )

    # Scene-wide consistency.
    alias_to_figures: dict[str, set[str]] = {}
    alias_to_roles: dict[str, set[str]] = {}
    figure_to_aliases: dict[str, set[str]] = {}
    for _shot_id, fig in shot_figures:
        alias = fig.get("kling_alias")
        figure_id = fig.get("figure_id")
        role = fig.get("role")
        if isinstance(alias, str) and isinstance(figure_id, str):
            alias_to_figures.setdefault(alias, set()).add(figure_id)
            figure_to_aliases.setdefault(figure_id, set()).add(alias)
        if isinstance(alias, str) and isinstance(role, str):
            alias_to_roles.setdefault(alias, set()).add(role)

    for alias, figs in sorted(alias_to_figures.items()):
        if len(figs) > 1:
            errors.append(
                FigureRosterError(
                    scene_id, "ALIAS_MULTIPLE_FIGURES",
                    f"alias {alias} is bound to multiple distinct figures {sorted(figs)}; "
                    "give each figure its own alias (anti-clone).",
                )
            )
    for alias, roles in sorted(alias_to_roles.items()):
        if len(roles) > 1:
            errors.append(
                FigureRosterError(
                    scene_id, "ALIAS_MULTIPLE_FIGURES",
                    f"alias {alias} carries conflicting roles {sorted(roles)} across the scene.",
                )
            )
    for figure_id, aliases in sorted(figure_to_aliases.items()):
        if len(aliases) > 1:
            errors.append(
                FigureRosterError(
                    scene_id, "FIGURE_MULTIPLE_ALIASES",
                    f"figure {figure_id} uses multiple aliases {sorted(aliases)}; "
                    "a figure must map to exactly one alias.",
                )
            )

    # Rule 4: aliases must be bound in element_bindings.
    if bound_aliases is not None:
        for alias in sorted(alias_to_figures):
            if alias not in bound_aliases:
                errors.append(
                    FigureRosterError(
                        scene_id, "ALIAS_NOT_BOUND",
                        f"alias {alias} is used by a figure but is not declared in the scene's "
                        "element_bindings.yaml.",
                    )
                )

    return errors


def _load_yaml_docs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [d for d in yaml.safe_load_all(f) if isinstance(d, dict)]


def validate_scene_figures(repo_root: str | Path, scene_id: str) -> list[FigureRosterError]:
    """Load a scene's omni_clip_manifests + element_bindings and validate the roster."""
    repo_root = Path(repo_root)
    manifests_dir = repo_root / "planning" / "scenes" / scene_id / "manifests"
    shot_figures: list[tuple[str, dict[str, Any]]] = []
    for mpath in sorted(manifests_dir.glob("*.yaml")):
        docs = _load_yaml_docs(mpath)
        for doc in docs:
            if doc.get("record_type") == "omni_clip_manifest":
                shot_figures.extend(collect_figures_from_manifest(doc))

    bindings_path = repo_root / "visual_dev" / "omni_sets" / scene_id / "element_bindings.yaml"
    bound = bound_aliases_from_bindings(_load_yaml_docs(bindings_path)) if bindings_path.exists() else None

    return validate_figure_roster(scene_id, shot_figures, bound)
