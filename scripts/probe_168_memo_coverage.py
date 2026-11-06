"""The 168 list's MEMO: what can it contribute, and for whom?

The name-only rule (D9f-1) recovers the PLATFORM's date. On 2 of the 59
measured rows the platform and the PDF disagree, and the rule cannot recover
the PDF's date. The 168 list's `MEMO` field carries a 核定公告 date for the
rows it has, so it is a third source — independent of both the PDF and the
platform.

This probe measures the list's actual contribution:
  - how many of its rows carry a MEMO date, and how many do not;
  - what its MEMO dates mean (a 核定公告 is the gazette-announcement date, which
    is the PDF's own 核定日期 — or is it a different date?);
  - for the rows where the platform and the PDF disagree, whether the list
    holds the case at all.

Read-only, live.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import fetch_taipei_168_list_api  # noqa: E402

_MEMO_DATE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")


def memo_date(memo: str) -> str:
    m = _MEMO_DATE.search(memo or "")
    if not m:
        return ""
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))


def main() -> None:
    rows = fetch_taipei_168_list_api()
    dated = [r for r in rows if memo_date(str(r.get("MEMO") or ""))]
    print("the 168 list: %d rows" % len(rows))
    print("   rows carrying a MEMO date: %d" % len(dated))
    print("   rows without one (MEMO='-'): %d" % (len(rows) - len(dated)))
    print()
    print("the stage values among the dated rows:",
          dict(Counter(str(r.get("stage") or "") for r in dated)))
    print("the stage values among the UNdated rows:",
          dict(Counter(str(r.get("stage") or "") for r in rows
                       if not memo_date(str(r.get("MEMO") or "")))))
    print()

    # what is a MEMO date, in terms of the PDF's own 核定日期?
    # the corpus carries the PDF's dates; the list carries case ids. Join the
    # two on the case id, via the cache.
    print("=== what does the MEMO date mean? ===")
    print("joining the list's case ids to the corpus's dates, through the cache")
    cache = ROOT / "data" / ".link_cache"
    case_dates: dict[str, str] = {}
    case_rows: dict[str, dict] = {}
    for d in sorted(cache.iterdir()):
        f = d / "result.json"
        if not f.is_file():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        for cid, ms in (r.get("case_milestones") or {}).items():
            for label in ("核定日期", "權變核定日期"):
                if ms.get(label):
                    case_dates.setdefault(cid, ms[label])
                    case_rows.setdefault(cid, {"project": d.name, "label": label})
                    break
    agree = disagree = unmatched = 0
    examples = []
    for r in dated:
        cid = str(r.get("case_id") or "")
        memo = memo_date(str(r.get("MEMO") or ""))
        pdf = case_dates.get(cid)
        if not pdf:
            unmatched += 1
            continue
        from urtpe.extract import to_iso
        pdf_iso = to_iso(pdf)[0] or ""
        if pdf_iso == memo:
            agree += 1
        else:
            disagree += 1
            if len(examples) < 8:
                examples.append((cid, pdf, memo, case_rows.get(cid, {}).get("label")))
    print("   the list's dated cases also in a cache: %d" % (agree + disagree))
    print("   the MEMO date EQUALS the cached case's 核定日期: %d" % agree)
    print("   the MEMO date DIFFERS from it:                     %d" % disagree)
    print("   no cached date for the case:                       %d" % unmatched)
    print()
    if examples:
        print("   the disagreements:")
        for e in examples:
            print("      %-11s the cached date %-11s the MEMO %-11s (%s)"
                  % (e[0], e[1], e[2], e[3]))
    print()
    print("   what the MEMO text says, for a few rows:")
    for r in dated[:6]:
        print("      %-11s MEMO=%r  stage=%r" % (
            r.get("case_id"), r.get("MEMO"), r.get("stage")))


if __name__ == "__main__":
    main()
