"""Quick win 2: backfill case names from the case detail page (bypasses search).

For every city_case_id lacking a candidate_name: GET r_progress_detail.aspx?case_id=X,
extract the case name from <title>, write into candidate_names. 3 requests total.
"""
import html as html_mod
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import fetch_url

CACHE = Path("data/.link_cache")
js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
projects = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))["projects"]

targets = []  # (project_id, case_id)
for p in projects:
    rf = CACHE / re.sub(r"[^\w\-]", "_", p["project_id"]) / "result.json"
    if not rf.is_file():
        continue
    d = json.loads(rf.read_text(encoding="utf-8"))
    names = d.get("candidate_names") or {}
    for cid in d.get("city_case_ids") or []:
        if not names.get(cid):
            targets.append((p["project_id"], cid))

print(f"unnamed city_case_ids: {len(targets)}")
for pid, cid in targets:
    url = f"https://gis.uro.taipei/r_progress_detail.aspx?case_id={cid}"
    try:
        page = fetch_url(url, None, True)  # no cache dir, fresh GET
        m = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
        title = html_mod.unescape(m.group(1)).strip() if m else ""
        # strip site suffix: '-臺北市都市更新處' etc.
        name = re.split(r"[-–—|]", title)[0].strip() if title else ""
        print(f"  {cid} ({pid[:24]}): title={title[:70]!r} -> name={name[:50]!r}")
        if name and len(name) >= 6:
            rf2 = CACHE / re.sub(r"[^\w\-]", "_", pid) / "result.json"
            d2 = json.loads(rf2.read_text(encoding="utf-8"))
            d2.setdefault("candidate_names", {})[cid] = name
            rf2.write_text(json.dumps(d2, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"    written to candidate_names")
        else:
            print(f"    SKIPPED (no usable title)")
    except Exception as e:
        print(f"  {cid}: FETCH FAILED: {e}")
