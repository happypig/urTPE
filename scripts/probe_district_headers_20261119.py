"""Check district-table rows against the live case header (docs/portals/urotpe_district_pages.md §6).

Reads `preapproval_distinct_rows.json` from `probe_district_pages_20261119.py`, keeps the
rows the screen names (absent from the Viewer, and either an active review stage or an
unknown status), and asks `get_project168_top.ashx` for each. It compares name, status,
place and implementer.

Why it is bounded: the endpoint is public but undocumented, and a header reply proves
nothing about identity by itself (four ids name two cases each). It runs only for the
screened candidates, three requests at a time, never as a sweep. Use --limit for a
smoke run.

Outputs under --work (default data_test/district_probe/):
  district_header_verification.json   one entry per candidate, with the header and four flags
  district_header_summary.json        counts, the errors, and the rows whose header disagrees

Usage:  python scripts/probe_district_headers_20261119.py [--work DIR] [--limit N]
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = "https://gis.uro.taipei/ashx/get_project168_top.ashx"
ACTIVE_MARKERS = (
    "業已提出申請審查", "業申請幹事會審查", "業已辦理公開展覽",
    "業經幹事會審查", "業申請幹事會複審", "業經幹事會複審完竣",
    "業申請聽證", "業已辨理聽證", "業申請審議會審議",
    "業經審議會審議通過", "申請報府核定中",
)


def header(case_id):
    request = Request(API, data=urlencode({"case_id": case_id}).encode(), headers={
        "User-Agent": "Mozilla/5.0 (compatible; urTPE-source-review/1.0)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://gis.uro.taipei/r_progress_detail.aspx?case_id=" + case_id,
    })
    with urlopen(request, timeout=60) as response:
        raw = response.read()
        if raw[:2] == b"\x1f\x8b" or response.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8-sig", "replace"))


def norm(value):
    return re.sub(r"\s+", "", value or "")


def one(row):
    time.sleep(0.1)
    try:
        rows = header(row["case_id"])
        item = rows[0] if rows else {}
        error = "" if rows else "no header row"
    except Exception as exc:  # a failed check is unknown evidence, recorded as such
        item = {}
        error = f"{type(exc).__name__}: {exc}"
    return {
        "case_id": row["case_id"],
        "case_name": row["case_name"],
        "status": row["status"],
        "group": row["group"],
        "header": item,
        "error": error,
        "name_matches": norm(row["case_name"]) == norm(item.get("CASE_NAME")),
        "status_matches": row["status"] == item.get("NAME"),
        "place_matches": norm(row["place"]) == norm(item.get("PLACE")),
        "implementer_matches": norm(row["implementer"]) in (norm(item.get("EXE_NAME")), norm(item.get("exe_name2"))),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", default=str(ROOT / "data_test" / "district_probe"))
    ap.add_argument("--limit", type=int, default=0, help="check only the first N candidates")
    args = ap.parse_args()
    work = Path(args.work)

    rows = json.loads((work / "preapproval_distinct_rows.json").read_text(encoding="utf-8"))
    candidates = []
    for row in rows:
        if row["in_viewer_by_id"] or row["in_viewer_by_name"]:
            continue
        active = any(marker in row["status"] for marker in ACTIVE_MARKERS)
        if active or row["status"] in ("", "無", "其他"):
            row["group"] = "active" if active else "unknown"
            candidates.append(row)
    if args.limit:
        candidates = candidates[:args.limit]

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for index, result in enumerate(executor.map(one, candidates), start=1):
            results.append(result)
            if index % 100 == 0:
                print(f"checked {index}/{len(candidates)}", flush=True)
    (work / "district_header_verification.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    active = [r for r in results if r["group"] == "active" and not r["error"]]
    unknown = [r for r in results if r["group"] == "unknown" and not r["error"]]
    summary = {
        "candidate_rows": len(candidates),
        "active_rows": len(active),
        "unknown_rows": len(unknown),
        "errors": [r for r in results if r["error"]],
        "active_field_mismatches": {
            key: [r for r in active if not r[key]]
            for key in ("name_matches", "status_matches", "place_matches", "implementer_matches")
        },
        "unknown_status_counts": Counter(r["header"].get("NAME") for r in unknown),
        "unknown_name_match_count": sum(r["name_matches"] for r in unknown),
        "active_approval_status_count": sum("業經本府核定" in (r["header"].get("NAME") or "") for r in active),
        "active_closed_status_count": sum(
            any(word in (r["header"].get("NAME") or "") for word in ("駁回", "自行撤回", "撤銷核准"))
            for r in active),
    }
    (work / "district_header_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v)
                      for k, v in summary.items() if k != "active_field_mismatches"},
                     ensure_ascii=False, indent=2))
    print("active field mismatches:",
          {k: len(v) for k, v in summary["active_field_mismatches"].items()})


if __name__ == "__main__":
    main()
