"""The policy dashboard's derivation rules, asserted on the rendered page.

One test per scenario of the `policy-dashboard` spec (change `dashboard-spec`).
Each test writes a small fixture payload, renders the real `viewer/dashboard.js`
through `scripts/dashboard_smoke.js` (a stub DOM in node), and reads back what
the page shows: the cards, the stage bars, the two tables, the chart tooltips.
Nothing here re-implements a rule; a regression to a different stage order, a
different clock or a different application source fails here and nowhere else
— `tests/test_viewer_dashboard.py` pins the page's publishing contracts, not
its figures.

The fixture dates are chosen so the rounded figure is unambiguous: 365.25-day
years, two decimals in the row, one in the median.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "dashboard_smoke.js"
PUB = "2026-10-28"
STAGES = ["已核定未領建照", "已領建照未開工", "施工中", "已完工"]
EN_STAGES = ["Approved, no building permit", "Permit issued, not started",
             "Under construction", "Completed"]

# card order on the page: projects, stalled, review, households, public land, welfare
PROJECTS, STALLED, REVIEW, HOUSEHOLDS, PUBLIC, WELFARE = range(6)


def project(pid="大安區-測試段一小段-1地號等3筆", district="大安區", nodes=None,
            cm=None, mn=None, permit=None, impl=None, implementer="測試實施者"):
    """A minimal payload project. `cm` is one case's milestones (or a dict of
    cases), `mn` the national milestones, `permit` the use-permit witness,
    `impl` the implementation record."""
    links = {}
    if cm is not None:
        links["case_milestones"] = cm if "c1" in cm else {"c1": cm}
    if mn is not None:
        links["milestones_national"] = mn
    if permit is not None:
        links["permit"] = permit
    return {
        "project_id": pid, "district": district, "implementer": implementer,
        "nodes": nodes if nodes is not None else [{"date": "2026-01-15", "stage": "擬訂事業計畫"}],
        "links": links, "implementation": impl or {},
    }


def node(date, stage="擬訂", case="c1", track=None):
    """An approval node bound to one or more city cases, the shape the payload
    emits (`links.taipei` holds the case ids). `case` may be a list."""
    n = {"date": date, "stage": stage,
         "links": {"taipei": case if isinstance(case, list) else [case]}}
    if track:
        n["track"] = track
    return n


def review_points(out):
    """{(interval, year): (median, projects)} from the review chart's tooltips."""
    pts = {}
    for pt in out["review"]["series"]:
        for k, v in pt["values"].items():
            if k != "專案數" and k != "Projects":
                pts[(k, pt["head"])] = (v.split()[0], pt["values"].get("專案數", pt["values"].get("Projects")))
    return pts


FIRST, PREPERMIT = "自申請至首次核定", "自申請至建照核發前之核定"


def payload(projects, published=PUB):
    return {
        "published_date": published,
        "generated_at": published + "T00:00:00+08:00",
        "counts": {"projects": len(projects),
                   "records": sum(len(p["nodes"]) for p in projects)},
        "projects": projects,
    }


def render(tmp_path, doc, hash=None, preset=True, index_html=None, fetch=None,
           today=None, name="p.json"):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    assert HARNESS.exists(), "scripts/dashboard_smoke.js must drive the render path"
    p = tmp_path / name
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    args = [node, str(HARNESS), "--payload", str(p)]
    if preset:
        args.append("--preset")
    if hash:
        args += ["--hash", hash]
    if index_html is not None:
        ih = tmp_path / "index.html"
        ih.write_text(index_html, encoding="utf-8")
        args += ["--index-html", str(ih)]
    if fetch:
        args += ["--fetch", fetch]
    if today:
        args += ["--today", today]
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def stage_of(out):
    """The one stage bar whose total is 1 — for single-project fixtures."""
    rows = [r for r in out["pipeline"]["rows"] if r["total"] == "1"]
    assert len(rows) == 1, out["pipeline"]
    return rows[0]["label"]


# --- 1.2 stage ---------------------------------------------------------------

