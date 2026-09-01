"""Offline twur backfill from cached view.html (§6.10 recovery step 3).

For each twur-less project that has a cached view.html:
  1. recover the view_id from the page's own /view/{id} refs (require exactly 1 distinct),
  2. re-validate identity with the sweep's strict view_page_matches(),
  3. parse 推動歷程 + city ids with the sweep's extractors,
  4. merge per update_project_cache semantics (milestones new-wins, twur set,
     ledger entry cleared, city_case_ids untouched).
Zero network. Single-writer safe.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.fetch_remaining_national_portal import (
    LEDGER_PATH,
    clear_entry,
    load_candidates,
    load_ledger,
    save_ledger,
    view_page_matches,
)
from urtpe.links import extract_case_ids_from_view, extract_tuidui_history_from_view

CACHE = Path("data/.link_cache")
VIEW_RE = re.compile(r"/zh/urban/rebuild/view/(\d+)")


def coverage(projects):
    twur = miles = ulic = 0
    for p in projects:
        rf = CACHE / re.sub(r"[^\w\-]", "_", p["project_id"]) / "result.json"
        if not rf.is_file():
            continue
        d = json.loads(rf.read_text(encoding="utf-8"))
        if d.get("twur_url"):
            twur += 1
        if d.get("national_milestones"):
            miles += 1
        if any(k == "使用核發日期" for k in (d.get("national_milestones") or {})):
            ulic += 1
    return twur, miles, ulic


js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
projects = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))["projects"]
print("BEFORE (twur, milestones, 使用核發):", coverage(projects))

ledger = load_ledger()
cands = {c["project_id"]: c for c in load_candidates()}
updated = mismatch = ambiguous = 0

for pid, c in cands.items():
    pdir = CACHE / re.sub(r"[^\w\-]", "_", pid)
    rf = pdir / "result.json"
    vf = pdir / "view.html"
    if not rf.is_file() or not vf.is_file():
        continue
    result = json.loads(rf.read_text(encoding="utf-8"))
    if result.get("twur_url"):
        continue  # resolved since candidate load
    html = vf.read_text(encoding="utf-8", errors="replace")
    refs = set(VIEW_RE.findall(html))
    if len(refs) != 1:
        ambiguous += 1
        print(f"  AMBIGUOUS ({len(refs)} refs): {pid}")
        continue
    vid = refs.pop()
    if not view_page_matches(html, c["section"], c["parcel"], c.get("count", "")):
        mismatch += 1
        print(f"  IDENTITY MISMATCH vs view/{vid}: {pid}")
        continue
    milestones = extract_tuidui_history_from_view(html)
    merged = {**(result.get("national_milestones") or {}), **milestones}
    result["national_milestones"] = merged
    result["twur_view_id"] = vid
    result["twur_url"] = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{vid}"
    rf.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if pid in ledger:
        clear_entry(ledger, pid)
    updated += 1
    print(f"  backfilled {pid} -> view/{vid} ({len(milestones)} milestones)")

if updated:
    save_ledger(ledger)

print(f"\nbackfilled: {updated} · identity-mismatch: {mismatch} · ambiguous: {ambiguous}")
print("AFTER  (twur, milestones, 使用核發):", coverage(projects))
