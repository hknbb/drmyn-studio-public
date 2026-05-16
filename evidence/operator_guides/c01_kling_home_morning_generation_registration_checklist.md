# C01 Kling Home Morning Clean Baseline Checklist

## Status (2026-05-15)
SC0001 Kling/Omni is reset to a clean element-first baseline.

There is currently no active SC0001 SH001 Kling prompt, shot manifest, or
scene element binding set. Do not generate Kling Omni 3 output until the new
three-view element records are authored and the computed manifest gate is
`all_elements_ready`.

## Required Order
1. C01 Nadia: one Midjourney hero reference, then three ChatGPT Images 2 views
   (`front_reference`, `left_reference`, `right_reference`), then QC and Kling
   registration.
2. LOC001 kitchen passage: one Midjourney reference, then three production
   reference views, then QC and Kling registration.
3. PROP003 Vardova frame: one Midjourney reference, then three production
   reference views, then QC and Kling registration.
4. SH001 manifest: declare `all_elements_ready` only when the validator's
   computed gate is also `all_elements_ready`.
5. Kling prompt: generate only v02 alias-only text after the manifest passes.

## Hard Gates
- `gpt_images_perspective_pack.status` must be `review` or better.
- `kling_element_reference.status` must be `review` or better.
- `approval_gate.operator_approved` must be `true`.
- `approval_gate.all_perspectives_score_85_plus` must be `true`.
- Active Kling `prompt_text` may use only registered `@alias` references for
  required elements.

## Validation
- `python scripts/agents/operator_next_step.py --scene SC0001 --repo-root . --format text`
- `python scripts/validate_production_records.py --repo-root .`
- `python scripts/validate_prompt_records.py --repo-root .`