@pytest.mark.parametrize("source", ["cm", "ulic", "national", "permit"])
def test_a_completion_date_decides_the_stage(source, tmp_path):
    """Any of the four completion sources, with a start date present too."""
    kw = {"impl": {"Eng_Start_Date": "2024-03-01"},
          "cm": {"建照核發日期": "2023-06-01"}}
    if source == "cm":
        kw["cm"]["使照核發日期"] = "2026-05-01"
    elif source == "ulic":
        kw["impl"]["Ulic_Date"] = "2026-05-01"
    elif source == "national":
        kw["mn"] = {"使用核發日期": "115.05.01"}
    else:
        kw["permit"] = {"permit_no": "115使0001", "date": "2026-05-01", "permits": ["115使0001"]}
    out = render(tmp_path, payload([project(**kw)]))
    assert stage_of(out) == "已完工"


@pytest.mark.parametrize("source", ["cm", "eng"])
def test_a_start_date_without_a_completion_date(source, tmp_path):
    kw = {"cm": {"建照核發日期": "2023-06-01"}, "impl": {}}
    if source == "cm":
        kw["cm"]["開工日期"] = "2024-03-01"
    else:
        kw["impl"]["Eng_Start_Date"] = "2024-03-01"
    out = render(tmp_path, payload([project(**kw)]))
    assert stage_of(out) == "施工中"


def test_a_building_permit_without_a_start(tmp_path):
    out = render(tmp_path, payload([project(cm={"建照核發日期": "2024-06-01"})]))
    assert stage_of(out) == "已領建照未開工"


def test_approved_only(tmp_path):
    out = render(tmp_path, payload([project()]))
    assert stage_of(out) == "已核定未領建照"


def test_the_nodes_stage_label_does_not_decide(tmp_path):
    """A 變更 of a 權利變換計畫 is a planning step, not a construction state."""
    nodes = [{"date": "2022-01-10", "stage": "擬訂權利變換計畫"},
             {"date": "2026-01-10", "stage": "變更權利變換計畫(第1次)"}]
    out = render(tmp_path, payload([project(nodes=nodes)]))
    assert stage_of(out) == "已核定未領建照"


# --- 1.3 idle ----------------------------------------------------------------

def test_idle_five_years_or_more(tmp_path):
    # 2021-06-01 → 2026-10-28 is 1975 days: 5.41 years
    out = render(tmp_path, payload([project(nodes=[{"date": "2021-06-01", "stage": "擬訂事業計畫"}])]))
    assert out["cards"][STALLED]["num"] == "1"
    assert out["watch"]["rows"][0]["cells"][3] == "5.41"
    assert out["pipeline"]["rows"][0]["segs"] == {"停滯五年以上": "1"}


def test_idle_three_to_five_years(tmp_path):
    # 2022-10-28 → 2026-10-28 is 1461 days: 4.00 years
    out = render(tmp_path, payload([project(nodes=[{"date": "2022-10-28", "stage": "擬訂事業計畫"}])]))
    assert out["cards"][STALLED]["num"] == "0"
    assert "1" in out["cards"][STALLED]["sub"]          # 另有 1 件停滯三至五年
    assert out["watch"]["rows"][0]["cells"][3] == "4.00"
    assert out["pipeline"]["rows"][0]["segs"] == {"停滯三至五年": "1"}


def test_a_completed_project_is_never_flagged(tmp_path):
    out = render(tmp_path, payload([project(
        nodes=[{"date": "2010-01-10", "stage": "擬訂事業計畫"}],
        impl={"Ulic_Date": "2014-01-10"})]))
    assert stage_of(out) == "已完工"
    assert out["cards"][STALLED]["num"] == "0"
    assert out["watch"]["rows"] == [] and out["watch"]["empty"]
    assert out["pipeline"]["rows"][3]["segs"] == {"已完工或推進中": "1"}


def test_the_clock_is_the_gazette_not_today(tmp_path):
    doc = payload([project(nodes=[{"date": "2021-06-01", "stage": "擬訂事業計畫"}])])
    a = render(tmp_path, doc, today="2030-01-01", name="a.json")
    b = render(tmp_path, doc, today="2040-01-01", name="b.json")
    assert a["watch"] == b["watch"] and a["cards"] == b["cards"]
    assert a["watch"]["rows"][0]["cells"][3] == "5.41"


# --- 1.4 dates ---------------------------------------------------------------

