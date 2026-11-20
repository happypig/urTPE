"""Crawl the 12 uro.gov.taipei district case tables and compare them with the Viewer and
the 168 list (docs/portals/urotpe_district_pages.md §1, §3, §5). Read-only.

Why this exists: the district tables are the only public list that holds cases *before*
approval, and nothing in `urtpe/` reads them. This probe measured them once, on
2026-11-19. It is dated archaeology, like the `probe_*.py` family: it reads the network and
the emitted payload, and writes only under --work.

Two traps it encodes, both measured:
  * The entry URL and the 北投 district link return the same 270 rows. Following both
    gives 3,925 rows; the distinct set is 3,655. Duplicates are removed on the six
    published fields, never on the source URL.
  * A case id is seven or eight digits. An eight-digit-only parser silently drops 44 legacy
    北投 rows (226 instead of 270). Ids are normalised with zfill(8).

Outputs under --work (default data_test/district_probe/):
  preapproval_rows.json           every parsed row, duplicates kept (3,925 on 2026-11-19)
  preapproval_distinct_rows.json  first-seen rows on the six fields (3,655), with the three
                                  membership flags; the later probes read this file
  preapproval_analysis.json       the screen's counts, computed on the distinct rows

Usage:  python scripts/probe_district_pages_20261119.py [--work DIR] [--pause 0.25]
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "https://uro.gov.taipei/cp.aspx?n=E06DCE2A43AF2B4F"
SIX_FIELDS = ("district", "case_id", "case_name", "place", "implementer", "status")

# An allowlist, not "contains 核定": 申請報府核定中 is still pre-approval.
ACTIVE_MARKERS = (
    "業已提出申請審查", "業申請幹事會審查", "業已辦理公開展覽",
    "業經幹事會審查", "業申請幹事會複審", "業經幹事會複審完竣",
    "業申請聽證", "業已辨理聽證", "業申請審議會審議",
    "業經審議會審議通過", "申請報府核定中",
)


class DistrictPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.district_links = []
        self.rows = []
        self._table_depth = 0
        self._row = None
        self._cell = None
        self._skip = 0
        self._cell_links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        if tag == "table":
            self._table_depth += 1
        if self._table_depth and tag == "tr":
            self._row = []
        if self._row is not None and tag in ("td", "th"):
            self._cell = []
            self._cell_links = []
        if tag == "a" and attrs.get("href"):
            href = urljoin(BASE, attrs["href"])
            if "E06DCE2A43AF2B4F" in href and "s=" in href:
                self.district_links.append((href, attrs.get("title", "")))
            if self._cell is not None:
                self._cell_links.append(href)
        if self._cell is not None and tag == "br":
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        if self._cell is not None and tag in ("td", "th"):
            self._row.append({
                "text": re.sub(r"\s+", " ", "".join(self._cell)).strip(),
                "links": self._cell_links,
            })
            self._cell = None
        if self._row is not None and tag == "tr":
            self.rows.append(self._row)
            self._row = None
        if tag == "table":
            self._table_depth = max(0, self._table_depth - 1)

    def handle_data(self, data):
        if self._cell is not None and not self._skip:
            self._cell.append(data)


def fetch(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; urTPE-source-review/1.0)",
        "Accept-Encoding": "gzip",
    })
    with urlopen(req, timeout=60) as response:
        raw = response.read()
        if raw[:2] == b"\x1f\x8b" or response.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode("utf-8-sig", "replace")


def parse(html):
    parser = DistrictPage()
    parser.feed(html)
    parsed_rows = []
    for cells in parser.rows:
        texts = [c["text"] for c in cells]
        if len(texts) >= 6 and re.fullmatch(r"\d{7,8}", texts[1]) and texts[0] != "行政區":
            parsed_rows.append({
                "district": texts[0],
                "case_id": texts[1].zfill(8),
                "case_name": texts[2],
                "place": texts[3],
                "implementer": texts[4],
                "status": texts[5],
                "extra_cells": texts[6:],
                "links": [link for c in cells for link in c["links"]],
            })
    links = list(dict.fromkeys(url for url, _ in parser.district_links))
    return parsed_rows, links


def norm(text):
    return re.sub(r"\s+", "", text or "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", default=str(ROOT / "data_test" / "district_probe"))
    ap.add_argument("--pause", type=float, default=0.25, help="seconds between page requests")
    args = ap.parse_args()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    first = fetch(BASE)
    _, district_links = parse(first)
    urls = list(dict.fromkeys([BASE] + district_links))
    all_rows, fetch_report = [], []
    for index, url in enumerate(urls):
        html = first if index == 0 else fetch(url)
        rows, _ = parse(html)
        fetch_report.append({"url": url, "rows": len(rows),
                             "districts": Counter(row["district"] for row in rows)})
        for row in rows:
            row["source_url"] = url
        all_rows.extend(rows)
        if index < len(urls) - 1:
            time.sleep(args.pause)

    payload = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
    viewer_ids, viewer_names = {}, defaultdict(list)
    for project in payload["projects"]:
        for node in project["nodes"]:
            viewer_names[norm(node["case_name"])].append((project["project_id"], node["recno"]))
            for cid in (node.get("links") or {}).get("taipei") or []:
                viewer_ids.setdefault(cid, []).append((project["project_id"], node["recno"]))
        for cid in (project.get("links") or {}).get("taipei") or []:
            viewer_ids.setdefault(cid, [])

    from urtpe.archive import DEFAULT_ARCHIVE_ROOT
    archive = Path(DEFAULT_ARCHIVE_ROOT)
    state = json.loads((archive / "p168_state.json").read_text(encoding="utf-8"))
    snapshot = archive / "p168_snapshots" / f"p168-{state['sha256'][:16]}.json"
    p168_ids = {str(row["case_id"]) for row in json.loads(snapshot.read_text(encoding="utf-8"))}

    for row in all_rows:
        row["in_viewer_by_id"] = row["case_id"] in viewer_ids
        row["in_viewer_by_name"] = norm(row["case_name"]) in viewer_names
        row["in_168"] = row["case_id"] in p168_ids

    # Distinct on the six published fields, first seen wins. The entry page and the 北投
    # link are the same table, so this removes exactly the crawl artefact.
    seen, distinct = set(), []
    for row in all_rows:
        key = tuple(row[f] for f in SIX_FIELDS)
        if key not in seen:
            seen.add(key)
            distinct.append(row)

    absent = [r for r in distinct if not r["in_viewer_by_id"] and not r["in_viewer_by_name"]]
    active = [r for r in absent if any(m in r["status"] for m in ACTIVE_MARKERS)]
    unknown = [r for r in absent if r["status"] in ("", "無", "其他")]
    outside_168 = [r for r in active if not r["in_168"]]
    by_id = Counter(r["case_id"] for r in distinct)
    result = {
        "fetches": fetch_report,
        "raw_rows": len(all_rows),
        "distinct_rows": len(distinct),
        "distinct_case_ids": len(by_id),
        "ids_on_more_than_one_row": sorted(c for c, n in by_id.items() if n > 1),
        "cell_link_count": sum(len(r["links"]) for r in distinct),
        "extra_cell_count": sum(bool(r["extra_cells"]) for r in distinct),
        "status_counts": Counter(r["status"] for r in distinct),
        "viewer_id_space": len(viewer_ids),
        "in_viewer_by_id": sum(r["in_viewer_by_id"] for r in distinct),
        "in_168": sum(r["in_168"] for r in distinct),
        "absent_from_viewer": len(absent),
        "active_review": len(active),
        "active_review_outside_168": len(outside_168),
        "unknown_status": len(unknown),
        "active_status_counts": Counter(r["status"] for r in active),
        "active_district_counts": Counter(r["district"] for r in active),
        "snapshot": str(snapshot),
        "snapshot_checked_at": state["checked_at"],
        "viewer_published_date": payload["published_date"],
        "viewer_counts": payload["counts"],
    }
    (work / "preapproval_rows.json").write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (work / "preapproval_distinct_rows.json").write_text(
        json.dumps(distinct, ensure_ascii=False, indent=2), encoding="utf-8")
    (work / "preapproval_analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
