"""
Tests for A6.2 model guidance snapshot records.

Validates that all four initial snapshots (Kling, Midjourney, ChatGPT, Nano Banana)
exist, validate against schema, resolve correctly, and are human-verified and non-expired.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest
import yaml

from scripts.agents.model_guidance_resolver import resolve_model_guidance


REPO_ROOT = Path(__file__).parent.parent.parent


class TestSnapshotFilesExist:
	"""Verify all four snapshot files are present."""

	def test_kling_snapshot_exists(self):
		snapshot_path = REPO_ROOT / "model_guidance_snapshots" / "kling" / "20260508T140000Z_kling_omni_video_best_available.yaml"
		assert snapshot_path.exists(), f"Kling snapshot missing: {snapshot_path}"

	def test_midjourney_snapshot_exists(self):
		snapshot_path = REPO_ROOT / "model_guidance_snapshots" / "midjourney" / "20260508T120000Z_midjourney_image_best_available.yaml"
		assert snapshot_path.exists(), f"Midjourney snapshot missing: {snapshot_path}"

	def test_chatgpt_snapshot_exists(self):
		snapshot_path = REPO_ROOT / "model_guidance_snapshots" / "openai" / "20260508T130000Z_chatgpt_image_best_available.yaml"
		assert snapshot_path.exists(), f"ChatGPT snapshot missing: {snapshot_path}"

	def test_nano_banana_snapshot_exists(self):
		snapshot_path = REPO_ROOT / "model_guidance_snapshots" / "google" / "20260508T110000Z_nano_banana_best_available.yaml"
		assert snapshot_path.exists(), f"Nano Banana snapshot missing: {snapshot_path}"


class TestSnapshotSchema:
	"""Verify all snapshots validate against model_guidance_snapshot.schema.json."""

	@pytest.fixture
	def schema(self):
		schema_path = REPO_ROOT / "schemas" / "model_guidance_snapshot.schema.json"
		with open(schema_path, "r", encoding="utf-8") as f:
			return json.load(f)

	@pytest.fixture
	def validator(self, schema):
		return jsonschema.Draft202012Validator(schema)

	def _load_snapshot(self, filename: str) -> dict:
		for subdir in ["kling", "midjourney", "openai", "google"]:
			path = REPO_ROOT / "model_guidance_snapshots" / subdir / filename
			if path.exists():
				with open(path, "r", encoding="utf-8") as f:
					return yaml.safe_load(f)
		raise FileNotFoundError(f"Snapshot not found: {filename}")

	def test_kling_snapshot_valid(self, validator):
		snapshot = self._load_snapshot("20260508T140000Z_kling_omni_video_best_available.yaml")
		validator.validate(snapshot)  # Raises ValidationError if invalid

	def test_midjourney_snapshot_valid(self, validator):
		snapshot = self._load_snapshot("20260508T120000Z_midjourney_image_best_available.yaml")
		validator.validate(snapshot)

	def test_chatgpt_snapshot_valid(self, validator):
		snapshot = self._load_snapshot("20260508T130000Z_chatgpt_image_best_available.yaml")
		validator.validate(snapshot)

	def test_nano_banana_snapshot_valid(self, validator):
		snapshot = self._load_snapshot("20260508T110000Z_nano_banana_best_available.yaml")
		validator.validate(snapshot)


class TestSnapshotResolver:
	"""Verify all snapshots resolve through resolve_model_guidance()."""

	def test_kling_resolves(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="kling_omni_video_best_available",
		)
		assert result["resolved_model_name"] == "Kling 3.0 Omni"
		assert result["provider"] == "kling"
		assert result["provider_surface"] in {"api", "web_ui", "manual_external"}

	def test_midjourney_resolves(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="midjourney_image_best_available",
		)
		assert result["resolved_model_name"] == "V8.1"
		assert result["provider"] == "midjourney"
		assert result["provider_surface"] == "web_ui"

	def test_chatgpt_resolves(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="chatgpt_image_best_available",
		)
		assert result["resolved_model_name"] == "gpt-image-2"
		assert result["provider"] == "openai"
		assert result["provider_surface"] == "chatgpt_ui"

	def test_nano_banana_resolves(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="nano_banana_best_available",
		)
		assert "Nano Banana Pro" in result["resolved_model_name"]
		assert "gemini-3-pro-image-preview" in result["resolved_model_name"]
		assert result["provider"] == "google"
		assert result["provider_surface"] == "gemini_app"


class TestSnapshotVerification:
	"""Verify human_verified, expiry, and no placeholder values."""

	def _load_all_snapshots(self) -> dict[str, dict]:
		snapshots = {}
		for subdir in ["kling", "midjourney", "openai", "google"]:
			snapshot_dir = REPO_ROOT / "model_guidance_snapshots" / subdir
			for yaml_file in snapshot_dir.glob("*.yaml"):
				with open(yaml_file, "r", encoding="utf-8") as f:
					snapshots[yaml_file.name] = yaml.safe_load(f)
		return snapshots

	def test_all_human_verified(self):
		snapshots = self._load_all_snapshots()
		for filename, snapshot in snapshots.items():
			assert snapshot.get("human_verified") is True, f"{filename}: human_verified must be true"

	def test_all_not_expired(self):
		snapshots = self._load_all_snapshots()
		now = datetime.now(timezone.utc)
		for filename, snapshot in snapshots.items():
			expires_at_str = snapshot.get("expires_at")
			assert expires_at_str is not None, f"{filename}: expires_at missing"
			expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
			assert expires_at > now, f"{filename}: expires_at must be in future (got {expires_at_str})"

	def test_no_placeholder_model_values(self):
		placeholders = {"TBD", "TODO", "unknown", "", "PLACEHOLDER"}
		snapshots = self._load_all_snapshots()
		for filename, snapshot in snapshots.items():
			for key in ["current_default_model", "latest_available_model", "best_for_this_task"]:
				value = snapshot.get(key)
				assert value not in placeholders, f"{filename}: {key} is placeholder ({value!r})"

	def test_kling_uses_omni_target(self):
		snapshots = self._load_all_snapshots()
		kling_snapshot = next(
			s for name, s in snapshots.items() if "kling" in name.lower()
		)
		assert kling_snapshot.get("internal_model_target") == "kling_omni_video_best_available"

	def test_no_old_kling_target_in_snapshots(self):
		snapshots = self._load_all_snapshots()
		for filename, snapshot in snapshots.items():
			target = snapshot.get("internal_model_target")
			assert target != "kling_video_best_available", (
				f"{filename}: must use kling_omni_video_best_available, not kling_video_best_available"
			)


class TestSnapshotProviderNames:
	"""Verify provider model names appear ONLY in model_guidance_snapshots/**, not elsewhere."""

	PROVIDER_MODEL_NAMES = {
		"Kling 3.0 Omni",
		"V8.1",
		"V7",
		"gpt-image-2",
		"gemini-3-pro-image-preview",
		"Nano Banana Pro",
	}

	def test_provider_names_not_in_adapters(self):
		"""Provider model names must not appear as hardcoded assignments in adapter code."""
		adapter_dir = REPO_ROOT / "scripts" / "agents" / "adapters"
		for py_file in adapter_dir.glob("*.py"):
			if py_file.name == "__pycache__":
				continue
			with open(py_file, "r", encoding="utf-8") as f:
				lines = f.readlines()

			# Check for hardcoded assignments (skip docstrings/comments)
			in_docstring = False
			for i, line in enumerate(lines, 1):
				# Track docstring state
				if '"""' in line or "'''" in line:
					in_docstring = not in_docstring

				if in_docstring or line.strip().startswith("#"):
					continue  # Skip docstrings and comments

				for model_name in self.PROVIDER_MODEL_NAMES:
					# Check for hardcoded assignment patterns
					if f'"{model_name}"' in line or f"'{model_name}'" in line:
						if any(keyword in line for keyword in ["=", "return", "model"]):
							raise AssertionError(
								f"Adapter {py_file.name}:{i} contains hardcoded model name: {model_name!r}\n"
								f"Line: {line.rstrip()}"
							)

	def test_provider_names_not_in_resolver(self):
		"""Provider model names must not appear in resolver source code."""
		resolver_path = REPO_ROOT / "scripts" / "agents" / "model_guidance_resolver.py"
		with open(resolver_path, "r", encoding="utf-8") as f:
			content = f.read()
		for model_name in self.PROVIDER_MODEL_NAMES:
			assert model_name not in content, (
				f"Resolver contains hardcoded model name: {model_name!r}"
			)

	def test_provider_names_appear_in_snapshots(self):
		"""Provider model names MUST appear in snapshot files."""
		snapshots = {}
		for subdir in ["kling", "midjourney", "openai", "google"]:
			snapshot_dir = REPO_ROOT / "model_guidance_snapshots" / subdir
			for yaml_file in snapshot_dir.glob("*.yaml"):
				with open(yaml_file, "r", encoding="utf-8") as f:
					snapshots[yaml_file.name] = yaml.safe_load(f)

		snapshot_text = json.dumps(snapshots)
		for model_name in self.PROVIDER_MODEL_NAMES:
			assert model_name in snapshot_text, (
				f"Provider model name {model_name!r} must appear in at least one snapshot"
			)


class TestSnapshotPathResolution:
	"""Verify resolver can find snapshots by internal_model_target."""

	def test_resolver_finds_kling_snapshot(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="kling_omni_video_best_available",
		)
		snapshot_ref = result["model_guidance_snapshot_ref"]
		assert "kling" in snapshot_ref
		assert "kling_omni_video_best_available" in snapshot_ref or "kling_omni" in snapshot_ref

	def test_resolver_finds_midjourney_snapshot(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="midjourney_image_best_available",
		)
		snapshot_ref = result["model_guidance_snapshot_ref"]
		assert "midjourney" in snapshot_ref

	def test_resolver_finds_chatgpt_snapshot(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="chatgpt_image_best_available",
		)
		snapshot_ref = result["model_guidance_snapshot_ref"]
		assert "openai" in snapshot_ref

	def test_resolver_finds_nano_banana_snapshot(self):
		result = resolve_model_guidance(
			REPO_ROOT,
			internal_model_target="nano_banana_best_available",
		)
		snapshot_ref = result["model_guidance_snapshot_ref"]
		assert "google" in snapshot_ref
