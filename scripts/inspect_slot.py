#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI provenance explainer: where did a construction date come from?

Usage:
    python scripts/inspect_slot.py <project_id-prefix> [slot]

Prints, for one project (and optionally one slot of
建照核發日期/開工日期/使照核發日期), the full provenance breakdown:
merged value, milestones_source winner, per-case stage values (from the
project cache), implementation payload dates + carrying case, and the
national fallback — with a resolution verdict per slot.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

DATA_JS = Path(__file__).resolve().parents[1] / "viewer" / "projects.data.js"
CACHE = Path(__file__).resolve().parents[1] / "data" / ".link_cache"
SLOTS = ("建照核發日期", "開工日期", "使照核發日期")
IMPL_FIELDS = {"開工日期": "Eng_Start_Date", "使照核發日期": "Ulic_Date"}


def main() -> int:
    pid = sys.argv[1] if len(sys.argv) > 1 else ""
    only = sys.argv[2] if len(sys.argv) > 2 else ""
    if not pid:
        print(__doc__)
        return 1

    txt = DATA_JS.read_text(encoding="utf-8")
    doc = json.loads(re.sub(r"^window\.PROJECTS\s*=\s*", "", txt.strip()).rstrip(";"))
    p = next((x for x in doc["projects"] if x["project_id"].startswith(pid)), None)
    if not p:
        print(f"project not found: {pid}")
        return 1

    links = p.get("links") or {}
    mt = links.get("milestones_taipei") or {}
    mn = links.get("milestones_national") or {}
    src = links.get("milestones_source") or {}
    impl = p.get("implementation") or {}
    impl_case = impl.get("case_id") or ""

    # per-case stage values from the project cache
    cms = {}
    cache_file = CACHE / p["project_id"] / "result.json"
    if cache_file.is_file():
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        cms = raw.get("case_milestones") or {}

    anchored = {}
    for n in p.get("nodes") or []:
        for cid in ((n.get("links") or {}).get("taipei") or []):
            anchored[cid] = f"recno {n['recno']} ({n['date']})"

    slots = [only] if only else list(SLOTS)
    print(f"project : {p['project_id']}")
    print(f"impl    : case {impl_case or '-'}")
    for slot in slots:
        v = mt.get(slot, "")
        nat = mn.get("使用核發日期", "") if slot == "使照核發日期" else ""
        winner = src.get(slot, "")
        impl_field = IMPL_FIELDS.get(slot, "")
        print(f"\n[{slot}]")
        print(f"  merged value       : {v or '(absent)'}")
        print(f"  milestones_source  : {winner or '(absent)'}")
        if nat or slot == "使照核發日期":
            print(f"  national 使用核發日期 : {nat or '(absent)'}")
        carriers = [(cid, ms.get(slot)) for cid, ms in sorted(cms.items())
                    if (ms.get(slot) or "") != ""]
        if carriers:
            print(f"  per-case values    : {carriers}")
        # verdict
        if not v and not nat:
            verdict = "ISOLATED (no value)"
        elif winner:
            verdict = f"resolved → {winner}" + (f" ({anchored.get(winner, 'unanchored')})" if winner in anchored else " (unanchored)")
        elif impl_field and impl_case and impl.get(impl_field) == v:
            verdict = f"resolved → {impl_case} (implementation exact-match)" + (f" ({anchored.get(impl_case, 'unanchored')})" if impl_case in anchored else " (unanchored)")
        elif nat:
            verdict = "resolved → national 使用核發日期 (green group)"
        else:
            verdict = "ISOLATED (unprovable)"
        print(f"  verdict            : {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
