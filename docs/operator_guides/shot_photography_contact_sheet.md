# Shot Photography & Contact Sheet Playbook (Anchor & Animate)

> ⚠️ **HISTORICAL / DEPRECATED for SC0014 (v07).** The still → contact-sheet →
> `anchored_i2v` route below is retired for SC0014: the 22-still pass and contact
> sheets proved too manual. The current route is **text_only literal multi-shot** —
> see [`kling_literal_multishot_playbook.md`](kling_literal_multishot_playbook.md).
> This document is kept for historical reference only.

## 1. Overview

This playbook covers the **Anchor & Animate** production loop for a scene. Every shot is
photographed as a still first (ChatGPT Images 2 with element identity refs), those stills are
assembled into a per-clip contact sheet (storyboard reference), and Kling then receives the
clip's start-frame still plus element refs plus short motion text (`anchored_i2v` mode).

Visual continuity is carried by the images, not by prose. The motion text budget drops to
**< 1800 characters per clip** (hard cap 2500).

**Pipeline order per scene:**

```
for each shot (22 for SC0014):
    generate still → archive --subdir shots

for each clip (8 for SC0014):
    generate contact sheet → archive --subdir contact_sheets
    generate Kling anchored_i2v clip
```

---

## 2. Prerequisites

All elements for the scene must be at `binding_status: created` in
`visual_dev/omni_sets/{scene_id}/element_bindings.yaml`. Run:

```
python scripts/validate_production_records.py --repo-root .
```

Zero issues required before starting still generation.

---

## 3. Step A — Generate shot stills (ChatGPT Images 2)

### 3.1 Read the still prompts

```
prompts/draft/{SCENE_ID}__still-{NN}__v01.yaml
```

Each record's `generation_params` carries:
- `input_reference_images` — the perspective-view local paths to upload
- `archive_filename` — the output filename to use when saving
- `protected_subject_flags` — non-empty for shots containing C08 (infant)

### 3.2 Upload & generate in ChatGPT Images 2

1. Open ChatGPT Images 2 in the browser.
2. Upload the images listed in `input_reference_images` (check local paths in
   `evidence/local_media_indices/`).
3. Paste `prompt_text` verbatim.
4. For shots with `protected_subject_flags: [C08_NO_CONTACT, C08_DISTRESS_OFF_FRAME]`:
   - Verify generated still: infant calm, fully supported, distress off-frame, no contact
     with non-caregiver adults. **Do not proceed if these criteria are not met.**
5. Save the output as the exact `archive_filename` from `generation_params`.

### 3.3 Archive the still

```
python scripts/archive_media.py \
  --repo-root . \
  --project nexuszero \
  --scene  SC0014 \
  --subdir shots \
  --file   /path/to/SC0014_NN_clip-sc0014-NN_shot-sc0014-NN-x.png \
  --media-type image
```

This writes to `archive/nexuszero/SC0014/shots/` (gitignored binary) and appends an entry
to `evidence/local_media_indices/LOCAL_MEDIA_INDEX_{SCENE_ID}_ARCHIVE_V001.yaml`.

### 3.4 Repeat for all shots (scene-global order 01..22 for SC0014)

Keep the global 01..22 order — it drives the frame-chain and contact-sheet upload order.

---

## 4. Step B — Generate contact sheets (ChatGPT Images 2, multi-panel)

### 4.1 Read the contact-sheet prompts

```
prompts/draft/{SCENE_ID}__contact-clip-{NN}__v01.yaml
```

Each record's `generation_params.operator_upload_order` lists the exact archive filenames
for this clip's shots in order. Upload them in that order.

### 4.2 Generate the contact sheet

1. Open ChatGPT Images 2.
2. Upload the stills in `operator_upload_order` sequence (≤ 6 per clip, ≤ 16 total inputs).
3. Paste `prompt_text` verbatim.
4. Save output as `{SCENE_ID}_clip{NN}_contact.png`.

### 4.3 Archive the contact sheet

