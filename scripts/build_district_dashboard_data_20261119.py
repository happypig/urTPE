"""Build the data files behind the "Taipei Case Sources" dashboard artifact
(docs/portals/urotpe_district_pages.md §8). Offline: reads the two probes' outputs, the
Viewer payload and the saved 168 snapshot; writes only under --work.

Outputs under --work/dashboard-data/:
  cp-rows.json          every distinct district row, header evidence added to the three
                        meeting-label rows
  p168-rows.json        the saved 168 snapshot, unchanged
  viewer-ids.json       Viewer case ids that carry a name (candidate names, else the node's)
  duplicates.json       the ids that appear on more than one row, with the live header
  field-reference.json  the cp / 168 field comparison
  metadata.json         dates and source urls

Not generated here: `special-records.json` (the nine amendments and three meeting-label
records) was written by hand from the header check. It is a reading of that evidence, not a
computation, so it is not reproduced by a script.

Two facts to keep in mind when reading the output:
  * The Viewer set here holds the ids that carry a name (candidate names, else the node's).
    The probe's membership flags use every id in links.taipei, so that set is a little
    larger. The extra ids carry no name. On 2026-11-20 the two sets held 2,028 and 2,030.
  * `11510016` is added to the header table by hand below: it was the one conflicting id the
    candidate pass never asked about, so it was read live once and recorded.

Usage:  python scripts/build_district_dashboard_data_20261119.py [--work DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MEETING_LABELS = ("516次審議會", "511次審議會", "第522次審議會")

FIELDS = [
    {"concept": "Case ID", "cp_field": "案件編號", "p168_field": "case_id", "comparison": "Shared numeric ID. Four IDs have conflicting district rows."},
    {"concept": "Case name", "cp_field": "案名", "p168_field": "T_name", "comparison": "Same concept; the text can differ between sources."},
    {"concept": "District", "cp_field": "行政區", "p168_field": "Not supplied", "comparison": "The 168 name often contains a district, but there is no separate field."},
    {"concept": "Location", "cp_field": "區位", "p168_field": "Not supplied", "comparison": "Available on cp; obtain it through the detail API for 168 cases."},
    {"concept": "Applicant", "cp_field": "實施者", "p168_field": "Not supplied", "comparison": "Available on cp; the detail header supplies EXE_NAME / exe_name2."},
    {"concept": "Review state", "cp_field": "目前辦理情形", "p168_field": "stage", "comparison": "Different vocabulary. cp gives the detailed process state; 168 gives a programme stage."},
    {"concept": "Schedule state", "cp_field": "Not supplied", "p168_field": "progress", "comparison": "In this snapshot, values are 符合進度 or -."},
    {"concept": "Delay reason", "cp_field": "Not supplied", "p168_field": "reason", "comparison": "The 168 programme supplies this separately."},
    {"concept": "Completion rate", "cp_field": "Not supplied", "p168_field": "COMPLETION_RATE", "comparison": "A programme metric; - is common in this snapshot."},
    {"concept": "Programme note", "cp_field": "Not supplied", "p168_field": "MEMO", "comparison": "Can hold an approval announcement date or programme note."},
    {"concept": "List size", "cp_field": "One table per district", "p168_field": "TotalCount", "comparison": "cp supplies no total; P_project168 repeats the total on every row."},
    {"concept": "Paging / filters", "cp_field": "District s parameter", "p168_field": "type, TRANSITION_NO, pageIndex, pageSize", "comparison": "The page also offers a 正軌/轉軌 lookup separately."},
    {"concept": "Detail link", "cp_field": "No link in the table", "p168_field": "Rendered from case_id", "comparison": "Both ID spaces feed r_progress_detail.aspx?case_id=<id>."},
]


def iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", default=str(ROOT / "data_test" / "district_probe"))
    args = ap.parse_args()
    work = Path(args.work)
    out = work / "dashboard-data"
    out.mkdir(parents=True, exist_ok=True)

    def write(name, value):
        path = out / name
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(name, path.stat().st_size)

    distinct = work / "preapproval_distinct_rows.json"
    verification = work / "district_header_verification.json"
    cp = json.loads(distinct.read_text(encoding="utf-8"))
    headers = {r["case_id"]: r for r in json.loads(verification.read_text(encoding="utf-8"))}

    from urtpe.archive import DEFAULT_ARCHIVE_ROOT
    archive = Path(DEFAULT_ARCHIVE_ROOT)
    state = json.loads((archive / "p168_state.json").read_text(encoding="utf-8"))
    p168 = json.loads((archive / "p168_snapshots" / f"p168-{state['sha256'][:16]}.json").read_text(encoding="utf-8"))
    payload = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))

    # Every district row is kept: an id can occur twice with different names.
    cp_fields = ("district", "case_id", "case_name", "place", "implementer", "status", "source_url")
    cp_rows = [{k: r[k] for k in cp_fields} for r in cp]
    for r in cp_rows:
        evidence = headers.get(r["case_id"])
        if evidence and not evidence["error"] and r["case_name"] in MEETING_LABELS:
            r["header_name"] = evidence["header"].get("CASE_NAME", "")
            r["header_status"] = evidence["header"].get("NAME", "")

    viewer_names = {}
    for project in payload["projects"]:
        for cid, name in ((project.get("links") or {}).get("candidate_names") or {}).items():
            viewer_names.setdefault(cid, set()).add(name)
        for node in project["nodes"]:
            for cid in (node.get("links") or {}).get("taipei") or []:
                if cid not in viewer_names:
                    viewer_names[cid] = {node["case_name"]}
    viewer_rows = [{"case_id": cid, "names": sorted(names), "published_date": payload["published_date"]}
                   for cid, names in sorted(viewer_names.items())]

    # The one conflicting id the candidate pass never asked about; read live once on 2026-11-19.
    headers.setdefault("11510016", {
        "error": "",
        "header": {
            "CASE_NAME": "變更(第二次)臺北市大安區仁愛段五小段480地號等2筆(原1筆)土地都市更新權利變換計畫案",
            "NAME": "權利變換計畫階段─業已提出申請審查",
        },
    })
    by_id = {}
    for row in cp_rows:
        by_id.setdefault(row["case_id"], []).append(row)
    duplicates = []
    for cid, rows in sorted(by_id.items()):
        if len(rows) < 2:
            continue
        evidence = headers.get(cid, {})
        duplicates.append({
            "case_id": cid,
            "rows": rows,
            "header_name": evidence.get("header", {}).get("CASE_NAME", ""),
            "header_status": evidence.get("header", {}).get("NAME", ""),
            "header_error": evidence.get("error", ""),
            "viewer_names": sorted(viewer_names.get(cid, [])),
        })

    write("cp-rows.json", cp_rows)
    write("p168-rows.json", p168)
    write("viewer-ids.json", viewer_rows)
    write("duplicates.json", duplicates)
    write("field-reference.json", FIELDS)
    write("metadata.json", {
        "viewer_published_date": payload["published_date"],
        "viewer_generated_at": payload["generated_at"],
        "viewer_project_count": payload["counts"]["projects"],
        "p168_snapshot_at": state["checked_at"],
        "cp_checked_at": iso(distinct),
        "header_checked_at": iso(verification),
        "cp_row_count": len(cp_rows),
        "source_urls": [
            "https://uro.gov.taipei/cp.aspx?n=E06DCE2A43AF2B4F",
            "https://gis.uro.taipei/P_project168.aspx",
            "https://happypig.github.io/urTPE/viewer/",
        ],
    })


if __name__ == "__main__":
    main()
