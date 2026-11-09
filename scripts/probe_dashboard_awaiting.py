"""How many projects await approval, and by district?

The dashboard document (§5) counts 97 projects awaiting approval out of 682,
and names the 12 districts. The
bind-the-unplaced-by-searching-the-cell-section change (2026-11-09) gave 7
projects their city case ids, so the figure is re-measured.

The rule is the pipeline's own — `urtpe.links.cached_cases_awaiting_approval`
— not a predicate written here, so the dashboard and the refresh pass agree
on what "awaiting approval" means.

    python scripts/probe_dashboard_awaiting.py

Reads the payload and the caches. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "viewer" / "projects.data.js"
CACHE = ROOT / "data" / ".link_cache"

sys.path.insert(0, str(ROOT))
from urtpe.links import cached_cases_awaiting_approval  # noqa: E402


def load_payload() -> dict:
    text = PAYLOAD.read_text(encoding="utf-8")
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def main() -> int:
    doc = load_payload()
    projects = doc["projects"]

    awaiting: list[tuple[str, str]] = []
    by_district: Counter = Counter()
    no_cache = 0

    for p in projects:
        rf = CACHE / p["project_id"] / "result.json"
        if not rf.is_file():
            no_cache += 1
            continue
        data = json.loads(rf.read_text(encoding="utf-8"))
        if cached_cases_awaiting_approval(
            data.get("case_milestones") or {},
            data.get("case_schedules") or {},
            data.get("case_headers") or {},
            data.get("superseded_by") or {},
        ):
            awaiting.append((p["project_id"], p.get("district", "")))
            by_district[p.get("district", "")] += 1

    print("projects: %d   (no cache: %d)" % (len(projects), no_cache))
    print("awaiting approval: %d" % len(awaiting))
    print("districts: %d" % len(by_district))
    for district, n in by_district.most_common():
        print("   %-8s %d" % (district, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
