"""The 168 list's MEMO as a third source for the approval date.

The name-only rule (D9f-1) recovers the PLATFORM's date. On 2 of the 59
measured rows the platform and the PDF disagree — recno 37 by 1 day, recno 47
by 16 days — and the rule cannot recover the PDF's date, because no candidate
carries it.

The 168 list's `MEMO` field carries the 核定公告 date for the rows it has
(measured: 10011271 → 2022/08/02核定公告, 10011273 → 2023/03/21核定公告). So
it is a THIRD source, independent of both the PDF and the platform.

This probe asks, for each case the rule would consider:
  - does the 168 list hold a row for that case?
  - what does its MEMO say?
  - does the MEMO agree with the PDF's date, with the platform's, or with
    neither?

Read-only, live.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import fetch_taipei_168_list_api  # noqa: E402

# the two measured disagreement rows, and the case the rule would pick
CASES = [
    # (the corpus row's date, the platform's date, the case id, the unit)
    ("2026-07-01", "2026-07-02", "11502013", "玉泉段二小段40"),
    ("2026-06-01", "2026-06-17", "11410007", "大業段三小段184-1"),
    # the row the whole step is about
    ("2026-10-15", "2026-10-15", "11501034", "通化段四小段336"),
]

_MEMO_DATE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")


def memo_date(memo: str) -> str:
    m = _MEMO_DATE.search(memo or "")
    if not m:
        return ""
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))


def main() -> None:
    rows = fetch_taipei_168_list_api()
    print("the 168 list: %d rows" % len(rows))
    by_case = {str(r.get("case_id") or ""): r for r in rows}
    print()
    for pdf_date, plat_date, cid, unit in CASES:
        print("=== %s (case %s) ===" % (unit, cid))
        print("   the PDF's date      : %s" % pdf_date)
        print("   the platform's date : %s" % plat_date)
        row = by_case.get(cid)
        if row is None:
            # the list may name the case under a different id — search by name
            hits = [r for r in rows if unit in str(r.get("T_name") or "")]
            print("   the 168 list holds this case id? NO")
            print("   rows naming the unit %s: %d" % (unit, len(hits)))
            for h in hits:
                print("      %-11s MEMO=%-22r %s" % (
                    h.get("case_id"), h.get("MEMO"), (h.get("T_name") or "")[:46]))
        else:
            print("   the 168 list holds this case id? YES")
            print("      MEMO   : %r" % row.get("MEMO"))
            print("      stage  : %r" % row.get("stage"))
            print("      name   : %s" % (row.get("T_name") or "")[:60])
            d = memo_date(str(row.get("MEMO") or ""))
            print("      the MEMO's date: %s" % (d or "(none)"))
            if d:
                if d == pdf_date:
                    print("      -> the MEMO AGREES WITH THE PDF")
                elif d == plat_date:
                    print("      -> the MEMO AGREES WITH THE PLATFORM")
                else:
                    print("      -> the MEMO AGREES WITH NEITHER")
        print()


if __name__ == "__main__":
    main()
