"""D9g step 9's ingest: the project diff, attributed. Read-only.

The 2026-10-28 gazette was ingested with --recover-truncated. This probe
compares the payload before and after and attributes every changed project to
a cause:

  NEW_APPROVAL  the gazette carries an approval the corpus did not
  RECOVERED     the reader completed a row (a truncated 地號 or the empty
                核定日期 of 編號 3) — a reader-side completion, not a
                publisher change
  RECLASSIFIED  the same approval moved between projects (a family merge)
  FLAG          a review flag was added or removed
  REST          the rest: the node's own dates moved because the gazette
                re-sorts its history by 核定日期

Read-only.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    before = load(ROOT / "data" / "_projects_before_step9.json")
    after = load(ROOT / "data" / "projects.json")
    b = {p["project_id"]: p for p in before["projects"]}
    a = {p["project_id"]: p for p in after["projects"]}

    counts = Counter()
    unexplained = []
    for pid in sorted(set(b) | set(a)):
        x, y = b.get(pid), a.get(pid)
        if x is None:
            counts["NEW PROJECT"] += 1
            continue
        if y is None:
            counts["GONE"] += 1
            unexplained.append(pid)
            continue
        if x == y:
            counts["unchanged"] += 1
            continue
        reasons = set()
        # a node that gained or lost a recovery provenance
        bx = {n["recno"]: n for n in x.get("nodes", [])}
        by = {n["recno"]: n for n in y.get("nodes", [])}
        recnos = set(bx) | set(by)
        if any((bx.get(r) or {}).get("recovery") != (by.get(r) or {}).get("recovery")
               for r in recnos):
            reasons.add("RECOVERED")
        # the node set itself changed (a family merged or split)
        if set(bx) != set(by):
            reasons.add("RECLASSIFIED")
        # a flag changed
        if any((bx.get(r) or {}).get("review_flags") != (by.get(r) or {}).get("review_flags")
               for r in recnos):
            reasons.add("FLAG")
        # a node's date moved
        if any((bx.get(r) or {}).get("date") != (by.get(r) or {}).get("date")
               for r in recnos):
            reasons.add("DATE MOVED")
        # the project's own link set changed
        if (x.get("links") or {}).get("twur") != (y.get("links") or {}).get("twur"):
            reasons.add("TWUR")
        if (x.get("links") or {}).get("milestones_taipei") != \
                (y.get("links") or {}).get("milestones_taipei"):
            reasons.add("MILESTONES")
        if not reasons:
            reasons.add("other")
            unexplained.append(pid)
        for r in reasons:
            counts[r] += 1
    print("the project diff:")
    for k, v in sorted(counts.items()):
        print("   %-16s %d" % (k, v))
    if unexplained:
        print()
        print("changed with no attributed cause (%d):" % len(unexplained))
        for pid in unexplained[:20]:
            print("   ", pid)


if __name__ == "__main__":
    main()
