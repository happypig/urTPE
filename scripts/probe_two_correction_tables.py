"""Compare the board's correction table with the dashboard document's. Read-only.

Two documents record the same six corrections: `docs/inspection-batchD.md`
(the board) and `docs/DashboardNUXUI.md` (the dashboard exploration). They
were written by two sessions and drifted: the board grew to six rows, the
document still said four, and one row counted groups where the other counted
things.

A reader who compares the two places would see two different accounts of the
same history. This compares them cell for cell, so the agreement is measured
rather than believed.

Read-only.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

BOARD = ROOT / "docs" / "inspection-batchD.md"
DOC = ROOT / "docs" / "DashboardNUXUI.md"

# The rows that make up each table, keyed by the correction they describe.
BOARD_ROWS = [
    "a character read by eye",
    "a match compared against `None`",
    "a field guessed from the neighbouring column",
    "a reader count taken from the reader in view",
    "a denominator taken from a sample",
    "a blast radius read as a scope",
]


def cells_of(text: str, first_column: str) -> dict[str, list[str]]:
    """Every table row whose first cell names one of the corrections.

    The board's table has 3 columns (the correction, what was stated, what
    was true). The dashboard's numbers its rows, so it has 4 (the number,
    then the same three). The number is dropped before comparing.
    """
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        parts = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(parts) < 3:
            continue
        # drop a leading row number, if there is one
        if re.fullmatch(r"\d+", parts[0]):
            parts = parts[1:]
        for key in first_column:
            if key in parts[0]:
                out.setdefault(key, []).append(parts)
    return out


def plain(cell: str) -> str:
    """A cell with markdown emphasis removed, so the comparison is about the
    TEXT and not about which document chose to bold it."""
    return re.sub(r"\*\*", "", cell).strip()


def main() -> int:
    board = BOARD.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    print("=== the correction tables ===")
    print("  the board:      %s" % BOARD.name)
    print("  the dashboard:  %s" % DOC.name)

    b = cells_of(board, BOARD_ROWS)
    d = cells_of(doc, BOARD_ROWS)

    print()
    print("  the board holds %d of the %d corrections" % (len(b), len(BOARD_ROWS)))
    print("  the dashboard holds %d of the %d corrections" % (len(d), len(BOARD_ROWS)))

    print()
    mismatches = 0
    for key in BOARD_ROWS:
        if key not in b:
            print("  MISSING from the board:    %s" % key)
            mismatches += 1
            continue
        if key not in d:
            print("  MISSING from the dashboard: %s" % key)
            mismatches += 1
            continue
        brow = b[key][0]
        drow = d[key][0]
        # the row number has already been dropped; compare the TEXT, so a
        # difference in which document chose to bold a word is not a
        # difference in what the two documents say
        same = [plain(c) for c in brow] == [plain(c) for c in drow]
        if not same:
            mismatches += 1
            print("  DIFFERS: %s" % key)
            print("     board      %s" % brow)
            print("     dashboard  %s" % drow)
        else:
            print("  same: %s" % key)

    print()
    print("  cells compared: %d   mismatches: %d" % (len(BOARD_ROWS), mismatches))

    # the counts each document claims
    print()
    print("=== the counts each document claims ===")
    for name, text in (("board", board), ("dashboard", doc)):
        for m in re.finditer(r"[^.]*\b(four|six|three|four|six)\s+corrections[^.]*\.", text):
            print("  %-10s %s" % (name, m.group(0).strip()[:110]))

    print()
    print("=== the pins ===")
    for name, text in (("board", board), ("dashboard", doc)):
        for m in re.finditer(r"[^.]*\*\*(\w+ )?pins\*\*[^.]*\.", text):
            print("  %-10s %s" % (name, m.group(0).strip()[:110]))
        for m in re.finditer(r"^\s*(\d)\. .*live case[^.]*$", text, re.M):
            print("  %-10s pin %s" % (name, m.group(1)))

    print()
    if mismatches:
        print("  VERDICT: the two tables DISAGREE on %d row(s)." % mismatches)
        return 1
    print("  VERDICT: the two tables are identical, cell for cell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
