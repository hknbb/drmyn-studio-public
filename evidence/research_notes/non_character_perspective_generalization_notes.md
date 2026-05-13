# Non-Character Perspective Pack Generalization (Research Notes)

## Purpose
This document records the forward-looking framework for extending the Stage 4 anatomy-anchored separate-call paradigm to non-character element types (wardrobe, prop, location). It is **research and planning only** - no schema, validator, or production record is touched by it.

## Scope
- Forward-looking framework documentation
- Web research summary
- Candidate future perspective enum sets (subject to schema review)
- Element-specific landmark anchor formulae
- Future PR roadmap

This file is intentionally non-binding. Concrete schema and pack records will be introduced in PROD-LINE-15A-6 / 15A-7 / 15A-8.

## Generalization Principle

Similar directional ambiguity can appear in symmetric or near-symmetric non-character elements when opposing views are requested in one prompt. The Stage 4 character fix (separate-call generation + anatomy-anchored disambiguation + hero-lock reference) applies analogously to wardrobe, prop, and location packs.

Element anchor map (high level):

| Element type | Anchor candidates | Mirror-pair risk surface |
|---|---|---|
| Character (implemented) | ear, shoulder, cheek, hair silhouette | three-quarter left vs right, profile vs profile |
| Wardrobe | lapel, cuff, pocket, seam, label, closure direction | front/back of asymmetric closures, sleeve orientation |
| Prop | handle, logo, asymmetric edge, material feature, scale reference | object rotation around vertical axis |
| Location | doorway, window, fireplace, furniture placement | room rotation around vertical axis |

## Candidate Future Perspective Sets (subject to schema review)

### Wardrobe candidates
- `flat_lay` - garment laid flat on a featureless backdrop, top-down
- `on_mannequin_front` - garment on featureless headless mannequin, front
- `on_mannequin_back` - same mannequin, back view
- `material_detail` - fabric texture close-up

### Prop candidates
- `ortho_front` - strict front orthographic, neutral backdrop
- `ortho_side` - strict 90-degree side orthographic (asymmetric landmark visible)
- `ortho_rear` - strict rear orthographic
- `top_orthographic` - strict top-down orthographic

For asymmetric props, prompts must include landmark anchor (for example, "handle visible on the character-left or character-right side of the visible face").

### Location candidates
Existing schema enums likely sufficient:
- `front_hero` (or `establishing` if added) - establishing hero shot, primary landmark centered
- `reverse_angle` - camera rotated 180 degrees, primary landmark behind camera
- `side_depth` - camera rotated 90 degrees, secondary landmark continuity
- `detail_or_threshold` - tight detail of threshold landmark

No new enum likely needed for location.

## Stage 3 Terminology Note

Hero lock terminology generalizes as **"Stage 3 FRONT HERO LOCK / equivalent element hero lock"**:
- Character: FRONT HERO LOCK
- Wardrobe: garment hero reference
- Prop: object hero reference
- Location: establishing hero shot

## Web Research Findings

(Non-authoritative; informs future PR design only.)

- **Wardrobe / e-commerce:** GPT Image 2 product photography is the model's most reliable category. Flat-lay + on-mannequin front/back combination produces the most stable garment turnaround. Sources: Atlas Cloud, Uwear.ai, Photoroom (2026 guides).
- **Prop / orthographic:** Orthographic view generators (Krea, PixelLab, Anifusion) achieve highest stability with strict front/side/top references and consistent lighting. ControlNet or seed locking improves pose accuracy.
- **Location / environment:** ArchiVinci Panorama Generator, DiT360, Skybox AI offer 360-degree panorama generation, but production locking is more stable with sequential separate-angle workflow (nat.io 2026: "build the location first, treat environment generation like set design"). Seedance 2.0 cinematic-consistency models support reference-anchored multi-shot continuity.

Core common pattern across all three element types: **landmark anchoring + sequential separate calls + hero-lock reference**.

## Future PR Roadmap

| PR | Element type | Scope |
|---|---|---|
| PROD-LINE-15A-5 | character downstream harmonization | migrate kling_elements, image_selection, perspective_qc, element_view_plan for C01-C05 to new key set |
| PROD-LINE-15A-6 | wardrobe | schema enum additions + wardrobe doctrine kit + first WDXX perspective_pack record |
| PROD-LINE-15A-7 | prop | schema enum additions + prop doctrine kit + first PROPXX perspective_pack record |
| PROD-LINE-15A-8 | location | doctrine kit + first LOCXXX perspective_pack record (likely reuses existing enums) |

Each future PR is additive at the schema level; historical enum values remain valid.

## Cross-references

- Doctrine: `evidence/operator_guides/character_visual_prompt_kit_doctrine.md` -> "Element-Type Generalization (Forward-Looking)"
- Schema: `schemas/gpt_images_perspective_pack.schema.json` (`element_type` enum already supports character/location/prop/wardrobe)
