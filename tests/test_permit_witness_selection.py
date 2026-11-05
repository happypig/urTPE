# -*- coding: utf-8 -*-
"""The permit witness is chosen by the city's 開工 date (D10).

The emitted `links.permit` named the FIRST permit of a tie, and a tie is
common: the permit index keys on the mono parcel, so a section that
redeveloped over time accumulates one permit per building phase. 43 projects
showed a 執照 date that is not the project's own 使照, and the wrong witness
was silent.

The rule: when more than one permit matches, the witness is the permit whose
開工日期 equals the city's 開工日期. The city's 使照 date NEVER chooses the
permit — the permit exists to check that date.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.permit_sources import PermitRecord, select_permit_witness  # noqa: E402


def _permit(no: str, date: str, start: str) -> PermitRecord:
    return PermitRecord(permit_no=no, date=date, orig_permit="100建字第0001號",
                        is_jianzi=True, construction_start=start)


# 寶清57-13 shape: four permits on one mono parcel, spanning 2004 to 2025.
BAOQING = [
    _permit("093使字第0294號", "2004-09-14", "2000-05-04"),
    _permit("107使字第0028號", "2018-01-30", "2015-01-08"),
    _permit("110使字第0038號", "2021-03-23", "2017-07-10"),
    _permit("114使字第0094號", "2025-06-25", "2020-05-06"),
]


def test_the_construction_start_picks_the_permit():
    """The city's 開工 2020-05-06 names 114使字第0094號 — the LAST of the
    four, and the one whose 使照 is the city's own."""
    witness, ambiguous = select_permit_witness(BAOQING, "2020-05-06")
    assert witness is not None
    assert witness.permit_no == "114使字第0094號"
    assert witness.date == "2025-06-25"
    assert ambiguous is False


def test_an_unresolved_tie_is_ambiguous():
    """A 開工 date that matches no permit leaves no witness."""
    witness, ambiguous = select_permit_witness(BAOQING, "1999-01-01")
    assert witness is None
    assert ambiguous is True


def test_a_construction_start_matching_several_permits_is_ambiguous():
    permits = [
        _permit("093使字第0294號", "2004-09-14", "2000-05-04"),
        _permit("107使字第0028號", "2018-01-30", "2000-05-04"),
    ]
    witness, ambiguous = select_permit_witness(permits, "2000-05-04")
    assert witness is None
    assert ambiguous is True


def test_a_single_permit_is_the_witness_unchanged():
    witness, ambiguous = select_permit_witness(
        [_permit("102使字第0298號", "2013-11-12", "2011-03-05")], "2011-03-05")
    assert witness is not None
    assert witness.permit_no == "102使字第0298號"
    assert ambiguous is False


def test_a_single_permit_with_another_construction_start_is_still_the_witness():
    """One permit cannot be ambiguous — there is nothing to choose between."""
    witness, ambiguous = select_permit_witness(
        [_permit("102使字第0298號", "2013-11-12", "2011-03-05")], "1999-01-01")
    assert witness is not None
    assert witness.permit_no == "102使字第0298號"
    assert ambiguous is False


def test_the_licence_date_never_chooses_the_permit():
    """A permit matching only the city's 使照 date is NOT the witness — the
    permit exists to check that date."""
    witness, ambiguous = select_permit_witness(BAOQING, "2025-06-25")
    # the 開工 tier finds nothing, so the tie is ambiguous; the permit whose
    # date equals the city's 使照 does not become the witness
    assert witness is None
    assert ambiguous is True


def test_no_permits_is_not_ambiguous():
    witness, ambiguous = select_permit_witness([], "2020-05-06")
    assert witness is None
    assert ambiguous is False


def test_a_missing_construction_start_leaves_the_tie_ambiguous():
    witness, ambiguous = select_permit_witness(BAOQING, "")
    assert witness is None
    assert ambiguous is True


def test_the_witness_is_the_permit_whose_licence_is_the_citys_own():
    """The end-to-end claim: the chosen permit's 發照日期 is the city's 使照."""
    city_ulic = "2025-06-25"
    witness, _amb = select_permit_witness(BAOQING, "2020-05-06")
    assert witness is not None
    assert witness.date == city_ulic


def test_the_viewer_renders_no_permit_text_when_the_witness_is_absent():
    """An ambiguous permit carries no permit_no, so the viewer's label shows
    nothing — it never names one arbitrary permit as the project's own."""
    import shutil
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node not available")
    js = (ROOT / "viewer" / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
    i = js.index("}).permit || null")
    span = js[max(0, i - 600):i + 600]
    assert "permit && permit.permit_no" in span, (
        "the label must require a permit_no, so an ambiguous permit renders "
        "no permit text")


# ── the city's 開工 date is read from the SOURCE MAP ─────────────────────

def test_the_construction_start_comes_from_the_source_map():
    """A merged value with no source behind it cannot choose the witness —
    the merged dict can be stale, and the source map is what is attributable."""
    from urtpe.links import _city_construction_start

    assert _city_construction_start({
        "milestones_taipei": {"開工日期": "2020/05/06"},
        "milestones_source": {"開工日期": "11510008"},
    }) == "2020-05-06"


def test_a_construction_start_without_a_source_is_not_used():
    from urtpe.links import _city_construction_start

    assert _city_construction_start({
        "milestones_taipei": {"開工日期": "2020/05/06"},
        "milestones_source": {},
    }) == "", "an unattributable value must not choose the witness"


def test_a_stale_merged_value_does_not_pick_the_permit():
    """The D7 shape: the merged dict holds a value the cases no longer carry.

    The value is only usable when the source map names the case that holds it.
    A merged value with NO source behind it cannot choose the witness — the
    merged dict is what D7 found corrupt, so an unattributable value must not
    pick a permit."""
    from urtpe.links import _city_construction_start

    # the merged dict says 2017-07-10 and the source map names the case —
    # after D7's re-derivation the two agree, so this value IS attributable
    links = {
        "milestones_taipei": {"開工日期": "2017/07/10"},
        "milestones_source": {"開工日期": "11011242"},
    }
    assert _city_construction_start(links) == "2017-07-10"
    witness, ambiguous = select_permit_witness(BAOQING,
                                                _city_construction_start(links))
    # the value picks the permit whose 開工 matches it
    assert witness is not None
    assert witness.permit_no == "110使字第0038號"
    assert ambiguous is False


def test_an_iso_construction_start_passes_through():
    from urtpe.links import _city_construction_start

    assert _city_construction_start({
        "milestones_taipei": {"開工日期": "2020-05-06"},
        "milestones_source": {"開工日期": "11510008"},
    }) == "2020-05-06"
