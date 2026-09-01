"""Category-1 targeted resolver: complete Taipei side for twur'd unresolved
projects via their portal view page's 相關連結 case links.

For each unresolved project that has a twur view_id:
  1. get the view page (cached view.html, else fetch once),
  2. extract 相關連結 case_ids the cache is missing,
  3. per new case_id: fetch second.ashx milestones + top.ashx CASE_NAME,
  4. attach (city_case_ids / case_milestones / candidate_names /
     milestones_taipei / milestones_source) and set status=resolved.

Deliberately conservative: no guard re-litigation, no third/fourth.ashx.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import (
    TAIPEI_TOP_API,
    VIEW_URL_BASE,
    _post_taipei_api,
    extract_case_ids_from_view,
    extract_tuidui_history_from_view,
    fetch_taipei_milestones_api,
    fetch_url,
)

CACHE = Path("data/.link_cache")
DELAY = 1.0
js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
projects = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))["projects"]

attempted = resolved = 0
for p in projects:
    pid = p["project_id"]
    safe = re.sub(r"[^\w\-]", "_", pid)
    rf = CACHE / safe / "result.json"
    if not rf.is_file():
        continue
    d = json.loads(rf.read_text(encoding="utf-8"))
    if d.get("status") == "resolved":
        continue
    vid = d.get("twur_view_id")
    if not vid:
        continue
    attempted += 1

    vf = CACHE / safe / "view.html"
    if vf.is_file():
        html = vf.read_text(encoding="utf-8", errors="replace")
    else:
        try:
            html = fetch_url(f"{VIEW_URL_BASE}{vid}", None, True)
            vf.write_text(html, encoding="utf-8")
            time.sleep(DELAY)
        except Exception as e:
            print(f"  {pid}: view fetch failed: {e}")
            continue

    page_ids = extract_case_ids_from_view(html)
    page_miles = extract_tuidui_history_from_view(html)
    have = set(d.get("city_case_ids") or [])
    new_ids = [c for c in page_ids if c not in have]
    if not new_ids:
        print(f"  {pid} (view/{vid}): no new case_ids on page")
        continue

    case_miles = d.get("case_milestones") or {}
    names = d.get("candidate_names") or {}
    ms_taipei = d.get("taipei_milestones") or {}
    ms_source = d.get("milestones_source") or {}
    attached = []
    for cid in new_ids:
        try:
            miles = fetch_taipei_milestones_api(cid)
            time.sleep(DELAY)
            top = json.loads(_post_taipei_api(TAIPEI_TOP_API, {"case_id": cid}))
            time.sleep(DELAY)
        except Exception as e:
            print(f"  {pid}: case {cid} fetch failed: {e}")
            continue
        row = top[0] if isinstance(top, list) and top else (top if isinstance(top, dict) else {})
        name = str(row.get("CASE_NAME", "")).strip()
        if name:
            names[cid] = name
        if miles:
            case_miles[cid] = miles
            for label, date in miles.items():
                ms_taipei.setdefault(label, date)
                ms_source.setdefault(label, cid)
        attached.append(cid)
        print(f"  {pid}: case {cid} attached ({len(miles)} milestones, name={'y' if name else 'n'})")

    if attached:
        d["city_case_ids"] = sorted(set(d.get("city_case_ids") or []) | set(attached))
        # cases pulled off this project's own view page are portal-verified —
        # exempt from the landcore similarity gate in ghost creation
        verified = set(d.get("view_verified_case_ids") or []) | set(attached)
        d["view_verified_case_ids"] = sorted(verified)
        d["case_milestones"] = case_miles
        d["candidate_names"] = names
        d["taipei_milestones"] = ms_taipei
        d["milestones_source"] = ms_source
        d["status"] = "resolved"
        d["error"] = ""
        merged_nat = {**(d.get("national_milestones") or {}), **page_miles}
        d["national_milestones"] = merged_nat
        rf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        resolved += 1

print(f"\nattempted: {attempted} · resolved now: {resolved}")
