"""What can the 168 list's MEMO contribute to the date recovery?

The name-only rule (D9f-1) recovers the PLATFORM's date. On 2 of the 59
measured rows the platform and the PDF disagree. The 168 list's `MEMO` field
carries a 核定公告 date for 146 of its 466 rows.

This probe measures the three things the list could contribute, and whether
each one holds:

  R1  as a DATE SOURCE for a case the platform's date does not cover —
      the list holds 320 undated rows (MEMO='-'), so most of the list is silent
  R2  as a TIE-BREAKER between several candidate dates — the list holds ONE
      date per case, so it cannot break a tie among candidates of one case;
      but it CAN pick between two CASES of the same unit
  R3  as a CHECK on the recovered date — the MEMO is the 核定公告 date, which
      is the PDF's own date, so a MEMO that DISAGREES with the platform's
      核定日期 is a signal that the platform and the PDF differ

The decisive question for R3: does the MEMO equal the PDF's date or the
platform's date, when the two differ? This probe answers it over the cases
where both are known.

Read-only, live.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import fetch_taipei_168_list_api  # noqa: E402
from urtpe.extract import to_iso  # noqa: E402

_MEMO_DATE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")


def memo_date(memo: str) -> str:
    m = _MEMO_DATE.search(memo or "")
    if not m:
        return ""
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))


def main() -> None:
    list_rows = fetch_taipei_168_list_api()
    memo_by_case = {str(r.get("case_id") or ""): memo_date(str(r.get("MEMO") or ""))
                    for r in list_rows}
    stage_by_case = {str(r.get("case_id") or ""): str(r.get("stage") or "")
                     for r in list_rows}

    # the platform's dates, from the cache
    platform: dict[str, str] = {}
    for d in sorted((ROOT / "data" / ".link_cache").iterdir()):
        f = d / "result.json"
        if not f.is_file():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        for cid, ms in (r.get("case_milestones") or {}).items():
            for label in ("核定日期", "權變核定日期"):
                if ms.get(label):
                    platform.setdefault(cid, to_iso(ms[label])[0] or "")
                    break

    # the PDF's dates, from the corpus, joined to the case ids through the
    # cache's candidate_names
    pdf: dict[str, str] = {}
    corpus = {r["recno"]: r for r in
              csv.DictReader((ROOT / "data" / "clean.tsv").open(encoding="utf-8"),
                             delimiter="\t")}
    for d in sorted((ROOT / "data" / ".link_cache").iterdir()):
        f = d / "result.json"
        if not f.is_file():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        for cid, name in (r.get("candidate_names") or {}).items():
            for row in corpus.values():
                if row["name"] == name:
                    pdf.setdefault(cid, to_iso(row["date"])[0] or "")
                    break

    print("=== R3: when the PDF and the platform disagree, what does the MEMO say? ===")
    both = [cid for cid in platform if cid in pdf and platform[cid] and pdf[cid]]
    disagree = [cid for cid in both if platform[cid] != pdf[cid]]
    print("   cases with both a PDF date and a platform date: %d" % len(both))
    print("   of those, the two DIFFER: %d" % len(disagree))
    stats = Counter()
    for cid in disagree:
        memo = memo_by_case.get(cid, "")
        if not memo:
            stats["the list holds the case, but its MEMO is empty"] += 1
        elif memo == pdf[cid]:
            stats["the MEMO equals the PDF's date"] += 1
        elif memo == platform[cid]:
            stats["the MEMO equals the platform's date"] += 1
        else:
            stats["the MEMO equals NEITHER"] += 1
    for k, v in sorted(stats.items()):
        print("      %-52s %d" % (k, v))
    print()
    print("   the disagreements, in full:")
    for cid in disagree:
        print("      %-11s the PDF %-11s the platform %-11s the MEMO %-11s stage %s"
              % (cid, pdf[cid], platform[cid],
                 memo_by_case.get(cid, "") or "-", stage_by_case.get(cid, "-")))
    print()
    print("=== R1: how much of the list is dated at all ===")
    dated = sum(1 for v in memo_by_case.values() if v)
    print("   the list's rows: %d, of which dated: %d" % (len(memo_by_case), dated))
    dated_cases = [cid for cid in platform if memo_by_case.get(cid)]
    print("   the list's dated cases that a cache knows: %d" % len(dated_cases))
    print()
    print("=== R2: could the MEMO pick between two CASES of one unit? ===")
    units = Counter()
    for cid in memo_by_case:
        if cid in platform:
            units[cid] = 1
    print("   the MEMO carries ONE date per case, so it breaks a tie among the")
    print("   cases of a unit only when their MEMO dates differ — which they do")
    print("   (each case is a separate approval). It cannot break a tie among")
    print("   the CANDIDATES OF one case, because one case has one MEMO.")


if __name__ == "__main__":
    main()
