"""Check whether the sibling case_ids are already in the per-project cache.

If a sibling case_id is already in the project's cached `city_case_ids` and its
milestones are cached, then the D9c-2 discovery fix needs NO network — only a
re-emit. If it is absent, the fix needs a targeted cache refresh.
"""
from __future__ import annotations

import json
from pathlib import Path

CACHE = Path("data/.link_cache")

targets = {
    "10708311": "南港區-南港段四小段-566地號等1筆",
    "11412011": "南港區-玉成段二小段-166地號等12筆",
    "11410026": "中正區-臨沂段三小段-412地號等12筆",
}

print(f"cache dir exists: {CACHE.exists()}")
if not CACHE.exists():
    raise SystemExit(0)

for case_id, project_id in targets.items():
    d = CACHE / project_id
    rj = d / "result.json"
    print(f"=== {case_id} / {project_id} ===")
    print(f"  cache dir exists: {d.exists()}")
    if not rj.exists():
        print(f"  NO result.json (cache miss) — needs discovery")
        # check for alias/stub variants
        for cand in CACHE.iterdir():
            if project_id[:6] in cand.name or case_id in cand.name:
                print(f"    nearby: {cand.name}")
        print()
        continue
    data = json.loads(rj.read_text(encoding="utf-8"))
    cids = data.get("city_case_ids") or []
    cm = data.get("case_milestones") or {}
    tm = data.get("taipei_milestones") or {}
    print(f"  status={data.get('status')}")
    print(f"  city_case_ids ({len(cids)}): {cids}")
    print(f"  case_milestones keys ({len(cm)}): {sorted(cm.keys())}")
    print(f"  taipei_milestones labels ({len(tm)}): {sorted(tm.keys())[:8]}")
    print(f"  --> case_id {case_id} in city_case_ids? {case_id in cids}")
    print(f"  --> case_id {case_id} has cached milestones? {case_id in cm}")
    print(f"  twur_view_id={data.get('twur_view_id')} twur_url={data.get('twur_url')}")
    print()

# Also: is the 崇仁新村 D6 target's cache present and what does it hold?
print("=== D6 target: 萬華區-崇仁新村青年段一小段-711-3地號等2筆 ===")
for name in ["萬華區-崇仁新村青年段一小段-711-3地號等2筆",
             "萬華區-崇仁新村青年段一小段-711-3地號等_筆",
             "未解析-1354"]:
    d = CACHE / name
    rj = d / "result.json"
    print(f"  {name}: dir={d.exists()} result.json={rj.exists()} view.html={(d / 'view.html').exists()}")
    if rj.exists():
        data = json.loads(rj.read_text(encoding="utf-8"))
        nm = data.get("national_milestones") or {}
        print(f"    twur_view_id={data.get('twur_view_id')} national_milestones={len(nm)} city_case_ids={data.get('city_case_ids')}")
