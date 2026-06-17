"""
Kling Omni metadata-only prompt adapter for Batch 8.

This adapter writes draft prompt/run metadata for external Kling generation.
It never calls Kling, never writes video binaries, and never creates video take
review or selected clip records.

Model version resolved from model_guidance_snapshot at runtime via dynamic_snapshot
mode, not hardcoded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from scripts.agents.model_guidance_resolver import (
    ModelGuidanceResolutionError,
    resolve_model_guidance,
)


CANONICAL_ID_RE = re.compile(r"\b(SC\d{4}|C\d{2}|LOC\d{3}|PROP\d{3}|WD\d{3})\b")
CHARACTER_ID_RE = re.compile(r"^C\d{2}$")

# Strict canonical-id leak guard for element-first Kling Omni 3 prompts.
# Matches any repo-canonical element identifier (C##, LOC###, LOC###_SUBAREA,
# PROP###, WD###, STYLE###). When the strict gate is active the synthesized
# prompt_text must reference elements only through their @alias values; raw
# canonical IDs must not leak into the text Kling receives.
ELEMENT_CANONICAL_ID_LEAK_RE = re.compile(
    r"(?<!@)\b(C\d{2}|LOC\d{3}(?:_[A-Z0-9_]+)?|PROP\d{3}|WD\d{3}|STYLE\d{3})\b"
)
MANIFEST_READY_GATE_STATUS = "all_elements_ready"

# Matches screenplay-style speaker cues: SPEAKERNAME: "..." or NAME (CONT'D): "..."
# Handles truncated lines (no closing quote). Used to strip dialogue from prompt_action
# when the audio_plan component owns the spoken content.
SCREENPLAY_CUE_RE = re.compile(
    r"""\b[A-Z]{2,}(?:\s+\(CONT'D\))?\s*:\s*"[^"]*"?"""
)


def _assert_no_canonical_id_leak(prompt_text: str) -> None:
    """Raise KlingOmniAdapterError if a repo-canonical element ID leaks into prompt_text.

    The element-first contract requires Kling Omni 3 prompts to reference
    elements only via their registered @alias. Canonical IDs (``C01``,
    ``LOC001``, ``PROP003`` and so on) belong in YAML metadata fields, not
    in the prompt text the model sees.
    """
    matches = sorted({m.group(0) for m in ELEMENT_CANONICAL_ID_LEAK_RE.finditer(prompt_text)})
    if matches:
        raise KlingOmniAdapterError(
            "prompt_text leaks repo-canonical element ids that must appear "
            "only as registered @aliases: " + ", ".join(matches)
        )

# Binding statuses that mean the element is active in Kling Element Library
ACTIVE_BINDING_STATUSES = frozenset({"created", "voice_capable", "voice_locked"})

# Pronouns that may be rewritten to a character alias when exactly one character is known
LEADING_PRONOUN_RE = re.compile(r"^(She|He|Her|His)\b")
VARIANT_MODES = frozenset({"safe", "creative", "aggressive"})
RENDER_PASSES = frozenset(
    {"visual_test", "performance_test", "final_candidate", "final_locked"}
)
# Final passes: the prompt is a delivery artifact, so a >2500-char overflow is a
# hard failure rather than a warning (the API would reject/truncate it).
_FINAL_PASSES = frozenset({"final_candidate", "final_locked"})
QUALITY_TIERS = frozenset({"test_720p", "final_1080p"})

# Goro-style timecode-first shot heading labels. A shot's natural framing label
# is chosen from coverage_role first (so a reaction/insert reads as "Cutaway"/
# "Insert"), then from the camera.framing enum.
_FRAMING_LABELS: dict[str, str] = {
    "wide": "Wide shot",
    "medium_wide": "Medium-wide shot",
    "medium": "Medium shot",
    "medium_close": "Medium close-up",
    "close": "Close-up",
    "extreme_close": "Extreme close-up",
    "insert": "Insert",
}
_COVERAGE_LABELS: dict[str, str] = {
    "insert": "Insert",
    "detail": "Insert",
    "reaction": "Cutaway",
    "reverse": "Reverse angle",
}
# Camera movement enum -> natural prose woven into the shot, never telemetry.
_MOVEMENT_PROSE: dict[str, str] = {
    "static": "the frame holds steady",
    "pan": "the camera pans across the action",
    "tilt": "the camera tilts with the movement",
    "dolly_in": "a slow dolly forward",
    "dolly_out": "a slow dolly back",
    "tracking": "the camera tracks the movement",
    "crane": "a craning move",
    "handheld": "a restrained handheld frame",
    "whip_pan": "a whip pan",
    "rack_focus": "a rack focus",
}


def _allowed_shot_count(total_duration_seconds: int) -> int:
    if total_duration_seconds <= 5:
        return 2
    if total_duration_seconds <= 10:
        return 5
    return 6


def _format_timecode(seconds: int) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


class KlingOmniAdapterError(ValueError):
    """Raised when Phase 3 Kling prompt gates are not satisfied."""


@dataclass(frozen=True)
class KlingOmniBuildResult:
    prompt_record: dict[str, Any]
    run_record: dict[str, Any]
    warnings: list[str]


def _read_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _read_beat_plan_lookup(path: Path) -> dict[str, str]:
    doc = _read_yaml(path)
    if not doc:
        return {}
    beats = doc.get("source_beats")
    if not isinstance(beats, list):
        return {}
    lookup: dict[str, str] = {}
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        bid = beat.get("beat_id")
        content = beat.get("content")
        if isinstance(bid, str) and isinstance(content, str) and content.strip():
            lookup[bid] = content.strip()
    return lookup


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _text(value: Any, fallback: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _sanitize_prompt_text(text: str) -> str:
    text = CANONICAL_ID_RE.sub("the referenced production element", text)
    text = re.sub(r"\.{2,}", ".", text)
    return " ".join(text.split())


def _strip_screenplay_dialogue(prompt_action: str) -> str:
    """Remove SPEAKER: \"...\" cues from prompt_action when audio_plan owns spoken content."""
    stripped = SCREENPLAY_CUE_RE.sub("", prompt_action).strip()
    return " ".join(stripped.split())


def _load_dialogue_beats_lines(dialogue_beats_ref: str, repo_root: Path) -> list[dict[str, Any]]:
    """Load dialogue_lines list from a dialogue_beats.yaml file."""
    path = repo_root / dialogue_beats_ref
    doc = _read_yaml(path)
    if not doc:
        return []
    lines = doc.get("dialogue_lines")
    if not isinstance(lines, list):
        return []
    return [line for line in lines if isinstance(line, dict)]


def _load_element_aliases(scene_id: str, repo_root: Path) -> tuple[dict[str, str], set[str]]:
    """Load active element bindings for a scene.

    Returns:
        alias_map: {element_id: kling_alias} for active bindings only.
        char_ids: element_ids whose element_type == "character".
    """
    bindings_path = (
        repo_root / "visual_dev" / "omni_sets" / scene_id / "element_bindings.yaml"
    )
    if not bindings_path.exists():
        return {}, set()

    import yaml as _yaml  # local import to avoid top-level duplicate

    alias_map: dict[str, str] = {}
    char_ids: set[str] = set()

    try:
        with bindings_path.open(encoding="utf-8") as fh:
            for doc in _yaml.safe_load_all(fh):
                if not isinstance(doc, dict):
                    continue
                status = doc.get("binding_status", "planned")
                if status not in ACTIVE_BINDING_STATUSES:
                    continue
                elem_id = doc.get("element_id")
                alias = doc.get("kling_alias")
                if not elem_id or not alias:
                    continue
                alias_map[elem_id] = alias
                if doc.get("element_type") == "character":
                    char_ids.add(elem_id)
    except Exception:
        pass

    return alias_map, char_ids


def _load_continuity_states(
    scene_id: str, clip_id: str, repo_root: Path
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Load this clip's entry/exit state from the scene_continuity_ledger, if present.

    Returns (entry_state, exit_state); either may be None when no ledger exists or
    the clip is not chained. Inter-clip continuity must reach the prompt, not just
    sit in a record.
    """
    ledger_path = (
        repo_root / "planning" / "scenes" / scene_id / "scene_continuity_ledger.yaml"
    )
    if not ledger_path.exists():
        return None, None
    import yaml as _yaml

    try:
        with ledger_path.open(encoding="utf-8") as fh:
            data = _yaml.safe_load(fh)
    except Exception:
        return None, None
    if not isinstance(data, dict):
        return None, None
    for entry in data.get("clip_chain") or []:
        if isinstance(entry, dict) and entry.get("clip_id") == clip_id:
            return entry.get("entry_state"), entry.get("exit_state")
    return None, None


def _load_continuity_render_states(
    scene_id: str, clip_id: str, repo_root: Path
) -> tuple[str | None, str | None]:
    """Load this clip's literal render_start_state / render_end_state seam strings.

    These are the model-facing, alias-locked seam strings used by the
    kling_literal_alias_locked profile. The poetic entry_state/exit_state
    bookkeeping is never printed under that profile.
    """
    ledger_path = (
        repo_root / "planning" / "scenes" / scene_id / "scene_continuity_ledger.yaml"
    )
    if not ledger_path.exists():
        return None, None
    try:
        with ledger_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception:
        return None, None
    if not isinstance(data, dict):
        return None, None
    for entry in data.get("clip_chain") or []:
        if isinstance(entry, dict) and entry.get("clip_id") == clip_id:
            start = entry.get("render_start_state")
            end = entry.get("render_end_state")
            return (
                start if isinstance(start, str) and start.strip() else None,
                end if isinstance(end, str) and end.strip() else None,
            )
    return None, None


def _load_audio_readiness(scene_id: str, repo_root: Path) -> dict[str, str]:
    """Load native_audio_readiness by element_id from element_bindings."""
    bindings_path = (
        repo_root / "visual_dev" / "omni_sets" / scene_id / "element_bindings.yaml"
    )
    if not bindings_path.exists():
        return {}
    readiness: dict[str, str] = {}
    try:
        with bindings_path.open(encoding="utf-8") as fh:
            for doc in yaml.safe_load_all(fh):
                if not isinstance(doc, dict):
                    continue
                elem_id = doc.get("element_id")
                if not isinstance(elem_id, str) or not elem_id:
                    continue
                native = doc.get("native_audio_readiness")
                if isinstance(native, str) and native.strip():
                    readiness[elem_id] = native.strip().lower()
    except Exception:
        return {}
    return readiness


def _rewrite_shot_action(
    prompt_action: str,
    shot_element_ids: list[str],
    alias_map: dict[str, str],
    char_ids: set[str],
) -> tuple[str, list[str]]:
    """Inject aliases and rewrite leading pronouns in a single shot's prompt_action.

    Rules:
    - Replace all-caps character name (e.g. NADIA → @Nadia) if element is active.
    - If exactly one created character element and text starts with She/He/Her/His,
      replace that leading pronoun with the character alias.
    - If multiple character elements + ambiguous leading pronoun, emit warning (no change).

    Returns:
        (rewritten_text, warnings)
    """
    warnings: list[str] = []
    text = prompt_action

    # 1. Replace all-caps character names (e.g. NADIA → @Nadia)
    for elem_id in shot_element_ids:
        if elem_id not in alias_map or elem_id not in char_ids:
            continue
        alias = alias_map[elem_id]
        char_name = alias.lstrip("@")
        text = re.sub(rf"(?<!@)\b{re.escape(char_name.upper())}\b", alias, text)

    # 2. Leading pronoun rewrite
    m = LEADING_PRONOUN_RE.match(text)
    if m:
        active_chars = [
            eid for eid in shot_element_ids
            if eid in char_ids and eid in alias_map
        ]
        if len(active_chars) == 1:
            alias = alias_map[active_chars[0]]
            text = alias + text[m.end():]
        elif len(active_chars) > 1:
            warnings.append(
                f"Ambiguous pronoun '{m.group(1)}' in shot with multiple active character "
                f"elements {active_chars}; explicit shot text required — pronoun not rewritten."
            )

    return text, warnings


class KlingOmniAdapter:
    """Build draft Kling Omni prompt records from human-approved scene metadata."""

    MODEL_ID = "kling_omni"
    MODEL_SLUG = "kling-omni"
    ABBREV = "KO"
    INTERNAL_MODEL_TARGET = "kling_omni_video_best_available"

    def __init__(
        self,
        repo_root: str | Path,
        *,
        model_guidance_mode: str = "locked_guide",
        model_guidance_snapshot: str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.model_guidance_mode = model_guidance_mode
        self.model_guidance_snapshot = model_guidance_snapshot

    def generate(
        self,
        scene_id: str,
        *,
        version: int = 1,
        run_counter: int = 1,
        run_at: str | None = None,
    ) -> KlingOmniBuildResult:
        scene_card_path = self.repo_root / "planning" / "scenes" / scene_id / "scene_card.yaml"
        scene_card = _read_yaml(scene_card_path)
        if scene_card is None:
            raise KlingOmniAdapterError(f"Missing scene card: {scene_card_path}")

        shot_list = scene_card.get("shot_list_omni")
        if not isinstance(shot_list, list) or not shot_list:
            raise KlingOmniAdapterError(
                f"{scene_id} blocked: scene_card.shot_list_omni is empty."
            )

        omni_set_ref = _text(scene_card.get("omni_set_ref"))
        if not omni_set_ref:
            raise KlingOmniAdapterError(
                f"{scene_id} blocked: scene_card.omni_set_ref is missing."
            )

        warnings = self._pack_gate_warnings(scene_id, omni_set_ref)
        blocking = [warning for warning in warnings if warning.startswith("BLOCKED:")]
        if blocking:
            raise KlingOmniAdapterError("; ".join(blocking))

        prompt_record = self._prompt_record(
            scene_id=scene_id,
            scene_card=scene_card,
            shot_list=shot_list,
            scene_card_path=scene_card_path,
            omni_set_ref=omni_set_ref,
            version=version,
        )
        run_record = self._run_record(
            scene_id=scene_id,
            prompt_id=prompt_record["prompt_id"],
            run_counter=run_counter,
            run_at=run_at,
        )
        return KlingOmniBuildResult(
            prompt_record=prompt_record,
            run_record=run_record,
            warnings=warnings,
        )

    def generate_from_clip_manifest(
        self,
        manifest_ref: str | Path,
        *,
        version: int = 1,
        run_counter: int = 1,
        run_at: str | None = None,
        variant_mode: str = "safe",
        render_pass: str = "visual_test",
        quality_tier: str = "test_720p",
        shot_element_manifest_ref: str | Path | None = None,
        input_mode: str = "text_only",
        start_frame_ref: str | None = None,
        contact_sheet_ref: str | None = None,
        active_element_aliases: list[str] | None = None,
        language_profile: str = "legacy_prose",
        continuity_seed_ref: str | None = None,
    ) -> KlingOmniBuildResult:
        """Generate prompt/run records from a single omni_clip_manifest.yaml.

        Args:
            manifest_ref: Path to omni_clip_manifest.yaml (relative or absolute)
            version: Prompt version number (default 1)
            run_counter: Run counter for run_id (default 1)
            run_at: ISO 8601 timestamp for run execution (default now)
            variant_mode: Prompt variant mode (safe|creative|aggressive)
            render_pass: Render pass stage
            quality_tier: Render quality tier
            shot_element_manifest_ref: Optional path to the shot_element_manifest
                that gates this clip's element registration. When provided, the
                adapter enters strict element-first mode: it refuses to emit a
                prompt unless the manifest declares
                ``gate_status: all_elements_ready``, at least one required
                element resolves to an active Kling alias, and the synthesized
                ``prompt_text`` does not leak any repo-canonical element ids.
                The reference is also embedded in ``generation_params`` so
                downstream prompt-record validation enforces the same gate.

        Returns:
            KlingOmniBuildResult with prompt_record and run_record

        Raises:
            KlingOmniAdapterError: If manifest is missing, invalid, or constraints violated
        """
        variant_mode = self._validate_variant_mode(variant_mode)
        render_pass = self._validate_render_pass(render_pass)
        quality_tier = self._validate_quality_tier(quality_tier)

        _valid_input_modes = {"text_only", "anchored_i2v"}
        if input_mode not in _valid_input_modes:
            raise KlingOmniAdapterError(
                f"Invalid input_mode {input_mode!r}; expected one of {sorted(_valid_input_modes)}"
            )
        is_anchored = input_mode == "anchored_i2v"
        if is_anchored and not start_frame_ref:
            raise KlingOmniAdapterError(
                "input_mode='anchored_i2v' requires start_frame_ref to be set."
            )

        _valid_language_profiles = {"kling_literal_alias_locked", "legacy_prose"}
        if language_profile not in _valid_language_profiles:
            raise KlingOmniAdapterError(
                f"Invalid language_profile {language_profile!r}; expected one of "
                f"{sorted(_valid_language_profiles)}"
            )
        is_literal = language_profile == "kling_literal_alias_locked"
        if is_literal and is_anchored:
            # The literal alias-locked profile (v07) is the text-only multi-shot
            # route; it never carries the anchored_i2v visual-input triplet.
            raise KlingOmniAdapterError(
                "language_profile='kling_literal_alias_locked' is text_only only; "
                "it cannot be combined with input_mode='anchored_i2v'."
            )

        manifest_path = Path(manifest_ref)
        if not manifest_path.is_absolute():
            manifest_path = self.repo_root / manifest_path

        manifest = _read_yaml(manifest_path)
        if manifest is None:
            raise KlingOmniAdapterError(f"Missing manifest: {manifest_path}")

        self._validate_manifest_shape(manifest)

        strict_element_first = shot_element_manifest_ref is not None
        shot_manifest_data: dict[str, Any] | None = None
        shot_manifest_rel: str | None = None
        if strict_element_first:
            shot_manifest_path = Path(shot_element_manifest_ref)
            if not shot_manifest_path.is_absolute():
                shot_manifest_path = self.repo_root / shot_manifest_path
            shot_manifest_data = _read_yaml(shot_manifest_path)
            if not isinstance(shot_manifest_data, dict):
                raise KlingOmniAdapterError(
                    f"Missing or unreadable shot_element_manifest: {shot_manifest_path}"
                )
            declared_gate = shot_manifest_data.get("gate_status")
            if declared_gate != MANIFEST_READY_GATE_STATUS:
                raise KlingOmniAdapterError(
                    "shot_element_manifest gate_status is "
                    f"{declared_gate!r}; Kling Omni 3 prompt synthesis requires "
                    f"{MANIFEST_READY_GATE_STATUS!r}"
                )
            shot_manifest_rel = _relative(shot_manifest_path, self.repo_root)

        scene_id = manifest["scene_id"]
        clip_id = manifest["clip_id"]
        shots = manifest["shots"]
        total_duration = manifest["total_duration_seconds"]
        continuity_mode = manifest["continuity_input_mode"]
        kling_native_audio = manifest["kling_native_audio"]
        scene_beat_plan_ref = manifest["source_scene_beat_plan_ref"]
        dialogue_beats_ref = manifest["source_dialogue_beats_ref"]
        beat_plan_lookup = _read_beat_plan_lookup(self.repo_root / scene_beat_plan_ref)

        scene_card_path = self.repo_root / "planning" / "scenes" / scene_id / "scene_card.yaml"
        scene_card = _read_yaml(scene_card_path)

        max_duration = self._max_duration_seconds()

        # Load active element aliases for this scene
        alias_map, char_ids = _load_element_aliases(scene_id, self.repo_root)

        # Inter-clip continuity: pull this clip's entry/exit world state from the
        # scene_continuity_ledger so the hand-off reaches the prompt text.
        continuity_entry, continuity_exit = _load_continuity_states(
            scene_id, clip_id, self.repo_root
        )

        # Load dialogue beats lines and readiness map unconditionally so both the
        # audio_plan component and the existing audio gate block share one load.
        dialogue_beats_lines_data = (
            _load_dialogue_beats_lines(dialogue_beats_ref, self.repo_root)
            if dialogue_beats_ref
            else []
        )
        readiness_map_data = _load_audio_readiness(scene_id, self.repo_root)

        # Collect clip-level required element IDs (union of all shot-level IDs)
        clip_elem_ids: list[str] = list(manifest.get("required_element_ids") or [])
        if not clip_elem_ids:
            seen: dict[str, None] = {}
            for shot in shots:
                for eid in shot.get("required_element_ids") or []:
                    seen[eid] = None
            clip_elem_ids = list(seen)

        # Build required aliases (only active bindings contribute)
        required_aliases: list[str] = []
        seen_aliases: dict[str, None] = {}
        for eid in clip_elem_ids:
            alias = alias_map.get(eid)
            if alias and alias not in seen_aliases:
                seen_aliases[alias] = None
                required_aliases.append(alias)

        # Figure-level aliases (anti-clone): a single base character (e.g. C10) may
        # appear as two distinct on-screen figures, each with its own @alias
        # (@C10_HOLDER, @C10_CARRIER). The element_id->alias map collapses these, so
        # attach figure aliases directly from the manifest shots[].figures[].
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            for fig in shot.get("figures") or []:
                if not isinstance(fig, dict):
                    continue
                fig_alias = fig.get("kling_alias")
                if fig_alias and fig_alias not in seen_aliases:
                    seen_aliases[fig_alias] = None
                    required_aliases.append(fig_alias)

        if strict_element_first and not required_aliases:
            raise KlingOmniAdapterError(
                "shot_element_manifest_ref is set but the omni_clip_manifest "
                "resolves to zero active Kling aliases; element-first synthesis "
                "requires at least one element_binding with binding_status "
                "'created' or better that matches the clip's required_element_ids"
            )

        if is_literal:
            render_start_state, render_end_state = _load_continuity_render_states(
                scene_id, clip_id, self.repo_root
            )
            prompt_text, alias_warnings = self._build_prompt_text_literal(
                shots=shots,
                total_duration=total_duration,
                continuity_mode=continuity_mode,
                variant_mode=variant_mode,
                alias_map=alias_map,
                required_aliases=required_aliases,
                dialogue_beats_lines=dialogue_beats_lines_data or None,
                render_start_state=render_start_state,
                render_end_state=render_end_state,
                render_pass=render_pass,
            )
        else:
            prompt_text, alias_warnings = self._build_prompt_text_with_aliases(
                shots=shots,
                total_duration=total_duration,
                max_duration=max_duration,
                continuity_mode=continuity_mode,
                variant_mode=variant_mode,
                alias_map=alias_map,
                char_ids=char_ids,
                required_aliases=required_aliases,
                beat_content_lookup=beat_plan_lookup,
                strict_element_first=strict_element_first,
                dialogue_beats_lines=dialogue_beats_lines_data or None,
                readiness_map=readiness_map_data,
                continuity_entry=continuity_entry,
                continuity_exit=continuity_exit,
                render_pass=render_pass,
                suppress_entry_anchors=is_anchored,
            )

        # Warn if anchored_i2v prompt exceeds recommended target (not fatal)
        if is_anchored and len(prompt_text) > 1800:
            alias_warnings.append(
                f"anchored_i2v prompt_text is {len(prompt_text)} characters; "
                "target is <1800 for anchored_i2v mode. Shorten motion direction text."
            )

        # Warn about planned-only elements (in required_element_ids but not active)
        planned_warnings: list[str] = []
        for eid in clip_elem_ids:
            if eid not in alias_map:
                planned_warnings.append(
                    f"Element {eid!r} is in required_element_ids but has no active "
                    "Kling binding (status may be 'planned'); alias not injected."
                )
        all_warnings = alias_warnings + planned_warnings

        source_refs: dict[str, Any] = {
            "scene_card": _relative(scene_card_path, self.repo_root),
            "scene_excerpt": f"planning/scenes/{scene_id}/scene_excerpt.md",
        }

        # Use clip_id slug (replace underscores with hyphens) for prompt_id
        clip_slug = clip_id.lower().replace("_", "-")
        prompt_id = (
            f"{scene_id}__omni-kling-omni-clip-{clip_slug}-{variant_mode}__v{version:02d}"
        )

        generation_params: dict[str, Any] = {
            "model_guidance_mode": self.model_guidance_mode,
            "adapter_name": self.MODEL_ID,
            "clip_id": clip_id,
            "total_duration_seconds": total_duration,
            "continuity_input_mode": continuity_mode,
            "omni_clip_manifest_ref": _relative(manifest_path, self.repo_root),
            "source_scene_beat_plan_ref": scene_beat_plan_ref,
            "source_dialogue_beats_ref": dialogue_beats_ref,
            "repo_binary_committed": False,
            "external_generation_required": True,
            "recommended_cfg_scale": 0.5,
            "recommended_ar": "16:9",
            "variant_mode": variant_mode,
            "render_pass": render_pass,
            "quality_tier": quality_tier,
            "prompt_component_model": "docs/methodology/omni_prompt_component_model.md",
            "language_profile": language_profile,
            "input_mode": input_mode,
        }

        if is_literal and continuity_seed_ref:
            # text_only-only optional continuity seed; deliberately NOT the
            # anchored_i2v triplet (no contact_sheet_ref, no visual_input_budget).
            generation_params["continuity_seed_ref"] = continuity_seed_ref

        if required_aliases:
            generation_params["required_element_aliases"] = required_aliases

        if shot_manifest_rel is not None:
            generation_params["shot_element_manifest_ref"] = shot_manifest_rel

        if is_anchored:
            generation_params["input_mode"] = "anchored_i2v"
            generation_params["start_frame_ref"] = start_frame_ref
            if contact_sheet_ref:
                generation_params["contact_sheet_ref"] = contact_sheet_ref
            generation_params["visual_input_budget"] = (
                {"total": 7, "start_frame": 1, "contact_sheet": 1, "element_slots": 5}
                if contact_sheet_ref
                else {"total": 7, "start_frame": 1, "element_slots": 6}
            )
            generation_params["frame_chain_source"] = "designed_still_pass1"
            if active_element_aliases:
                generation_params["active_element_aliases"] = active_element_aliases

        audio_enabled = bool(kling_native_audio.get("enabled"))
        gate_status = "allowed_audio_off"
        gate_reason = "audio_not_requested"
        audio_passes = {"performance_test", "final_candidate", "final_locked"}
        if render_pass == "visual_test":
            gate_reason = "visual_test_default_audio_off"
            if audio_enabled:
                gate_status = "blocked"
                gate_reason = "visual_test_requires_audio_off"
                all_warnings.append(
                    "Native Audio blocked: render_pass=visual_test requires audio-off."
                )
        elif render_pass in audio_passes and audio_enabled:
            # Audio-enabled passes require ready speaking character bindings.
            speaking_ids: set[str] = set()
            for shot in shots:
                if not isinstance(shot, dict):
                    continue
                for eid in shot.get("required_element_ids") or []:
                    if isinstance(eid, str) and (
                        eid in char_ids or bool(CHARACTER_ID_RE.match(eid))
                    ):
                        speaking_ids.add(eid)
            not_ready = [eid for eid in sorted(speaking_ids) if readiness_map_data.get(eid) != "ready"]
            if not_ready:
                gate_status = "blocked"
                gate_reason = "speaker_not_ready:" + ",".join(not_ready)
                all_warnings.append(
                    "Native Audio blocked: speaking character bindings not ready: "
                    + ", ".join(not_ready)
                )
            else:
                gate_status = "allowed"
                gate_reason = "speakers_ready"
                generation_params["kling_native_audio"] = {
                    "enabled": True,
                    "provider_policy": kling_native_audio.get("provider_policy"),
                }
        elif audio_enabled:
            gate_status = "allowed"
            gate_reason = "audio_enabled_non_performance_pass"
            generation_params["kling_native_audio"] = {
                "enabled": True,
                "provider_policy": kling_native_audio.get("provider_policy"),
            }

        generation_params["audio_gate_status"] = gate_status
        generation_params["audio_gate_reason"] = gate_reason

        if self.model_guidance_mode == "dynamic_snapshot":
            resolved = resolve_model_guidance(
                repo_root=self.repo_root,
                internal_model_target=self.INTERNAL_MODEL_TARGET,
            )
            generation_params.update({
                "model_guidance_snapshot_ref": resolved["model_guidance_snapshot_ref"],
                "provider": resolved["provider"],
                "provider_surface": resolved["provider_surface"],
                "resolved_model_name": resolved["resolved_model_name"],
                "resolved_model_role": resolved["resolved_model_role"],
                "guidance_observed_at": resolved["guidance_observed_at"],
                "guidance_expires_at": resolved["guidance_expires_at"],
            })
        else:
            generation_params["model_guidance_ref"] = "docs/model_guides/kling_omni.yaml"
            if self.model_guidance_snapshot:
                generation_params["model_guidance_snapshot"] = self.model_guidance_snapshot

        record: dict[str, Any] = {
            "prompt_id": prompt_id,
            "scene_id": scene_id,
            "prompt_type": "omni_instruction",
            "lifecycle_stage": "draft",
            "target_models": [self.MODEL_ID],
            "source_refs": source_refs,
            "prompt_text": prompt_text,
            "negative_prompt": self._build_negative_prompt(
                scene_card or {},
                extra_terms=(
                    ["subtitles", "visible-grid", "timecode-overlay"]
                    if contact_sheet_ref
                    else None
                ),
            ),
            "generation_params": generation_params,
            "expected_output": {
                "asset_type": "clip",
                "duration_seconds": total_duration,
            },
            "status": "active",
            "canon_lock": False,
        }

        run_record = self._run_record(
            scene_id=scene_id,
            prompt_id=prompt_id,
            run_counter=run_counter,
            run_at=run_at,
            clip_id=clip_id,
        )

        return KlingOmniBuildResult(
            prompt_record=record,
            run_record=run_record,
            warnings=all_warnings,
        )

    def render_prompt_text_only(
        self,
        scene_id: str,
        clip_id: str,
        *,
        variant_mode: str = "safe",
        render_pass: str = "visual_test",
    ) -> str:
        """Render a clip's prompt_text WITHOUT writing any records (pure dry-run).

        Used by validate_state_chain to check that the carried-state anchor and
        per-figure actions actually reach the prompt, with no side effects. Mirrors
        the prompt-build path of generate_from_clip_manifest (no strict gate, no
        audio-gate/record assembly).
        """
        variant_mode = self._validate_variant_mode(variant_mode)
        render_pass = self._validate_render_pass(render_pass)

        manifest_path = (
            self.repo_root / "planning" / "scenes" / scene_id
            / "manifests" / f"{clip_id}_manifest.yaml"
        )
        manifest = _read_yaml(manifest_path)
        if manifest is None:
            raise KlingOmniAdapterError(f"Missing manifest: {manifest_path}")
        self._validate_manifest_shape(manifest)

        shots = manifest["shots"]
        total_duration = manifest["total_duration_seconds"]
        continuity_mode = manifest["continuity_input_mode"]
        scene_beat_plan_ref = manifest["source_scene_beat_plan_ref"]
        dialogue_beats_ref = manifest["source_dialogue_beats_ref"]
        beat_plan_lookup = _read_beat_plan_lookup(self.repo_root / scene_beat_plan_ref)
        max_duration = self._max_duration_seconds()

        alias_map, char_ids = _load_element_aliases(scene_id, self.repo_root)
        continuity_entry, continuity_exit = _load_continuity_states(
            scene_id, clip_id, self.repo_root
        )
        dialogue_beats_lines_data = (
            _load_dialogue_beats_lines(dialogue_beats_ref, self.repo_root)
            if dialogue_beats_ref
            else []
        )
        readiness_map_data = _load_audio_readiness(scene_id, self.repo_root)

        clip_elem_ids: list[str] = list(manifest.get("required_element_ids") or [])
        if not clip_elem_ids:
            seen: dict[str, None] = {}
            for shot in shots:
                if isinstance(shot, dict):
                    for eid in shot.get("required_element_ids") or []:
                        seen[eid] = None
            clip_elem_ids = list(seen)

        required_aliases: list[str] = []
        seen_aliases: dict[str, None] = {}
        for eid in clip_elem_ids:
            alias = alias_map.get(eid)
            if alias and alias not in seen_aliases:
                seen_aliases[alias] = None
                required_aliases.append(alias)
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            for fig in shot.get("figures") or []:
                if isinstance(fig, dict):
                    fig_alias = fig.get("kling_alias")
                    if fig_alias and fig_alias not in seen_aliases:
                        seen_aliases[fig_alias] = None
                        required_aliases.append(fig_alias)

        prompt_text, _ = self._build_prompt_text_with_aliases(
            shots=shots,
            total_duration=total_duration,
            max_duration=max_duration,
            continuity_mode=continuity_mode,
            variant_mode=variant_mode,
            alias_map=alias_map,
            char_ids=char_ids,
            required_aliases=required_aliases,
            beat_content_lookup=beat_plan_lookup,
            strict_element_first=False,
            dialogue_beats_lines=dialogue_beats_lines_data or None,
            readiness_map=readiness_map_data,
            continuity_entry=continuity_entry,
            continuity_exit=continuity_exit,
            render_pass=render_pass,
        )
        return prompt_text

    def _validate_manifest_shape(self, manifest: dict[str, Any]) -> None:
        """Defensive validation of omni_clip_manifest structure."""
        if manifest.get("record_type") != "omni_clip_manifest":
            raise KlingOmniAdapterError(
                f"Manifest record_type must be 'omni_clip_manifest', got {manifest.get('record_type')!r}"
            )

        scene_id = manifest.get("scene_id")
        if not scene_id or not isinstance(scene_id, str):
            raise KlingOmniAdapterError("Manifest missing or invalid scene_id")

        clip_id = manifest.get("clip_id")
        if not clip_id or not isinstance(clip_id, str):
            raise KlingOmniAdapterError("Manifest missing or invalid clip_id")

        total_duration = manifest.get("total_duration_seconds")
        if not isinstance(total_duration, int) or total_duration <= 0:
            raise KlingOmniAdapterError("Manifest total_duration_seconds must be a positive integer")

        shots = manifest.get("shots")
        if not isinstance(shots, list) or not shots:
            raise KlingOmniAdapterError("Manifest shots must be a non-empty array")

        for idx, shot in enumerate(shots):
            if not isinstance(shot, dict):
                raise KlingOmniAdapterError(f"Manifest shots[{idx}] must be a mapping")

            shot_id = shot.get("shot_id")
            if not shot_id:
                raise KlingOmniAdapterError(f"Manifest shots[{idx}] missing shot_id")

            duration = shot.get("duration_seconds")
            if not isinstance(duration, int) or duration <= 0:
                raise KlingOmniAdapterError(
                    f"Manifest shots[{idx}] duration_seconds must be a positive integer"
                )

            source_beat_ids = shot.get("source_beat_ids")
            if not isinstance(source_beat_ids, list) or not source_beat_ids:
                raise KlingOmniAdapterError(
                    f"Manifest shots[{idx}] source_beat_ids must be a non-empty array"
                )

            prompt_action = shot.get("prompt_action")
            if not prompt_action or not isinstance(prompt_action, str):
                raise KlingOmniAdapterError(f"Manifest shots[{idx}] missing or invalid prompt_action")

            duration_reason = shot.get("duration_reason")
            if not duration_reason or not isinstance(duration_reason, str):
                raise KlingOmniAdapterError(f"Manifest shots[{idx}] missing or invalid duration_reason")

        scene_beat_plan = manifest.get("source_scene_beat_plan_ref")
        if not scene_beat_plan or not isinstance(scene_beat_plan, str):
            raise KlingOmniAdapterError("Manifest missing or invalid source_scene_beat_plan_ref")

        dialogue_beats = manifest.get("source_dialogue_beats_ref")
        # Empty string is valid: it marks a no-dialogue scene (e.g. a silent fight).
        # The omni_clip_manifest semantic validator and the dialogue loaders already
        # treat an empty ref as "no dialogue" (guarded by `if ref:`); the adapter must
        # accept it too rather than forcing every scene to carry a dialogue_beats file.
        if dialogue_beats is None or not isinstance(dialogue_beats, str):
            raise KlingOmniAdapterError("Manifest missing or invalid source_dialogue_beats_ref")

        kling_native_audio = manifest.get("kling_native_audio")
        if not isinstance(kling_native_audio, dict):
            raise KlingOmniAdapterError("Manifest kling_native_audio must be a mapping")

    @staticmethod
    def _validate_variant_mode(variant_mode: str) -> str:
        mode = str(variant_mode or "").strip().lower()
        if mode not in VARIANT_MODES:
            raise KlingOmniAdapterError(
                f"Invalid variant_mode {variant_mode!r}; expected one of {sorted(VARIANT_MODES)}"
            )
        return mode

    @staticmethod
    def _validate_render_pass(render_pass: str) -> str:
        value = str(render_pass or "").strip().lower()
        if value not in RENDER_PASSES:
            raise KlingOmniAdapterError(
                f"Invalid render_pass {render_pass!r}; expected one of {sorted(RENDER_PASSES)}"
            )
        return value

    @staticmethod
    def _validate_quality_tier(quality_tier: str) -> str:
        value = str(quality_tier or "").strip().lower()
        if value not in QUALITY_TIERS:
            raise KlingOmniAdapterError(
                f"Invalid quality_tier {quality_tier!r}; expected one of {sorted(QUALITY_TIERS)}"
            )
        return value

    def _build_prompt_text_with_aliases(
        self,
        shots: list[Any],
        total_duration: int,
        max_duration: int,
        continuity_mode: str,
        variant_mode: str,
        alias_map: dict[str, str],
        char_ids: set[str],
        required_aliases: list[str],
        beat_content_lookup: dict[str, str] | None = None,
        strict_element_first: bool = False,
        dialogue_beats_lines: list[dict[str, Any]] | None = None,
        readiness_map: dict[str, str] | None = None,
        continuity_entry: dict[str, Any] | None = None,
        continuity_exit: dict[str, Any] | None = None,
        render_pass: str = "visual_test",
        suppress_entry_anchors: bool = False,
    ) -> tuple[str, list[str]]:
        """Build prompt text with element alias injection and pronoun rewriting.

        When ``strict_element_first`` is False (legacy callers) and there are
        no active aliases, this falls back to plain text synthesis. When the
        flag is True the caller has already validated that
        ``required_aliases`` is non-empty, so the fallback path is unreachable
        and the prompt is built with @alias injection only.

        Returns:
            (prompt_text, warnings)
        """
        all_warnings: list[str] = []

        if not required_aliases:
            if strict_element_first:
                raise KlingOmniAdapterError(
                    "element-first Kling Omni prompt synthesis cannot fall back "
                    "to plain text: no active Kling aliases were resolved from "
                    "the omni_clip_manifest's required_element_ids"
                )
            # No active aliases — fall back to plain text (legacy path)
            return (
                self._build_prompt_text_from_manifest(
                    shots,
                    total_duration,
                    max_duration,
                    continuity_mode,
                    variant_mode,
                    beat_content_lookup,
                ),
                [],
            )

        parts: list[str] = [
            f"Kling Omni element-based clip; duration {total_duration}s.",
            f"Active elements: {', '.join(required_aliases)}.",
            "Direct action and camera; @elements carry identity, wardrobe, and look.",
            self._variant_preamble(variant_mode),
        ]

        figure_line = self._build_figure_roster_line(shots)
        if figure_line:
            parts.append(figure_line)

        if continuity_entry:
            parts.append(self._continuity_phrase("Continue from previous clip", continuity_entry))

        elapsed = 0
        rendered_line_ids: set[str] = set()
        seam_printed = bool(continuity_entry)
        for index, shot in enumerate(shots, start=1):
            if index > 6:
                raise KlingOmniAdapterError(
                    "Kling Omni clip-manifest prompt synthesis supports at most "
                    "6 shots per generation."
                )
            duration = int(shot.get("duration_seconds", 0))
            raw_action = _text(shot.get("prompt_action"), "approved action")
            source_beat_ids: list[str] = list(shot.get("source_beat_ids") or [])
            if raw_action.endswith("...") and source_beat_ids and beat_content_lookup:
                full = beat_content_lookup.get(source_beat_ids[0], "")
                if full:
                    raw_action = full
            # Strip any screenplay SPEAKER: "..." cue from the action; the verbatim
            # line is rendered once, inline, as alias-tagged dialogue below.
            if dialogue_beats_lines is not None and shot.get("dialogue_line_ids"):
                raw_action = _strip_screenplay_dialogue(raw_action)
                if not raw_action:
                    raw_action = "The exchange plays out"
            shot_elem_ids: list[str] = list(shot.get("required_element_ids") or [])

            rewritten, warnings = _rewrite_shot_action(
                raw_action, shot_elem_ids, alias_map, char_ids
            )
            all_warnings.extend(warnings)

            heading = self._build_shot_heading(duration, elapsed, shot)
            entry_anchor = (
                ""
                if suppress_entry_anchors
                else self._build_shot_entry_anchor(
                    shot, continuity_entry, index == 1, seam_printed, alias_map, char_ids
                )
            )
            action_sentence = self._compose_action_sentence(rewritten, shot)
            figure_actions = self._compose_figure_actions(shot, alias_map, char_ids)
            camera_sentence = self._build_camera_sentence(shot)
            dialogue_clause = self._render_shot_dialogue(
                shot, dialogue_beats_lines or [], alias_map, rendered_line_ids
            )
            audio_clause = self._build_diegetic_audio_clause(shot)

            # Order: heading -> carried-state anchor -> environment action ->
            # per-character action -> camera -> dialogue -> audio. State first,
            # then the new action; each character's action is its own clause.
            block = heading
            if entry_anchor:
                block += f" {entry_anchor}"
            block += f" {action_sentence}"
            if figure_actions:
                block += f" {figure_actions}"
            if camera_sentence:
                block += f" {camera_sentence}"
            if dialogue_clause:
                block += f" {dialogue_clause}"
            if audio_clause:
                block += f" {audio_clause}"
            parts.append(block)
            elapsed += duration

        if continuity_exit:
            parts.append(self._continuity_phrase("End state for next clip", continuity_exit))

        parts.append(f"Continuity: {continuity_mode}.")
        parts.append(
            f"Keep {total_duration}s; end settled. Do not add new story facts."
        )

        raw_joined = " ".join(p for p in parts if p)
        if strict_element_first:
            # Catch authoring mistakes loudly: in strict mode the sanitizer is
            # not a silent safety net. Canonical ids must never appear in the
            # source shot_action / beat content the operator authored.
            _assert_no_canonical_id_leak(raw_joined)
        text = _sanitize_prompt_text(raw_joined)

        # Hard limit: 2500 characters (Kling API). For a final pass the prompt is
        # a delivery artifact, so overflow is fatal; earlier passes warn (the
        # state anchor + per-figure actions make overflow more likely, so this
        # gate is render_pass-aware rather than always-soft).
        if len(text) > 2500:
            message = (
                f"prompt_text is {len(text)} characters, exceeds 2500-char API limit. "
                "Shorten shot descriptions."
            )
            if render_pass in _FINAL_PASSES:
                raise KlingOmniAdapterError(message)
            all_warnings.append(message)

        return text, all_warnings

    def _build_prompt_text_literal(
        self,
        shots: list[Any],
        total_duration: int,
        continuity_mode: str,
        variant_mode: str,
        alias_map: dict[str, str],
        required_aliases: list[str],
        dialogue_beats_lines: list[dict[str, Any]] | None,
        render_start_state: str | None,
        render_end_state: str | None,
        render_pass: str = "visual_test",
    ) -> tuple[str, list[str]]:
        """Build prompt text under language_profile=kling_literal_alias_locked.

        Thin literal emitter: prints ONLY the model-facing ``render_*`` fields
        (shots[].render_action/render_camera/render_diegetic_audio,
        figures[].render_action/render_label, ledger render_start/end_state) plus
        the alias roster, timecodes, and literal alias-tagged dialogue. It never
        prints prompt_action, performance_note, role, distinguishing_detail,
        lens_bias, ledger summary, or any screen_position/subject_screen_position
        bookkeeping — those stay human-readable and out of the prompt.
        """
        warnings: list[str] = []
        if not required_aliases:
            raise KlingOmniAdapterError(
                "kling_literal_alias_locked synthesis requires at least one active "
                "Kling alias resolved from the manifest's required_element_ids."
            )

        parts: list[str] = [
            f"Kling Omni element-based clip; duration {total_duration}s.",
            f"Active elements: {', '.join(required_aliases)}.",
            "Direct action and camera; @elements carry identity, wardrobe, and look.",
            self._variant_preamble(variant_mode),
        ]

        roster = self._build_figure_roster_line_literal(shots)
        if roster:
            parts.append(roster)

        if isinstance(render_start_state, str) and render_start_state.strip():
            parts.append(f"Start state: {render_start_state.strip().rstrip('.')}.")

        elapsed = 0
        rendered_line_ids: set[str] = set()
        for index, shot in enumerate(shots, start=1):
            if index > 6:
                raise KlingOmniAdapterError(
                    "Kling Omni clip-manifest prompt synthesis supports at most "
                    "6 shots per generation."
                )
            duration = int(shot.get("duration_seconds", 0))
            heading = self._build_shot_heading(duration, elapsed, shot)
            action = self._literal_shot_action(shot)
            figure_actions = self._compose_figure_actions_literal(shot)
            camera_sentence = self._build_camera_sentence_literal(shot)
            dialogue_clause = self._render_shot_dialogue(
                shot, dialogue_beats_lines or [], alias_map, rendered_line_ids
            )
            audio_clause = self._build_diegetic_audio_clause_literal(shot)
            if not action and not figure_actions:
                warnings.append(
                    f"shot {shot.get('shot_id')!r} has no render_action and no figure "
                    "render_action under the literal profile; the manifest needs "
                    "render_* fields authored for kling_literal_alias_locked."
                )

            block = heading
            if action:
                block += f" {action}"
            if figure_actions:
                block += f" {figure_actions}"
            if camera_sentence:
                block += f" {camera_sentence}"
            if dialogue_clause:
                block += f" {dialogue_clause}"
            if audio_clause:
                block += f" {audio_clause}"
            parts.append(block)
            elapsed += duration

        if isinstance(render_end_state, str) and render_end_state.strip():
            parts.append(f"End state: {render_end_state.strip().rstrip('.')}.")

        parts.append(f"Continuity: {continuity_mode}.")
        parts.append(f"Keep {total_duration}s; end settled. Do not add new story facts.")

        raw_joined = " ".join(p for p in parts if p)
        _assert_no_canonical_id_leak(raw_joined)
        text = _sanitize_prompt_text(raw_joined)

        if len(text) > 2500:
            message = (
                f"prompt_text is {len(text)} characters, exceeds 2500-char API limit. "
                "Shorten render_action descriptions."
            )
            if render_pass in _FINAL_PASSES:
                raise KlingOmniAdapterError(message)
            warnings.append(message)

        return text, warnings

    @staticmethod
    def _build_figure_roster_line_literal(shots: list[Any]) -> str:
        """Anti-clone roster line for the literal profile: uses the NEUTRAL
        render_label (no role nouns) instead of distinguishing_detail."""
        ordered: list[str] = []
        details: dict[str, str] = {}
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            for fig in shot.get("figures") or []:
                if not isinstance(fig, dict):
                    continue
                alias = fig.get("kling_alias")
                if not isinstance(alias, str) or not alias:
                    continue
                if alias not in ordered:
                    ordered.append(alias)
                    label = fig.get("render_label")
                    if isinstance(label, str) and label.strip():
                        details[alias] = label.strip()
        if not ordered:
            return ""
        labelled = [f"{a} ({details[a]})" if a in details else a for a in ordered]
        return (
            f"Figures: exactly {len(ordered)} distinct figure(s) — {', '.join(labelled)}. "
            "No additional, extra, or duplicated people; do not clone or multiply any figure."
        )

    @staticmethod
    def _literal_shot_action(shot: dict[str, Any]) -> str:
        """Literal shot action from render_action only. Never falls back to the
        poetic prompt_action/performance_note."""
        action = shot.get("render_action")
        if not (isinstance(action, str) and action.strip()):
            return ""
        text = action.strip()
        if not text.endswith((".", "!", "?", '"')):
            text += "."
        return text[0].upper() + text[1:]

    @staticmethod
    def _compose_figure_actions_literal(shot: dict[str, Any]) -> str:
        """One literal clause per figure from figures[].render_action only."""
        clauses: list[str] = []
        for fig in shot.get("figures") or []:
            if not isinstance(fig, dict):
                continue
            act = fig.get("render_action")
            alias = fig.get("kling_alias")
            if not (isinstance(act, str) and act.strip() and isinstance(alias, str)):
                continue
            text = act.strip()
            if alias not in text:
                text = f"{alias} {text}"
            if not text.endswith((".", "!", "?")):
                text += "."
            clauses.append(text[0].upper() + text[1:])
        return " ".join(clauses)

    @staticmethod
    def _build_camera_sentence_literal(shot: dict[str, Any]) -> str:
        """Literal camera sentence from render_camera; falls back to the movement
        enum prose only (never the poetic lens_bias)."""
        camera = shot.get("camera") if isinstance(shot.get("camera"), dict) else {}
        render_camera = shot.get("render_camera")
        if isinstance(render_camera, str) and render_camera.strip():
            sentence = render_camera.strip()
        else:
            movement = camera.get("movement")
            phrase = _MOVEMENT_PROSE.get(movement) if isinstance(movement, str) else None
            if not phrase:
                return ""
            sentence = phrase
        if not sentence.endswith((".", "!", "?")):
            sentence += "."
        return sentence[0].upper() + sentence[1:]

    @staticmethod
    def _build_diegetic_audio_clause_literal(shot: dict[str, Any]) -> str:
        """Literal 'Audio:' line from render_diegetic_audio only (never the poetic
        diegetic_audio, which may carry role nouns like 'infant')."""
        audio = shot.get("render_diegetic_audio")
        if isinstance(audio, str) and audio.strip():
            a = audio.strip()
            if not a.endswith((".", "!", "?")):
                a += "."
            return f"Audio: {a}"
        return ""

    @staticmethod
    def _build_figure_roster_line(shots: list[Any]) -> str:
        """Anti-clone roster line: enumerate the exact distinct figures and forbid extras.

        First mention of each figure carries its distinguishing_detail so the model
        keeps physically distinct figures apart (Kling Element guide pattern).
        """
        ordered: list[str] = []
        details: dict[str, str] = {}
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            for fig in shot.get("figures") or []:
                if not isinstance(fig, dict):
                    continue
                alias = fig.get("kling_alias")
                if not isinstance(alias, str) or not alias:
                    continue
                if alias not in ordered:
                    ordered.append(alias)
                    detail = fig.get("distinguishing_detail")
                    if isinstance(detail, str) and detail.strip():
                        details[alias] = detail.strip()
        if not ordered:
            return ""
        labelled = [f"{a} ({details[a]})" if a in details else a for a in ordered]
        return (
            f"Figures: exactly {len(ordered)} distinct figure(s) — {', '.join(labelled)}. "
            "No additional, extra, or duplicated people; do not clone or multiply any figure."
        )

    @staticmethod
    def _format_positions(state: dict[str, Any]) -> str:
        """Render key_positions + props_state into carried-state prose.

        ``@C01_NADIA center, seated, holding @C08_JIN; @C04_DIMITRI right; the
        door open``. This is the position data the model needs to keep subjects
        in place across a cut; previously it was dropped from the prompt.
        """
        bits: list[str] = []
        for pos in state.get("key_positions") or []:
            if not isinstance(pos, dict):
                continue
            subj = pos.get("subject")
            if not isinstance(subj, str) or not subj:
                continue
            detail: list[str] = []
            for key in ("screen_position", "posture", "relation"):
                val = pos.get(key)
                if isinstance(val, str) and val.strip():
                    detail.append(val.strip())
            vis = pos.get("visibility")
            if vis in ("off_frame", "heard_offscreen"):
                detail.append(vis.replace("_", " "))
            bits.append(f"{subj} {', '.join(detail)}" if detail else subj)
        for prop in state.get("props_state") or []:
            if not isinstance(prop, dict):
                continue
            p, st = prop.get("prop"), prop.get("state")
            if isinstance(p, str) and isinstance(st, str) and p and st:
                bits.append(f"{p} {st}")
        return "; ".join(bits)

    @classmethod
    def _continuity_phrase(cls, label: str, state: dict[str, Any]) -> str:
        """Render a scene_continuity_ledger entry/exit state into a prompt clause."""
        bits: list[str] = []
        summary = state.get("summary")
        if isinstance(summary, str) and summary.strip():
            # Prefer the authored summary; positions would duplicate it and the
            # 2500-char API budget is tight. Fall back to positions only when no
            # summary is authored (so the position data still reaches the prompt).
            bits.append(summary.strip())
        else:
            positions = cls._format_positions(state)
            if positions:
                bits.append(positions)
        cam = state.get("camera_state") if isinstance(state.get("camera_state"), dict) else {}
        shot_size = cam.get("shot_size")
        if isinstance(shot_size, str):
            bits.append(f"camera {shot_size}")
        direction = state.get("screen_direction")
        if isinstance(direction, str) and direction != "neutral":
            bits.append(f"screen direction {direction.replace('_', ' ')}")
        if not bits:
            return ""
        return f"{label}: " + "; ".join(bits) + "."

    def _build_shot_entry_anchor(
        self,
        shot: dict[str, Any],
        ledger_entry: dict[str, Any] | None,
        is_first: bool,
        seam_printed: bool,
        alias_map: dict[str, str],
        char_ids: set[str],
    ) -> str:
        """Carried-state anchor printed at the START of a shot block.

        Restates where each on-frame subject/prop is as the shot opens (the prior
        shot's exit), BEFORE the new action, so positions chain instead of
        resetting at the cut. The first shot defers to the clip-seam line
        ("Continue from previous clip") when that already printed the entry state.
        """
        state = shot.get("entry_state")
        if not isinstance(state, dict):
            if is_first and isinstance(ledger_entry, dict):
                state = ledger_entry
            else:
                return ""
        if is_first and seam_printed:
            return ""
        summary = state.get("summary")
        if isinstance(summary, str) and summary.strip():
            text = summary.strip()
        else:
            text = self._format_positions(state)
        if not text:
            return ""
        shot_elem_ids = list(shot.get("required_element_ids") or [])
        text, _ = _rewrite_shot_action(text, shot_elem_ids, alias_map, char_ids)
        if not text.endswith((".", "!", "?")):
            text += "."
        return text

    def _compose_figure_actions(
        self,
        shot: dict[str, Any],
        alias_map: dict[str, str],
        char_ids: set[str],
    ) -> str:
        """One distinct action clause per figure (multi-character disambiguation).

        Kling/FAL.ai: bind each action to a unique character so the model never
        confuses who does what. Falls back to nothing when no figure carries an
        ``action`` (the shot's prompt_action then stands alone, back-compat).
        """
        shot_elem_ids = list(shot.get("required_element_ids") or [])
        clauses: list[str] = []
        for fig in shot.get("figures") or []:
            if not isinstance(fig, dict):
                continue
            act = fig.get("action")
            alias = fig.get("kling_alias")
            if not (isinstance(act, str) and act.strip() and isinstance(alias, str)):
                continue
            text = act.strip()
            if alias not in text:
                text = f"{alias} {text}"
            text, _ = _rewrite_shot_action(text, shot_elem_ids, alias_map, char_ids)
            if not text.endswith((".", "!", "?")):
                text += "."
            clauses.append(text[0].upper() + text[1:])
        return " ".join(clauses)

    @staticmethod
    def _compose_action_sentence(action: str, shot: dict[str, Any]) -> str:
        """Action prose with the shot's performance_note woven in (acting/emotion).

        Performance is direction for the actor, not a new story fact; it is added
        to the action sentence the way a director's note rides on a beat.
        """
        text = action.strip()
        # When the shot carries per-figure actions, performance lives per-figure;
        # weaving the shot-level performance_note here would duplicate it and cost
        # scarce prompt budget, so skip it.
        has_figure_actions = any(
            isinstance(f, dict) and isinstance(f.get("action"), str) and f["action"].strip()
            for f in (shot.get("figures") or [])
        )
        perf = shot.get("performance_note")
        if not has_figure_actions and isinstance(perf, str) and perf.strip():
            text = text.rstrip(" .") + " — " + perf.strip()
        if not text.endswith((".", "!", "?", '"')):
            text += "."
        return text

    @staticmethod
    def _build_camera_sentence(shot: dict[str, Any]) -> str:
        """Natural camera-direction sentence (movement + lens bias), no telemetry.

        Numeric motion intensities and structured Camera:/Lighting:/Motion: labels
        stay in the manifest for QC; the prompt reads like a director's instruction.
        """
        camera = shot.get("camera") if isinstance(shot.get("camera"), dict) else {}
        movement = camera.get("movement")
        lens = camera.get("lens_bias")
        bits: list[str] = []
        phrase = _MOVEMENT_PROSE.get(movement) if isinstance(movement, str) else None
        if phrase:
            bits.append(phrase)
        if isinstance(lens, str) and lens.strip():
            bits.append(lens.strip())
        if not bits:
            return ""
        sentence = "; ".join(bits)
        return sentence[0].upper() + sentence[1:] + "."

    @staticmethod
    def _build_diegetic_audio_clause(shot: dict[str, Any]) -> str:
        """In-world sound-design line (non-speech). Spoken dialogue is rendered
        separately by _render_shot_dialogue."""
        audio = shot.get("diegetic_audio")
        if isinstance(audio, str) and audio.strip():
            a = audio.strip()
            if not a.endswith((".", "!", "?")):
                a += "."
            return f"Audio: {a}"
        return ""

    @staticmethod
    def _render_shot_dialogue(
        shot: dict[str, Any],
        dialogue_lines: list[dict[str, Any]],
        alias_map: dict[str, str],
        rendered_ids: set[str],
    ) -> str:
        """Render this shot's verbatim dialogue inline as alias-tagged speech.

        Format (Kling Omni native-audio dialogue): ``— @Alias (tone): "line_text"``
        with multiple lines in one shot sequenced by "Immediately,". The verbatim
        ``line_text`` is the single source of truth; this is always rendered as
        on-screen dialogue text regardless of native-audio readiness — the readiness
        gate only controls whether spoken VOICE is generated (audio_gate_status).
        """
        if not dialogue_lines:
            return ""
        explicit = [d for d in (shot.get("dialogue_line_ids") or []) if isinstance(d, str)]
        if explicit:
            order = {lid: i for i, lid in enumerate(explicit)}
            candidates = sorted(
                (l for l in dialogue_lines if l.get("line_id") in order),
                key=lambda l: order.get(l.get("line_id"), 0),
            )
        else:
            beat_ids = set(shot.get("source_beat_ids") or [])
            candidates = [
                l for l in dialogue_lines if l.get("target_beat_id") in beat_ids
            ]

        clauses: list[str] = []
        for line in candidates:
            lid = line.get("line_id")
            if lid in rendered_ids:
                continue
            if line.get("line_type") == "implied":
                continue
            line_text = line.get("line_text", "") or ""
            eid = line.get("speaker_element_id", "")
            alias = alias_map.get(eid) or line.get("speaker_kling_alias", "")
            if not line_text or not alias:
                continue
            line_type = line.get("line_type", "spoken")
            delivery = line.get("delivery_note", "") or ""
            if line_type == "offscreen":
                tone = "offscreen"
            elif delivery:
                tone = re.split(r"[.,]", delivery)[0].strip()[:40]
            else:
                tone = ""
            tag = f"{alias} ({tone})" if tone else alias
            clauses.append(f'{tag}: "{line_text}"')
            if isinstance(lid, str):
                rendered_ids.add(lid)

        if not clauses:
            return ""
        joined = clauses[0]
        for clause in clauses[1:]:
            joined += " Immediately, " + clause
        return "— " + joined

    @classmethod
    def _build_shot_heading(cls, duration: int, start: int, shot: dict[str, Any]) -> str:
        """Timecode-first Goro-style heading: ``[MM:SS - MM:SS] <Framing label>:``."""
        end = start + duration
        camera = shot.get("camera") if isinstance(shot.get("camera"), dict) else {}
        framing = camera.get("framing")
        coverage = shot.get("coverage_role")
        label: str | None = None
        if isinstance(coverage, str) and coverage in _COVERAGE_LABELS:
            label = _COVERAGE_LABELS[coverage]
        if label is None and isinstance(framing, str):
            label = _FRAMING_LABELS.get(framing)
        if label is None:
            label = "Cinematic shot"
        return f"[{_format_timecode(start)} - {_format_timecode(end)}] {label}:"

    def _build_prompt_text_from_manifest(
        self,
        shots: list[Any],
        total_duration: int,
        max_duration: int,
        continuity_mode: str,
        variant_mode: str,
        beat_content_lookup: dict[str, str] | None = None,
    ) -> str:
        """Build prompt text from manifest shots (not scene_card.shot_list_omni).
        Legacy path used when no active element aliases are available.
        """
        shot_lines: list[str] = []
        elapsed = 0
        for index, shot in enumerate(shots, start=1):
            if index > 6:
                raise KlingOmniAdapterError(
                    "Kling Omni clip-manifest prompt synthesis supports at most "
                    "6 shots per generation."
                )
            duration = int(shot.get("duration_seconds", 0))
            prompt_action = _text(shot.get("prompt_action"), "approved action")
            source_beat_ids: list[str] = list(shot.get("source_beat_ids") or [])
            if prompt_action.endswith("...") and source_beat_ids and beat_content_lookup:
                full = beat_content_lookup.get(source_beat_ids[0], "")
                if full:
                    prompt_action = full
            heading = self._build_shot_heading(duration, elapsed, shot)
            action_sentence = self._compose_action_sentence(prompt_action, shot)
            camera_sentence = self._build_camera_sentence(shot)
            audio_clause = self._build_diegetic_audio_clause(shot)
            block = f"{heading} {action_sentence}"
            if camera_sentence:
                block += f" {camera_sentence}"
            if audio_clause:
                block += f" {audio_clause}"
            shot_lines.append(block)
            elapsed += duration

        parts = [
            "Create one external Kling Omni video instruction.",
            f"Total duration: {total_duration} seconds.",
            self._variant_preamble(variant_mode),
        ]

        parts.extend(shot_lines)

        continuity_note = f"Continuity mode: {continuity_mode}."
        if continuity_mode == "frame_input_active":
            continuity_note += " First/last frame inputs may be passed to Kling."
        elif continuity_mode == "frame_input_eligible":
            continuity_note += " Frame inputs eligible but not active in this generation."
        else:
            continuity_note += " Use continuity metadata only; do not claim frame inputs."
        parts.append(continuity_note)

        parts.append(
            f"Keep the clip at {total_duration} seconds, never over {max_duration} seconds. "
            "End with a clear settled state. Do not add new story facts."
        )
        return _sanitize_prompt_text(" ".join(part for part in parts if part))

    @staticmethod
    def _variant_preamble(variant_mode: str) -> str:
        if variant_mode == "safe":
            return (
                "Variant SAFE: prioritize stable continuity, restrained camera language, "
                "and conservative execution."
            )
        if variant_mode == "creative":
            return (
                "Variant CREATIVE: allow controlled atmospheric enrichment while keeping "
                "all source-grounded facts unchanged."
            )
        return (
            "Variant AGGRESSIVE: use stronger cinematic expression and camera energy "
            "without adding any new story facts."
        )

    def _prompt_record(
        self,
        *,
        scene_id: str,
        scene_card: dict[str, Any],
        shot_list: list[Any],
        scene_card_path: Path,
        omni_set_ref: str,
        version: int,
    ) -> dict[str, Any]:
        prompt_id = f"{scene_id}__omni-kling-omni__v{version:02d}"
        max_duration = self._max_duration_seconds()
        total_duration = self._validated_shot_duration_total(shot_list, max_duration)
        prompt_text = self._build_prompt_text(
            scene_card,
            shot_list,
            total_duration,
            max_duration,
        )
        source_refs: dict[str, Any] = {
            "scene_card": _relative(scene_card_path, self.repo_root),
            "scene_excerpt": f"planning/scenes/{scene_id}/{scene_card.get('excerpt_ref') or 'scene_excerpt.md'}",
            "omni_set_ref": omni_set_ref,
        }

        generation_params: dict[str, Any] = {
            "model_guidance_mode": self.model_guidance_mode,
            "adapter_name": self.MODEL_ID,
            "max_duration_seconds": max_duration,
            "repo_binary_committed": False,
            "external_generation_required": True,
            "recommended_cfg_scale": 0.5,
            "recommended_ar": "16:9",
        }

        # Dynamic model resolution: resolve from snapshot at runtime
        if self.model_guidance_mode == "dynamic_snapshot":
            resolved = resolve_model_guidance(
                repo_root=self.repo_root,
                internal_model_target=self.INTERNAL_MODEL_TARGET,
            )
            generation_params.update({
                "model_guidance_snapshot_ref": resolved["model_guidance_snapshot_ref"],
                "provider": resolved["provider"],
                "provider_surface": resolved["provider_surface"],
                "resolved_model_name": resolved["resolved_model_name"],
                "resolved_model_role": resolved["resolved_model_role"],
                "guidance_observed_at": resolved["guidance_observed_at"],
                "guidance_expires_at": resolved["guidance_expires_at"],
            })
        else:
            # Legacy mode: locked_guide (default)
            generation_params["model_guidance_ref"] = "docs/model_guides/kling_omni.yaml"
            if self.model_guidance_snapshot:
                generation_params["model_guidance_snapshot"] = self.model_guidance_snapshot

        record: dict[str, Any] = {
            "prompt_id": prompt_id,
            "scene_id": scene_id,
            "prompt_type": "omni_instruction",
            "lifecycle_stage": "draft",
            "target_models": [self.MODEL_ID],
            "source_refs": source_refs,
            "prompt_text": prompt_text,
            "negative_prompt": self._build_negative_prompt(scene_card),
            "generation_params": generation_params,
            "expected_output": {
                "asset_type": "clip",
                "duration_seconds": total_duration,
            },
            "status": "active",
            "canon_lock": False,
        }
        return record

    def _run_record(
        self,
        *,
        scene_id: str,
        prompt_id: str,
        run_counter: int,
        run_at: str | None,
        clip_id: str | None = None,
    ) -> dict[str, Any]:
        if clip_id:
            run_id = f"RUN_{scene_id}_{clip_id}_{self.ABBREV}_{run_counter:04d}"
        else:
            run_id = f"RUN_{scene_id}_{self.ABBREV}_{run_counter:04d}"
        record: dict[str, Any] = {
            "run_id": run_id,
            "prompt_id": prompt_id,
            "model": self.MODEL_ID,
            "run_at": run_at or _now_iso(),
            "outputs_expected": 1,
            "cost": {"unit": "unknown", "value": 0},
            "status": "pending",
        }
        # In dynamic_snapshot mode, the snapshot ref is in generation_params;
        # in locked_guide mode, optionally include it here
        if self.model_guidance_snapshot:
            record["model_guidance_snapshot"] = self.model_guidance_snapshot
        return record

    def _build_prompt_text(
        self,
        scene_card: dict[str, Any],
        shot_list: list[Any],
        total_duration: int,
        max_duration: int,
    ) -> str:
        scene_title = _text(scene_card.get("title"), "Selected scene")
        purpose = _text(scene_card.get("purpose"), "")
        visual_targets = scene_card.get("visual_targets")
        if not isinstance(visual_targets, dict):
            visual_targets = {}
        shots: list[str] = []
        for index, shot in enumerate(shot_list, start=1):
            if not isinstance(shot, dict):
                continue
            subject = _text(shot.get("subject"), "approved scene subject")
            framing = _text(shot.get("framing"), "source-grounded framing")
            movement = _text(
                shot.get("camera_movement") or shot.get("movement"),
                "controlled camera movement",
            )
            lighting = _text(shot.get("lighting"))
            duration = int(shot["duration_seconds"])
            details = [subject, framing, movement]
            if lighting:
                details.append(lighting)
            details.append("end by settling into the approved scene state")
            shots.append(
                f"Shot {index} ({duration}s): " + "; ".join(details) + "."
            )
        parts = [
            "Create one external Kling Omni video instruction.",
            f"Scene tone: {scene_title}.",
            f"Total duration: {total_duration} seconds.",
        ]
        if purpose:
            parts.append(f"Dramatic intent: {purpose}.")
        parts.extend(shots)
        if visual_targets:
            parts.append(
                "Visual treatment: "
                + "; ".join(
                    _text(visual_targets.get(key))
                    for key in ("palette", "framing_bias", "movement_bias", "lighting_bias")
                    if _text(visual_targets.get(key))
                )
                + "."
            )
        parts.append(
            f"Keep the clip at {total_duration} seconds, never over {max_duration} seconds. "
            "End with a clear settled state. Do not add new story facts."
        )
        return _sanitize_prompt_text(" ".join(part for part in parts if part))

    def _build_negative_prompt(
        self,
        scene_card: dict[str, Any],
        extra_terms: list[str] | None = None,
    ) -> str:
        """
        Build Kling negative_prompt from scene do-not constraints.
        Terms written directly (no 'no' prefix — Kling parses terms, not sentences).
        Falls back to default motion-artifact prevention terms.
        """
        visual_targets = scene_card.get("visual_targets") or {}
        # Base motion-artifact terms (always present — prevents common Kling artifacts)
        base_terms = [
            "sliding-feet",
            "morphing",
            "floating-objects",
            "flickering",
            "lens-distortion",
        ]
        all_terms = base_terms + (extra_terms or [])
        return ", ".join(all_terms)

    def _pack_gate_warnings(self, scene_id: str, omni_set_ref: str) -> list[str]:
        warnings: list[str] = []
        element_set_path = self.repo_root / omni_set_ref / "element_set.yaml"
        element_set = _read_yaml(element_set_path)
        if element_set is None:
            warnings.append(
                f"WARNING: no element_set.yaml found for {scene_id}; pack lock status could not be verified."
            )
            return warnings

        refs = element_set.get("element_refs") or []
        if not isinstance(refs, list):
            warnings.append("WARNING: element_set.element_refs is not a list.")
            return warnings

        for ref in refs:
            ref_path = self.repo_root / str(ref)
            element_ref = _read_yaml(ref_path)
            if not isinstance(element_ref, dict):
                warnings.append(f"WARNING: missing element descriptor: {ref}")
                continue
            pack_path = _text(element_ref.get("pack_path_expected"))
            if not pack_path:
                warnings.append(f"WARNING: no pack_path_expected in {ref}")
                continue
            pack_manifest_path = self.repo_root / pack_path / "pack_manifest.yaml"
            pack_manifest = _read_yaml(pack_manifest_path)
            if pack_manifest is None:
                warnings.append(f"WARNING: no pack_manifest.yaml at {pack_path}")
                continue
            status = pack_manifest.get("pack_status")
            if status != "locked":
                warnings.append(
                    f"BLOCKED: {pack_path} pack_status is {status!r}, expected 'locked'."
                )
        return warnings

    def _max_duration_seconds(self) -> int:
        matrix_path = self.repo_root / "docs" / "model_guides" / "model_capability_matrix.yaml"
        matrix = _read_yaml(matrix_path) or {}
        models = matrix.get("models") if isinstance(matrix, dict) else {}
        kling = models.get("kling_omni") if isinstance(models, dict) else {}
        value = kling.get("max_duration_seconds") if isinstance(kling, dict) else None
        return int(value) if isinstance(value, int) else 10

    @staticmethod
    def _validated_shot_duration_total(shot_list: list[Any], max_duration: int) -> int:
        total = 0
        for index, shot in enumerate(shot_list, start=1):
            if not isinstance(shot, dict):
                raise KlingOmniAdapterError(f"shot_list_omni[{index}] must be a mapping.")
            duration = shot.get("duration_seconds")
            if not isinstance(duration, int) or duration <= 0:
                raise KlingOmniAdapterError(
                    f"shot_list_omni[{index}].duration_seconds must be a positive integer."
                )
            total += duration

        if total <= 0:
            raise KlingOmniAdapterError("shot_list_omni total duration must be positive.")
        if total > max_duration:
            raise KlingOmniAdapterError(
                f"shot_list_omni total duration {total}s exceeds max {max_duration}s."
            )

        allowed_shots = _allowed_shot_count(total)
        if len(shot_list) > allowed_shots:
            raise KlingOmniAdapterError(
                f"shot_list_omni has {len(shot_list)} shots for {total}s, "
                f"max allowed is {allowed_shots}."
            )
        return total
