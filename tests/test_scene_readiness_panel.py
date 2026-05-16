from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.copilot_dashboard import scene_readiness_panel  # noqa: E402


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_yaml_multi(path: Path, docs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")


def _ready_kling_reference() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "kling_element_reference_record",
        "kling_element_reference_id": "KLING_REF_C01_V001",
        "status": "review",
        "element_id": "C01",
        "element_type": "character",
        "source_midjourney_reference": {
            "reference_id": "MJ_ELEMENT_C01_HERO_LOCKED_V001",
            "prompt_id": "MJ_PROMPT_C01_HERO_LOCKED_V001",
        },
        "gpt_images_2_perspectives": {
            "front_reference": "GPTIMG2_C01_FRONT_REFERENCE_V002",
            "left_reference": "GPTIMG2_C01_LEFT_REFERENCE_V002",
            "right_reference": "GPTIMG2_C01_RIGHT_REFERENCE_V002",
        },
        "continuity_anchors": ["identity"],
        "approval_gate": {
            "all_perspectives_score_85_plus": True,
            "operator_approved": True,
            "operator_session_ref": "OP-TEST",
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }


def _ready_gpt_pack() -> dict:
    return {
        "schema_version": "0.x-draft",
        "record_type": "gpt_images_perspective_pack",
        "prompt_pack_id": "GPTIMG2_C01_PERSPECTIVE_PACK_V002",
        "status": "review",
        "source_reference_id": "MJ_ELEMENT_C01_HERO_LOCKED_V002",
        "target_model": "gpt_images_2",
        "target_role": "multi_perspective_element_expander",
        "element_id": "C01",
        "element_type": "character",
        "shared_preservation_instruction": "Preserve identity.",
        "perspective_policy": "three_view_no_rear",
        "prompts": [
            {
                "prompt_id": "GPTIMG2_C01_FRONT_REFERENCE_V002",
                "perspective": "front_reference",
                "prompt_text": "Front full-body studio reference.",
                "constraints": ["single character only"],
                "expected_output": {"asset_type": "still"},
            },
            {
                "prompt_id": "GPTIMG2_C01_LEFT_REFERENCE_V002",
                "perspective": "left_reference",
                "prompt_text": "Left profile studio reference.",
                "constraints": ["single character only"],
                "expected_output": {"asset_type": "still"},
            },
            {
                "prompt_id": "GPTIMG2_C01_RIGHT_REFERENCE_V002",
                "perspective": "right_reference",
                "prompt_text": "Right profile studio reference.",
                "constraints": ["single character only"],
                "expected_output": {"asset_type": "still"},
            },
        ],
        "qc_gate": {
            "minimum_score": 85,
            "all_perspectives_required": True,
            "failed_perspective_revision_only": True,
        },
        "downstream_use": ["kling_omni_3_shot_prompt"],
    }


def _scaffold_ready_scene(repo_root: Path) -> None:
    _write_yaml_multi(
        repo_root / "visual_dev" / "omni_sets" / "SC0001" / "element_bindings.yaml",
        [
            {
                "schema_version": "0.x-draft",
                "record_type": "element_binding",
                "element_id": "C01",
                "element_type": "character",
                "kling_alias": "@Nadia",
                "binding_status": "created",
            }
        ],
    )
    element_root = repo_root / "visual_dev" / "elements" / "characters" / "C01"
    _write_yaml(element_root / "pack_manifest.yaml", {"element_id": "C01"})
    _write_yaml(element_root / "gpt_images_perspective_pack.yaml", _ready_gpt_pack())
    _write_yaml(element_root / "kling_element_reference.yaml", _ready_kling_reference())
    _write_yaml(
        repo_root
        / "visual_dev"
        / "omni_sets"
        / "SC0001"
        / "shot_element_manifests"
        / "SH001.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "shot_element_manifest",
            "manifest_id": "MANIFEST_SC0001_SH001_V001",
            "scene_id": "SC0001",
            "shot_id": "SH001",
            "required_elements": [
                {
                    "element_id": "C01",
                    "element_type": "character",
                    "role": "primary_subject",
                    "registration_state_required": "created",
                }
            ],
            "environmental_only_allowed_ids": [],
            "gate_status": "all_elements_ready",
        },
    )


def _scaffold_blocked_scene(repo_root: Path) -> None:
    _write_yaml_multi(
        repo_root / "visual_dev" / "omni_sets" / "SC0001" / "element_bindings.yaml",
        [
            {
                "schema_version": "0.x-draft",
                "record_type": "element_binding",
                "element_id": "C01",
                "element_type": "character",
                "kling_alias": "@Nadia",
                "binding_status": "planned",
            }
        ],
    )
    element_root = repo_root / "visual_dev" / "elements" / "characters" / "C01"
    _write_yaml(element_root / "pack_manifest.yaml", {"element_id": "C01"})
    _write_yaml(element_root / "gpt_images_perspective_pack.yaml", _ready_gpt_pack())
    ref = _ready_kling_reference()
    ref["status"] = "draft"
    _write_yaml(element_root / "kling_element_reference.yaml", ref)
    _write_yaml(
        repo_root
        / "visual_dev"
        / "omni_sets"
        / "SC0001"
        / "shot_element_manifests"
        / "SH001.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "shot_element_manifest",
            "manifest_id": "MANIFEST_SC0001_SH001_V001",
            "scene_id": "SC0001",
            "shot_id": "SH001",
            "required_elements": [
                {
                    "element_id": "C01",
                    "element_type": "character",
                    "role": "primary_subject",
                    "registration_state_required": "created",
                }
            ],
            "environmental_only_allowed_ids": [],
            "gate_status": "blocked",
        },
    )


