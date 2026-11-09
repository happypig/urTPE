"""What does the payload now say about each project's link coverage?

The dashboard's 資料未驗證 column was designed around one predicate: no
national portal link AND no city case id. The
bind-the-unplaced-by-searching-the-cell-section change (2026-11-09) gave 7
projects their city case ids, so the predicate now selects 0 instead of 6.

This counts every link shape the payload offers, so the column's design can
be based on the population as it stands rather than on a set that has moved.

    python scripts/probe_dashboard_link_shapes.py

Reads the payload and the caches. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "viewer" / "projects.data.js"
CACHE = ROOT / "data" / ".link_cache"


def load_payload() -> dict:
    import re
    text = PAYLOAD.read_text(encoding="utf-8")
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def main() -> int:
    doc = load_payload()
    projects = doc["projects"]
    total = len(projects)

    twur_only = city_only = both = neither = 0
    neither_ids: list[str] = []
    city_only_ids: list[str] = []
    for p in projects:
        links = p.get("links") or {}
        has_twur = bool((links.get("twur") or "").strip())
        has_city = bool(links.get("taipei") or [])
        if has_twur and has_city:
            both += 1
        elif has_twur:
            twur_only += 1
        elif has_city:
            city_only += 1
            city_only_ids.append(p["project_id"])
        else:
            neither += 1
            neither_ids.append(p["project_id"])

    print("projects: %d" % total)
    print("  national link AND city case id : %d" % both)
    print("  national link only              : %d" % twur_only)
    print("  city case id only               : %d  <- no national page" % city_only)
    print("  neither                         : %d  <- the old unverified predicate" % neither)
    if neither_ids:
        print()
        print("neither:")
        for pid in neither_ids:
            print("   ", pid)

    # the case_headers proxy the dashboard document discusses for Option 1
    with_headers = 0
    without_headers = 0
    for p in projects:
        d = CACHE / p["project_id"] / "result.json"
        if not d.is_file():
            without_headers += 1
            continue
        try:
            data = json.loads(d.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            without_headers += 1
            continue
        if data.get("case_headers"):
            with_headers += 1
        else:
            without_headers += 1
    print()
    print("caches with case_headers: %d   without: %d" % (with_headers, without_headers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
