"""Quick win 2 (v2): revert bad title-writes, then backfill names via top.ashx.

1. Remove the garbage candidate_names entries written by v1 (site title, not case name).
2. For every still-unnamed city_case_id: POST get_project168_top.ashx (case_id)
   -> CASE_NAME field (§11 endpoint map; §6.9 correction). 3 case_ids expected.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import TAIPEI_TOP_API, _post_taipei_api

CACHE = Path("data/.link_cache")
GARBAGE = "都市更新審議服務平台｜臺北市都市更新處"
js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
projects = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))["projects"]

# 1) revert v1 garbage
reverted = 0
for p in projects:
    rf = CACHE / re.sub(r"[^\w\-]", "_", p["project_id"]) / "result.json"
    if not rf.is_file():
        continue
    d = json.loads(rf.read_text(encoding="utf-8"))
    names = d.get("candidate_names") or {}
    bad = [k for k, v in names.items() if v == GARBAGE]
    if bad:
        for k in bad:
            del names[k]
        rf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        reverted += 1
print(f"reverted garbage writes in {reverted} caches")

# 2) top.ashx CASE_NAME backfill
for p in projects:
    pid = p["project_id"]
    rf = CACHE / re.sub(r"[^\w\-]", "_", pid) / "result.json"
    if not rf.is_file():
        continue
    d = json.loads(rf.read_text(encoding="utf-8"))
    names = d.get("candidate_names") or {}
    missing = [c for c in (d.get("city_case_ids") or []) if not names.get(c)]
    for cid in missing:
        try:
            body = _post_taipei_api(TAIPEI_TOP_API, {"case_id": cid})
            row = json.loads(body)
            row = row[0] if isinstance(row, list) and row else (row if isinstance(row, dict) else {})
            name = str(row.get("CASE_NAME", "")).strip()
        except Exception as e:
            print(f"  {cid}: top.ashx FAILED: {e}")
            continue
        print(f"  {cid} ({pid[:26]}): CASE_NAME={name[:60]!r}")
        if name:
            d.setdefault("candidate_names", {})[cid] = name
            rf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"    written")
