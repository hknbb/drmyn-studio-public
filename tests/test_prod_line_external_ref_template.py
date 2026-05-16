from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_external_ref_template_contains_four_prompt_ids() -> None:
    template = (
        REPO_ROOT
        / "evidence/templates/GPTIMG2_C01_EXTERNAL_REF_REGISTRATION_TEMPLATE.yaml"
    ).read_text(encoding="utf-8")
    assert "GPTIMG2_C01_P01_REAR_V001" in template
    assert "GPTIMG2_C01_P02_THREE_QUARTER_LEFT_V001" in template
    assert "GPTIMG2_C01_P03_RIGHT_PROFILE_V001" in template
    assert "GPTIMG2_C01_P04_LEFT_PROFILE_V001" in template


def test_external_ref_template_requires_repo_binary_false() -> None:
    template = (
        REPO_ROOT
        / "evidence/templates/GPTIMG2_C01_EXTERNAL_REF_REGISTRATION_TEMPLATE.yaml"
    ).read_text(encoding="utf-8")
    assert template.count("repo_binary_committed: false") == 4


def test_external_ref_checklist_warns_no_binary_commit() -> None:
    guide = (
        REPO_ROOT
        / "evidence/operator_guides/gpt_images_external_ref_replacement_checklist.md"
    ).read_text(encoding="utf-8")
    assert "Generated image binaries must stay outside this repository." in guide
    assert "Do not commit" in guide
