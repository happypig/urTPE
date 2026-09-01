"""Attach national side (view/18) to both 崇仁新村 caches — curated exception.

Identity verified: view/18 title = (原崇仁新村) parcel-renamed unit; its 相關連結
points to our case 09112120; 推動歷程 核定 94.02.24 / 第一次變更 97.01.02 match
recno 1399 / 1354 node dates exactly. Strict matcher would reject (title uses
711地號 without 之/hyphen sub-parcel and no 筆 count) — exception documented.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import DiscoveryResult, VIEW_URL_BASE, extract_tuidui_history_from_view, fetch_url

CACHE = Path("data/.link_cache")
TARGETS = ["未解析-1354", "萬華區-崇仁新村青年段一小段-711-3地號等2筆"]

html = fetch_url(f"{VIEW_URL_BASE}18", None, True)
milestones = extract_tuidui_history_from_view(html)
print(f"view/18 推動歷程: {len(milestones)} milestones")

for pid in TARGETS:
    safe = re.sub(r"[^\w\-]", "_", pid)
    pdir = CACHE / safe
    rf = pdir / "result.json"
    d = json.loads(rf.read_text(encoding="utf-8"))
    merged = {**(d.get("national_milestones") or {}), **milestones}
    d["national_milestones"] = merged
    d["twur_view_id"] = "18"
    d["twur_url"] = f"{VIEW_URL_BASE}18"
    if not (pdir / "view.html").is_file():
        (pdir / "view.html").write_text(html, encoding="utf-8")
    DiscoveryResult(**d)  # §6.10 hazard guard
    rf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"attached view/18 -> {pid}")
print("done")
