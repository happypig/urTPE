"""Release-diff tests: how the project count moves between two PDF releases.

The report answers one question: why does the total number of projects differ
between two PDF releases? Two counts move for different reasons, and the report
must keep them apart:

- **records** move because the city published new approvals, re-dated or edited
  old ones, or because the reader dropped rows it could not trust.
- **projects** move because the records changed AND the similarity merge
  clustered them differently. A new approval landing inside an existing family
  adds a record and no project.

So the diff is computed at both levels and the project-level movement is
explained against the record-level movement.

Project identity across releases is matched on member content (ISO approval date
plus the normalized 地號 cell), never on `project_id`. The slug is the land core
of the newest approval and it churns (~11% of multi-record families have moved),
so keying on it would report every rename as a death and every birth as a loss.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.release_diff import (
    ReleaseFamily,
    ReleaseRecord,
    diff_releases,
    family_content_keys,
    match_families,
    publisher_link_for,
)


def _rec(recno: int, date: str, land: str, name: str = "n") -> ReleaseRecord:
    return ReleaseRecord(recno=recno, iso_date=date, land=land, name=name,
                         district="中正區")


def _fam(pid: str, members: list[ReleaseRecord]) -> ReleaseFamily:
    return ReleaseFamily(project_id=pid, members=members)


# --- family content keys ----------------------------------------------------

def test_family_keys_use_date_and_land_not_the_slug():
    """A family's identity is its member content, so a slug change does not
    make it a different family."""
    a = _fam("中正區-甲段-1地號等1筆", [_rec(1, "2026-01-01", "臺北市中正區甲段1地號等1筆土地")])
    b = _fam("中正區-甲段-2地號等3筆", [_rec(1, "2026-01-01", "臺北市中正區甲段1地號等1筆土地")])
    assert family_content_keys(a) == family_content_keys(b)


def test_family_keys_ignore_the_approval_order():
    a = _fam("x", [_rec(1, "2026-01-01", "L1"), _rec(2, "2026-02-02", "L2")])
    b = _fam("x", [_rec(2, "2026-02-02", "L2"), _rec(1, "2026-01-01", "L1")])
    assert family_content_keys(a) == family_content_keys(b)


def test_family_keys_are_a_multiset_so_duplicate_members_count():
    """Two families whose members carry the same keys but in different
    multiplicity are different families."""
    a = _fam("x", [_rec(1, "2026-01-01", "L1"), _rec(1, "2026-01-01", "L1")])
    b = _fam("x", [_rec(1, "2026-01-01", "L1")])
    assert family_content_keys(a) != family_content_keys(b)


# --- matching families across releases ---------------------------------------

def test_matching_is_on_content_so_a_renamed_slug_is_the_same_family():
    old = [_fam("old-slug", [_rec(1, "2026-01-01", "L1")])]
    new = [_fam("new-slug", [_rec(1, "2026-01-01", "L1")])]
    matched, gained, lost = match_families(old, new)
    assert len(matched) == 1
    assert matched[0][0].project_id == "old-slug"
    assert matched[0][1].project_id == "new-slug"
    assert gained == [] and lost == []


def test_a_family_that_grew_is_matched_not_reported_as_dead_and_born():
    old = [_fam("p", [_rec(1, "2026-01-01", "L1")])]
    new = [_fam("p", [_rec(1, "2026-01-01", "L1"), _rec(2, "2026-02-02", "L2")])]
    matched, gained, lost = match_families(old, new)
    assert len(matched) == 1
    assert gained == [] and lost == []


def test_a_family_whose_only_member_moved_to_another_family_is_reported():
    """A record that leaves one family and joins another moves the count by
    one in each direction: the old family dies, the new one is born."""
    old = [_fam("a", [_rec(1, "2026-01-01", "L1")])]
    new = [_fam("b", [_rec(2, "2026-02-02", "L2")])]
    matched, gained, lost = match_families(old, new)
    assert matched == []
    assert [f.project_id for f in gained] == ["b"]
    assert [f.project_id for f in lost] == ["a"]


def test_a_family_keeps_its_identity_when_it_merges_with_another():
    """Two old families that become one new family: the count drops by one.
    The new family matches one of them, so exactly one old family is lost."""
    old = [_fam("a", [_rec(1, "2026-01-01", "L1")]),
           _fam("b", [_rec(2, "2026-02-02", "L2")])]
    new = [_fam("c", [_rec(1, "2026-01-01", "L1"), _rec(2, "2026-02-02", "L2")])]
    matched, gained, lost = match_families(old, new)
    assert len(matched) == 1
    assert gained == []
    assert [f.project_id for f in lost] == ["b"]


def test_a_family_split_in_two_reports_one_death_and_one_birth():
    old = [_fam("a", [_rec(1, "2026-01-01", "L1"), _rec(2, "2026-02-02", "L2")])]
    new = [_fam("b", [_rec(1, "2026-01-01", "L1")]),
           _fam("c", [_rec(2, "2026-02-02", "L2")])]
    matched, gained, lost = match_families(old, new)
    assert len(matched) == 1
    assert [f.project_id for f in gained] == ["c"]
    assert lost == []


# --- the diff ---------------------------------------------------------------

def test_diff_reports_the_net_project_change():
    old = [_fam("a", [_rec(1, "2026-01-01", "L1")])]
    new = [_fam("a", [_rec(1, "2026-01-01", "L1")]),
           _fam("b", [_rec(2, "2026-02-02", "L2")])]
    diff = diff_releases("r1", "r2", old, new)
    assert diff.previous_projects == 1
    assert diff.current_projects == 2
    assert diff.net_projects == 1


def test_diff_explains_a_drop_as_deaths_minus_births():
    """The net count must be reconstructible from the named families. A reader
    who sees -5 must be able to see which 5."""
    old = [_fam("a", [_rec(1, "2026-01-01", "L1")]),
           _fam("b", [_rec(2, "2026-02-02", "L2")]),
           _fam("c", [_rec(3, "2026-03-03", "L3")])]
    new = [_fam("a", [_rec(1, "2026-01-01", "L1")])]
    diff = diff_releases("r1", "r2", old, new)
    assert diff.net_projects == -2
    assert len(diff.dead) == 2
    assert diff.born == []
    assert diff.net_projects == len(diff.born) - len(diff.dead)


def test_diff_names_the_members_a_family_gained():
    old = [_fam("a", [_rec(1, "2026-01-01", "L1")])]
    new = [_fam("a", [_rec(1, "2026-01-01", "L1"), _rec(2, "2026-02-02", "L2")])]
    diff = diff_releases("r1", "r2", old, new)
    assert len(diff.grew) == 1
    assert [m.recno for m in diff.grew[0].added] == [2]


def test_diff_names_the_members_a_family_lost():
    old = [_fam("a", [_rec(1, "2026-01-01", "L1"), _rec(2, "2026-02-02", "L2")])]
    new = [_fam("a", [_rec(1, "2026-01-01", "L1")])]
    diff = diff_releases("r1", "r2", old, new)
    assert len(diff.shrank) == 1
    assert [m.recno for m in diff.shrank[0].removed] == [2]


def test_diff_counts_the_records_on_both_sides():
    old = [_fam("a", [_rec(1, "2026-01-01", "L1")])]
    new = [_fam("a", [_rec(1, "2026-01-01", "L1")]),
           _fam("b", [_rec(2, "2026-02-02", "L2")])]
    diff = diff_releases("r1", "r2", old, new)
    assert diff.previous_records == 1
    assert diff.current_records == 2
    assert diff.net_records == 1


def test_a_family_that_only_renamed_is_not_reported_as_a_change():
    """A slug change is not a data change. It must not appear among the
    grew/shrank lists, because the count did not move."""
    old = [_fam("old", [_rec(1, "2026-01-01", "L1")])]
    new = [_fam("new", [_rec(1, "2026-01-01", "L1")])]
    diff = diff_releases("r1", "r2", old, new)
    assert diff.grew == []
    assert diff.shrank == []
    assert diff.renamed == 1


def test_the_diff_is_reconstructible_from_its_parts():
    """previous + born - dead == current. If this ever fails, the report's
    headline number is not explainable by the rows beneath it."""
    old = [_fam("a", [_rec(1, "2026-01-01", "L1")]),
           _fam("b", [_rec(2, "2026-02-02", "L2")])]
    new = [_fam("c", [_rec(1, "2026-01-01", "L1"), _rec(2, "2026-02-02", "L2")]),
           _fam("d", [_rec(3, "2026-03-03", "L3")])]
    diff = diff_releases("r1", "r2", old, new)
    assert diff.previous_projects + len(diff.born) - len(diff.dead) == diff.current_projects
    assert diff.net_projects == diff.current_projects - diff.previous_projects


# --- the 地號 cell is not stable across releases ---------------------------

def test_a_land_cell_that_lost_its_last_character_is_the_same_record():
    """The publisher printed `…地號等6筆土` in one release and `…地號等6筆土地`
    in the next. The cell text differs, but the approval is the same one, so
    the family must not read as dying and another as being born."""
    name = "擬訂臺北市大同區大龍段二小段23地號等6筆土地都市更新事業計畫案"
    old = [_fam("大同區-大龍段二小段-23地號等6筆",
                [ReleaseRecord(recno=1, iso_date="2007-04-02",
                               land="臺北市大同區大龍段二小段14-1、21-2、22-1、23、26、108地號等6筆土",
                               name=name, district="大同區")])]
    new = [_fam("大同區-大龍段二小段-23地號等6筆",
                [ReleaseRecord(recno=1, iso_date="2007-04-02",
                               land="臺北市大同區大龍段二小段14-1、21-2、22-1、23、26、108地號等6筆土地",
                               name=name, district="大同區")])]
    matched, born, lost = match_families(old, new)
    assert len(matched) == 1
    assert born == [] and lost == []


def test_a_family_is_never_both_born_and_lost():
    """The defect the 2026-08-27 -> 2026-09-24 comparison exposed: three units
    had a 地號 cell that differed by one character, and each was counted as a
    death and a birth at once."""
    old = [_fam("x", [_rec(1, "2013-02-06", "L1")])]
    new = [_fam("x", [_rec(1, "2013-02-06", "L2")])]
    matched, born, lost = match_families(old, new)
    dead_ids = {f.project_id for f in lost}
    born_ids = {f.project_id for f in born}
    assert not (dead_ids & born_ids)


def test_a_record_whose_name_carries_no_core_falls_back_to_the_land_cell():
    """Not every 案名 parses. A record with no parseable core still has to be
    matchable, so the 地號 cell is the fallback."""
    name = "核定公告"
    old = [_fam("x", [ReleaseRecord(recno=1, iso_date="2026-01-01", land="臺北市中正區甲段1地號等1筆土地",
                                   name=name, district="中正區")])]
    new = [_fam("y", [ReleaseRecord(recno=1, iso_date="2026-01-01", land="臺北市中正區甲段1地號等1筆土地",
                                   name=name, district="中正區")])]
    matched, born, lost = match_families(old, new)
    assert len(matched) == 1
    assert born == [] and lost == []


def test_two_stage_approvals_of_one_unit_at_different_dates_stay_two_records():
    """The date is part of the identity. Without it, a 擬訂 and its 變更 would
    match each other and the family's member count would not move."""
    old = [_fam("x", [_rec(1, "2020-01-01", "L1")])]
    new = [_fam("x", [_rec(1, "2020-01-01", "L1"), _rec(2, "2021-01-01", "L1")])]
    diff = diff_releases("r1", "r2", old, new)
    assert len(diff.grew) == 1
    assert [m.recno for m in diff.grew[0].added] == [2]
    assert diff.grew[0].removed == ()


