"""Append the 萬隆519 confirm_merge entry to the live ledger.

The two 文山區-萬隆段二小段-519地號等NN筆 projects are one 更新單元: both
resolve to the national page view/153 and both name the same three city
cases (09611281, 10303241, 10303242). The gazette's 地號 cells disagree about
the count — 23筆 (2017, 2022) against 56筆 (2013) — because the 2013 cell is
publisher-truncated: it declares 56 筆, reads 53 parcels, and ends mid-list at
`…575 、 575 -`. The merge scores the pair 0.654, in the flag band and below
the 0.7 merge threshold, so it is named as a borderline pair (docs
inspection-batchD, the 2026-10-28 ingest's 臨界對 list) and a person decides.

This appends that decision. The ledger is append-only; fixing a wrong
correction means appending one that supersedes it.

    python scripts/append_wanlong_confirm_merge.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.ledger import Correction, CorrectionLedger  # noqa: E402

LEDGER = pathlib.Path("D:/project/urtpe-gazettes/corrections.jsonl")

# the two records, copied verbatim from the cleansed rows (data/clean.tsv).
# The key is (normalized 地號 cell, ISO date), so the date is what tells
# recno 970 from recno 410 — they share one cell.
MATCH_LAND = ("臺北市文山區萬隆段二小段 519、519-14、519-19、519-20、519-21、519-22、"
              "519-23、51-24、519-25、519-26、519-27、519-29、519-30、519-31、519-32、"
              "519-33、519-34、531、536、540、551、575 及 575-4 地號等 23筆土地")
MATCH_DATE = "2017-08-01"          # recno 970
WITH_LAND = ("臺北市文山區萬隆段二小段519 、 519 -4、519 -5、519-6、519-7、 519 -8、"
             "519 -9、519 -10 、519 -11 、 519 -12 、519-13 、519-14 、 519 -15 、"
             "519-16 、 519 -17 、 519 -18 、 519-19 、519 -20 、 519 -21 、519 519-22 、"
             "519 -23 、 519 -24 、519-25 、519 -26 、 519 -27 、519-28 、519-29 、"
             " 519 -30 、519-31 、 519 -32 、 519 -33 、519 -34 、531 、533 、534、 535 、"
             "536 、539 、540 、541 、544 、 546 、547 、548 、549 、550 、551 、 552 、"
             "553 、555 、558 、559 、575 、 575 -")
WITH_DATE = "2013-02-07"           # recno 1208

WHY = ("both resolve to the national page view/153 and both name the same three "
       "city cases (09611281, 10303241, 10303242), so the portal reads one "
       "更新單元; the gazette's 地號 cells disagree on the count (23筆 against "
       "56筆) because the 2013 cell is publisher-truncated — it declares 56 筆, "
       "reads 53 parcels, and ends mid-list at `…575 、 575 -`, so the missing "
       "parcels are absent from the PDF rather than miscounted. The merge "
       "scores the pair 0.654, in the flag band and below the 0.7 merge "
       "threshold, so it is named as a borderline pair and a person confirms "
       "it (the 吉林676 precedent, ledger-confirm-merge D5). "
       "user-confirmed 2026-11-10")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entry = Correction(
        match_land_core=MATCH_LAND, match_iso_date=MATCH_DATE,
        field="", to=None,
        confirm_merge=True,
        with_land_core=WITH_LAND, with_iso_date=WITH_DATE,
        why=WHY, by="happypig",
    )
    print(entry.describe()[:200])

    if args.dry_run:
        print("dry run — nothing written")
        return 0

    led = CorrectionLedger(LEDGER)
    before = len(led.entries())
    # the ledger is append-only and a duplicate correction is applied twice, so
    # refuse to append an entry that is already there
    for existing in led.entries():
        if (existing.key == entry.key
                and existing.with_key == entry.with_key
                and existing.confirm_merge == entry.confirm_merge):
            print("already present — nothing appended")
            return 0
    led.append(entry)
    after = led.entries()
    print("appended: %d -> %d entries" % (before, len(after)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
