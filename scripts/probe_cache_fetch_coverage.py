"""What do the caches' own files say about when each project was last fetched?

The dashboard document (§5.3) says the 6 unverified projects are exactly the
caches with no `view.html` and no rewrite — `result.json` dated 2026-08-29,
the day the cache was first built. The
bind-the-unplaced-by-searching-the-cell-section change (2026-11-09) refreshed
7 caches and re-emitted the payload, so the file dates moved.

This reports, per project, what the cache directory itself records: whether
it holds a `view.html`, when `result.json` was written, and whether
`result.json` is newer than `view.html` (a rewrite with no fetch).

    python scripts/probe_cache_fetch_coverage.py [--names]

Reads file metadata and the payload. Writes nothing, reaches no network.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / ".link_cache"
PAYLOAD = ROOT / "viewer" / "projects.data.js"


def load_payload() -> dict:
    text = PAYLOAD.read_text(encoding="utf-8")
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--names", action="store_true",
                    help="name every project with no view.html")
    args = ap.parse_args()

    doc = load_payload()
    projects = doc["projects"]

    with_view = 0
    without_view = 0
    rewritten = 0
    same = 0
    result_older = 0
    no_view_ids: list[str] = []

    result_dates: dict[str, str] = {}
    for p in projects:
        d = CACHE / p["project_id"]
        rf = d / "result.json"
        vf = d / "view.html"
        if not rf.is_file():
            continue
        rm = datetime.datetime.fromtimestamp(rf.stat().st_mtime).strftime("%Y-%m-%d")
        result_dates[p["project_id"]] = rm
        if not vf.is_file():
            without_view += 1
            no_view_ids.append(p["project_id"])
            continue
        with_view += 1
        vm = vf.stat().st_mtime
        if rf.stat().st_mtime >= vm:
            rewritten += 1
        elif rf.stat().st_mtime == vm:
            same += 1
        else:
            result_older += 1

    print("cache directories with a result.json: %d of %d projects"
          % (len(result_dates), len(projects)))
    print("  with a view.html            : %d" % with_view)
    print("  without a view.html         : %d" % without_view)
    print("  result.json newer than view.html (rewritten, no fetch): %d" % rewritten)
    print("  written together            : %d" % same)
    print("  result.json older           : %d" % result_older)

    from collections import Counter
    print()
    print("result.json write dates:")
    for date, n in sorted(Counter(result_dates.values()).items(), reverse=True):
        print("   %s  %d" % (date, n))

    if args.names:
        print()
        print("projects with no view.html:")
        for pid in no_view_ids:
            print("   %-46s result.json %s" % (pid, result_dates.get(pid, "-")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