# --- the publisher link each release may carry --------------------------------

LIVE = "https://www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/live.pdf"
VERSIONED = ("https://www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/"
             "1d9657b0-55a3-4bbb-8846-f28eeb1a5a85.pdf")


def test_the_newest_release_links_to_the_live_publisher_pdf():
    link = publisher_link_for("2026-10-28", live_url=LIVE,
                               newest_published_date="2026-10-28")
    assert link.url == LIVE
    assert link.kind == "live"
    assert link.known


def test_an_older_release_does_not_link_to_the_live_pdf():
    """The live URL serves the newest document. Linking an older release to it
    would send a reader to a different gazette while the link looked right."""
    link = publisher_link_for("2026-08-11", live_url=LIVE,
                               newest_published_date="2026-10-28")
    assert not link.known
    assert link.url == ""
    assert link.kind == ""


def test_an_older_release_links_to_its_own_recorded_url():
    link = publisher_link_for("2026-10-15", recorded_url=VERSIONED,
                               live_url=LIVE, newest_published_date="2026-10-28")
    assert link.url == VERSIONED
    assert link.kind == "versioned"


def test_a_release_with_no_recorded_url_says_so():
    """The absence of a link is stated, not filled with the wrong document."""
    link = publisher_link_for("2026-08-11", live_url=LIVE,
                               newest_published_date="2026-10-28")
    assert link.label == "未記錄"
    assert not link.known


