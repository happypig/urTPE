"""Regenerate docs/temp_unjoined_projects.md — live city cases, no national page.

For each link cache that discovery resolved with no `twur_view_id`, list the
project's LIVE city cases with their schedules. A case is dead when its
schedule is 已駁回 / 自行撤回 / 已失效, or its case header's NAME carries
撤銷核准 (the platform's revoked state — a revoked approval is never gazetted,
D9a, and schedule_from_top derives no value for it). A project with no live
case is not listed.

A row whose project_id is not in the current data/projects.json is marked
**[stranded]**: the cache directory outlived the project_id that named it.

    python scripts/temp_unjoined_projects.py

Reads data/.link_cache/ and data/projects.json. Writes docs/temp_unjoined_projects.md
and nothing else. The output file is a paste pad (docs/temp.* convention): it is
pinned to one moment and is stale the moment it is written.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / ".link_cache"
PAYLOAD = ROOT / "data" / "projects.json"
OUT = ROOT / "docs" / "temp_unjoined_projects.md"

DEAD_SCHEDULES = {"已駁回", "自行撤回", "已失效", "已撤銷"}


def case_dead(cid: str, d: dict) -> bool:
    """A case is dead when its schedule says so, or its header NAME says 撤銷."""
    if (d.get("case_schedules") or {}).get(cid) in DEAD_SCHEDULES:
        return True
    h = (d.get("case_headers") or {}).get(cid)
    if isinstance(h, dict):
        return "撤銷" in (h.get("NAME") or "")
    if isinstance(h, str):
        return "撤銷" in h
    return False


def main() -> int:
    doc = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    known = {p["project_id"] for p in doc["projects"]}

    lines = [
        "# The unjoined projects — live city cases, no national view link",
        "",
        f"Generated {dt.date.today().isoformat()} by scripts/temp_unjoined_projects.py from "
        f"data/.link_cache/*/result.json. A project is listed when it holds at",
        "least one LIVE city case and discovery found no twur view id. Dead:",
        "schedule 已駁回/自行撤回/已失效/已撤銷, or header NAME 撤銷核准.",
        "Stranded rows (project_id not in the current dataset) are marked.",
        "",
        "| Project | Live cases (schedule) |",
        "| --- | --- |",
    ]
    n = stranded_n = 0
    for entry in sorted(CACHE.iterdir()):
        rf = entry / "result.json"
        if not rf.is_file():
            continue
        try:
            d = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("twur_view_id"):
            continue
        live = [c for c in (d.get("city_case_ids") or []) if not case_dead(c, d)]
        if not live:
            continue
        n += 1
        pid = d.get("project_id") or entry.name
        mark = ""
        if pid not in known:
            stranded_n += 1
            mark = " **[stranded]**"
        schedules = d.get("case_schedules") or {}
        cells = ", ".join(f"{c} ({schedules.get(c) or '—'})" for c in live)
        lines.append(f"| {pid}{mark} | {cells} |")
    lines += [
        "",
        f"{n} projects ({stranded_n} stranded). 實踐641 (view/9) is joined and absent.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} with {n} projects ({stranded_n} stranded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
