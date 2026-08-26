#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted repair: recno 621 track/name (add-stage-filter-621-repair).

The cleanse.py normalization (事業換計畫 → 事業計畫) landed after the last
`--from-js` regeneration, so the emitted data still carries the scrambled
name and the resulting track 其他 for recno 621 (北投區-大業段三小段-184-1
地號等10筆). This script patches the emitted data to exactly what the next
full PDF build will produce (the cleanse rule is regression-tested):

    track:      其他 → 事業計畫
    case_name:  事業換計畫 → 事業計畫
    auto_fixes: += 案名錯字→事業計畫

Files: viewer/projects.data.js, data/projects.json. Idempotent — re-runs
report "already applied" and change nothing.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
PID_PREFIX = "北投區-大業段三小段-184-1"
RECNO = 621
OLD, NEW = "事業換計畫", "事業計畫"
FIX = "案名錯字→事業計畫"


def patch_record(rec: dict) -> bool:
    """Patch one record in place. Returns True if anything changed."""
    changed = False
    if rec.get("track") == "其他":
        rec["track"] = NEW
        changed = True
    name = rec.get("case_name", "")
    if OLD in name:
        rec["case_name"] = name.replace(OLD, NEW)
        changed = True
    fixes = rec.setdefault("auto_fixes", [])
    if changed and FIX not in fixes:
        fixes.append(FIX)
        changed = True
    return changed


def patch_data_js() -> None:
    f = ROOT / "viewer" / "projects.data.js"
    txt = f.read_text(encoding="utf-8")
    doc = json.loads(re.sub(r"^window\.PROJECTS\s*=\s*", "", txt.strip()).rstrip(";"))
    p = next(x for x in doc["projects"] if x["project_id"].startswith(PID_PREFIX))
    rec = next(n for n in p["nodes"] if n["recno"] == RECNO)
    if patch_record(rec):
        f.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";\n",
                     encoding="utf-8")
        print(f"  projects.data.js: patched recno {RECNO}")
    else:
        print("  projects.data.js: already applied")


def patch_projects_json() -> None:
    f = ROOT / "data" / "projects.json"
    doc = json.loads(f.read_text(encoding="utf-8"))
    projs = doc["projects"] if isinstance(doc, dict) else doc
    p = next(x for x in projs if x.get("project_id", "").startswith(PID_PREFIX))
    mem = p.get("members") or p.get("nodes") or []
    rec = next(m for m in mem if m.get("recno") == RECNO)
    if patch_record(rec):
        f.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  projects.json: patched recno {RECNO}")
    else:
        print("  projects.json: already applied")


def check_cache() -> None:
    f = ROOT / "data" / ".link_cache" / (PID_PREFIX + "地號等10筆") / "result.json"
    if not f.is_file():
        print("  cache: result.json not found (nothing to patch)")
        return
    raw = json.loads(f.read_text(encoding="utf-8"))
    carries = any(k in raw for k in ("track", "case_name", "auto_fixes"))
    print("  cache: " + ("unexpected track/name fields present — inspect manually"
                        if carries else
                        "carries no track/案名 fields — nothing to patch (by design)"))


if __name__ == "__main__":
    print(f"repairing recno {RECNO} ({PID_PREFIX}…):")
    patch_data_js()
    patch_projects_json()
    check_cache()
