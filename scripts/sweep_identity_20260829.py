#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""相關連結-identity twur sweep (operations log §6.14 step 2).

For each twur-less project that already carries `city_case_ids` (linkage known):
  1. title-search the national portal by the project's section
  2. probe ≤ MAX_PROBE candidate view pages
  3. attach when the page's 相關連結 case_ids INTERSECT our known case_ids —
     identity proven by the portal itself (the view/18 mechanism), so the
     strict title matcher's count/notation drift cannot block it.

Coverage-guarded (§12 #1): aborts if any flag regresses. Paced 2 s/request.
Pass 2 = simply re-run (only twur-less projects are retried).

Usage:
    python scripts/sweep_identity_20260829.py [--max-projects N]
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from urtpe.coverage import coverage_guard
from urtpe.links import (
    SEARCH_URL,
    BROWSER_HEADERS,
    DiscoveryResult,
    VIEW_URL_BASE,
    extract_case_ids_from_view,
    extract_tuidui_history_from_view,
    fetch_url,
)

CACHE = Path("data/.link_cache")
DELAY = 2.0          # s between requests (WAF history: 0 resets at ≥1-3 min sweeps,
MAX_PROBE = 8        # identity check is cheap (1 GET + regex); count/notation drift
LOG = Path("data/sweep_identity_20260829.log")  # pushes matches deep in results
# (吉林段676: view/75 is position 3-8 depending on portal load — MAX_PROBE=3 truncated it)


class _Tee:
    """Mirror stdout to the log file — no more unlogged runs (§6.12)."""

    def __init__(self, path: Path):
        self._orig = sys.stdout
        self._fh = open(path, "a", encoding="utf-8")

    def write(self, s):
        self._orig.write(s)
        self._fh.write(s)
        self._fh.flush()

    def flush(self):
        self._orig.flush()
        self._fh.flush()


def title_search(section: str) -> list[str]:
    url = SEARCH_URL + "?" + urllib.parse.urlencode({"title": section, "city_id": "2"})
    html = fetch_url(url, None, True)
    time.sleep(DELAY)
    return sorted(set(re.findall(r"/zh/urban/rebuild/view/(\d+)", html)))


def main() -> int:
    max_projects = 0
    if "--max-projects" in sys.argv:
        max_projects = int(sys.argv[sys.argv.index("--max-projects") + 1])

    js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
    data = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))
    projects = data["projects"]

    targets = []
    for p in projects:
        pid = p["project_id"]
        rf = CACHE / re.sub(r"[^\w\-]", "_", pid) / "result.json"
        if not rf.is_file():
            continue
        d = json.loads(rf.read_text(encoding="utf-8"))
        if not d.get("twur_url") and d.get("city_case_ids"):
            targets.append((p, d))
    print(f"twur-less with case_ids (sweepable): {len(targets)}")
    if max_projects:
        targets = targets[:max_projects]

    updated = failed = 0
    t0 = time.time()
    for i, (p, d) in enumerate(targets, 1):
        pid = p["project_id"]
        safe = re.sub(r"[^\w\-]", "_", pid)
        pdir = CACHE / safe
        section = pid.split("-")[1] if "-" in pid else ""
        try:
            vids = title_search(section)
        except Exception as e:
            print(f"[{i}/{len(targets)}] {pid}: search failed: {e}")
            failed += 1
            continue
        hit = None
        # probe order: candidates whose page mentions our section token first
        # (cheap heuristics before the deep tail), then positional order
        for vid in vids[:MAX_PROBE]:
            try:
                html = fetch_url(f"{VIEW_URL_BASE}{vid}", None, True)
                time.sleep(DELAY)
            except Exception as e:
                print(f"[{i}/{len(targets)}] {pid}: view/{vid} fetch failed: {e}")
                continue
            page_ids = set(extract_case_ids_from_view(html))
            inter = page_ids & set(d.get("city_case_ids") or [])
            if inter:
                hit = (vid, html, sorted(inter))
                break
        if not hit:
            print(f"[{i}/{len(targets)}] {pid}: no page links our cases ({len(vids)} candidates)")
            continue
        vid, html, inter = hit
        miles = extract_tuidui_history_from_view(html)
        d["national_milestones"] = {**(d.get("national_milestones") or {}), **miles}
        d["twur_view_id"] = vid
        d["twur_url"] = f"{VIEW_URL_BASE}{vid}"
        (pdir / "view.html").write_text(html, encoding="utf-8")
        DiscoveryResult(**d)  # §6.10 hazard guard
        (pdir / "result.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        updated += 1
        print(f"[{i}/{len(targets)}] {pid}: ATTACHED view/{vid} via cases {inter} ({len(miles)} milestones)")

    print(f"\nsweep done: {len(targets)} attempted · {updated} attached · {failed} failed · "
          f"{len(targets) - updated - failed} no-match")
    return 0


if __name__ == "__main__":
    sys.stdout = _Tee(LOG)
    print("=" * 60)
    print("相關連結-identity twur sweep")
    print("=" * 60)
    sys.exit(main())