def test_a_recorded_url_wins_over_the_live_url_for_the_newest_release():
    """When the newest release has its own recorded URL, that is the more
    specific address; the live one is a fallback for a release the index has
    never seen a URL for."""
    link = publisher_link_for("2026-10-28", recorded_url=VERSIONED, live_url=LIVE,
                               newest_published_date="2026-10-28")
    assert link.url == VERSIONED
    assert link.kind == "versioned"


def test_the_two_kinds_of_link_are_distinguishable():
    live = publisher_link_for("2026-10-28", live_url=LIVE,
                               newest_published_date="2026-10-28")
    versioned = publisher_link_for("2026-10-15", recorded_url=VERSIONED,
                                   newest_published_date="2026-10-28")
    assert live.label != versioned.label
    assert live.kind != versioned.kind


def test_the_publisher_stamp_travels_with_the_link():
    """The live link carries the publisher's current stamp."""
    link = publisher_link_for("2026-10-28", live_url=LIVE,
                               live_stamp="115-11-03 13:47",
                               newest_published_date="2026-10-28")
    assert link.publisher_stamp == "115-11-03 13:47"


def test_a_release_never_inherits_another_releases_stamp():
    """The 資料更新 date dates the document the link serves. An older release
    with its own URL carries its own stamp; without one it carries none, and
    the publisher's current stamp is not borrowed for it."""
    own = publisher_link_for("2026-10-15", recorded_url=VERSIONED,
                             publisher_stamp="115-10-21 08:34",
                             live_stamp="115-11-03 13:47",
                             newest_published_date="2026-10-28")
    assert own.publisher_stamp == "115-10-21 08:34"

    bare = publisher_link_for("2026-10-15",
                              live_stamp="115-11-03 13:47",
                              newest_published_date="2026-10-28")
    assert bare.publisher_stamp == ""


def test_with_no_live_url_at_all_the_newest_release_has_no_link():
    """The publisher's page carries one link; if it could not be read, the
    report says the URL is unknown rather than inventing one."""
    link = publisher_link_for("2026-10-28", newest_published_date="2026-10-28")
    assert not link.known
