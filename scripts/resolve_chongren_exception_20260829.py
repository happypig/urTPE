"""Exception resolution: 崇仁新村 (未解析-1354 + 崇仁新村711-3 sibling).

Two stacked platform mismatches, verified live 2026-08-29:
  1. section drift: PDF '崇仁新村青年段一小段' vs platform '青年段一小段' (0 hits with prefix)
  2. parcel-less case names: 09112120/09112121 carry no 地號 -> parcel guard rejects
User-verified land: 臺北市萬華區崇仁新村青年段一小段711-3、青年段二小段18地號土地.
Exception: attach cases 09112120 (擬訂 -> recno 1399) + 09112121 (變更 -> recno 1354)
to BOTH projects; validate DiscoveryResult(**data) before every write (§6.10 hazard).
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import (
    DiscoveryResult,
    TAIPEI_THIRD_API,
    TAIPEI_TOP_API,
    _post_taipei_api,
    fetch_taipei_milestones_api,
    fetch_taipei_payload_api,
)

CACHE = Path("data/.link_cache")
TARGETS = ["未解析-1354", "萬華區-崇仁新村青年段一小段-711-3地號等2筆"]
CASES = ["09112120", "09112121"]  # 擬訂 / 變更 — same unit, 已完工

# 1) fetch case data once
case_data = {}
for cid in CASES:
    miles = fetch_taipei_milestones_api(cid)
    time.sleep(1.0)
    top = json.loads(_post_taipei_api(TAIPEI_TOP_API, {"case_id": cid}))
    row = top[0] if isinstance(top, list) and top else (top if isinstance(top, dict) else {})
    name = str(row.get("CASE_NAME", "")).strip()
    phase = str(row.get("phase", ""))
    impl = fetch_taipei_payload_api(TAIPEI_THIRD_API, cid)
    time.sleep(1.0)
    case_data[cid] = {"milestones": miles, "name": name, "phase": phase, "implementation": impl}
    print(f"{cid}: {name[:46]!r} phase={phase} milestones={len(miles)} impl_fields={len(impl)}")
    for label, date in list(miles.items())[:4]:
        print(f"    {label} = {date}")

# 2) attach to both projects (project-level links = raw search output, §6.7 rule;
#    node anchoring places each case on its recno at regen)
for pid in TARGETS:
    safe = re.sub(r"[^\w\-]", "_", pid)
    rf = CACHE / safe / "result.json"
    d = json.loads(rf.read_text(encoding="utf-8"))
    d["city_case_ids"] = sorted(set(d.get("city_case_ids") or []) | set(CASES))
    d.setdefault("case_milestones", {}).update(
        {cid: case_data[cid]["milestones"] for cid in CASES if case_data[cid]["milestones"]}
    )
    d.setdefault("candidate_names", {}).update(
        {cid: case_data[cid]["name"] for cid in CASES if case_data[cid]["name"]}
    )
    ms_taipei = d.get("taipei_milestones") or {}
    ms_source = d.get("milestones_source") or {}
    for cid in CASES:
        for label, date in case_data[cid]["milestones"].items():
            ms_taipei.setdefault(label, date)
            ms_source.setdefault(label, cid)
    d["taipei_milestones"] = ms_taipei
    d["milestones_source"] = ms_source
    impl = d.get("implementation") or {}
    for cid in CASES:
        if case_data[cid]["implementation"] and cid not in impl:
            payload = dict(case_data[cid]["implementation"])
            payload["case_id"] = cid
            impl[cid] = payload
    d["implementation"] = impl
    d["status"] = "resolved"
    d["error"] = ""
    if not d.get("land_core"):
        d["land_core"] = "萬華區崇仁新村青年段一小段711-3地號等2筆"

    # §6.10 hazard guard: the write must round-trip the dataclass
    DiscoveryResult(**d)
    rf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"resolved + validated: {pid}")

print("done")
