import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validators.validate_shot_element_manifest import (
    validate_shot_element_manifest_file,
)


CANONICAL_ID_RE = re.compile(r"(?<!@)\b(?:C\d{2}|LOC\d{3}(?:_[A-Z0-9_]+)?|PROP\d{3}|WD\d{3})\b")


def _load_yaml_mapping(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_scene_element_binding_aliases(repo_root, scene_id):
    bindings_path = repo_root / "visual_dev" / "omni_sets" / scene_id / "element_bindings.yaml"
    if not bindings_path.exists():
        return set()

    aliases = set()
    try:
        with open(bindings_path, "r", encoding="utf-8") as f:
            for doc in yaml.safe_load_all(f):
                if not isinstance(doc, dict):
                    continue
                alias = doc.get("kling_alias")
                if isinstance(alias, str) and alias.startswith("@"):
                    aliases.add(alias)
    except Exception:
        return aliases
    return aliases


def _load_scene_element_binding_docs(repo_root, scene_id):
    bindings_path = repo_root / "visual_dev" / "omni_sets" / scene_id / "element_bindings.yaml"
    if not bindings_path.exists():
        return []

    docs = []
    try:
        with open(bindings_path, "r", encoding="utf-8") as f:
            for doc in yaml.safe_load_all(f):
                if isinstance(doc, dict):
                    docs.append(doc)
    except Exception:
        return docs
    return docs


def _load_canonical_kling_aliases(repo_root):
    aliases = set()
    for path in repo_root.glob("visual_dev/elements/characters/*/kling_elements/*.yaml"):
        data = _load_yaml_mapping(path)
        alias = data.get("kling_element_alias")
        if isinstance(alias, str) and alias.startswith("@"):
            aliases.add(alias)
    return aliases


def _string_items(value):
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _camel_words(value):
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", value)
    return [word for word in words if word]


def _raw_name_candidates_from_bindings(bindings):
    candidates = set()
    for binding in bindings:
        alias = binding.get("kling_alias")
        if isinstance(alias, str) and alias.startswith("@") and len(alias) > 1:
            bare = alias[1:]
            candidates.add(bare)
            words = _camel_words(bare)
            if words:
                spaced = " ".join(words)
                candidates.add(spaced)
                candidates.add(words[0])
                if len(words) >= 2:
                    candidates.add(" ".join(words[:2]))

        display_name = binding.get("display_name")
        if isinstance(display_name, str) and display_name.strip():
            candidates.add(display_name.strip())

    return {candidate for candidate in candidates if len(candidate) >= 3}


def _model_facing_text_items(instance):
    for field_name in ("prompt_text", "negative_prompt"):
        value = instance.get(field_name)
        if isinstance(value, str):
            yield field_name, value


def _contains_unescaped_raw_name(text, raw_name):
    return re.search(rf"(?<!@)\b{re.escape(raw_name)}\b", text) is not None


def _prompt_semantic_errors(instance, repo_root):
    if not isinstance(instance, dict):
        return []

    target_models = instance.get("target_models") or []
    if "kling_omni" not in target_models:
        return []

    params = instance.get("generation_params") or {}
    if not isinstance(params, dict):
        return []

    scene_id = instance.get("scene_id")
    if not isinstance(scene_id, str) or not scene_id:
        return []

    is_deprecated = (
        instance.get("lifecycle_stage") == "deprecated"
        or instance.get("status") == "deprecated"
    )
    binding_docs = _load_scene_element_binding_docs(repo_root, scene_id)
    canonical_aliases = _load_canonical_kling_aliases(repo_root)
    platform_aliases = {
        doc.get("kling_alias")
        for doc in binding_docs
        if isinstance(doc.get("kling_alias"), str)
        and str(doc.get("kling_alias")).startswith("@")
    }
    all_aliases = canonical_aliases | platform_aliases
    errors = []

    manifest_ref = params.get("shot_element_manifest_ref")
    manifest_data = None
    if not is_deprecated and not (isinstance(manifest_ref, str) and manifest_ref.strip()):
        errors.append(
            "generation_params.shot_element_manifest_ref is required for active "
            "Kling Omni prompts"
        )

    if not is_deprecated and params.get("not_attached_as_kling_elements") is not None:
        errors.append(
            "generation_params.not_attached_as_kling_elements is not allowed for "
            "active Kling Omni prompts; use environmental_only_allowed_ids in the "
            "manifest instead"
        )

    if isinstance(manifest_ref, str) and manifest_ref.strip():
        manifest_path = repo_root / manifest_ref
        if not manifest_path.exists():
            errors.append(
                f"generation_params.shot_element_manifest_ref not found: {manifest_ref}"
            )
        else:
            manifest_issues = validate_shot_element_manifest_file(
                manifest_path, repo_root, report_causes=True
            )
            errors.extend(
                f"shot_element_manifest_ref {issue.field_path}: {issue.message}"
                for issue in manifest_issues
            )
            manifest_data = _load_yaml_mapping(manifest_path)
            declared_gate = manifest_data.get("gate_status") if manifest_data else None
            if declared_gate != "all_elements_ready":
                errors.append(
                    f"shot_element_manifest_ref gate_status is {declared_gate!r}; "
                    "Kling Omni prompt synthesis requires 'all_elements_ready'"
                )

        if params.get("not_attached_as_kling_elements") is not None:
            errors.append(
                "generation_params.not_attached_as_kling_elements is not allowed when "
                "shot_element_manifest_ref is present; use environmental_only_allowed_ids "
                "in the manifest instead"
            )

    not_attached = set(_string_items(params.get("not_attached_as_kling_elements")))

    required_aliases = _string_items(params.get("required_element_aliases"))
    for alias in required_aliases:
        if not alias.startswith("@"):
            continue
        if alias not in all_aliases:
            errors.append(
                f"generation_params.required_element_aliases contains unresolved alias {alias!r}; "
                "alias must exist in scene element_bindings.yaml or a kling_character_look_element record"
            )
        if alias in not_attached:
            errors.append(
                f"generation_params.required_element_aliases contains {alias!r}, "
                "but the same value is listed in not_attached_as_kling_elements"
            )

    attached_refs = params.get("attached_element_refs")
    if isinstance(attached_refs, list):
        for index, ref in enumerate(attached_refs):
            if not isinstance(ref, dict):
                continue
            repo_alias = ref.get("repo_alias")
            if isinstance(repo_alias, str) and repo_alias.startswith("@"):
                if repo_alias not in canonical_aliases:
                    errors.append(
                        f"generation_params.attached_element_refs[{index}].repo_alias "
                        f"{repo_alias!r} does not resolve to a kling_character_look_element alias"
                    )
                if repo_alias in not_attached:
                    errors.append(
                        f"generation_params.attached_element_refs[{index}].repo_alias "
                        f"{repo_alias!r} is also listed in not_attached_as_kling_elements"
                    )

            platform_alias = ref.get("platform_alias")
            if isinstance(platform_alias, str) and platform_alias.startswith("@"):
                if platform_alias not in platform_aliases:
                    errors.append(
                        f"generation_params.attached_element_refs[{index}].platform_alias "
                        f"{platform_alias!r} does not resolve to this scene's element_bindings.yaml"
                    )
                if platform_alias in not_attached:
                    errors.append(
                        f"generation_params.attached_element_refs[{index}].platform_alias "
                        f"{platform_alias!r} is also listed in not_attached_as_kling_elements"
                    )

    context_aliases = _string_items(params.get("required_context_aliases"))
    for alias in context_aliases:
        if not alias.startswith("@"):
            continue
        if alias not in platform_aliases:
            errors.append(
                f"generation_params.required_context_aliases contains unresolved alias {alias!r}; "
                "context aliases must resolve through this scene's element_bindings.yaml"
            )
        if alias in not_attached:
            errors.append(
                f"generation_params.required_context_aliases contains {alias!r}, "
                "but the same value is listed in not_attached_as_kling_elements"
            )

    prop_cues = _string_items(params.get("required_prop_cue"))
    for cue in prop_cues:
        if cue in not_attached:
            errors.append(
                f"generation_params.required_prop_cue contains {cue!r}, "
                "but the same value is listed in not_attached_as_kling_elements"
            )

    if manifest_data:
        environmental_allowed = set(
            _string_items(manifest_data.get("environmental_only_allowed_ids"))
        )
        for field_name in ("text_context_refs", "visual_cue_refs"):
            for item in _string_items(params.get(field_name)):
                if item not in environmental_allowed:
                    errors.append(
                        f"generation_params.{field_name} contains {item!r}, "
                        "but the shot element manifest does not list it in "
                        "environmental_only_allowed_ids"
                    )

    raw_name_candidates = _raw_name_candidates_from_bindings(binding_docs)
    for field_name, text in _model_facing_text_items(instance):
        canonical_matches = sorted(set(CANONICAL_ID_RE.findall(text)))
        if canonical_matches:
            errors.append(
                f"{field_name} leaks repo-canonical element ids: "
                f"{', '.join(canonical_matches)}"
            )
        leaked_names = sorted(
            candidate
            for candidate in raw_name_candidates
            if _contains_unescaped_raw_name(text, candidate)
        )
        if leaked_names:
            errors.append(
                f"{field_name} leaks raw element names instead of @alias: "
                f"{', '.join(leaked_names)}"
            )

    return errors


def parse_args():
    parser = argparse.ArgumentParser(description="Validate prompt records against schema.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root directory"
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("evidence/validation_reports/prompt_records_validation_report.json"),
        help="Output JSON report path"
    )
    return parser.parse_args()


def main(args=None):
    if args is None:
        args = parse_args()

    repo_root = args.repo_root
    report_path = repo_root / args.report_json if not args.report_json.is_absolute() else args.report_json

    schema_path = repo_root / "schemas" / "prompt_record.schema.json"
    if not schema_path.exists():
        print(f"Error: Schema not found at {schema_path}")
        return 1

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    validator = Draft202012Validator(schema)

    prompt_dirs = ["draft", "review", "approved", "locked"]
    yaml_files = []
    for d in prompt_dirs:
        dir_path = repo_root / "prompts" / d
        if dir_path.exists():
            yaml_files.extend(list(dir_path.glob("*.yaml")))

    report = {
        "total_files_scanned": len(yaml_files),
        "files_with_errors": 0,
        "errors": {}
    }

    if not yaml_files:
        print("0 files validated.")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return 0

    has_errors = False
    for file_path in yaml_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                instance = yaml.safe_load(f)

            file_errors = [
                f"{e.json_path}: {e.message}" for e in validator.iter_errors(instance)
            ]
            file_errors.extend(_prompt_semantic_errors(instance, repo_root))
            if file_errors:
                has_errors = True
                report["files_with_errors"] += 1
                report["errors"][file_path.relative_to(repo_root).as_posix()] = file_errors
        except Exception as e:
            has_errors = True
            report["files_with_errors"] += 1
            report["errors"][file_path.relative_to(repo_root).as_posix()] = [
                f"File parsing error: {str(e)}"
            ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if has_errors:
        print(f"Validation failed. See {report_path} for details.")
        return 1

    print(f"{len(yaml_files)} files validated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