```
python scripts/archive_media.py \
  --repo-root . \
  --project nexuszero \
  --scene  SC0014 \
  --subdir contact_sheets \
  --file   /path/to/SC0014_clip01_contact.png \
  --media-type image
```

Contact sheets are QC/storyboard references for the operator.  
**Kling receives a contact sheet only if the operator explicitly sets `contact_sheet_ref`.**  
Default is off (`contact_sheet_for_kling_default: off`).

---

## 5. Step C — Generate Kling anchored_i2v clips

### 5.1 Read the Kling prompts

```
prompts/draft/{SCENE_ID}__omni-kling-omni-clip-clip-sc0014-{NN}-safe__v01.yaml
```

Key `generation_params` fields:

| Field | Value |
|---|---|
| `input_mode` | `anchored_i2v` |
| `start_frame_ref` | archive path of the previous clip's last shot still (pass-1) |
| `visual_input_budget.total` | 7 max (1 start-frame + ≤ 6 element slots) |
| `frame_chain_source` | `designed_still_pass1` |
| `required_element_aliases` | list of `@alias` values for this clip's elements |

### 5.2 Upload to Kling VIDEO 3.0 Omni

1. **Start-frame input:** upload the image at `start_frame_ref`.
2. **Element refs:** upload each element's reference image (from KER records listed under
   `required_element_aliases`; priority views per `_CHAR_VIEW_PRIORITY` / `_LOC_VIEW_PRIORITY`).
3. Total visual inputs ≤ 7 (enforced by `visual_input_budget`).
4. Paste `prompt_text` verbatim. **Do not exceed 2500 characters.**
5. For clips containing C08 shots: operator human-approval gate remains in force.

### 5.3 Two-pass frame chain

**Pass 1 (current):** `start_frame_ref` points to the *designed still* of the previous
clip's last shot — the `designed_still_pass1` convention.

**Pass 2 (after takes are selected):** When a Kling take is selected and its last frame is
extracted, write an `extracted_frame_reference` record and update the next clip's manifest
`first_frame_reference` to point to the extracted frame (supersedes pass-1).

---

## 6. Validation

After generating stills and contact sheets:

```
python scripts/validate_production_records.py --repo-root .
```

The `validate_shot_still_coverage` validator checks:

| Error code | What it catches |
|---|---|
| `STILL_MISSING` | A manifest shot has no still_generation prompt |
| `CONTACT_SHEET_MISSING` | A manifest clip has no shot_design prompt |
| `CONTACT_SHEET_ORDER_MISMATCH` | Upload order ≠ manifest shot order |
| `ARCHIVE_FILENAME_DUPLICATE` | Two stills share the same archive filename |
| `VISUAL_BUDGET_EXCEEDED` | anchored_i2v prompt budget > 7 |
| `PROTECTED_FLAGS_MISSING` | C08 shot still missing safety flags |

**Note:** The validator runs only when still_generation or shot_design prompts exist for
the scene. Before any stills are generated it silently skips (no false positives).

---

## 7. Prompt character budget guidance

| Mode | Target | Hard cap |
|---|---|---|
| `text_only` (legacy) | < 2000 chars | 2500 chars |
| `anchored_i2v` | **< 1800 chars** | 2500 chars (fatal on final passes) |

Start-frame visual continuity replaces most of the state-description text, so
`anchored_i2v` prompts should focus only on motion direction and emotional performance.
Entry-state text anchors are suppressed automatically (`suppress_entry_anchors=True`).

---

## 8. Archive path conventions (K4)

| Subdir | Archive path pattern |
|---|---|
| Shot stills | `archive/{project}/{scene}/shots/{filename}` |
| Contact sheets | `archive/{project}/{scene}/contact_sheets/{filename}` |

`shots` and `contact_sheets` are scene-level subcategories, not new media types. The
existing `stage{N}/images|video` path convention for element perspective packs is
unchanged.

---

## 9. Generation script

To regenerate the full v01 anchored package from manifests:

```
python -m scripts.generate_sc0014_v06_anchored --repo-root . [--dry-run]
```

This writes 22 still + 8 contact-sheet + 8 Kling prompts. Run only after all elements are
at `binding_status: created`.
