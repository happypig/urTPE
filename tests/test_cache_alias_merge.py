# -*- coding: utf-8 -*-
"""An aliased cache directory is merged, not shadowed (D9c-2a).

`resolve_cache_dir` returned the current directory whenever it existed, so an
alias was consulted only when there was none. The current directory can be a
STUB: the 2026-11-02 run wrote one under
`南港區-南港段四小段-566地號等1筆` while the richer `…等6筆` — the project's
former identity, aliased in `data/project_aliases.json` — held three case ids
with full milestones.

The result was silent: two nodes kept the flag `節點未能對應平台案件` although
the case and its milestones were in the cache all along.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import load_project_cache, resolve_cache_dir  # noqa: E402

CURRENT = "南港區-南港段四小段-566地號等1筆"
FORMER = "南港區-南港段四小段-566地號等6筆"


def _write(cache_dir: Path, pid: str, **fields) -> Path:
    d = cache_dir / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": f"core-{pid}", "status": "resolved",
        "case_milestones": {}, "city_case_ids": [],
        "twur_url": "", "twur_view_id": "", "national_milestones": {},
        "taipei_milestones": {}, "milestones_source": {},
        "implementation": {}, "rewards": {}, "search_rejected": {},
        "candidate_names": {}, "case_schedules": {}, "case_headers": {},
        "case_case_names": {}, "superseded_by": {}, "view_rejected": {},
        "view_verified_case_ids": [], "error": "",
    }
    payload.update(fields)
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    return d


def _alias_table(cache_dir: Path, mapping: dict) -> None:
    (cache_dir.parent / "project_aliases.json").write_text(
        json.dumps({"aliases": mapping}, ensure_ascii=False), encoding="utf-8")


def test_a_stub_and_a_richer_aliased_directory_are_merged(tmp_path):
    """The current directory gains the aliased directory's case ids and
    milestones."""
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _write(cache, CURRENT, city_case_ids=["10708312"],
           case_milestones={"10708312": {"申請計畫日期": "2018/01/01"}})
    _write(cache, FORMER, city_case_ids=["10708312", "10708311", "10006032"],
           case_milestones={
               "10708312": {"申請計畫日期": "2018/01/01"},
               "10708311": {"核定日期": "2019/11/20"},
               "10006032": {"核定日期": "2016/02/25"}})
    _alias_table(cache, {FORMER: CURRENT})

    merged = load_project_cache(cache, CURRENT)
    assert merged is not None
    assert set(merged.city_case_ids) == {"10708312", "10708311", "10006032"}, (
        f"the merged cache must hold every case id, got {merged.city_case_ids}")
    assert merged.case_milestones["10708311"]["核定日期"] == "2019/11/20"
    assert merged.case_milestones["10006032"]["核定日期"] == "2016/02/25"


def test_a_conflict_keeps_the_current_directorys_value(tmp_path):
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _write(cache, CURRENT, city_case_ids=["10708312"],
           case_milestones={"10708312": {"核定日期": "2020/01/01"}})
    _write(cache, FORMER, city_case_ids=["10708312", "10708311"],
           case_milestones={
               "10708312": {"核定日期": "2018/01/01"},
               "10708311": {"核定日期": "2019/11/20"}})
    _alias_table(cache, {FORMER: CURRENT})

    merged = load_project_cache(cache, CURRENT)
    assert merged is not None
    assert merged.case_milestones["10708312"]["核定日期"] == "2020/01/01", (
        "the current directory's value wins a conflict")


def test_the_current_directorys_identity_fields_are_unchanged(tmp_path):
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _write(cache, CURRENT, city_case_ids=["10708312"], land_core="core-current")
    _write(cache, FORMER, city_case_ids=["10708312", "10708311"],
           land_core="core-former")
    _alias_table(cache, {FORMER: CURRENT})

    merged = load_project_cache(cache, CURRENT)
    assert merged is not None
    assert merged.project_id == CURRENT
    assert merged.land_core == "core-current", (
        "the aliased directory's identity fields must not overwrite the current")


def test_no_aliased_directory_changes_nothing(tmp_path):
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _write(cache, CURRENT, city_case_ids=["10708312"],
           case_milestones={"10708312": {"核定日期": "2020/01/01"}})

    merged = load_project_cache(cache, CURRENT)
    assert merged is not None
    assert merged.city_case_ids == ["10708312"]
    assert merged.case_milestones == {"10708312": {"核定日期": "2020/01/01"}}


def test_the_resolution_still_prefers_the_direct_directory(tmp_path):
    """The merge happens at the READ, so the resolution order itself does not
    change: the direct directory is where the merge lands."""
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _write(cache, CURRENT)
    _write(cache, FORMER)
    _alias_table(cache, {FORMER: CURRENT})

    assert resolve_cache_dir(cache, CURRENT).name == CURRENT


def test_the_merge_is_reported(tmp_path, capsys):
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _write(cache, CURRENT, city_case_ids=["10708312"])
    _write(cache, FORMER, city_case_ids=["10708312", "10708311"])
    _alias_table(cache, {FORMER: CURRENT})

    load_project_cache(cache, CURRENT)
    out = capsys.readouterr().out
    assert "10708311" in out, (
        "the merge must name what it added — a silent merge is the defect it "
        "fixes\n  got: %r" % out)


# ── the second id source ─────────────────────────────────────────────────

def _seed(cache: Path, pid: str = "玉成段") -> Path:
    d = cache / pid
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps({
        "project_id": pid, "land_core": "x", "status": "resolved",
        "case_milestones": {"10901211": {"核定日期": "2019/01/01"}},
        "city_case_ids": ["10901211"],
        "twur_url": "", "twur_view_id": "", "national_milestones": {},
        "taipei_milestones": {}, "milestones_source": {},
        "implementation": {}, "rewards": {}, "search_rejected": {},
        "candidate_names": {}, "case_schedules": {}, "case_headers": {},
        "case_case_names": {}, "superseded_by": {}, "view_rejected": {},
        "view_verified_case_ids": [], "error": "",
    }, ensure_ascii=False), encoding="utf-8")
    return d


def _refresh(cache: Path, pid: str, list_rows, headers, **kw):
    from urtpe.links import refresh_project
    kw.setdefault("fetch", lambda cid: {"核定日期": "2026/02/03"})
    kw.setdefault("fetch_status", lambda cid: headers.get(cid, {}))
    kw.setdefault("fetch_implementation", lambda cid: {})
    kw.setdefault("fetch_rewards", lambda cid: {})
    kw.setdefault("fetch_list", lambda: list_rows)
    kw.setdefault("search", lambda *a, **k: [])
    kw.setdefault("search_key", ("玉成段二小段", "166", ""))
    return refresh_project(cache, pid, **kw)


def _rows(*ids):
    """The list rows: a case id and the city's own name for the case."""
    return [{"case_id": cid, "T_name": f"案{cid} 臺北市南港區玉成段二小段166地號等12筆土地都市更新事業計畫案"}
            for cid in ids]


