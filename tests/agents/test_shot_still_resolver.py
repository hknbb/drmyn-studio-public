"""
Tests for scripts/agents/shot_still_resolver.py

Validates:
1. SC0014 resolves to exactly 22 shots (8 clips, 2-4 shots each)
2. Global indices are 1-based and sequential (no gaps)
3. Archive filenames follow the SC0014_{NN:02d}_{clip-slug}_{shot-slug}.png pattern
4. Clips appear in sorted manifest order (CLIP_01 before CLIP_02, etc.)
5. required_element_ids are threaded through to each entry
6. C08 element refs carry protected_subject_flags
7. archive filename helper produces correct slugs from canonical IDs
8. KER records are resolved to ElementRef objects (no crash on missing LMI entries)
9. Multiple KER records for same element_id (C10 carrier+holder) both resolved
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.agents.shot_still_resolver import (
    ShotStillResolver,
    _build_archive_filename,
)

REPO_ROOT = Path(__file__).parent.parent.parent
SC0014_MANIFEST_DIR = REPO_ROOT / "planning" / "scenes" / "SC0014" / "manifests"

# -------------------------------------------------------------------------
# Archive filename helper
# -------------------------------------------------------------------------

def test_archive_filename_format_basic():
    fn = _build_archive_filename("SC0014", 1, "CLIP_SC0014_01", "SHOT_SC0014_01_A")
    assert fn == "SC0014_01_clip-sc0014-01_shot-sc0014-01-a.png"


def test_archive_filename_two_digit_index():
    fn = _build_archive_filename("SC0014", 10, "CLIP_SC0014_03", "SHOT_SC0014_03_C")
    assert fn == "SC0014_10_clip-sc0014-03_shot-sc0014-03-c.png"


def test_archive_filename_index_zero_padded():
    fn = _build_archive_filename("SC0014", 5, "CLIP_SC0014_02", "SHOT_SC0014_02_B")
    assert fn == "SC0014_05_clip-sc0014-02_shot-sc0014-02-b.png"


# -------------------------------------------------------------------------
# Full SC0014 resolution
# -------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sc0014_entries():
    resolver = ShotStillResolver(repo_root=REPO_ROOT, scene_id="SC0014")
    return resolver.resolve()


def test_sc0014_total_shot_count(sc0014_entries):
    assert len(sc0014_entries) == 22, (
        f"Expected 22 shots for SC0014, got {len(sc0014_entries)}"
    )


def test_sc0014_global_indices_are_sequential(sc0014_entries):
    indices = [e.global_index for e in sc0014_entries]
    assert indices == list(range(1, len(sc0014_entries) + 1))


def test_sc0014_clip_order_ascending(sc0014_entries):
    clip_ids = [e.clip_id for e in sc0014_entries]
    # clip_id changes should be monotonically non-decreasing when sorted
    clip_nums = [int(cid.split("_")[-1]) for cid in clip_ids]
    assert clip_nums == sorted(clip_nums)


def test_sc0014_first_shot_is_clip01(sc0014_entries):
    assert sc0014_entries[0].clip_id == "CLIP_SC0014_01"


def test_sc0014_last_shot_is_clip08(sc0014_entries):
    assert sc0014_entries[-1].clip_id == "CLIP_SC0014_08"


def test_sc0014_archive_filenames_unique(sc0014_entries):
    filenames = [e.archive_filename for e in sc0014_entries]
    assert len(filenames) == len(set(filenames)), "Duplicate archive filenames detected"


def test_sc0014_archive_filename_pattern(sc0014_entries):
    import re
    pattern = re.compile(r"^SC0014_\d{2}_clip-sc0014-\d{2}_shot-sc0014-\d{2}-[a-z]\.png$")
    for entry in sc0014_entries:
        assert pattern.match(entry.archive_filename), (
            f"Archive filename does not match pattern: {entry.archive_filename}"
        )


def test_sc0014_first_entry_archive_filename(sc0014_entries):
    assert sc0014_entries[0].archive_filename == "SC0014_01_clip-sc0014-01_shot-sc0014-01-a.png"


def test_sc0014_required_element_ids_not_empty(sc0014_entries):
    for entry in sc0014_entries:
        assert entry.required_element_ids, (
            f"Shot {entry.shot_id} has no required_element_ids"
        )


def test_sc0014_c08_shots_have_protected_flags(sc0014_entries):
    c08_entries = [e for e in sc0014_entries if "C08" in e.required_element_ids]
    assert c08_entries, "Expected shots with C08 in required_element_ids"
    for entry in c08_entries:
        c08_refs = [r for r in entry.element_refs if r.element_id == "C08"]
        assert c08_refs, f"C08 element_ref missing in shot {entry.shot_id}"
        for ref in c08_refs:
            assert "C08_NO_CONTACT" in ref.protected_subject_flags
            assert "C08_DISTRESS_OFF_FRAME" in ref.protected_subject_flags


def test_sc0014_c10_yields_two_ker_records(sc0014_entries):
    c10_entries = [e for e in sc0014_entries if "C10" in e.required_element_ids]
    assert c10_entries, "Expected shots with C10 in required_element_ids"
    for entry in c10_entries:
        c10_refs = [r for r in entry.element_refs if r.element_id == "C10"]
        # C10 has two KER records (carrier + holder)
        assert len(c10_refs) == 2, (
            f"Expected 2 C10 KER records for shot {entry.shot_id}, got {len(c10_refs)}"
        )


def test_sc0014_element_refs_have_ker_ids(sc0014_entries):
    for entry in sc0014_entries:
        for ref in entry.element_refs:
            assert ref.ker_id, (
                f"element_id={ref.element_id} in shot {entry.shot_id} has no ker_id"
            )


def test_sc0014_loc001_shots_have_element_ref(sc0014_entries):
    loc_entries = [e for e in sc0014_entries if "LOC001" in e.required_element_ids]
    assert loc_entries, "Expected shots referencing LOC001"
    for entry in loc_entries:
        loc_refs = [r for r in entry.element_refs if r.element_id == "LOC001"]
        assert loc_refs, f"LOC001 element_ref missing in shot {entry.shot_id}"
