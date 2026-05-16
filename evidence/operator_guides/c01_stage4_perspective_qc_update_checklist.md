# C01 Stage 4 Perspective QC Update Checklist

## Scope Guard
- Metadata-only updates.
- No binaries.
- No schema/validator edits.
- No lifecycle promotion (`approved`/`locked`/`materialized` unchanged).

## Inputs (must already exist)
- `P01 rear_or_side` external output registered.
- `P02 three_quarter_left` external output registered.
- `P03 right_profile_side` external output registered.
- `P04 left_profile_side` external output registered.

## Files Allowed in QC Update PR
- `evidence/perspective_qc/PQC_C01_PERSPECTIVE_PACK_V001.yaml`
- `visual_dev/elements/characters/C01/gptimg2_perspectives/image_selection.yaml`

## Update Rules
1. In `PQC_C01_PERSPECTIVE_PACK_V001.yaml`:
   - Populate per-perspective QC numeric fields.
   - Set `total_score` and `decision` per perspective.
   - Update `gate.can_advance_to_kling_reference` only if gate conditions are truly met.
2. In `image_selection.yaml`:
   - Replace placeholder `quality_scores` with review-based values.
   - Keep `status: candidate` until explicit human selection decision is made.
   - Keep `canonical_images` empty unless explicitly approved in the same review.
3. Keep notes explicit:
   - Mention human QC completion status.
   - Mention if selection/canonical decision is deferred.

## Validation
- Run `python scripts/validate_production_records.py --repo-root .`
- Run `python scripts/validate_prompt_records.py --repo-root .`
- Run `python -m pytest -q` only if changes touch schema/test paths.

## Suggested Branch + PR
- Branch: `chore/c01-stage4-perspective-qc-update`
- PR title: `chore(c01): update Stage 4 perspective QC scores`
- PR body scope line: `metadata-only; no binaries; no lifecycle promotion`