def test_a_dotted_roc_date(tmp_path):
    """107.02.08 is 2018-02-08: it is the project's last progress, 8.72 years
    before the 2026-10-28 gazette (design D7 of dashboard-review-time — the
    national application date is no longer a review source, so the probe is
    idle time, read through the same date parser)."""
    out = render(tmp_path, payload([project(
        nodes=[{"date": "2016-01-01", "stage": "擬訂事業計畫"}],
        mn={"事業計畫核定日期": "107.02.08"})]))
    row = out["watch"]["rows"][0]
    assert row["cells"][2] == "2018-02-08"
    assert row["cells"][3] == "8.72"


def test_a_date_that_does_not_exist(tmp_path):
    out = render(tmp_path, payload([project(impl={"Ulic_Date": "2026/2/30"})]))
    assert stage_of(out) == "已核定未領建照"


def test_a_date_after_the_gazette(tmp_path):
    """A use permit dated after 統計至 neither completes the project nor
    shortens its idle time: the last progress stays at the 2020 approval."""
    out = render(tmp_path, payload([project(
        nodes=[{"date": "2020-01-01", "stage": "擬訂事業計畫"}],
        impl={"Ulic_Date": "2027-01-01"})]))
    assert stage_of(out) == "已核定未領建照"
    row = out["watch"]["rows"][0]
    assert row["cells"][2] == "2020-01-01"
    assert row["cells"][3] == "6.82"


# --- 1.5 review --------------------------------------------------------------

def test_both_dates_present(tmp_path):
    """The first approval's own case: 申請計畫 2015-01-01, 核定 2018-01-01."""
    out = render(tmp_path, payload([project(
        nodes=[node("2018-01-01")],
        cm={"申請計畫日期": "2015-01-01", "核定日期": "2018-01-01"})]))
    assert review_points(out)[(FIRST, "2018")] == ("3.0", "1")


def test_approval_before_application(tmp_path):
    out = render(tmp_path, payload([project(
        nodes=[node("2014-01-01")],
        cm={"申請計畫日期": "2015-01-01", "核定日期": "2014-01-01"})]))
    assert out["cards"][REVIEW]["num"] == "—"
    assert out["review"]["series"] == [] and out["review"]["empty"]


def test_the_median_over_an_even_count(tmp_path):
    # first-approval years 1.0, 2.0, 3.0, 10.0 against one 2020-01-01 approval each
    apps = ["2019-01-01", "2018-01-01", "2017-01-01", "2010-01-01"]
    docs = [project(pid="p%d" % i, nodes=[node("2020-01-01")],
                    cm={"申請計畫日期": a, "核定日期": "2020-01-01"}) for i, a in enumerate(apps)]
    out = render(tmp_path, payload(docs))
    assert review_points(out)[(FIRST, "2020")] == ("2.5", "4")


def test_the_count_travels_with_the_median(tmp_path):
    docs = [project(pid="p%d" % i, nodes=[node("2018-0%d-01" % (i + 1))],
                    cm={"申請計畫日期": "2015-01-01", "核定日期": "2018-0%d-01" % (i + 1)}) for i in range(2)]
    out = render(tmp_path, payload(docs))
    pts = review_points(out)
    assert pts[(FIRST, "2018")][1] == "2"
    assert pts[(PREPERMIT, "2018")][1] == "2"


def test_the_application_is_read_from_the_first_approvals_own_case(tmp_path):
    """Case A on the 擬訂 node applied 2016; case B on the later 變更 applied
    2012. The interval is A's 2.0 years, not B's 6.0."""
    out = render(tmp_path, payload([project(
        nodes=[node("2018-01-01", case="c1"), node("2020-01-01", stage="變更", case="c2")],
        cm={"c1": {"申請計畫日期": "2016-01-01", "核定日期": "2018-01-01"},
            "c2": {"申請計畫日期": "2012-01-01", "核定日期": "2020-01-01"}})]))
    assert review_points(out)[(FIRST, "2018")][0] == "2.0"


