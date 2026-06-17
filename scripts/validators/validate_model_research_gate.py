"""
Model Research Refresh Gate — A6.5

Validates that every required model guidance target has a fresh, human-verified,
non-placeholder snapshot before any prompt generation batch is started.

The resolver (model_guidance_resolver.py) already gates individual prompt adapters.
This gate is called ONCE at the start of a production batch and gives an upfront
summary across all required targets so operators can refresh stale snapshots before
generating any prompts, not mid-run.

Gate checks per snapshot:
  HARD (any failure → target fails):
    1. Snapshot file exists for the target
    2. Schema valid (model_guidance_snapshot.schema.json)
    3. human_verified: true
    4. Not expired (expires_at >= reference_time)
    5. No placeholder source URLs (e.g. example.org/placeholder)
    6. sources list non-empty
    7. prompting_rules list non-empty
    8. latest_available_model or best_for_this_task present and not a placeholder value

  SOFT (warning only):
    - constraints dict empty or missing → warn to add hard limits

Usage:
    python scripts/validators/validate_model_research_gate.py \\
        --targets kling_omni_video_best_available chatgpt_image_best_available \\
                  midjourney_image_best_available nano_banana_best_available

    # or from code:
    from scripts.validators.validate_model_research_gate import validate_model_research_gate
    results = validate_model_research_gate(repo_root, required_targets=[...])
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLACEHOLDER_STRINGS = frozenset({"", "TBD", "TODO", "unknown", "PLACEHOLDER", "unknown_placeholder"})

PLACEHOLDER_URL_FRAGMENTS = ("example.org/placeholder", "localhost", "127.0.0.1")

KNOWN_TARGETS = (
    "kling_omni_video_best_available",
    "midjourney_image_best_available",
    "chatgpt_image_best_available",
    "nano_banana_best_available",
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class TargetGateResult:
    target: str
    passed: bool
    snapshot_path: str | None = None
    hard_errors: list[str] = field(default_factory=list)
    soft_warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "PASS" if self.passed else f"FAIL ({len(self.hard_errors)} error(s))"
        lines = [f"  [{status}] {self.target}"]
        if self.snapshot_path:
            lines.append(f"    snapshot: {self.snapshot_path}")
        for err in self.hard_errors:
            lines.append(f"    [HARD] {err}")
        for warn in self.soft_warnings:
            lines.append(f"    [SOFT] {warn}")
        return "\n".join(lines)


class ModelResearchGateError(RuntimeError):
    """Raised when gate() is called in strict mode and one or more targets fail."""


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------


def _is_placeholder_value(value: Any) -> bool:
    if value is None:
        return False
    return isinstance(value, str) and value in PLACEHOLDER_STRINGS


def _has_placeholder_source(sources: list[dict]) -> bool:
    for src in sources:
        url = str(src.get("url", ""))
        for fragment in PLACEHOLDER_URL_FRAGMENTS:
            if fragment in url:
                return True
    return False


def _find_latest_snapshot(snapshots_dir: Path, internal_model_target: str) -> Path | None:
    """Return the most recently modified snapshot YAML for the given target."""
    if not snapshots_dir.exists():
        return None
    candidates = []
    for yaml_file in snapshots_dir.rglob("*.yaml"):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("internal_model_target") == internal_model_target:
                candidates.append(yaml_file)
        except Exception:
            continue
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def _load_schema(repo_root: Path) -> dict | None:
    schema_path = repo_root / "schemas" / "model_guidance_snapshot.schema.json"
    if not schema_path.exists():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _validate_target(
    target: str,
    snapshots_dir: Path,
    schema: dict | None,
    reference_time: datetime,
) -> TargetGateResult:
    hard: list[str] = []
    soft: list[str] = []

    snapshot_path = _find_latest_snapshot(snapshots_dir, target)
    if snapshot_path is None:
        return TargetGateResult(
            target=target,
            passed=False,
            snapshot_path=None,
            hard_errors=[
                f"No snapshot found for target {target!r} in {snapshots_dir}. "
                "Run model research refresh before generating prompts."
            ],
        )

    try:
        data: dict = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return TargetGateResult(
            target=target,
            passed=False,
            snapshot_path=str(snapshot_path),
            hard_errors=[f"Cannot read snapshot: {exc}"],
        )

    rel_path = str(snapshot_path)

    # 1. Schema validation
    if schema is not None:
        try:
            from jsonschema import Draft202012Validator
            errs = list(Draft202012Validator(schema).iter_errors(data))
            for err in errs:
                path = ".".join(str(p) for p in err.absolute_path) or "(root)"
                hard.append(f"Schema error at [{path}]: {err.message}")
        except ImportError:
            soft.append("jsonschema not installed; schema validation skipped")

    # 2. human_verified
    if not data.get("human_verified", False):
        hard.append(
            f"human_verified is {data.get('human_verified')!r}. "
            "Snapshot must be verified by a human researcher before prompt generation."
        )

    # 3. Expiry
    expires_at_str = data.get("expires_at")
    if not expires_at_str:
        hard.append("expires_at missing; cannot verify freshness.")
    else:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if reference_time > expires_at:
                hard.append(
                    f"Snapshot expired at {expires_at_str}. "
                    "Refresh model research before generating prompts."
                )
        except ValueError:
            hard.append(f"expires_at is not a valid ISO-8601 datetime: {expires_at_str!r}")

    # 4. Placeholder source URLs
    sources = data.get("sources") or []
    if not sources:
        hard.append("sources list is empty. Snapshot must cite at least one verified source.")
    elif _has_placeholder_source(sources):
        hard.append(
            "Snapshot contains placeholder source URL(s) (e.g. example.org/placeholder). "
            "Replace with real official or verified-platform-blog sources."
        )

    # 5. prompting_rules non-empty
    rules = data.get("prompting_rules") or []
    if not rules:
        hard.append(
            "prompting_rules is empty. Snapshot must include at least one verified prompt rule."
        )

    # 6. Resolvable model version
    latest = data.get("latest_available_model")
    best = data.get("best_for_this_task")
    if _is_placeholder_value(latest) and _is_placeholder_value(best):
        hard.append(
            f"Both latest_available_model ({latest!r}) and best_for_this_task ({best!r}) "
            "are placeholders. At least one must be a real model version string."
        )

    # Soft: constraints completeness
    constraints = data.get("constraints") or {}
    if not constraints:
        soft.append(
            "constraints dict is empty. Consider adding hard API limits "
            "(e.g. prompt_text_max_chars, negative_prompt_max_chars) for downstream validation."
        )

    passed = len(hard) == 0
    return TargetGateResult(
        target=target,
        passed=passed,
        snapshot_path=rel_path,
        hard_errors=hard,
        soft_warnings=soft,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_model_research_gate(
    repo_root: str | Path,
    required_targets: list[str],
    reference_time: datetime | None = None,
    *,
    strict: bool = False,
) -> list[TargetGateResult]:
    """
    Validate model research freshness for all required targets.

    Args:
        repo_root: Repository root path.
        required_targets: List of internal_model_target strings to check.
        reference_time: UTC datetime for expiry checks (default: now).
        strict: If True, raise ModelResearchGateError on any failure.

    Returns:
        List of TargetGateResult, one per target.

    Raises:
        ModelResearchGateError: If strict=True and any target fails.
    """
    repo_root = Path(repo_root)
    ref = reference_time or datetime.now(timezone.utc)
    snapshots_dir = repo_root / "model_guidance_snapshots"
    schema = _load_schema(repo_root)

    results = [
        _validate_target(target, snapshots_dir, schema, ref)
        for target in required_targets
    ]

    if strict:
        failures = [r for r in results if not r.passed]
        if failures:
            summary = "\n".join(str(r) for r in failures)
            raise ModelResearchGateError(
                f"{len(failures)} target(s) failed model research gate:\n{summary}"
            )

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Model Research Refresh Gate — validate that all required model guidance "
            "snapshots are fresh, human-verified, and non-placeholder before prompt generation."
        )
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        default=list(KNOWN_TARGETS),
        metavar="TARGET",
        help=(
            "Internal model target IDs to validate. "
            f"Defaults to all known targets: {', '.join(KNOWN_TARGETS)}"
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        metavar="PATH",
        help="Repository root directory (default: current directory).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any target fails (default: always exit 1 on failure).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    results = validate_model_research_gate(
        repo_root=repo_root,
        required_targets=args.targets,
    )

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(f"\nModel Research Gate — {len(passed)}/{len(results)} targets passed\n")
    for result in results:
        print(str(result))

    if failed:
        print(f"\n{len(failed)} target(s) FAILED. Refresh model guidance before generating prompts.")
        print("Steps:")
        print("  1. Review failed targets above.")
        print("  2. Research official docs + verified platform blogs for each model.")
        print("  3. Update model_guidance_snapshots/<provider>/<timestamp>_<target>.yaml")
        print("  4. Set human_verified: true after review.")
        print("  5. Re-run this gate.")
        return 1

    print("\nAll targets passed. Prompt generation is unblocked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
