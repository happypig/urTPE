#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill milestones_source into per-project caches (2026-08-26).

Caches written before refine-event-source-edges lack the label → winning-case
map. Recompute it from each cache's own case_milestones (last-write-wins over
city_case_ids order — same rule as the live merge) and write it back, so the
next --links attach pass carries slot provenance to the viewer without any
network traffic.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from urtpe.links import merge_stage_milestones

ROOT = Path("data/.link_cache")
patched = skipped = 0
for dd in ROOT.iterdir():
    f = dd / "result.json"
    if not f.is_file():
        continue
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    if raw.get("milestones_source"):
        skipped += 1
        continue
    cms = raw.get("case_milestones") or {}
    if not cms:
        skipped += 1
        continue
    all_ms, source = {}, {}
    for cid in raw.get("city_case_ids") or []:
        merge_stage_milestones(all_ms, source, cid, cms.get(cid) or {})
    if source:
        raw["milestones_source"] = source
        f.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        patched += 1
    else:
        skipped += 1
print(f"patched: {patched}, skipped: {skipped}")