def test_a_case_id_from_the_list_enters_when_its_header_confirms_it(tmp_path):
    """玉成166's 11412011: the parcel search does not index it, and it is in
    no cache. The 168 list names it, and its own header confirms it."""
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _seed(cache, "玉成段")
    headers = {
        "11412011": {"NAME": "事業計畫階段─業經本府核定",
                     "CASE_NAME": "變更(第二次)臺北市南港區玉成段二小段166地號等12筆土地都市更新事業計畫案"},
        "10901211": {"NAME": "事業計畫階段─業經本府核定", "CASE_NAME": "案"},
    }

    report = _refresh(cache, "玉成段", _rows("10901211", "11412011"), headers)

    saved = json.loads((cache / "玉成段" / "result.json").read_text(encoding="utf-8"))
    assert "11412011" in saved["city_case_ids"], (
        f"the confirmed id must enter the case list, got {saved['city_case_ids']}")
    assert "11412011" in str(report.get("added")), (
        f"the added id must be reported, got {report.get('added')}")


def test_an_unconfirmed_id_does_not_enter_and_is_named(tmp_path):
    """An empty header is not a confirmation — one empty response is no
    evidence."""
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _seed(cache, "玉成段")

    report = _refresh(cache, "玉成段", _rows("10901211", "11412011"),
                      {"10901211": {"NAME": "已核定", "CASE_NAME": "案"}})

    saved = json.loads((cache / "玉成段" / "result.json").read_text(encoding="utf-8"))
    assert "11412011" not in saved["city_case_ids"], (
        "an id with no header row must not enter the case list")
    assert "11412011" in report.get("unconfirmed", []), (
        f"the unconfirmed id must be named, got {report.get('unconfirmed')}")


