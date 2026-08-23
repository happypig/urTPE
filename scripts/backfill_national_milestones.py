"""Backfill national_milestones into per-project link caches.

Re-parses locally cached view.html files with the fixed ViewPageParser and
updates result.json in place. Corrupted caches (gzipped bodies saved as
replacement-mangled text by an older code path) are re-fetched from the
portal once.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import extract_tuidui_history_from_view, fetch_url

ROOT = Path("data/.link_cache")
VIEW_URL_BASE = "https://twur.nlma.gov.tw/zh/urban/rebuild/view/"


def looks_like_page(html: str) -> bool:
    return "data_table_box" in html or "type4_table" in html


updated = refetched = empty = skipped = 0
for d in sorted(ROOT.iterdir()):
    if not d.is_dir():
        continue
    rj = d / "result.json"
    vh = d / "view.html"
    if not rj.exists():
        continue
    try:
        result = json.loads(rj.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        skipped += 1
        continue
    view_id = result.get("twur_view_id")
    if not view_id:
        skipped += 1
        continue

    html = vh.read_text(encoding="utf-8") if vh.exists() else ""
    if not looks_like_page(html):
        # corrupted (gzip-as-text mojibake) or missing → one polite refetch
        try:
            html = fetch_url(f"{VIEW_URL_BASE}{view_id}", None, True)
            time.sleep(1.0)
        except Exception as e:
            print(f"  refetch failed {d.name} (view {view_id}): {e}")
            empty += 1
            continue
        vh.write_text(html, encoding="utf-8")
        refetched += 1

    milestones = extract_tuidui_history_from_view(html)
    if result.get("national_milestones") == milestones:
        skipped += 1
        continue
    result["national_milestones"] = milestones
    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    updated += 1 if milestones else 0
    if not milestones:
        empty += 1

print(
    f"updated: {updated} · refetched: {refetched} · "
    f"parsed-empty: {empty} · unchanged/skipped: {skipped}"
)
