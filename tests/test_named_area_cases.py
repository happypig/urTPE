# -*- coding: utf-8 -*-
"""A 更新單元 named for a place rather than a parcel, and date ordering after --from-js.

Test-writing group 1 of named-area-case-discovery. Both defects here were visible on one
project and both were violations of requirements that already existed.

1. `萬華區-崇仁新村青年段一小段-711-3地號等?筆` is missing Taipei case 09112121 (變更). The
   platform has it: it came back from a search on 711. The gazette prints 711-3 and the
   city's index is keyed on 711, so the form we search returns a zero-length body -- which
   read as "this project has no cases". And when the stem did answer, the §6.7 parcel guard
   rejected both cases, because neither name declares a 地號: they name the area 崇仁新村.

   The guard's premise is "a name lacking the parcel marks a foreign/sibling case". That is
   false here. So the guard gains a corroborated path -- and only that: a name that
   declares a parcel of its own is still rejected, because a conflicting 地號 is real
   evidence of a foreign family no matter how much area text it shares.

2. The timeline renders 變更 (2008) above 擬訂 (2005). `cli.py:95` reads `ymd` off each
   emitted node, but `build_project_graph` never emits one, so every node loads as
   ymd=(0,0,0) and `_sort`'s (ymd, recno) key degrades to 編號. That is the AGENTS.md trap
   exactly, and --from-js reads its own output, so it re-inverts on every run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import urtpe.links as links  # noqa: E402
from urtpe.links import (  # noqa: E402
    search_taipei_cases_api,
)

CHONGREN = "崇仁新村青年段一小段"
ANCHOR_NAME = "變更臺北市萬華區崇仁新村都市更新事業計畫及權利變換計畫案"  # the real gazette 案名 (clean.tsv)
PID = "萬華區-崇仁新村青年段一小段-711-3地號等?筆"

# The three rows the live API returns for 青年段一小段 / 711, verbatim.
LIVE = [
    ("09112120", "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案", "已完工"),
    ("09112121", "變更臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案", "已完工"),
]


def _entry(case_id: str, name: str, schedule: str = "已完工") -> dict:
    return {
        "details": f"https://gis.uro.taipei/r_progress_detail.aspx?case_id={case_id}",
        "case_name": name,
        "schedule": schedule,
    }


def _api(monkeypatch, responder):
    """Stub the POST, recording every (section, parcel) the search actually asks for."""
    asked: list[str] = []

    def _post(url, params, max_retries=3):
        mono = params.get("monobuf", "")
        suno = params.get("sunobuf", "")
        parcel = mono if suno in ("", "0") else f"{mono}-{suno}"
        asked.append("%s|%s" % (params.get("sectstr", ""), parcel))
        return json.dumps(responder(asked[-1]))

    monkeypatch.setattr(links, "_post_taipei_api", _post)
    return asked


# --- 1.1 / 1.2: the stem retry ---------------------------------------------

def test_the_mono_stem_is_searched_when_the_subdivided_parcel_returns_nothing(monkeypatch):
    rows = {"青年段一小段|711": [_entry(c, n, s) for c, n, s in LIVE]}
    asked = _api(monkeypatch, lambda p: rows.get(p, []))

    kept = search_taipei_cases_api("青年段一小段", "711-3",
                                   anchor_name=ANCHOR_NAME)

    assert asked == ["青年段一小段|711-3", "青年段一小段|711"], (
        "the gazette prints 711-3 and the city's index is keyed on 711; searching only the "
        "printed form returns a zero-length body, which is indistinguishable from a project "
        "that genuinely has no cases")
    assert [e["case_id"] for e in kept] == ["09112120", "09112121"], (
        "09112121 is the 變更 case the dataset was missing")


def test_no_stem_retry_when_the_original_parcel_matched(monkeypatch):
    rows = {"寶清段四小段|57-13": [_entry("10212211", "擬訂臺北市中山區寶清段四小段57-13地號等1筆土地都市更新事業計畫案")]}
    asked = _api(monkeypatch, lambda p: rows.get(p, []))

    kept = search_taipei_cases_api("寶清段四小段", "57-13", anchor_name="寶清段四小段更新案")

    assert asked == ["寶清段四小段|57-13"], "the ordinary case must stay a single request"
    assert [e["case_id"] for e in kept] == ["10212211"]


def test_a_partial_first_result_is_trusted_and_never_re_searched(monkeypatch):
    """The retry fires only on an empty body, so there is nothing to merge.

    Worth pinning: a first search that returns *some* rows is taken as the answer even if
    the stem would have held more. Re-querying on a non-empty result would double every
    project's request count to chase cases the platform did not offer.
    """
    one = [_entry("09112120", "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案")]
    asked = _api(monkeypatch, lambda p: one if p == "青年段一小段|711-3" else one + [_entry(
        "09112121", "變更臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案")])

    kept = search_taipei_cases_api("青年段一小段", "711-3", anchor_name=ANCHOR_NAME)

    assert asked == ["青年段一小段|711-3"], asked
    assert [e["case_id"] for e in kept] == ["09112120"], (
        "09112121 is only reachable via the stem; a non-empty first answer is taken as-is "
        "and the case stays absent rather than the project paying a second request")
    assert len({e["case_id"] for e in kept}) == len(kept), "and never duplicated"


# --- 1.3: section-name drift ----------------------------------------------
#
# The second key drifts too, and it was the one that actually blocked the run: the gazette
# prints 崇仁新村青年段一小段 while the city's index holds 青年段一小段. Verified against the
# live API -- of four section spellings tried, only 青年段一小段 + 711 returned anything, so
# the parcel-stem retry alone recovers nothing.

def test_a_section_carrying_a_place_prefix_is_searched_without_it(monkeypatch):
    rows = {"青年段一小段|711": [_entry(c, n, s) for c, n, s in LIVE]}
    asked = _api(monkeypatch, lambda p: rows.get(p, []))

    kept = search_taipei_cases_api("崇仁新村青年段一小段", "711-3", anchor_name=ANCHOR_NAME)

    assert "崇仁新村|711" not in asked, "the place prefix is not a section on its own"
    assert kept and [e["case_id"] for e in kept] == ["09112120", "09112121"], (
        "both keys drift: the printed section adds 崇仁新村 and the printed parcel adds -3, "
        "and only the unprefixed section with the bare stem answers")


def test_a_plain_section_name_never_grows_extra_variants(monkeypatch):
    rows = {"玉泉段二小段|40": [_entry("10110181", "擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫及權利變換計畫案")]}
    asked = _api(monkeypatch, lambda p: rows.get(p, []))

    search_taipei_cases_api("玉泉段二小段", "40", anchor_name="玉泉段二小段更新案")

    assert asked == ["玉泉段二小段|40"], (
        "玉泉段二小段 is already a whole section name; there is no prefix to strip, so the "
        "ordinary project must not pay for retries")


def test_an_empty_first_answer_still_costs_only_the_bounded_retries(monkeypatch):
    asked = _api(monkeypatch, lambda p: [])

    search_taipei_cases_api("崇仁新村青年段一小段", "711-3", anchor_name=ANCHOR_NAME)

    assert len(asked) <= 4, (
        "retries are bounded: full parcel+section, bare stem, unprefixed section, and both "
        "together. An unbounded sweep would let one unmatchable project fan out into dozens "
        "of requests against a WAF-fronted endpoint. got %r" % (asked,))


# --- 1.4 / 1.5: corroborated acceptance -----------------------------------

def test_a_parcel_less_case_naming_the_same_area_is_kept(monkeypatch):
    asked = _api(monkeypatch, lambda p: [_entry(c, n, s) for c, n, s in LIVE] if p == "青年段一小段|711" else [])

    kept = search_taipei_cases_api("青年段一小段", "711", anchor_name=ANCHOR_NAME)

    assert [e["case_id"] for e in kept] == ["09112120", "09112121"]
    assert [e["case_name"] for e in kept] == [n for _, n, _ in LIVE]


def test_a_parcel_less_case_naming_a_different_area_is_rejected(monkeypatch):
    other = [_entry("09999999", "擬訂臺北市萬華區另一新村土地都市更新事業計畫案")]
    _api(monkeypatch, lambda p: other if p == "青年段一小段|711" else [])
    dropped: dict[str, str] = {}

    kept = search_taipei_cases_api("青年段一小段", "711",
                                   anchor_name=ANCHOR_NAME, dropped_out=dropped)

    assert kept == [], (
        "another 更新單元 in the same 段 can also have a parcel-less name; without a shared "
        "area token this is exactly the §6.7 pollution")
    assert "09999999" in dropped


def test_a_case_declaring_a_conflicting_parcel_is_rejected_even_when_the_area_matches(monkeypatch):
    """A shared area token must NOT be read as sufficient on its own."""
    conflicting = [_entry("09888888",
                          "擬訂臺北市萬華區崇仁新村999-1地號土地都市更新事業計畫案")]
    _api(monkeypatch, lambda p: conflicting if p == "青年段一小段|711" else [])
    dropped: dict[str, str] = {}

    kept = search_taipei_cases_api("青年段一小段", "711",
                                   anchor_name=ANCHOR_NAME, dropped_out=dropped)

    assert kept == [], (
        "a name carrying its own 地號 is real evidence of a specific unit; 999-1 is not the "
        "parcel searched, so corroboration must not rescue it")
    assert "09888888" in dropped


def test_a_rejected_case_is_still_reported_so_it_can_be_recorded_by_hand(monkeypatch, capsys):
    other = [_entry("09999999", "擬訂臺北市萬華區另一新村土地都市更新事業計畫案")]
    _api(monkeypatch, lambda p: other if p == "青年段一小段|711" else [])
    dropped: dict[str, str] = {}

    search_taipei_cases_api("青年段一小段", "711", anchor_name=ANCHOR_NAME, dropped_out=dropped)

    assert dropped == {"09999999": "擬訂臺北市萬華區另一新村土地都市更新事業計畫案"}, (
        "corroboration failed, so the case must stay auditable rather than vanish")


# --- 1.5: the existing §6.7 scenarios must not move ------------------------

@pytest.mark.parametrize("name", [
    "擬訂臺北市大同區玉泉段二小段40地號等24筆土地都市更新事業概要案",   # foreign same-section
    "擬訂臺北市大同區玉泉段二小段41地號等1筆土地都市更新事業計畫案",    # conflicting parcel
])
def test_a_declared_parcel_still_governs(name, monkeypatch):
    _api(monkeypatch, lambda p: [_entry("10110181", name)])
    dropped: dict[str, str] = {}

    kept = search_taipei_cases_api("玉泉段二小段", "40",
                                   anchor_name="玉泉段二小段更新案", dropped_out=dropped)

    assert kept == [] or _carries(name, "40")
    if not _carries(name, "40"):
        assert "10110181" in dropped


def _carries(name: str, parcel: str) -> bool:
    return links._case_name_carries_parcel(name, parcel)


def test_notation_drift_is_still_tolerated(monkeypatch):
    drifted = [_entry("11412018", "擬訂臺北市中山區寶清段四小段57之13等1筆土地都市更新權利變換計畫案")]
    _api(monkeypatch, lambda p: drifted)

    kept = search_taipei_cases_api("寶清段四小段", "57-13", anchor_name="寶清段四小段更新案")

    assert [e["case_id"] for e in kept] == ["11412018"], "之 ↔ - is still accepted"


# --- 2: date ordering after a --from-js rebuild ----------------------------

def _payload(path: str = "viewer/projects.data.js") -> dict:
    text = Path(ROOT / path).read_text(encoding="utf-8")
    return json.loads(text[text.find("{"):text.rfind("}") + 1])


def test_from_js_load_restores_ymd():
    from urtpe.cli import _load_projects_from_js
    projects, _meta = _load_projects_from_js(str(ROOT / "viewer/projects.data.js"))
    p = next(x for x in projects if x.project_id == PID)

    assert {m.recno: m.ymd for m in p.members} == {
        1362: (2008, 1, 2), 1407: (2005, 2, 24)}, (
        "cli.py:95 reads a `ymd` key the emitter never writes, so every node loads as "
        "(0,0,0) and _sort's (ymd, recno) key degrades to 編號 order")


def test_a_loaded_project_orders_nodes_by_date_not_recno():
    from urtpe.cli import _load_projects_from_js
    from urtpe.graph import build_project_graph
    projects, _meta = _load_projects_from_js(str(ROOT / "viewer/projects.data.js"))
    p = next(x for x in projects if x.project_id == PID)

    nodes = build_project_graph(p, implementer="", name="")["nodes"]

    assert [n["recno"] for n in nodes] == [1407, 1362], (
        "擬訂 2005-02-24 belongs above 變更 2008-01-02; history-graph requires date order "
        "with the anchor highlighted, not the anchor first")
    assert [n["is_current"] for n in nodes] == [False, True], (
        "the anchor is marked, not promoted to the first row")


def test_no_dated_node_in_the_emitted_payload_is_left_unordered():
    """Guards the whole class: not one project, not just this one."""
    from urtpe.cli import _load_projects_from_js
    projects, _meta = _load_projects_from_js(str(ROOT / "viewer/projects.data.js"))

    bad = [(p.project_id, m.recno) for p in projects for m in p.members
           if m.iso_date and m.ymd == (0, 0, 0)]

    assert bad == [], (
        "%d dated nodes carry the empty ordering key, so every one of them orders by 編號 "
        "whenever the graph is rebuilt from emitted state" % len(bad))