def test_an_id_the_search_already_returned_is_not_added_twice(tmp_path):
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _seed(cache, "玉成段")

    _refresh(cache, "玉成段", _rows("10901211", "11412012"),
             {"10901211": {"NAME": "已核定", "CASE_NAME": "案"},
              "11412012": {"NAME": "已核定", "CASE_NAME": "案"}})

    saved = json.loads((cache / "玉成段" / "result.json").read_text(encoding="utf-8"))
    ids = saved["city_case_ids"]
    assert ids.count("10901211") == 1, f"the id must appear once, got {ids}"


def test_the_existing_ids_keep_their_positions(tmp_path):
    """The positional fallback binds by index, so an appended id must not
    shift the existing ones."""
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _seed(cache, "玉成段")

    _refresh(cache, "玉成段", _rows("10901211", "11412011"),
             {"10901211": {"NAME": "已核定", "CASE_NAME": "案"},
              "11412011": {"NAME": "已核定", "CASE_NAME": "案"}})

    saved = json.loads((cache / "玉成段" / "result.json").read_text(encoding="utf-8"))
    assert saved["city_case_ids"][0] == "10901211", (
        f"the existing id must keep its position, got {saved['city_case_ids']}")


def test_a_row_naming_another_section_is_not_a_candidate(tmp_path):
    """The list is scoped by the project's own section, so a refresh spends a
    header request only on the ids that could name its section."""
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _seed(cache, "玉成段")
    rows = [{"case_id": "09503232",
             "T_name": "擬訂臺北市南港區新光段二小段134地號等13筆土地都市更新事業計畫案"}]
    headers = {"09503232": {"NAME": "已核定", "CASE_NAME": "案"}}

    report = _refresh(cache, "玉成段", rows, headers)

    saved = json.loads((cache / "玉成段" / "result.json").read_text(encoding="utf-8"))
    assert "09503232" not in saved["city_case_ids"]
    assert "09503232" not in report.get("unconfirmed", []), (
        "a row naming another section is not even a candidate")


def test_a_bound_node_does_not_keep_the_unplaced_flag(tmp_path):
    """The flag says the node binds no case. When the second id source (or the
    alias merge) gives the node its case, the flag must go — a flag carried
    forward by the --from-js loader would read as a live finding."""
    from urtpe import cli
    from urtpe.graph import build_project_graph

    cache = tmp_path / ".link_cache"
    cache.mkdir()
    _seed(cache, "玉成段")

    # a node that carries the flag, and a project whose cache binds it
    doc = {
        "projects": [{
            "project_id": "玉成段", "anchor_recno": 563,
            "nodes": [{
                "recno": 563, "date": "2021-08-03", "iso_date": "2021-08-03",
                "stage": "擬訂", "stage_index": 0, "track": "事業計畫",
                "area": "", "case_name": "擬訂臺北市南港區玉成段二小段166地號等12筆土地都市更新事業計畫案",
                "land": "臺北市南港區玉成段二小段166地號等12筆土地",
                "section": "玉成段二小段", "first_parcel": "166",
                "parcels": ["166"], "aliases": {}, "land_count": 12,
                "district": "南港區", "district_land": "南港區",
                "area_section": "", "is_current": True,
                "implementer": "甲", "planner": "乙",
                "review_flags": ["節點未能對應平台案件(案名:擬訂臺北市南港區玉成段二小段166地號等12筆土地都市更新事業計畫案, 日期:2021-08-03)"],
                "auto_fixes": [],
            }],
        }],
        "published_date": "2026-10-15",
        "counts": {"projects": 1, "records": 1},
    }
    js = tmp_path / "projects.data.js"
    js.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";",
                  encoding="utf-8")
    projects, _meta = cli._load_projects_from_js(str(js))

    from urtpe.links import DiscoveryResult, attach_links_to_projects
    disc = DiscoveryResult(project_id="玉成段", land_core="x")
    disc.city_case_ids = ["10901211"]
    disc.case_milestones = {"10901211": {"核定日期": "2021/08/03"}}
    disc.taipei_milestones = {"核定日期": "2021/08/03"}
    attach_links_to_projects(projects, {"玉成段": disc})

    graph = build_project_graph(projects[0], implementer="甲", name="案")
    flags = graph["nodes"][0]["review_flags"]
    assert not any("節點未能對應平台案件" in f for f in flags), (
        f"a bound node must not keep the unplaced flag, got {flags}")
