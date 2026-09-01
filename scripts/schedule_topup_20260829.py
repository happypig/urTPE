#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schedule top-up sweep (§7.2.7) — fill `case_schedules` corpus-wide.

For every cache with `city_case_ids` lacking a schedule entry: query
`get_project168_top.ashx` per case, map phase/NAME → schedule via
`schedule_from_top`, validate, write. Paced 0.8 s/case; resumable (skips
case_ids that already have a schedule); single-writer.

Usage:
    python scripts/schedule_topup_20260829.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import TAIPEI_TOP_API, _post_taipei_api, schedule_from_top

CACHE = Path("data/.link_cache")
DELAY = 0.8
LOG = Path("data/schedule_topup_20260829.log")


class _Tee:
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


def main() -> int:
    js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
    data = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))
    projects = data["projects"]

    updated = errors = 0
    calls = 0
    t0 = time.time()
    for i, p in enumerate(projects, 1):
        pid = p["project_id"]
        safe = re.sub(r"[^\w\-]", "_", pid)
        rf = CACHE / safe / "result.json"
        if not rf.is_file():
            continue
        d = json.loads(rf.read_text(encoding="utf-8"))
        cids = d.get("city_case_ids") or []
        scheds = d.get("case_schedules") or {}
        todo = [c for c in cids if not scheds.get(c)]
        if not todo:
            continue
        for cid in todo:
            try:
                top = json.loads(_post_taipei_api(TAIPEI_TOP_API, {"case_id": cid}))
                calls += 1
            except Exception as e:
                print(f"[{i}/{len(projects)}] {pid} {cid}: top failed: {e}")
                errors += 1
                time.sleep(2.0)
                continue
            row = top[0] if isinstance(top, list) and top else (top if isinstance(top, dict) else {})
            sched = schedule_from_top(row)
            if sched:
                scheds[cid] = sched
            time.sleep(DELAY)
        if scheds:
            d["case_schedules"] = scheds
            rf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            updated += 1
        if i % 25 == 0:
            print(f"  …{i}/{len(projects)} projects ({calls} top calls, {updated} caches updated)")

    print(f"\ntop-up done: {updated} caches updated · {calls} top.ashx calls · {errors} errors · "
          f"{time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.stdout = _Tee(LOG)
    print("=" * 60)
    print("case_schedules top-up sweep")
    print("=" * 60)
    sys.exit(main())
