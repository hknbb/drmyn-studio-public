# C01 Kling Prompt Readiness Final Checklist

## Purpose
Final operator checklist before generating Kling Omni 3 prompts or video outputs for C01 Nadia.

## Preconditions
- C01 has one Midjourney hero/reference output registered externally.
- ChatGPT Images 2 has exactly three externally registered views:
  `front_reference`, `left_reference`, and `right_reference`.
- All three views passed the QC threshold.
- Human selection gate completed with selected three-view perspective set.
- `kling_element_reference.yaml` approval gate is ready.
- New Kling look elements reference the current three-view pack.

## Allowed Next Work
- Prepare Kling Omni 3 prompt drafts only after a shot manifest computes to
  `all_elements_ready`.
- Reference selected three-view perspective set as character continuity support.
- Use registered Kling `@alias` values only in model-facing prompt text.

## Forbidden In This Checklist PR
- No generated Kling video output.
- No image/video/audio binaries.
- No lifecycle promotion to approved/locked/materialized.
- No QC score mutation.
- No canonical_images mutation.
- No bypassing schema or validator gates.

## Required Language
Use "selected three-view perspective set".
Do not call the set canonical unless a future schema-supported canonicalization PR explicitly permits it.

## Validation
- `python scripts/validate_production_records.py --repo-root .`
- `python scripts/validate_prompt_records.py --repo-root .`
