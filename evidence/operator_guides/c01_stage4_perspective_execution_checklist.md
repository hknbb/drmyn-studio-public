# C01 Stage 4 Perspective Execution Checklist

## Source Lock
- Use C01 FRONT HERO LOCK:
  `external://local_manual/drmyn-studio-images/ChatGPT Image 13 May 2026 15_55_45.png`

## Required Calls
1. `P01 rear_or_side`
2. `P02 three_quarter_left`
3. `P03 right_profile_side`
4. `P04 left_profile_side`

## Rules
- One GPT Images 2 call per perspective.
- Use FRONT HERO LOCK as identity anchor.
- Preserve facial topology, short wavy bob, body proportions, wardrobe/material palette.
- No redesign.
- No costume change.
- No contact sheet.
- No multi-panel output.
- No text/logo/watermark.
- Do not use camera-left/camera-right wording.

## Output Registration After Generation
- Update local media index.
- Update image selection candidates.
- Update perspective QC scaffold.
- Do not set QC score before human review.
- Do not set approved/locked/materialized lifecycle states.

## Validation
- Run `python scripts/validate_production_records.py --repo-root .`
- Run `python scripts/validate_prompt_records.py --repo-root .`
- Run `python -m pytest -q` only if metadata changes touch schema/test paths.