def test_a_niding_node_is_preferred_as_the_first_approval(tmp_path):
    """德惠段813-1's shape: a 變更 row printed 2017-05-10 precedes the 擬訂 row
    of 2017-11-23. The 擬訂 node is the first approval: 2015-10-26 → 2017-11-23
    is 2.08 years, in the year 2017; the 變更 case would read 0.27 in 2018."""
    out = render(tmp_path, payload([project(
        nodes=[node("2017-05-10", stage="變更", case="c1"), node("2017-11-23", case="c2")],
        cm={"c1": {"申請計畫日期": "2018-01-30", "核定日期": "2018-05-10"},
            "c2": {"申請計畫日期": "2015-10-26", "核定日期": "2017-11-23", "建照核發日期": "2019-08-07"}})]))
    pts = review_points(out)
    assert pts[(FIRST, "2017")][0] == "2.1"
    assert (FIRST, "2018") not in pts


def test_only_outline_approvals(tmp_path):
    out = render(tmp_path, payload([
        project(pid="p0", nodes=[{"date": "2024-07-29", "stage": "擬訂", "track": "事業概要"}]),
        project(pid="p1", nodes=[node("2018-01-01", track="事業計畫")],
                cm={"申請計畫日期": "2015-01-01", "核定日期": "2018-01-01"})]))
    assert out["cards"][PROJECTS]["num"] == "2"
    pts = review_points(out)
    assert pts[(FIRST, "2018")] == ("3.0", "1")
    assert pts[(PREPERMIT, "2018")] == ("3.0", "1")
    assert "1" in out["reviewCap"] and "事業概要" in out["reviewCap"]


def test_time_to_the_approval_before_the_building_permit(tmp_path):
    """萬隆519's shape: 擬訂 2013, 變更 2017, 變更 2022, permit 2018-07-16. Line 2
    ends at the 2017 approval (9.0 years), not at 2022."""
    out = render(tmp_path, payload([project(
        nodes=[node("2013-02-07", case="c1"), node("2017-02-07", stage="變更", case="c2"),
               node("2022-11-23", stage="變更", case="c3")],
        cm={"c1": {"申請計畫日期": "2008-02-07", "核定日期": "2013-02-07", "建照核發日期": "2018-07-16"},
            "c2": {"核定日期": "2017-02-07"},
            "c3": {"核定日期": "2022-11-23"}})]))
    pts = review_points(out)
    assert pts[(FIRST, "2013")][0] == "5.0"
    assert pts[(PREPERMIT, "2013")][0] == "9.0"
    assert out["cards"][REVIEW]["num"] == "9.0"


def test_no_building_permit_the_latest_approval(tmp_path):
    out = render(tmp_path, payload([project(
        nodes=[node("2018-01-01", case="c1"), node("2020-01-01", stage="變更", case="c2")],
        cm={"c1": {"申請計畫日期": "2015-01-01", "核定日期": "2018-01-01"},
            "c2": {"核定日期": "2020-01-01"}})]))
    pts = review_points(out)
    assert pts[(FIRST, "2018")][0] == "3.0"
    assert pts[(PREPERMIT, "2018")][0] == "5.0"


def test_the_permit_precedes_every_approval(tmp_path):
    out = render(tmp_path, payload([project(
        nodes=[node("2018-01-01")],
        cm={"申請計畫日期": "2015-01-01", "核定日期": "2018-01-01", "建照核發日期": "2017-01-01"})]))
    pts = review_points(out)
    assert pts[(FIRST, "2018")][0] == "3.0"
    assert (PREPERMIT, "2018") not in pts
    assert out["cards"][REVIEW]["num"] == "—"


def test_the_card_shows_the_pre_permit_median(tmp_path):
    out = render(tmp_path, payload([project(
        nodes=[node("2018-01-01", case="c1"), node("2020-01-01", stage="變更", case="c2")],
        cm={"c1": {"申請計畫日期": "2015-01-01", "核定日期": "2018-01-01"},
            "c2": {"核定日期": "2020-01-01"}})]))
    assert out["cards"][REVIEW]["num"] == "5.0"
    assert "3.0" in out["cards"][REVIEW]["sub"]


