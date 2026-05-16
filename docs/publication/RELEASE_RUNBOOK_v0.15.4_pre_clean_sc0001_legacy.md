# v0.15.4 Pre-Clean SC0001 Legacy Runbook

Private checkpoint tag: `v0.15.4-pre-clean-sc0001-legacy`

This checkpoint preserves the legacy SC0001 Kling/Omni metadata state before
the clean element-first baseline reset. The clean reset intentionally removes
active SC0001 Kling draft prompts, the SH001 shot manifest, SC0001 active
element bindings, and partial LOC001/PROP003 Kling backfill records from the
active repository tree. These records are not migrated because PR-0 changes the
required element pipeline from legacy four-view packs to the new three-view
element-first policy.

The reset keeps canonical planning records, source notes, schemas, release
metadata, and non-SC0001 records. If the old state is needed for audit or
comparison, recover it from this tag rather than reintroducing the partial
records into the active baseline.

Post-clean target checkpoint: `v0.16.0-clean-element-first-baseline`