def _scaffold_mixed_scene_with_pending_empty_shot(repo_root: Path) -> None:
    _scaffold_ready_scene(repo_root)
    _write_yaml(
        repo_root
        / "visual_dev"
        / "omni_sets"
        / "SC0001"
        / "shot_element_manifests"
        / "SH002.yaml",
        {
            "schema_version": "0.x-draft",
            "record_type": "shot_element_manifest",
            "manifest_id": "MANIFEST_SC0001_SH002_V001",
            "scene_id": "SC0001",
            "shot_id": "SH002",
            "required_elements": [],
            "environmental_only_allowed_ids": [],
            "gate_status": "pending",
        },
    )


@dataclass
class FakeColumn:
    metric_calls: list[tuple[str, int]] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)

    def metric(self, label: str, value: int) -> None:
        self.metric_calls.append((label, value))

    def write(self, message: str) -> None:
        self.writes.append(message)


@dataclass
class FakeExpander:
    title: str
    writes: list[str] = field(default_factory=list)

    def __enter__(self) -> "FakeExpander":
        return self

    def __exit__(self, *args) -> None:  # noqa: ANN002
        return None

    def write(self, message: str) -> None:
        self.writes.append(message)


@dataclass
class FakeStreamlit:
    headers: list[str] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)
    subheaders: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    successes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    dataframes: list[list[dict[str, object]]] = field(default_factory=list)
    selectbox_default: str | None = None
    columns_returned: list[list[FakeColumn]] = field(default_factory=list)
    expanders: list[FakeExpander] = field(default_factory=list)

    def header(self, message: str) -> None:
        self.headers.append(message)

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def subheader(self, message: str) -> None:
        self.subheaders.append(message)

    def write(self, message: object) -> None:
        self.writes.append(str(message))

    def success(self, message: str) -> None:
        self.successes.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def info(self, message: str) -> None:
        self.infos.append(message)

    def dataframe(self, rows, hide_index=False, use_container_width=False):  # noqa: ARG002, ANN001
        self.dataframes.append(list(rows))

    def selectbox(self, label, options, index=0, key=None):  # noqa: ARG002, ANN001
        return options[index]

    def columns(self, n):  # noqa: ANN001
        cols = [FakeColumn() for _ in range(n)]
        self.columns_returned.append(cols)
        return cols

    def expander(self, title: str) -> FakeExpander:
        expander = FakeExpander(title=title)
        self.expanders.append(expander)
        return expander


def test_panel_handles_empty_repo(tmp_path: Path) -> None:
    fake = FakeStreamlit()

    scene_readiness_panel.render_panel(fake, tmp_path)

    assert any("No `visual_dev/omni_sets/SC####`" in msg for msg in fake.writes)
    assert fake.headers == ["Scene Readiness"]


def test_panel_renders_ready_scene_success(tmp_path: Path) -> None:
    _scaffold_ready_scene(tmp_path)
    fake = FakeStreamlit()

    scene_readiness_panel.render_panel(fake, tmp_path)

    assert fake.successes, "Ready scene must surface a success banner"
    assert "Kling Omni adapter may synthesize" in fake.successes[0]
    assert fake.errors == []
    metric_labels = [
        label
        for cols in fake.columns_returned
        for col in cols
        for label, _ in col.metric_calls
    ]
    assert "Ready" in metric_labels
    assert "Blocking" in metric_labels
    assert fake.dataframes, "Element rows table should be rendered"


def test_panel_renders_blocking_scene_with_next_steps(tmp_path: Path) -> None:
    _scaffold_blocked_scene(tmp_path)
    fake = FakeStreamlit()

    scene_readiness_panel.render_panel(fake, tmp_path)

    assert fake.errors, "Blocking scene must surface an error banner"
    assert any("Readiness gate blocked" in msg for msg in fake.errors)
    assert fake.expanders, "Blocker expanders must be rendered"
    # Writes inside `with st.expander(): st.write(...)` land on the
    # FakeStreamlit's main writes list (mirrors Streamlit's context-scoped
    # capture; our fake does not re-route into the expander).
    assert any("**Blockers:**" in w for w in fake.writes)
    assert any("**Next steps:**" in w for w in fake.writes)


def test_panel_does_not_mark_scene_ready_when_any_shot_gate_is_pending(tmp_path: Path) -> None:
    _scaffold_mixed_scene_with_pending_empty_shot(tmp_path)
    fake = FakeStreamlit()

    scene_readiness_panel.render_panel(fake, tmp_path)

    assert fake.successes == []
    assert fake.errors, "Scene with pending/empty manifest shot must block readiness"
    assert any("shot(s) are not all_elements_ready" in msg for msg in fake.errors)


def test_list_known_scene_ids_filters_to_sc_prefix(tmp_path: Path) -> None:
    (tmp_path / "visual_dev" / "omni_sets" / "SC0001").mkdir(parents=True)
    (tmp_path / "visual_dev" / "omni_sets" / "SC0050").mkdir(parents=True)
    (tmp_path / "visual_dev" / "omni_sets" / "not_a_scene").mkdir(parents=True)

    scene_ids = scene_readiness_panel.list_known_scene_ids(tmp_path)

    assert scene_ids == ["SC0001", "SC0050"]
