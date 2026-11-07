"""Compare one pin's wording across the two documents. Read-only.

The pin lists match in order and in the sentence each pin asserts, but the
board's pin 3 was once worded differently from the dashboard's, and a
difference in wording is what a reader comparing the two would notice first.

This prints the first sentence of a given pin from both documents, so the
wording can be compared rather than assumed.

    python scripts/probe_pin_wording.py [pin number]
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from probe_two_correction_tables import pins_of, plain  # noqa: E402

BOARD = ROOT / "docs" / "inspection-batchD.md"
DOC = ROOT / "docs" / "DashboardNUXUI.md"


def main() -> int:
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    board = BOARD.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    bp, dp = pins_of(board), pins_of(doc)
    if want > max(len(bp), len(dp)):
        print("pin %d does not exist" % want)
        return 1

    print("=== pin %d ===" % want)
    for name, pins in (("board", bp), ("dashboard", dp)):
        text = plain(pins[want - 1])
        print("  %-10s %s" % (name, text[:300]))
    print()

    b = plain(bp[want - 1])
    d = plain(dp[want - 1])
    same = b == d
    print("  identical: %s" % same)
    if not same:
        # the board's pins are lower-case sentences, the dashboard's are
        # capitalised headings — compare case-folded
        same_folded = b.lower() == d.lower()
        print("  identical ignoring case: %s" % same_folded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
