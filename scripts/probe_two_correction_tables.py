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


def _assertion(pin: str) -> str:
    """What a pin asserts: its claim, without its explanation.

    A pin reads as a claim, then an explanation. The board's pins carry
    more explanation than the dashboard's — a note about the record count, a
    code citation — and the two documents need not carry the same note. So
    the comparison is on the claim: the words up to the first full stop or
    em-dash, lower-cased.
    """
    text = re.sub(r"^\s*\d+\.\s*", "", plain(pin)).strip()
    # a full stop inside a code path or a number is not a sentence end
    text = re.sub(r"`[^`]*`", "`x`", text)
    # the claim ends at the first sentence end or dash; a semicolon inside
    # the claim ("unchanged in track;") is not
    text = re.split(r"\.\s| — |; ", text)[0]
    text = text.rstrip(".; —").lower()
    # the leading article is a choice of wording, not of claim
    text = re.sub(r"^(the\s+)?(one|a|an)\s+", "", text)
    text = re.sub(r"^the\s+", "", text)
    return text[:110]


def pins_of(text: str) -> list[str]:
    """The numbered pins of the test-first group.

    The board's list and the dashboard's list name the same six things, in
    the same order. The list is found by the heading that introduces it —
    the board says "The test-first group should pin", the dashboard says
    "The test-first group must pin six things" — and the list ends at the
    next heading.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.search(r"[Tt]he test-first group (should|must) pin", line):
            start = i
            break
    if start is None:
        return []
    out: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        if re.match(r"^\s*\d+\.\s", line):
            out.append(line.strip())
        elif out and line.strip():
            out[-1] += " " + line.strip()
    return out


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

    # the pin lists themselves — the two documents list the same six, and a
    # reader who opens both would compare them
    print()
    print("=== the pin lists ===")
    bp = pins_of(board)
    dp = pins_of(doc)
    print("  the board lists %d pins, the dashboard lists %d"
          % (len(bp), len(dp)))
    pin_mismatches = 0
    for i in range(max(len(bp), len(dp))):
        b = plain(bp[i]) if i < len(bp) else "(absent)"
        d = plain(dp[i]) if i < len(dp) else "(absent)"
        # the pin's ASSERTMENT is what matters: the words up to the first
        # full stop, lower-cased, so a capitalised heading and a sentence
        # that says the same thing compare equal
        b_key = _assertion(b)
        d_key = _assertion(d)
        same = b_key == d_key
        if not same:
            pin_mismatches += 1
        print("  pin %d %s" % (i + 1, "same" if same else "DIFFERS"))
        if not same:
            print("     board      %s" % b_key)
            print("     dashboard  %s" % d_key)

    if pin_mismatches:
        mismatches += pin_mismatches

    print()
    if mismatches:
        print("  VERDICT: the two tables DISAGREE on %d row(s)." % mismatches)
        return 1
    print("  VERDICT: the two tables are identical, cell for cell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