def test_joined_cases_take_the_earliest_application(tmp_path):
    """Two area cases on one recno: 2013-04-08 → 2019-07-24 is 6.29 years
    (6.3); the later case's 2013-06-01 would read 6.1."""
    out = render(tmp_path, payload([project(
        nodes=[node("2019-07-24", case=["c1", "c2"])],
        cm={"c1": {"申請計畫日期": "2013-06-01", "核定日期": "2019-07-24"},
            "c2": {"申請計畫日期": "2013-04-08", "核定日期": "2019-07-24"}})]))
    assert review_points(out)[(FIRST, "2019")][0] == "6.3"


# --- 1.6 approvals -----------------------------------------------------------

def test_a_change_and_a_new_plan_in_one_year(tmp_path):
    nodes = [{"date": "2020-03-01", "stage": "擬訂事業計畫"},
             {"date": "2020-09-01", "stage": "變更事業計畫(第1次)"}]
    out = render(tmp_path, payload([project(nodes=nodes)]))
    (yr,) = out["approvals"]["series"]
    assert yr["head"] == "2020"
    assert yr["values"] == {"擬訂": "1", "變更": "1"}


def test_an_undated_node_is_not_counted(tmp_path):
    nodes = [{"date": "", "stage": "擬訂事業計畫"},
             {"date": "2019-05-05", "stage": "變更事業計畫(第1次)"}]
    out = render(tmp_path, payload([project(nodes=nodes)]))
    assert [y["head"] for y in out["approvals"]["series"]] == ["2019"]
    assert out["approvals"]["series"][0]["values"] == {"擬訂": "0", "變更": "1"}


# --- 1.7 households and land -------------------------------------------------

def test_public_land_larger_than_the_site_is_capped(tmp_path):
    out = render(tmp_path, payload([project(
        impl={"State_Area": 600, "Muni_Area": 600, "Base_Area": 1000, "Old_Doors": 8})]))
    (row,) = out["public"]["rows"]
    assert row["cells"][2] == "1,200"
    assert row["cells"][3] == "100.0"
    assert out["cards"][PUBLIC]["num"] == "1,200"


def test_households_split_by_construction(tmp_path):
    docs = [
        project(pid="a", impl={"Eng_Start_Date": "2026-01-01", "Old_Doors": 30}),
        project(pid="b", cm={"建照核發日期": "2026-01-01"}, impl={"Old_Doors": 20}),
        project(pid="c", impl={"Ulic_Date": "2026-01-01", "Old_Doors": 50}),
    ]
    out = render(tmp_path, payload(docs))
    card = out["cards"][HOUSEHOLDS]
    assert card["num"] == "50"
    assert "30" in card["sub"] and "20" in card["sub"]
    (row,) = out["households"]["rows"]
    assert row["segs"] == {"施工中": "30", "尚未開工": "20"}


def test_public_benefit_area_counts_every_stage(tmp_path):
    out = render(tmp_path, payload([project(impl={"Ulic_Date": "2020-01-01", "Welfare_Area": 123.4})]))
    assert stage_of(out) == "已完工"
    assert out["cards"][WELFARE]["num"] == "123"
    assert "1 件" in out["cards"][WELFARE]["sub"]


# --- 1.8 scope ---------------------------------------------------------------

def _two_districts():
    old = [{"date": "2020-01-01", "stage": "擬訂事業計畫"}]
    return payload([
        project(pid="萬華區-a", district="萬華區", nodes=old, impl={"Old_Doors": 5}),
        project(pid="大安區-b", district="大安區", nodes=old, impl={"Old_Doors": 7}),
    ])


def test_a_district_is_selected(tmp_path):
    out = render(tmp_path, _two_districts(), hash="#district=萬華區")
    assert out["scope"] == "萬華區"
    assert out["cards"][PROJECTS]["num"] == "1"
    assert [r["cells"][0] for r in out["watch"]["rows"]] == ["萬華區-a"]
    by = {r["label"]: r for r in out["households"]["rows"]}
    assert set(by) == {"萬華區", "大安區"}
    assert by["萬華區"]["dim"] is False and by["大安區"]["dim"] is True


def test_an_unknown_district(tmp_path):
    out = render(tmp_path, _two_districts(), hash="#district=火星區")
    assert out["scope"] == "臺北市"
    assert out["cards"][PROJECTS]["num"] == "2"


# --- 1.9 tables --------------------------------------------------------------

