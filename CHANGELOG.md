# Changelog

## v0.15.0-character-visual-prompt-kit-checkpoint (2026-05-12)

### Summary
- Scientific checkpoint for PROD-LINE-15A-0 and PROD-LINE-15A-1.
- Scope is documentation-only and metadata-only, before real GPT Images 2 external-ref registration.

### Added
- Character visual prompt kit doctrine guide.
- Character visual prompt kits for C01, C02, C03, C04, C05.
- Reusable character visual prompt kit template.

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.
- No production record mutation.

### Next Step
- PROD-LINE-15A write-pass after real C01 GPT Images 2 perspective outputs are available externally and preflight is READY.
## v0.14.0-continuity-alias-checkpoint (2026-05-12)

### Summary
- Scientific checkpoint for PROD-LINE-14A through PROD-LINE-14H.
- Scope is metadata-only governance architecture before PROD-LINE-15 external-output registration.

### Added
- Look-specific Kling element alias architecture and records (`kling_character_look_element`).
- Scene-to-Kling alias resolver and operator hint report export.
- Operator guide append for Omni alias usage rule (`@C##_LOOK_ROLE`).

### Validation Evidence
- `python scripts/validate_production_records.py --repo-root .` -> 76 files scanned, 76 valid, 0 invalid.
- `python -m pytest -q` -> 1357 passed.
- `python scripts/validate_prompt_records.py --repo-root .` -> 7 files validated successfully.
- `python scripts/validators/validate_model_research_gate.py --repo-root . --targets midjourney_image_best_available chatgpt_image_best_available kling_omni_video_best_available` -> 3/3 passed.

### Policy Confirmation
- No binary image/video/audio outputs committed.
- No lifecycle promotion (`approved`, `locked`, `canon_lock`, `materialized`, `selected`, `applied`).
- No real external reference replacement performed at this checkpoint.

### Next Step
- PROD-LINE-15A: C01 GPT Images 2 real external-ref registration preflight (look-target aware).

