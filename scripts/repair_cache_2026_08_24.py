#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off cache repair for bugs found on 2026-08-24 (see docs/facts_2_portals.md §16)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from urtpe.links import fetch_view_page, extract_tuidui_history_from_view, VIEW_URL_BASE

ROOT = Path("data/.link_cache")

# 1) 河堤段263-19: correct twur view (262, was wrongly 1042 = 板橋 case) + its real milestones
p1 = ROOT / "中正區-河堤段四小段-263-19地號等25筆" / "result.json"
r1 = json.loads(p1.read_text(encoding="utf-8"))
r1["twur_view_id"] = "262"
r1["twur_url"] = f"{VIEW_URL_BASE}262"
# values verified from live view/262 推動歷程 (browser, 2026-08-24)
r1["national_milestones"] = {
    "事業計畫申請日期": "102.05.31",
    "事業計畫核定日期": "105.07.06",
    "第一次變更事業計畫核定日期": "108.08.01",
    "使用核發日期": "110.10.25",
}
# per-case timelines (probe-verified via second.ashx) for date-aligned node linking
r1["case_milestones"] = {
    "10204032": {"核定日期": "2016/07/05", "建照核發日期": "2017/07/14"},
    "10707031": {"核定日期": "2019/08/01"},
}
p1.write_text(json.dumps(r1, ensure_ascii=False, indent=2), encoding="utf-8")
print("repaired", p1)

# refresh view.html with the correct page (262); drop stale 板橋 html on failure
try:
    html = fetch_view_page("262", None, True)
    if "河堤段四小段263-19" in html:
        (p1.parent / "view.html").write_text(html, encoding="utf-8")
        print("view.html refreshed with view/262")
    else:
        (p1.parent / "view.html").unlink()
        print("fetched page not matching; stale view.html removed")
except Exception as e:
    (p1.parent / "view.html").unlink(missing_ok=True)
    print(f"view/262 fetch failed ({e}); stale view.html removed")

# 2) 金華段513-3: inject per-case timelines (dates align recno 1040/797)
p2 = ROOT / "大安區-金華段四小段-513-3地號等13筆" / "result.json"
r2 = json.loads(p2.read_text(encoding="utf-8"))
r2["case_milestones"] = {
    "10011041": {"核定日期": "2016/07/21", "建照核發日期": "2017/02/07"},
    "10011042": {"核定日期": "2019/05/14"},
}
p2.write_text(json.dumps(r2, ensure_ascii=False, indent=2), encoding="utf-8")
print("repaired", p2)
