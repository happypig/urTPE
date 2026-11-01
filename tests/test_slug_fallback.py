# -*- coding: utf-8 -*-
"""The slug count falls back to the family when the anchor carries none
(land-core-slug-fallback task 1.1).

The two live broken identities: anchors with land_count null rendered `等?筆`
into project_id. The truth sits in a sibling node. These tests pin the
fallback scan (anchor first, then members by 編號 ascending) and the honest
`?`-with-flag case when no member answers.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.merge import slug_for, merge  # noqa: E402
from urtpe.models import CleanRecord  # noqa: E402


def _rec(recno: int, *, land_count=None, district="松山區", section="寶清段一小段",
         parcel=None) -> CleanRecord:
    parcel = parcel or f"{recno}"
    return CleanRecord(
        recno=recno, date="2026-01-01", iso_date="2026-01-01", ymd=(2026, 1, 1),
        district=district, district_land=district,
        name=(f"擬訂臺北市{district}{section}{parcel}地號"
              + (f"等{land_count}筆" if land_count else "") + "土地都市更新事業計畫案"),
        name_raw="", land=f"臺北市{district}{section}{parcel}地號"
                           + (f"等{land_count}筆土地" if land_count else "土地"),
        section=section, first_parcel=parcel, parcels=[parcel], aliases={},
        land_count=land_count, orig_count=None, named_anchor="", area_section="",
        stage="擬訂", stage_index=0, track="事業計畫",
        implementer="甲", planner="乙", auto_fixes=[], review_flags=[],
    )


def test_anchor_null_falls_back_to_a_member_count():
    anchor = _rec(838, land_count=None)
    member = _rec(1080, land_count=1)
    slug = slug_for(anchor, family=[anchor, member])
    assert slug.endswith("等1筆"), slug
    assert "?" not in slug


def test_the_newest_member_with_a_count_wins():
    anchor = _rec(838, land_count=None)
    older = _rec(700, land_count=3)
    newer = _rec(900, land_count=5)
    slug = slug_for(anchor, family=[older, anchor, newer])
    assert slug.endswith("等5筆"), slug


def test_no_member_with_a_count_keeps_q_and_flags():
    anchor = _rec(838, land_count=None)
    slug, unresolved = slug_for(anchor, family=[anchor])
    assert "?" in slug
    assert unresolved, "no-count-anywhere must signal the caller to review-flag"


def test_an_anchor_with_a_count_is_unaffected():
    anchor = _rec(838, land_count=26)
    result = slug_for(anchor, family=[anchor])
    assert isinstance(result, str), (
        "the resolved path returns a bare str, call-compatible with every "
        "existing caller")
    assert result.endswith("等26筆")


def test_the_two_real_broken_identities_resolve():
    baoqing_anchor = _rec(838, land_count=None, parcel="51-13")
    baoqing_member = _rec(1080, land_count=1, parcel="51-13")
    slug_bq = slug_for(baoqing_anchor, family=[baoqing_anchor, baoqing_member])
    assert slug_bq == "松山區-寶清段一小段-51-13地號等1筆", slug_bq

    chongren_anchor = _rec(1375, land_count=None, district="萬華區",
                           section="崇仁新村青年段一小段", parcel="711-3")
    chongren_member = _rec(1423, land_count=2, district="萬華區",
                           section="崇仁新村青年段一小段", parcel="711-3")
    slug_cr = slug_for(chongren_anchor, family=[chongren_anchor, chongren_member])
    assert slug_cr == "萬華區-崇仁新村青年段一小段-711-3地號等2筆", slug_cr


def test_merge_appends_the_review_flag_when_no_member_answers():
    import inspect
    sig = inspect.signature(merge)
    # merge() internally clusters; feed two identical records so they cluster,
    # both without counts, and expect the anchor flagged.
    a = _rec(1, land_count=None, parcel="9")
    b = _rec(2, land_count=None, parcel="9")  # same unit → same family
    projects = merge([a, b])
    assert len(projects) == 1
    anchor = next(m for p in projects for m in p.members if m.recno == p.anchor_recno)
    assert any("land count" in f for f in anchor.review_flags), anchor.review_flags
