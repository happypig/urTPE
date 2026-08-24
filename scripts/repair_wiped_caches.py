"""Repair caches wiped by the 2026-08-24 21:23 concurrency race.

For every project cache with a twur_view_id but empty national_milestones,
re-fetch the view page fresh, parse with the fixed ViewPageParser, and restore
national_milestones (+ a clean view.html). Preserves all other fields.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import (
    fetch_url,
    extract_tuidui_history_from_view,
    VIEW_URL_BASE,
)

ROOT = Path("data/.link_cache")

repaired = still_empty = skipped = 0
for d in sorted(ROOT.iterdir()):
    if not d.is_dir():
        continue
    rj = d / "result.json"
    if not rj.exists():
        continue
    try:
        result = json.loads(rj.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        skipped += 1
        continue
    vid = result.get("twur_view_id")
    if not vid:
        skipped += 1
        continue
    if result.get("national_milestones"):
        skipped += 1
        continue

    try:
        html = fetch_url(f"{VIEW_URL_BASE}{vid}", None, True)
    except Exception as e:
        print(f"  refetch failed {d.name} (view {vid}): {e}")
        still_empty += 1
        time.sleep(1.0)
        continue

    milestones = extract_tuidui_history_from_view(html)
    result["national_milestones"] = milestones
    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "view.html").write_text(html, encoding="utf-8")
    if milestones:
        repaired += 1
    else:
        still_empty += 1
        print(f"  parsed-empty: {d.name} (view {vid})")
    time.sleep(1.0)

print(f"repaired: {repaired} · still-empty: {still_empty} · skipped: {skipped}")
