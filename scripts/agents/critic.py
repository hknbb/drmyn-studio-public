"""
Critic Agent v1 for Batch 5.

Performs hard schema and structural checks, plus soft keyword checks on
prompt records. Raises no exceptions — all findings are returned in a
CriticResult. Call CriticAgent.check(prompt_record) before writing.

Hard checks (any failure → passed=False):
  - JSON schema validation against prompt_record.schema.json
  - prompt_id matches ^SC\\d{4}__[a-z0-9\\-]+__v\\d{2}$
  - lifecycle_stage == "draft"
  - source_refs.scene_card and source_refs.scene_excerpt non-empty
  - No planning canonical IDs (C##, LOC###, PROP###, WD###, SC####) in prompt_text
  - Exactly 1 target_model
  - Model guidance (two modes):
    - locked_guide: generation_params.model_guidance_ref file exists, model_id matches
    - dynamic_snapshot: snapshot file exists, A6.3 fields present, snapshot validated
  - Negative prompt conditional on model capability (locked_guide or snapshot)

Soft checks (only → soft_warnings, never fail):
  - UNRESOLVED / TODO_REVIEW / TODO / EVIDENCE_THIN in prompt_text or negative_prompt

Deferred to v2:
  - Full semantic source-grounding
  - Prop continuity color/material contradiction analysis
  - do_not_invent keyword cross-check with planning records
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

PROMPT_ID_RE = re.compile(r"^SC\d{4}__[a-z0-9\-]+__v\d{2}$")

# Planning system IDs that must not appear literally in prompt_text
CANONICAL_ID_RE = re.compile(r"\b(C\d{2}|LOC\d{3}|PROP\d{3}|WD\d{3}|SC\d{4})\b")

# Markers that flag unresolved content
UNRESOLVED_RE = re.compile(r"\b(UNRESOLVED|TODO_REVIEW|TODO|EVIDENCE_THIN)\b")

# Valid Kling element alias syntax: @AlphanumericOrUnderscore
ELEMENT_ALIAS_RE = re.compile(r"^@[A-Za-z0-9_]+$")

# API character limits for Kling (sourced from Magnific API reference)
KLING_PROMPT_MAX_CHARS = 2500
KLING_NEGATIVE_PROMPT_MAX_CHARS = 2500


def _parse_utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CriticResult:
    """Outcome of a CriticAgent.check() call."""

    passed: bool
    hard_errors: list[str] = field(default_factory=list)
    soft_warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "PASSED" if self.passed else f"FAILED ({len(self.hard_errors)} hard errors)"
        parts = [f"CriticResult: {status}"]
        for err in self.hard_errors:
            parts.append(f"  [HARD] {err}")
        for warn in self.soft_warnings:
            parts.append(f"  [SOFT] {warn}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# CriticAgent
# ---------------------------------------------------------------------------


class CriticAgent:
    """
    Validates a prompt record dict against hard structural rules and
    soft keyword heuristics.

    ``repo_root`` is used to resolve file paths in generation_params
    (model_guidance_ref, model_guidance_snapshot).
    """

    def __init__(
        self,
        repo_root: str | Path,
        *,
        reference_time: datetime | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self._schema: dict[str, Any] | None = None
        self.reference_time = reference_time

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, prompt_record: dict[str, Any]) -> CriticResult:
        """Run all checks and return a CriticResult."""
        hard: list[str] = []
        soft: list[str] = []

        self._check_schema(prompt_record, hard)
        self._check_prompt_id(prompt_record, hard)
        self._check_lifecycle_stage(prompt_record, hard)
        self._check_source_refs(prompt_record, hard)
        self._check_no_canonical_ids(prompt_record, hard)
        self._check_no_planning_aliases(prompt_record, hard)
        self._check_target_models(prompt_record, hard)
        self._check_model_guidance(prompt_record, hard)
        self._check_negative_prompt_rule(prompt_record, hard)
        self._check_element_aliases(prompt_record, hard)
        self._check_prompt_char_limits(prompt_record, hard)

        # Soft checks — always after hard checks
        self._check_unresolved_markers(prompt_record, soft)

        return CriticResult(passed=not hard, hard_errors=hard, soft_warnings=soft)

    # ------------------------------------------------------------------
    # Hard checks
    # ------------------------------------------------------------------

    def _check_schema(self, record: dict, errors: list[str]) -> None:
        """Validate against prompt_record.schema.json (skipped if jsonschema missing)."""
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            return

        schema = self._load_schema()
        for err in Draft202012Validator(schema).iter_errors(record):
            path = ".".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"Schema: [{path}] {err.message}")

    def _check_prompt_id(self, record: dict, errors: list[str]) -> None:
        prompt_id = record.get("prompt_id", "")
        if not PROMPT_ID_RE.match(str(prompt_id)):
            errors.append(
                f"prompt_id {prompt_id!r} does not match "
                r"^SC\d{4}__[a-z0-9\-]+__v\d{2}$"
            )

    def _check_lifecycle_stage(self, record: dict, errors: list[str]) -> None:
        stage = record.get("lifecycle_stage")
        if stage != "draft":
            errors.append(
                f"lifecycle_stage must be 'draft' for agent-generated records; "
                f"got {stage!r}"
            )

    def _check_source_refs(self, record: dict, errors: list[str]) -> None:
        refs = record.get("source_refs") or {}
        for field_name in ("scene_card", "scene_excerpt"):
            value = refs.get(field_name)
            if not value or not str(value).strip():
                errors.append(f"source_refs.{field_name} is missing or empty")

    def _check_no_canonical_ids(self, record: dict, errors: list[str]) -> None:
        """Planning IDs (C01, LOC001, etc.) must not appear literally in prompt_text."""
        text = str(record.get("prompt_text") or "")
        for match in CANONICAL_ID_RE.finditer(text):
            errors.append(
                f"Canonical planning ID {match.group()!r} found in prompt_text. "
                "Remove planning IDs from generated text; they belong in source_refs only."
            )

    def _check_no_planning_aliases(self, record: dict, errors: list[str]) -> None:
        """Planning display names declared in planning_name_filter must not appear in prompt_text."""
        params = record.get("generation_params") or {}
        forbidden = (params.get("planning_name_filter") or {}).get("forbidden") or []
        if not forbidden:
            return
        text = str(record.get("prompt_text") or "")
        for alias in forbidden:
            if alias and alias in text:
                errors.append(
                    f"Planning name {alias!r} found in prompt_text. "
                    "Use prompt_subject_label (safe visual label) instead of planning display names."
                )

    def _check_target_models(self, record: dict, errors: list[str]) -> None:
        models = record.get("target_models") or []
        if len(models) != 1:
            errors.append(
                f"target_models must contain exactly 1 model; got {len(models)}: {models}"
            )

    def _check_model_guidance(self, record: dict, errors: list[str]) -> None:
        params = record.get("generation_params") or {}
        mode = params.get("model_guidance_mode", "locked_guide")
        target_models = record.get("target_models") or []

        if mode == "dynamic_snapshot":
            self._check_dynamic_snapshot_mode(record, errors)
        else:
            # Default: locked_guide mode
            self._check_locked_guide_mode(record, errors)

    def _check_locked_guide_mode(self, record: dict, errors: list[str]) -> None:
        """Validate locked_guide mode (legacy, default behavior)."""
        params = record.get("generation_params") or {}
        ref = params.get("model_guidance_ref")

        if not ref:
            errors.append("generation_params.model_guidance_ref is missing")
            return

        guide_path = self.repo_root / ref
        if not guide_path.exists():
            errors.append(f"model_guidance_ref file not found: {guide_path}")
            return

        # Verify model_id matches target_models[0]
        target_models = record.get("target_models") or []
        if target_models:
            try:
                guide = yaml.safe_load(guide_path.read_text(encoding="utf-8")) or {}
                guide_model_id = str(guide.get("model_id", ""))
                if guide_model_id != target_models[0]:
                    errors.append(
                        f"model_guidance_ref model_id ({guide_model_id!r}) does not match "
                        f"target_models[0] ({target_models[0]!r})"
                    )
            except Exception as exc:
                errors.append(f"Cannot read model_guidance_ref {ref!r}: {exc}")

    def _check_dynamic_snapshot_mode(self, record: dict, errors: list[str]) -> None:
        """Validate dynamic_snapshot mode (A6.3 resolution)."""
        params = record.get("generation_params") or {}
        target_models = record.get("target_models") or []
        target_model = target_models[0] if target_models else None

        # Map internal targets to target model IDs
        INTERNAL_TARGET_MAP = {
            "kling_omni": "kling_omni_video_best_available",
            "midjourney": "midjourney_image_best_available",
            "chatgpt_image": "chatgpt_image_best_available",
            "nano_banana": "nano_banana_best_available",
        }

        # Legacy compatibility: some records carry only model_guidance_snapshot path
        legacy_snapshot_ref = params.get("model_guidance_snapshot")
        if legacy_snapshot_ref and not params.get("model_guidance_snapshot_ref"):
            self._check_legacy_snapshot_mode(record, errors, str(legacy_snapshot_ref), target_model)
            return

        # Check required A6.3 fields
        required_fields = [
            "model_guidance_snapshot_ref",
            "provider",
            "provider_surface",
            "resolved_model_name",
            "resolved_model_role",
            "guidance_observed_at",
            "guidance_expires_at",
        ]
        for field in required_fields:
            if field not in params or not params[field]:
                errors.append(f"generation_params.{field} is missing or empty for dynamic_snapshot mode")

        # If any required field is missing, stop here
        if any(field not in params or not params[field] for field in required_fields):
            return

        snapshot_ref = params.get("model_guidance_snapshot_ref")
        snapshot_path = self.repo_root / snapshot_ref

        if not snapshot_path.exists():
            errors.append(f"model_guidance_snapshot_ref file not found: {snapshot_path}")
            return

        try:
            snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            errors.append(f"Cannot read model_guidance_snapshot_ref {snapshot_ref!r}: {exc}")
            return

        if not isinstance(snapshot, dict):
            errors.append(f"model_guidance_snapshot must be a mapping: {snapshot_path}")
            return

        # Validate snapshot structure
        if snapshot.get("record_type") != "model_guidance_snapshot":
            errors.append(f"Snapshot record_type must be 'model_guidance_snapshot', got {snapshot.get('record_type')!r}")

        if snapshot.get("human_verified") is not True:
            errors.append(
                f"model_guidance_snapshot human_verified must be true; "
                f"got {snapshot.get('human_verified')!r}"
            )

        # Check sources non-empty
        sources = snapshot.get("sources") or []
        if not isinstance(sources, list) or not sources:
            errors.append("model_guidance_snapshot sources must be a non-empty list")

        # Validate internal_model_target matches target_model
        snapshot_internal_target = snapshot.get("internal_model_target")
        expected_internal_target = INTERNAL_TARGET_MAP.get(target_model)
        if expected_internal_target and snapshot_internal_target != expected_internal_target:
            errors.append(
                f"Snapshot internal_model_target ({snapshot_internal_target!r}) does not match "
                f"expected target for {target_model!r} ({expected_internal_target!r})"
            )

        # Validate provider matches
        snapshot_provider = snapshot.get("provider")
        params_provider = params.get("provider")
        if snapshot_provider and params_provider and snapshot_provider != params_provider:
            errors.append(
                f"Snapshot provider ({snapshot_provider!r}) does not match "
                f"generation_params.provider ({params_provider!r})"
            )

        # Validate provider_surface matches
        snapshot_surface = snapshot.get("provider_surface")
        params_surface = params.get("provider_surface")
        if snapshot_surface and params_surface and snapshot_surface != params_surface:
            errors.append(
                f"Snapshot provider_surface ({snapshot_surface!r}) does not match "
                f"generation_params.provider_surface ({params_surface!r})"
            )

        # Validate observed_at matches
        snapshot_observed = snapshot.get("observed_at")
        params_observed = params.get("guidance_observed_at")
        if snapshot_observed and params_observed and snapshot_observed != params_observed:
            errors.append(
                f"Snapshot observed_at ({snapshot_observed!r}) does not match "
                f"generation_params.guidance_observed_at ({params_observed!r})"
            )

        # Validate expires_at matches
        snapshot_expires = snapshot.get("expires_at")
        params_expires = params.get("guidance_expires_at")
        if snapshot_expires and params_expires and snapshot_expires != params_expires:
            errors.append(
                f"Snapshot expires_at ({snapshot_expires!r}) does not match "
                f"generation_params.guidance_expires_at ({params_expires!r})"
            )

        # Validate expiration
        expires_at_str = snapshot.get("expires_at")
        if expires_at_str:
            try:
                expiry = _parse_utc_datetime(str(expires_at_str))
                reference_time = self.reference_time or datetime.now(timezone.utc)
                if reference_time > expiry:
                    errors.append(
                        f"model_guidance_snapshot has expired at {expires_at_str}; "
                        "refresh from official sources"
                    )
            except ValueError:
                errors.append(f"Snapshot expires_at is not parseable: {expires_at_str!r}")

        # Validate resolved_model_name matches the selected role
        resolved_model_name = params.get("resolved_model_name")
        resolved_model_role = params.get("resolved_model_role")

        if resolved_model_role == "current_default":
            expected = snapshot.get("current_default_model")
        elif resolved_model_role == "latest_available":
            expected = snapshot.get("latest_available_model")
        elif resolved_model_role == "best_for_this_task":
            expected = snapshot.get("best_for_this_task")
        elif resolved_model_role == "feature_required":
            # For feature_required, resolved_model_name must be in feature_required_model values
            feature_models = snapshot.get("feature_required_model", {})
            expected = None
            if resolved_model_name not in feature_models.values():
                errors.append(
                    f"resolved_model_name ({resolved_model_name!r}) not found in "
                    f"snapshot.feature_required_model ({list(feature_models.values())})"
                )
            return  # Already validated
        else:
            expected = None

        if expected and resolved_model_name != expected:
            errors.append(
                f"resolved_model_name ({resolved_model_name!r}) does not match "
                f"snapshot.{resolved_model_role} ({expected!r})"
            )

    def _check_legacy_snapshot_mode(
        self,
        record: dict[str, Any],
        errors: list[str],
        snapshot_ref: str,
        target_model: str | None,
    ) -> None:
        snapshot_path = self.repo_root / snapshot_ref
        if not snapshot_path.exists():
            errors.append(f"model_guidance_snapshot file not found: {snapshot_path}")
            return
        try:
            snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            errors.append(f"Cannot read model_guidance_snapshot {snapshot_ref!r}: {exc}")
            return
        if not isinstance(snapshot, dict):
            errors.append(f"model_guidance_snapshot must be a mapping: {snapshot_path}")
            return

        # Legacy checks expected by tests/test_model_guidance_gate.py
        if snapshot.get("model_id") and target_model and snapshot.get("model_id") != target_model:
            errors.append(
                f"model_id mismatch: snapshot model_id {snapshot.get('model_id')!r} != target {target_model!r}"
            )

        for i, src in enumerate(snapshot.get("sources") or []):
            if not isinstance(src, dict):
                continue
            url = str(src.get("url") or "")
            if "placeholder" in url.lower():
                errors.append(f"sources.{i}.url contains placeholder")
            if src.get("human_verified") is False:
                errors.append(f"sources.{i}.human_verified must be true")

        for rule in snapshot.get("extracted_rules") or []:
            if isinstance(rule, str) and "PLACEHOLDER" in rule:
                errors.append("PLACEHOLDER found in extracted_rules")

        if snapshot.get("do_not_use_without_verification"):
            errors.append("do_not_use_without_verification must be empty")

        validity = snapshot.get("snapshot_validity") or {}
        expires_at = validity.get("expires_at")
        if isinstance(expires_at, str):
            try:
                expiry = _parse_utc_datetime(expires_at)
                reference_time = self.reference_time or datetime.now(timezone.utc)
                if reference_time > expiry:
                    errors.append(f"snapshot expired at {expires_at}")
            except ValueError:
                errors.append(f"snapshot_validity.expires_at is not parseable: {expires_at!r}")

    def _check_negative_prompt_rule(self, record: dict, errors: list[str]) -> None:
        """
        Conditional negative_prompt rule derived from the model guide or snapshot capability.

        - supports_negative_prompt in (True, "limited") → negative_prompt required
        - supports_negative_prompt is False → constraint_strategy must be
          "embedded_positive_constraints" in generation_params
        """
        target_models = record.get("target_models") or []
        if not target_models:
            return  # caught by _check_target_models

        params = record.get("generation_params") or {}
        mode = params.get("model_guidance_mode", "locked_guide")

        neg_support = None

        if mode == "dynamic_snapshot":
            # Read capability from snapshot
            snapshot_ref = params.get("model_guidance_snapshot_ref")
            if snapshot_ref:
                snapshot_path = self.repo_root / snapshot_ref
                if snapshot_path.exists():
                    try:
                        snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
                        capabilities = snapshot.get("capabilities") or {}
                        neg_support = capabilities.get("supports_negative_prompt")
                    except Exception:
                        return  # Error caught elsewhere
        else:
            # locked_guide: read from guide file
            ref = params.get("model_guidance_ref")
            if not ref or not (self.repo_root / ref).exists():
                return  # caught by _check_model_guidance

            try:
                guide = yaml.safe_load(
                    (self.repo_root / ref).read_text(encoding="utf-8")
                ) or {}
            except Exception:
                return  # caught by _check_model_guidance

            cap = guide.get("capability") or {}
            neg_support = cap.get("supports_negative_prompt")

        if neg_support in (True, "limited"):
            neg = record.get("negative_prompt")
            if not neg or not str(neg).strip():
                errors.append(
                    f"Model {target_models[0]!r} has "
                    f"supports_negative_prompt={neg_support!r} but "
                    "negative_prompt is absent or empty"
                )
        elif neg_support is False:
            strategy = params.get("constraint_strategy")
            if strategy != "embedded_positive_constraints":
                errors.append(
                    f"Model {target_models[0]!r} has supports_negative_prompt=false; "
                    "generation_params.constraint_strategy must be "
                    "'embedded_positive_constraints'"
                )

    def _check_element_aliases(self, record: dict, errors: list[str]) -> None:
        """Validate generation_params.required_element_aliases against prompt_text.

        Hard errors:
        - required_element_aliases is not a list
        - any alias does not match ^@[A-Za-z0-9_]+$
        - any alias does not appear literally in prompt_text
        """
        params = record.get("generation_params") or {}
        aliases = params.get("required_element_aliases")
        if aliases is None:
            return  # field absent — no enforcement

        if not isinstance(aliases, list):
            errors.append(
                f"generation_params.required_element_aliases must be a list; "
                f"got {type(aliases).__name__}"
            )
            return

        prompt_text = str(record.get("prompt_text") or "")

        for alias in aliases:
            if not isinstance(alias, str) or not ELEMENT_ALIAS_RE.match(alias):
                errors.append(
                    f"Invalid element alias {alias!r}; must match ^@[A-Za-z0-9_]+$"
                )
                continue
            if alias not in prompt_text:
                errors.append(
                    f"Element alias {alias!r} listed in required_element_aliases "
                    "but not found in prompt_text. "
                    "Adapter must inject the alias before the record is written."
                )

    def _check_prompt_char_limits(self, record: dict, errors: list[str]) -> None:
        """Enforce Kling API character limits on prompt_text and negative_prompt.

        Hard errors:
        - prompt_text > 2500 characters
        - negative_prompt > 2500 characters

        Word count is not a hard limit; this check intentionally ignores it.
        """
        prompt_text = str(record.get("prompt_text") or "")
        if len(prompt_text) > KLING_PROMPT_MAX_CHARS:
            errors.append(
                f"prompt_text is {len(prompt_text)} characters; "
                f"Kling API hard limit is {KLING_PROMPT_MAX_CHARS} characters."
            )

        negative_prompt = str(record.get("negative_prompt") or "")
        if negative_prompt and len(negative_prompt) > KLING_NEGATIVE_PROMPT_MAX_CHARS:
            errors.append(
                f"negative_prompt is {len(negative_prompt)} characters; "
                f"Kling API hard limit is {KLING_NEGATIVE_PROMPT_MAX_CHARS} characters."
            )

    # ------------------------------------------------------------------
    # Soft checks
    # ------------------------------------------------------------------

    def _check_unresolved_markers(self, record: dict, warnings: list[str]) -> None:
        """Flag UNRESOLVED / TODO markers in prompt_text or negative_prompt."""
        for field_name in ("prompt_text", "negative_prompt"):
            value = record.get(field_name) or ""
            if UNRESOLVED_RE.search(str(value)):
                warnings.append(
                    f"UNRESOLVED marker found in {field_name!r}; "
                    "review before submitting to external model"
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_schema(self) -> dict[str, Any]:
        if self._schema is None:
            schema_path = (
                self.repo_root / "schemas" / "prompt_record.schema.json"
            )
            self._schema = json.loads(schema_path.read_text(encoding="utf-8"))
        return self._schema
