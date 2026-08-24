"""Restore national-portal links wiped by the 2026-08-25 bulk discovery refresh.

The refresh re-derived every result.json from the partial portal index
(110 entries) + fallback JSON (3 entries), dropping the targeted-fetch
campaign's land-core -> view_id mappings that lived only inside the deleted
files (docs/facts_2_portals.md §18).

For each backup cache with a twur link whose live counterpart lost it, merge
back exactly three fields — twur_view_id, twur_url, national_milestones —
preserving all Taipei-side gains of the refresh (case_milestones,
implementation, rewards, corrected labels). No network access.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKUP = Path("data/.link_cache_backup_20260824")
LIVE = Path("data/.link_cache")
MERGE_FIELDS = ["twur_view_id", "twur_url", "national_milestones"]

restored = already_ok = missing_live = malformed = 0
for bdir in sorted(BACKUP.iterdir()):
    if not bdir.is_dir():
        continue
    brj = bdir / "result.json"
    if not brj.exists():
        continue
    try:
        old = json.loads(brj.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        malformed += 1
        continue
    if not old.get("twur_url"):
        continue

    ldir = LIVE / bdir.name
    lrj = ldir / "result.json"
    if not lrj.exists():
        missing_live += 1
        print(f"  MISSING live cache: {bdir.name}")
        continue
    try:
        cur = json.loads(lrj.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        missing_live += 1
        print(f"  UNREADABLE live cache: {bdir.name}")
        continue

    if cur.get("twur_url") and cur.get("national_milestones"):
        already_ok += 1
        continue

    for field in MERGE_FIELDS:
        cur[field] = old.get(field) or cur.get(field) or ""
    if not cur["twur_view_id"]:
        # view_id is derivable from the URL: .../view/{id}
        cur["twur_view_id"] = str(cur["twur_url"]).rstrip("/").rsplit("/", 1)[-1]
    lrj.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    restored += 1

# Post-check: live totals must reach the pre-refresh state 292 / 292 / 58.
total = twur = nat_ms = use = 0
for d in LIVE.iterdir():
    rj = d / "result.json"
    if not d.is_dir() or not rj.exists():
        continue
    try:
        r = json.loads(rj.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        continue
    total += 1
    if r.get("twur_url"):
        twur += 1
    if r.get("national_milestones"):
        nat_ms += 1
    if "使用核發日期" in (r.get("national_milestones") or {}):
        use += 1

print(f"restored: {restored} · already-ok: {already_ok} · "
      f"missing/unreadable-live: {missing_live} · malformed-backup: {malformed}")
print(f"live totals: scanned {total} · twur {twur} · national_milestones {nat_ms} · 使用核發 {use}")
print("target:      scanned 709 · twur 292 · national_milestones 292 · 使用核發 58")