def test_the_watchlist_order_and_link(tmp_path):
    docs = [
        project(pid="中正區-短-1地號等1筆", district="中正區",
                nodes=[{"date": "2022-08-01", "stage": "擬訂事業計畫"}]),
        project(pid="中正區-長-2地號等2筆", district="中正區",
                nodes=[{"date": "2020-01-01", "stage": "擬訂事業計畫"}]),
    ]
    out = render(tmp_path, payload(docs))
    rows = out["watch"]["rows"]
    assert [r["cells"][0] for r in rows] == ["中正區-長-2地號等2筆", "中正區-短-1地號等1筆"]
    assert float(rows[0]["cells"][3]) > float(rows[1]["cells"][3])
    for r in rows:
        assert unquote(r["link"]) == "index.html#project=" + r["cells"][0]


def test_the_public_land_table_is_capped_at_twelve(tmp_path):
    docs = [project(pid="p%02d" % i, impl={"State_Area": i * 10, "Base_Area": 100000})
            for i in range(1, 15)]
    out = render(tmp_path, payload(docs))
    rows = out["public"]["rows"]
    assert len(rows) == 12
    assert [r["cells"][2] for r in rows][:3] == ["140", "130", "120"]
    assert rows[-1]["cells"][2] == "30"


def test_nothing_to_list(tmp_path):
    out = render(tmp_path, payload([project()]))
    assert out["watch"]["rows"] == []
    assert out["watch"]["empty"] == "此範圍內沒有停滯三年以上的未完工專案。"


# --- 1.10 view ---------------------------------------------------------------

def test_a_linked_view(tmp_path):
    out = render(tmp_path, _two_districts(), hash="#district=萬華區&lang=en")
    assert out["lang"] == "en"
    assert out["scope"] == "萬華區"
    assert [r["label"] for r in out["pipeline"]["rows"]] == EN_STAGES


def test_the_default_language(tmp_path):
    out = render(tmp_path, _two_districts())
    assert out["lang"] == "zh-Hant"
    assert out["scope"] == "臺北市"
    assert [r["label"] for r in out["pipeline"]["rows"]] == STAGES


def test_the_definitions_travel_with_the_language(tmp_path):
    zh = render(tmp_path, _two_districts(), name="zh.json")
    en = render(tmp_path, _two_districts(), hash="#lang=en", name="en.json")
    assert any("三年與五年的門檻是本頁的慣例" in n for n in zh["notes"])
    assert any("3 and 5 year cut-offs are a convention" in n for n in en["notes"])
    assert len(zh["notes"]) == len(en["notes"]) == 4


# --- 1.11 page ---------------------------------------------------------------

def test_the_figures_follow_the_payload(tmp_path):
    one = render(tmp_path, payload([project(pid="a")]), name="one.json")
    two = render(tmp_path, payload([project(pid="a"), project(pid="b")]), name="two.json")
    assert one["cards"][PROJECTS]["num"] == "1"
    assert two["cards"][PROJECTS]["num"] == "2"
    assert one["meta"].startswith("1 個專案 / 1 筆記錄")
    assert two["meta"].startswith("2 個專案 / 2 筆記錄")
    assert "統計至 " + PUB in one["meta"]


def test_the_dashboard_borrows_the_viewers_dataset_version(tmp_path):
    out = render(tmp_path, payload([project()]), preset=False,
                 index_html='<script src="projects.data.js?v=abc123"></script>')
    assert out["scriptSrc"] == "projects.data.js?v=abc123"
    assert out["cards"][PROJECTS]["num"] == "1"


@pytest.mark.parametrize("fetch", ["none", "reject", "404"])
def test_opened_from_disk(fetch, tmp_path):
    """No fetch at all, a rejected fetch, or a 404: the plain path, and a page."""
    out = render(tmp_path, payload([project()]), preset=False, fetch=fetch)
    assert out["scriptSrc"] == "projects.data.js"
    assert out["cards"][PROJECTS]["num"] == "1"


def test_the_payload_fails_to_load(tmp_path):
    out = render(tmp_path, {"published_date": PUB, "projects": None})
    assert out["failed"] == "無法載入 projects.data.js。"
    assert out.get("cards") is None
