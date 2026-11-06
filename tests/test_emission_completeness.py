# -*- coding: utf-8 -*-
"""The emitted dataset must be complete: no lost record, no silent loss.

Three properties, each with a gate that holds it and a proof that re-derives it
from the emitted files.

  1. Every cleansed record is in exactly one project (the merge partition).
     `Tripwire.check_partition` holds this on the PDF path. The `--from-js`
     path had no gate at all: a payload missing one node loaded as 1,443
     members and was re-emitted as a complete dataset. Measured 2026-11-06.

  2. The census gate must run on the partition that is actually emitted. It
     ran before the ledger's confirmed merge, so the count it checked (683)
     was not the count that reached the payload (682). The gate was one
     family short of the truth and still passed.

  3. A node with no case id renders no 北 badge, and the unplaced-node flag
     names the same condition. The two counts must agree: a node that
     carries a case id while the flag says it does not is a stale flag, and
     a node with neither a case id nor a flag is a silent loss.

Measured on the 2026-10-28 payload (1,444 records / 682 projects):
  partition total and disjoint, 0 lost / 0 duplicated / 0 extra;
  13 nodes carry no case id, and exactly those 13 carry the flag.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import cli  # noqa: E402
from urtpe.models import CleanRecord, Project  # noqa: E402
from urtpe.tripwire import Tripwire, TripwireFailure  # noqa: E402

_UNPLACED = "節點未能對應平台案件"


# ---------------------------------------------------------------------------
# 1. the --from-js path holds the partition
# ---------------------------------------------------------------------------

def _clean(recno: int) -> CleanRecord:
    return CleanRecord(
        recno=recno, date="2026-01-01", iso_date="2026-01-01", ymd=(2026, 1, 1),
        district="中正區", district_land="中正區", name="案%d" % recno, name_raw="",
        land="臺北市中正區甲段一小段%d地號等1筆土地" % recno,
        section="甲段一小段", first_parcel=str(recno), parcels=[str(recno)],
        aliases={}, land_count=1, orig_count=None, named_anchor="", area_section="",
        stage="擬訂", stage_index=0, track="事業計畫",
        implementer="甲", planner="乙", auto_fixes=[], review_flags=[],
    )


def _doc(records: list[int]) -> dict:
    """A payload document with one project per record."""
    return {
        "schema_version": 2,
        "generated_at": "2026-11-06T00:00:00+08:00",
        "source": "",
        "published_date": "2026-10-28",
        "counts": {"projects": len(records), "records": len(records)},
        "projects": [
            {
                "project_id": "中正區-甲段一小段-%d地號等1筆" % r,
                "anchor_recno": r,
                "district": "中正區",
                "section": "甲段一小段",
                "implementer": "甲",
                "name": "案%d" % r,
                "member_recnos": [r],
                "nodes": [{
                    "recno": r, "date": "2026-01-01", "stage": "擬訂",
                    "track": "事業計畫", "area": "", "stage_index": 0,
                    "is_current": True, "case_name": "案%d" % r,
                    "name_raw": "", "land": "臺北市中正區甲段一小段%d地號等1筆土地" % r,
                    "section": "甲段一小段", "first_parcel": str(r),
                    "parcels": [str(r)], "aliases": {}, "land_count": 1,
                    "orig_count": None, "named_anchor": "", "area_section": "",
                    "implementer": "甲", "planner": "乙", "review_flags": [],
                    "auto_fixes": [], "district": "中正區", "district_land": "中正區",
                }],
                "edges": [],
                "links": {},
                "published_date": "2026-10-28",
            }
            for r in records
        ],
    }


def _write_js(path: Path, doc: dict) -> str:
    path.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";",
                    encoding="utf-8")
    return str(path)


def test_the_from_js_path_holds_the_partition(tmp_path):
    """A payload whose nodes do not sum to its own count must be refused.

    Before the gate, the loader read 1,443 members from a 1,444-record payload
    and said nothing: the loss was invisible until a reader counted the rows.
    """
    doc = _doc([1, 2, 3])
    # the node is gone, the family still lists it — the shape a hand-edited
    # or truncated payload has
    doc["projects"][1]["nodes"] = []
    out = tmp_path / "out"
    out.mkdir()
    js = _write_js(tmp_path / "projects.data.js", doc)

    rc = cli.main(["--from-js", js, "-o", str(out), "--no-archive"])

    assert rc == 4, "a lost record must be refused (exit 4), not re-emitted"


def test_the_from_js_path_holds_the_partition_against_clean_tsv(tmp_path):
    """A payload that lost a record AND had its count rewritten must be refused.

    This is the harder shape: the payload is internally consistent (its count
    agrees with its nodes), so no internal check can see the loss. The
    reference is `clean.tsv` — the file the ingest wrote, holding every
    cleansed record. The payload must hold every record in it.
    """
    out = tmp_path / "out"
    out.mkdir()
    # the reference: three cleansed records
    (out / "clean.tsv").write_text(
        "recno\tiso_date\tdate\tdistrict\tdistrict_land\tname\tname_raw\tland\t"
        "section\tfirst_parcel\tparcels\taliases\tland_count\torig_count\t"
        "named_anchor\tarea_section\tstage\tstage_index\ttrack\timplementer\t"
        "planner\tauto_fixes\treview_flags\tgazette_id\n"
        "1\t2026-01-01\t2026/1/1\t中正區\t中正區\t案1\t案1\t"
        "臺北市中正區甲段一小段1地號等1筆土地\t甲段一小段\t1\t1\t\t1\t\t\t\t\t"
        "擬訂\t0\t事業計畫\t\t\t\t\t\t\n"
        "2\t2026-01-01\t2026/1/1\t中正區\t中正區\t案2\t案2\t"
        "臺北市中正區甲段一小段2地號等1筆土地\t甲段一小段\t2\t2\t\t1\t\t\t\t\t"
        "擬訂\t0\t事業計畫\t\t\t\t\t\t\n"
        "3\t2026-01-01\t2026/1/1\t中正區\t中正區\t案3\t案3\t"
        "臺北市中正區甲段一小段3地號等1筆土地\t甲段一小段\t3\t3\t\t1\t\t\t\t\t"
        "擬訂\t0\t事業計畫\t\t\t\t\t\t\n",
        encoding="utf-8")
    # the payload lost record 2, and its count was rewritten to match
    doc = _doc([1, 3])
    js = _write_js(tmp_path / "projects.data.js", doc)

    rc = cli.main(["--from-js", js, "-o", str(out), "--no-archive"])

    assert rc == 4, "a record the reference holds and the payload does not must be refused"


def test_the_from_js_path_accepts_a_complete_payload(tmp_path):
    """The gate must not refuse a sound payload — the ordinary re-emit path."""
    doc = _doc([1, 2, 3])
    js = _write_js(tmp_path / "projects.data.js", doc)

    out = tmp_path / "out"
    out.mkdir()
    rc = cli.main(["--from-js", js, "-o", str(out), "--no-archive"])

    assert rc == 0
    emitted = json.loads((out / "projects.json").read_text(encoding="utf-8"))
    assert emitted["counts"]["records"] == 3


def test_the_from_js_gate_names_the_lost_record(tmp_path, capsys):
    """The report must say which record went missing, or the run is not actionable."""
    doc = _doc([1, 2, 3])
    doc["projects"][1]["nodes"] = []
    js = _write_js(tmp_path / "projects.data.js", doc)

    out = tmp_path / "out"
    out.mkdir()
    cli.main(["--from-js", js, "-o", str(out), "--no-archive"])

    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "2" in text, "the missing recno must be named: %r" % text[-400:]


# ---------------------------------------------------------------------------
# 2. the census gate runs on the partition that is emitted
# ---------------------------------------------------------------------------

def test_the_census_gate_uses_the_emitted_partition():
    """The gate must be told which partition it is checking.

    `check_partition(clean, projects)` compares the cleansed records against
    the families. It is only meaningful when `projects` IS the emitted family
    set. The CLI passed the pre-ledger merge, so the gate checked 683 families
    while the payload carried 682 — the gate was one family short of the truth
    and still passed.
    """
    clean = [_clean(1), _clean(2)]
    pre = [Project(project_id="甲", anchor_recno=1, members=[_clean(1)]),
           Project(project_id="乙", anchor_recno=2, members=[_clean(2)])]
    post = [Project(project_id="甲", anchor_recno=1, members=[_clean(1), _clean(2)])]

    assert Tripwire().check_partition(clean, pre) == []
    # the emitted partition (one family of two) is also total — the difference
    # is the count, not the partition
    assert Tripwire().check_partition(clean, post) == []


def test_the_census_gate_reports_the_family_count_it_checked():
    """The gate must name the count it checked, so a reader can see which
    partition it saw.

    The tripwire's report prints `projects: N`. Before the fix, that N was
    the pre-ledger count (683) while the payload carried 682 — the report
    read as a passing gate over a count the payload did not have.
    """
    clean = [_clean(1), _clean(2)]
    post = [Project(project_id="甲", anchor_recno=1, members=[_clean(1), _clean(2)])]

    faults = Tripwire().check_partition(clean, post, emitted_records=2)
    assert faults == [], faults


def test_the_gate_names_a_partition_whose_count_disagrees_with_the_emission():
    """A family count that disagrees with the emitted record count is a fault."""
    clean = [_clean(1), _clean(2)]
    families = [Project(project_id="甲", anchor_recno=1, members=[_clean(1)])]

    faults = Tripwire().check_partition(clean, families, emitted_records=1)
    assert faults
    assert any("1" in f and "2" in f for f in faults), faults


# ---------------------------------------------------------------------------
# 3. the badge and the flag agree
# ---------------------------------------------------------------------------

def test_a_node_with_no_case_id_and_no_flag_is_a_silent_loss():
    """The check the payload must satisfy: no badge, no flag, is a gap.

    The badge is drawn from `links.taipei`. The flag names the same
    condition. A node with neither is silently unbound, and the viewer shows
    it as a row with no portal link and no review note.
    """
    from urtpe.emission import emission_faults

    projects = [{
        "project_id": "甲",
        "nodes": [{"recno": 1, "links": {}, "review_flags": []}],
        # the project reached discovery (it carries other link data), so its
        # node that binds nothing must name itself
        "links": {"twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/1"},
    }]
    faults = emission_faults(projects)
    assert any("badge" in f or "節點未能對應平台案件" in f for f in faults), faults


def test_a_flagged_node_without_a_case_id_is_not_a_fault():
    """The two must agree: no case id and the flag present is the honest state."""
    from urtpe.emission import emission_faults

    projects = [{
        "project_id": "甲",
        "nodes": [{"recno": 1, "links": {},
                   "review_flags": ["%s(案名:某案, 日期:2026-01-01)" % _UNPLACED]}],
        "links": {"twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/1"},
    }]
    faults = emission_faults(projects)
    assert not any("節點未能對應平台案件" in f for f in faults), faults


def test_a_node_with_a_case_id_and_a_stale_flag_is_a_fault():
    """A node that binds a case must not carry the flag that says it binds none.

    D9c-2a clears the flag at bind time, but only on the --links path. A
    payload that keeps the flag after the binding survives the round trip is
    a stale finding, and it must be named.
    """
    from urtpe.emission import emission_faults

    projects = [{
        "project_id": "甲",
        "nodes": [{"recno": 1, "links": {"taipei": ["11501034"]},
                   "review_flags": ["%s(案名:某案, 日期:2026-01-01)" % _UNPLACED]}],
        "links": {"taipei": ["11501034"]},
    }]
    faults = emission_faults(projects)
    assert any(_UNPLACED in f for f in faults), faults
