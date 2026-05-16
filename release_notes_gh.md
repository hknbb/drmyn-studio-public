## v0.16.2 — Readiness-Gated Omni 3 Dialogue Rendering + SC0001 Canon Selection

**Checkpoint date:** 2026-05-16 | **Release type:** Metadata-only scientific software checkpoint (no binary outputs)

### What this release adds

**Kling Omni 3 native-audio dialogue rendering infrastructure** — Three-PR patch (guidance refresh → adapter implementation → suppressed-path proof):
- Verified Kling 3.0 Omni native-audio syntax: in-prompt, action-first, `@alias (tone): "line"` format, temporal connectors
- New `audio_plan` component (position #8): renders `@alias`-keyed dialogue when speakers are `native_audio_readiness: ready`; emits exact suppression note when blocked
- Raw `SPEAKER: "..."` cues stripped from `prompt_action`; explicit `dialogue_line_ids` scoping prevents beat-overlap over-inclusion
- SC0001 dry-run proof confirms blocked path: suppression note present, zero line text, zero canonical ID leak
- 8 new tests; 1408 total pass

**SC0001 SH001 TAKE002 canon selection** — Element-first generation of SC0001's first shot with `@Nadia`, `@ValeResidenceKitchenPassage`, `@VardovaFrame`; TAKE002 selected (QC 88/100); locked metadata-only, no binary committed.

**Additional:** PROP003 perspective pack + QC, 4 new schemas, 98 production records valid.

### What this release does NOT include

C03 Birta element, real dialogue generation (blocked), SC0001 video binary (external).

**Date:** 2026-05-12

### Scope
- ✓ Character identity anchor schema and foundational records (C01–C05)
- ✓ Character look variant continuity governance (role-based dynamic look counts)
- ✓ Scene-to-character-look mapping for pilot-canon window (SC0001–SC0009)
- ✓ Look-specific Kling/Omni element alias architecture (@C##_LOOK_ROLE registry)
- ✓ Scene→look→alias resolver utility and operator hint report generation
- ⚠️ Canon boundary: SC0001–SC0009 only (KNOWN canon). SC0010+ deferred to PROD-LINE-16+ after canon hydration.

### Validation Evidence
- Production records: 76 scanned, 76 valid, 0 invalid
- Test suite: 1357 passed
- Prompt records: 7 files validated
- Model research gates: 3/3 targets passed (Midjourney, ChatGPT Image, Kling Omni)

### Governance Confirmation
- ✓ Metadata-only changes (no binaries)
- ✓ No lifecycle promotion (all new records remain in draft status)
- ✓ No real external-ref replacement (pending_external://... references retained)
- ✓ No perspective QC score population
- ✓ All validation gates passed; no deprecated lifecycle keys used

### Next Recommended Step
**PROD-LINE-15A preflight** (no write-pass):
- Verify four GPT Images 2 perspective outputs exist externally for C01–C05 locked heroes
- Verify image_selection / local_media_index consistency across character records
- Verify single look target alignment (do not mix HOME_MORNING and NIGHT_TIRED in one pack for Kling)

### Citation
See [`CITATION.cff`](CITATION.cff) for full citation metadata. For journal/publication cite as:

Babacan, H. (2026). DRMYN Studio: Repository-Native Continuity and Look-Specific Alias Governance for AI-Assisted Film Production (Version 0.14.0-continuity-alias-checkpoint) [Computer software]. https://github.com/hknbb/drmyn-studio-public/releases/tag/v0.14.0-continuity-alias-checkpoint

**DOI:** https://doi.org/10.5281/zenodo.20237165
