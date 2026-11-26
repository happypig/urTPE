# -*- coding: utf-8 -*-
"""The national-portal sweep reads every result page and screens by list title (twur-sweep-coverage).

Test-writing group 1 of the change. Board decisions N-D1 and N-D2 (docs/inspections/optimization.md,
Part IV). Measured 2026-11-26, live:

* A section search with 18 results returns 10 on page 1 and 8 on page 2. `search_portal` read
  page 1 only, and the probe limit of 8 fetched the first 8. Five 南港段一小段 projects sit at
  results 11 to 18.
* The list anchor carries each result's title in `title='...'`. Screening those titles for
  "section + whole parcel + 地號" finds each of the five with one hit.
* A view title with no count at all (view/239, 寶清段一小段51-13) parses to nothing and the strict
  matcher rejected it, although its siblings 51-3 (view/170) and 51-17 (view/204) are separate units.

Every title below is a real one from that measurement.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "sweep_cov", ROOT / "scripts" / "fetch_remaining_national_portal.py")
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)

SUFFIX = "-都更查詢-內政部國土管理署都市更新入口網"

V239 = "擬訂臺北市松山區寶清段一小段51-13地號土地都市更新事業計畫案" + SUFFIX
V170 = "擬訂臺北市松山區寶清段一小段51-3地號等1筆土地都市更新事業計畫及權利變換計畫案" + SUFFIX
V204 = "擬訂臺北市松山區寶清段一小段51-17地號1筆土地都市更新事業計畫案" + SUFFIX
V1169 = "擬訂臺北市南港區南港段一小段561地號1筆(原5筆)土地都市更新事業計畫案" + SUFFIX

BAOQING = "寶清段一小段"
NANGANG = "南港段一小段"

# The 18 list titles of the 南港段一小段 search, in the order the portal returned them
# (page 1: 10, page 2: 8). Probed 2026-11-26.
NANGANG_LIST = [
    ("1169", "擬訂臺北市南港區南港段一小段561地號1筆(原5筆)土地都市更新事業計畫案"),
    ("983", "擬訂臺北市南港段一小段601地號等25筆土地事業計畫案"),
    ("913", "擬訂臺北市南港區南港段一小段101地號等41筆土地都市更新事業計畫及權利變換計畫案"),
    ("846", "擬訂臺北市南港區南港段一小段138-1地號等58筆土地都市更新事業計畫案"),
    ("673", "擬訂臺北市南港區南港段一小段19-1地號等34筆土地都市更新事業計畫及權利變計畫案"),
    ("295", "擬訂臺北市南港區南港段一小段522地號等45筆土地(R13)都市更新事業計畫案"),
    ("242", "擬訂臺北市南港區南港段一小段379-1地號等43筆土地都市更新事業計畫案"),
    ("202", "擬訂臺北市南港區南港段一小段1110地號等21筆土地都市更新事業計畫及權利變換計畫案"),
    ("201", "擬訂臺北市南港區南港段一小段720地號等105筆土地都市更新事業計畫案"),
    ("172", "擬訂臺北市南港區南港段一小段531地號等2筆土地都市更新事業計畫及權利變換計畫案"),
    ("93", "擬訂臺北市南港區南港段一小段412-2地號等48筆土地都市更新事業計畫及權利變換計畫案"),
    ("82", "擬訂臺北市南港區南港段一小段384地號等11筆土地(R13)都市更新事業計畫及權利變換計畫"),
    ("81", "擬訂臺北市南港區南港段一小段366地號等21筆土地都市更新事業計畫案"),
    ("69", "擬訂臺北市南港區南港段一小段527地號等4筆土地(R13)都市更新權利變換計畫案"),
    ("62", "擬訂臺北市南港區南港段一小段520-2地號等16筆土地(R13)都市更新事業計畫及權利變換"),
    ("58", "擬訂臺北市南港區南港段一小段531-4地號等2筆土地(R13)都市更新事業計畫及權利變換計"),
    ("39", "擬訂臺北市南港區南港段一小段619地號等6筆土地(R14)都市更新事業計畫案"),
    ("38", "擬訂臺北市南港區南港段一小段560地號等16筆土地(R13)都市更新事業計畫及權利變換計畫"),
]
# Class A: candidate parcel, the count our payload carries (the title's own), and the view id twur holds.
CLASS_A = [("366", "21", "81"), ("384", "11", "82"), ("412-2", "48", "93"),
           ("527", "4", "69"), ("560", "16", "38")]


def view_html(title: str, body_parcel: str) -> str:
    return (f"<html><head><title>{title}</title></head>"
            f"<body>{body_parcel}地號 …</body></html>")


def list_page(rows) -> str:
    """A portal list page: single-quoted attributes, the title in `title='...'`."""
    cells = "".join(
        f"<tr><td><a href='https://twur.nlma.gov.tw/zh/urban/rebuild/view/{vid}' "
        f"title='{title}'>{title}</a></td></tr>" for vid, title in rows)
    return f"<html><body><table>{cells}</table></body></html>"


# --- 1.1: the title test ------------------------------------------------------

@pytest.mark.parametrize("title,section,parcel,expected", [
    (V239, BAOQING, "51-13", True),
    (V170, BAOQING, "51-13", False),            # 51-3地號
    (V204, BAOQING, "51-13", False),            # 51-17地號
    (V239, BAOQING, "51-3", False),
    (V239, BAOQING, "51-17", False),
    (V239, BAOQING, "51-1", False),             # 51-1 is a prefix of 51-13, 地號 does not follow
    (V239, BAOQING, "1-13", False),             # a digit precedes 1-13
    (V239, BAOQING, "13", False),               # a hyphen precedes 13
    (V239.replace("51-13地號", "51-130地號"), BAOQING, "51-13", False),
    (V239.replace("51-13", "51之13"), BAOQING, "51-13", True),          # 之 drift
    (V239.replace("51-13", "５１－１３").replace("－", "-"), BAOQING, "51-13", True),  # full-width digits
    (V239, BAOQING, "５１-１３", True),
    (V239, "清段一小段", "51-13", False),         # a longer section name is not the section
    (V239, "寶清段二小段", "51-13", False),        # another section
    ("擬訂臺北市南港段一小段601地號等25筆", NANGANG, "601", True),   # 市 directly before the section
    ("南港段一小段601地號等25筆", NANGANG, "601", True),            # the section opens the title
    (V1169, NANGANG, "561", True),
    ("", NANGANG, "561", False),
    (V239, "", "51-13", False),
    (V239, BAOQING, "", False),
])
def test_title_names_parcel_table(title, section, parcel, expected):
    assert sweep.title_names_parcel(title, section, parcel) is expected


# --- 1.2: countless titles in the strict matcher ------------------------------

def test_countless_title_is_accepted_for_its_own_parcel():
    page = view_html(V239, "51-13")
    assert sweep.view_page_matches(page, BAOQING, "51-13", "") is True
    assert sweep.view_page_matches(page, BAOQING, "51-13", "1") is True, \
        "an absent count on the title side skips the count check"


@pytest.mark.parametrize("cand_parcel", ["51-3", "51-17", "51-1", "1-13", "13"])
def test_countless_title_is_rejected_for_a_sibling_parcel(cand_parcel):
    # The body names the candidate's parcel, as it can on a page that lists its neighbours.
    page = view_html(V239, "51-13") + f"<p>{cand_parcel}地號</p>"
    assert sweep.view_page_matches(page, BAOQING, cand_parcel, "") is False


@pytest.mark.parametrize("title,cand_parcel", [(V170, "51-13"), (V204, "51-13")])
def test_counted_sibling_titles_are_rejected_for_51_13(title, cand_parcel):
    page = view_html(title, "51-13") + "<p>51-13地號</p>"
    assert sweep.view_page_matches(page, BAOQING, cand_parcel, "") is False


def test_countless_title_under_another_section_is_rejected():
    page = view_html(V239.replace("寶清段一小段", "寶清段二小段"), "51-13")
    assert sweep.view_page_matches(page, BAOQING, "51-13", "") is False


def test_a_countless_title_needs_the_parcel_in_the_body_too():
    page = f"<html><head><title>{V239}</title></head><body>無關</body></html>"
    assert sweep.view_page_matches(page, BAOQING, "51-13", "") is False


def test_a_counted_title_with_a_different_parcel_never_reaches_the_countless_rule():
    page = view_html(V170, "51-13")           # parses: 51-3, count 1
    assert sweep.view_page_matches(page, BAOQING, "51-13", "1") is False


def test_titles_that_already_parse_keep_their_verdicts():
    assert sweep.view_page_matches(view_html(V170, "51-3"), BAOQING, "51-3", "1") is True
    assert sweep.view_page_matches(view_html(V204, "51-17"), BAOQING, "51-17", "1") is True
    assert sweep.view_page_matches(view_html(V1169, "561"), NANGANG, "561", "1") is True
    # a count mismatch is still a mismatch
    assert sweep.view_page_matches(view_html(V170, "51-3"), BAOQING, "51-3", "9") is False


# --- 1.3: paging --------------------------------------------------------------

def _ids(page_rows):
    return [vid for vid, _ in page_rows]


class PagedPortal:
    """A fake fetch_url that serves list pages 1.. from `pages` and records every request."""

    def __init__(self, pages, fail_on=None):
        self.pages = pages
        self.fail_on = fail_on
        self.requests = []

    def __call__(self, url, data=None, browser=False):
        self.requests.append(url)
        page = int(url.split("page=")[1].split("&")[0])
        if self.fail_on == page:
            raise OSError("connection reset")
        return list_page(self.pages[page - 1]) if page <= len(self.pages) else "<html></html>"


@pytest.fixture
def sleeps(monkeypatch):
    """No test sleeps. The calls are recorded, so a test can say between pages only."""
    calls = []
    monkeypatch.setattr(sweep.time, "sleep", lambda s: calls.append(s))
    return calls


def test_a_two_page_search_returns_every_result(monkeypatch, sleeps):
    portal = PagedPortal([NANGANG_LIST[:10], NANGANG_LIST[10:], []])
    monkeypatch.setattr(sweep, "fetch_url", portal)

    outcome, ids = sweep.search_portal(NANGANG)

    assert outcome == "miss"
    assert list(ids) == _ids(NANGANG_LIST)
    assert len(portal.requests) == 2, "page 2 held 8 (a short page), so there is no page 3"
    assert len(sleeps) == 1, "one wait, between the two pages, and none before page 1"


def test_titles_come_from_the_single_quoted_attribute(monkeypatch, sleeps):
    monkeypatch.setattr(sweep, "fetch_url", PagedPortal([NANGANG_LIST[:10], NANGANG_LIST[10:]]))

    outcome, ids = sweep.search_portal(NANGANG)

    assert ids.titles["81"].startswith("擬訂臺北市南港區南港段一小段366地號"), ids.titles.get("81")
    assert ids.titles["58"].endswith("權利變換計"), "a cut-short title is kept as it is"
    assert len(ids.titles) == 18


def test_a_page_that_repeats_the_previous_page_ends_the_reading(monkeypatch, sleeps):
    full = NANGANG_LIST[:10]
    portal = PagedPortal([full, full, full, full])
    monkeypatch.setattr(sweep, "fetch_url", portal)

    outcome, ids = sweep.search_portal(NANGANG)

    assert list(ids) == _ids(full)
    assert len(portal.requests) == 2, "page 2 added no new id, so page 3 is never asked for"


def test_a_short_first_page_costs_one_request(monkeypatch, sleeps):
    portal = PagedPortal([NANGANG_LIST[:4]])
    monkeypatch.setattr(sweep, "fetch_url", portal)

    outcome, ids = sweep.search_portal(NANGANG)

    assert len(ids) == 4 and len(portal.requests) == 1 and sleeps == []


def test_the_page_cap_stops_a_portal_that_always_returns_new_ids(monkeypatch, sleeps):
    def endless(url, data=None, browser=False):
        n = int(url.split("page=")[1].split("&")[0])
        return list_page([(str(1000 * n + i), f"擬訂臺北市{NANGANG}{n}{i}地號等2筆") for i in range(10)])

    monkeypatch.setattr(sweep, "fetch_url", endless)
    outcome, ids = sweep.search_portal(NANGANG)

    assert len(ids) == 10 * sweep.MAX_LIST_PAGES
    assert outcome == "miss"


def test_a_plain_page_with_double_quoted_links_has_no_titles(monkeypatch, sleeps):
    html = '<a href="/view/1037">a</a><a href="/view/892">b</a>'
    monkeypatch.setattr(sweep, "fetch_url", lambda *a, **k: html)

    outcome, ids = sweep.search_portal("通化段六小段")

    assert ids == ["1037", "892"]
    assert dict(ids.titles) == {}


# --- 1.4: error truth for paging ----------------------------------------------

def test_page_one_failing_is_an_error_with_no_ids(monkeypatch, sleeps):
    monkeypatch.setattr(sweep, "fetch_url", PagedPortal([NANGANG_LIST[:10]], fail_on=1))
    outcome, ids = sweep.search_portal(NANGANG)
    assert outcome == "error" and ids == []


def test_page_two_failing_is_an_error_that_keeps_the_page_one_ids(monkeypatch, sleeps):
    monkeypatch.setattr(sweep, "fetch_url", PagedPortal([NANGANG_LIST[:10], NANGANG_LIST[10:]], fail_on=2))
    outcome, ids = sweep.search_portal(NANGANG)
    assert outcome == "error"
    assert list(ids) == _ids(NANGANG_LIST[:10])


def test_the_stop_time_passing_between_pages_is_an_error_not_a_miss(monkeypatch, sleeps):
    portal = PagedPortal([NANGANG_LIST[:10], NANGANG_LIST[10:]])
    monkeypatch.setattr(sweep, "fetch_url", portal)
    monkeypatch.setattr(sweep, "is_past_deadline", lambda: True)

    outcome, ids = sweep.search_portal(NANGANG)

    assert outcome == "error", "a search cut short by the stop time has not shown the portal lacks the case"
    assert list(ids) == _ids(NANGANG_LIST[:10])
    assert len(portal.requests) == 1


def _find(monkeypatch, search_result, pages, section, parcel, count="", max_probe=8):
    """Run find_matching_view_with_outcome with a faked search and faked view pages."""
    monkeypatch.setattr(sweep, "search_portal", lambda s: search_result)
    fetched = []

    def fake(url, *a, **k):
        vid = url.rsplit("/", 1)[-1]
        fetched.append(vid)
        return pages.get(vid, "<html><head><title>無關案件</title></head><body></body></html>")

    monkeypatch.setattr(sweep, "fetch_url", fake)
    result = sweep.find_matching_view_with_outcome(section, parcel, count, max_probe=max_probe)
    return result, fetched


def test_a_partial_search_with_no_match_is_an_error_not_a_miss(monkeypatch):
    ids = sweep.SearchIds(["a", "b"])
    result, fetched = _find(monkeypatch, ("error", ids), {}, NANGANG, "366", "21")
    assert fetched == ["a", "b"], "the ids already read are still probed"
    assert result[5] == "error", "an unread page might have held the match; this is no 14-day negative"
    assert result[4] == ["a", "b"]


def test_a_partial_search_that_still_matches_is_a_match(monkeypatch):
    ids = sweep.SearchIds(["a", "b"])
    pages = {"b": view_html(dict(NANGANG_LIST)["81"], "366")}
    result, fetched = _find(monkeypatch, ("error", ids), pages, NANGANG, "366", "21")
    assert result[0] == "b" and result[5] == "match"


def test_a_failed_search_with_no_ids_still_makes_no_probe_request(monkeypatch):
    result, fetched = _find(monkeypatch, ("error", []), {}, NANGANG, "366", "21")
    assert fetched == [] and result[5] == "error"


# --- 1.5: probe order ---------------------------------------------------------

def _results(n=18, hit=None, hit_title="擬訂臺北市南港區南港段一小段366地號等21筆土地"):
    ids = [f"r{i}" for i in range(n)]
    titles = {vid: f"擬訂臺北市南港區南港段一小段9{i}地號等3筆土地" for i, vid in enumerate(ids)}
    if hit is not None:
        titles[ids[hit]] = hit_title
    return sweep.SearchIds(ids, titles)


def test_order_puts_title_hits_first_and_keeps_every_result():
    ids = _results(18, hit=14)
    order = sweep.order_probes(ids, NANGANG, "366")
    assert order[0] == "r14"
    assert order[1:] == [f"r{i}" for i in range(18) if i != 14]
    assert sorted(order) == sorted(ids)


def test_order_without_titles_or_without_a_hit_is_the_returned_order():
    assert sweep.order_probes(["x", "y", "z"], NANGANG, "366") == ["x", "y", "z"]
    ids = _results(6)
    assert sweep.order_probes(ids, NANGANG, "366") == list(ids)


def test_a_title_hit_beyond_the_limit_is_probed_first_and_alone(monkeypatch):
    ids = _results(18, hit=14)
    pages = {"r14": view_html("擬訂臺北市南港區南港段一小段366地號等21筆土地都市更新事業計畫案", "366")}
    result, fetched = _find(monkeypatch, ("miss", ids), pages, NANGANG, "366", "21")
    assert fetched == ["r14"]
    assert result[0] == "r14" and result[5] == "match"


def test_a_title_hit_that_fails_the_strict_match_does_not_end_the_probing(monkeypatch):
    ids = _results(18, hit=3)
    result, fetched = _find(monkeypatch, ("miss", ids), {}, NANGANG, "366", "21")
    assert fetched == ["r3", "r0", "r1", "r2", "r4", "r5", "r6", "r7"]
    assert result[5] == "miss" and result[4] == fetched, "view_ids_checked lists what was fetched"


def test_a_cut_short_list_title_only_orders_the_probes(monkeypatch):
    # The list title is cut before its count, so it cannot be compared; the view page decides.
    ids = _results(12, hit=9, hit_title="擬訂臺北市南港區南港段一小段366地號等")
    pages = {"r9": view_html("擬訂臺北市南港區南港段一小段366地號等22筆土地都市更新事業計畫案", "366")}
    result, fetched = _find(monkeypatch, ("miss", ids), pages, NANGANG, "366", "21")
    assert fetched[0] == "r9", "the list title put it first"
    assert result[5] == "miss", "its own title says 等22筆 against our 21: still rejected"


def test_without_a_title_hit_the_unprobed_note_and_the_limit_are_unchanged(monkeypatch, capsys):
    ids = _results(12)
    result, fetched = _find(monkeypatch, ("miss", ids), {}, NANGANG, "366", "21")
    assert fetched == [f"r{i}" for i in range(8)]
    assert "4 unprobed" in capsys.readouterr().out


# --- 1.6: golden rows from the 2026-11-26 measurement -------------------------

@pytest.mark.parametrize("parcel,count,expected_view", CLASS_A)
def test_each_class_a_project_reaches_its_view_id_under_the_default_limit(
        monkeypatch, parcel, count, expected_view):
    ids = sweep.SearchIds([v for v, _ in NANGANG_LIST], dict(NANGANG_LIST))
    pages = {v: view_html(t + SUFFIX, p) for v, t in NANGANG_LIST
             for p in [t.split("小段")[1].split("地號")[0]]}
    result, fetched = _find(monkeypatch, ("miss", ids), pages, NANGANG, parcel, count)
    assert result[0] == expected_view and result[5] == "match"
    assert len(fetched) == 1, f"probed {fetched}"


def test_class_a_is_not_reachable_without_the_screen(monkeypatch):
    """The measurement behind the design: with page 2 read and no titles, a limit of 8 still misses."""
    plain = list(_ids(NANGANG_LIST))
    pages = {v: view_html(t + SUFFIX, t.split("小段")[1].split("地號")[0]) for v, t in NANGANG_LIST}
    result, _ = _find(monkeypatch, ("miss", plain), pages, NANGANG, "366", "21")
    assert result[5] == "miss"


def test_baoqing_siblings_each_reach_only_their_own_page(monkeypatch):
    rows = [("170", V170.replace(SUFFIX, "")), ("239", V239.replace(SUFFIX, "")),
            ("204", V204.replace(SUFFIX, ""))]
    ids = sweep.SearchIds([v for v, _ in rows], dict(rows))
    pages = {"170": view_html(V170, "51-3"), "239": view_html(V239, "51-13"),
             "204": view_html(V204, "51-17")}
    for parcel, count, view in [("51-3", "1", "170"), ("51-13", "", "239"), ("51-17", "1", "204")]:
        result, _ = _find(monkeypatch, ("miss", ids), pages, BAOQING, parcel, count)
        assert result[0] == view and result[5] == "match", (parcel, result[0])
