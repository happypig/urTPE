"""D9 step 5a: read the case header of each 168-list case that has no link.

Decides, per case, whether the city has approved it (uro_chk_date or
uro_chk_date2 present) or not. The not-approved set is the "submitted,
awaiting approval" list for the 168 program subset.

Read-only: writes data/p168_header_pass.json only, never .link_cache.
One request per case, with a delay; a failure is reported, not retried.

    python scripts/probe_header_pass_84.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import fetch_taipei_case_header_api  # noqa: E402

p168 = json.loads((ROOT / "data/p168_all.json").read_text(encoding="utf-8"))
doc = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))

linked: set[str] = set()
for p in doc["projects"]:
    linked.update(p.get("links", {}).get("taipei", []) or [])
    for n in p.get("nodes", []):
        linked.update(n.get("links", {}).get("taipei", []) or [])

# The 90 unlinked cases minus the 6 already explained (3 revoked, 2 unlinked, 1 pending).
explained = {"10112154", "10702271", "10904071", "10708311", "11412011", "11410026"}
targets = [c for c in p168 if c["case_id"] not in linked and c["case_id"] not in explained]
print(f"cases to read: {len(targets)}")

rows = []
for i, c in enumerate(targets, 1):
    cid = c["case_id"]
    try:
        h = fetch_taipei_case_header_api(cid) or {}
        err = ""
    except Exception as exc:
        h, err = {}, f"{type(exc).__name__}: {exc}"
    ok1 = str(h.get("uro_chk_date") or "")[:10]
    ok2 = str(h.get("uro_chk_date2") or "")[:10]
    state = ("error" if err else
             "approved" if (ok1 or ok2) else
             "no header" if not h else
             "not approved")
    rows.append({"case_id": cid, "state": state, "uro_chk_date": ok1, "uro_chk_date2": ok2,
                 "NAME": h.get("NAME", ""), "phase": h.get("phase", ""),
                 "CASE_NAME": h.get("CASE_NAME") or c["T_name"], "error": err})
    print(f"[{i:2d}/{len(targets)}] {cid} {state:13s} {ok1 or ok2:10s} {h.get('NAME', '')}")
    time.sleep(1.0)

out = ROOT / "data/p168_header_pass.json"
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
from collections import Counter
print("\nsummary:", dict(Counter(r["state"] for r in rows)))
print("by NAME:")
for k, v in Counter(r["NAME"] for r in rows).most_common():
    print(f"  {v:3d}  {k}")
print(f"wrote {out}")
