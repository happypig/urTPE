"""Does the compatibility form break parse_name_id? Read-only.

The peer session's document names a third reader: `parse_name_id()` in
`urtpe/cleanse.py` returns empty fields on the 6 corpus records, because its
regex cannot match a compatibility 北 or 都.

If that is true, the fix has a second reader after all — and the NFKC change
would move the national-portal index core for those 6 records. This measures
it: the parse before and after folding, for the 6 records and for the whole
corpus, and what the index core would become.

Read-only, offline.
"""
from __future__ import annotations

import csv
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.cleanse import parse_name_id  # noqa: E402

CLEAN = ROOT / "data" / "clean.tsv"


def main() -> None:
    rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))

    print("=== the 6 records: parse_name_id before and after folding ===")
    moved = 0
    for r in rows:
        name = r["name"]
        bad = [c for c in name
               if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "")]
        if not bad:
            continue
        before = parse_name_id(name)
        after = parse_name_id(unicodedata.normalize("NFKC", name))
        flag = "CHANGED" if before != after else "same"
        if before != after:
            moved += 1
        print("  recno %-5s %s" % (r["recno"], flag))
        print("      now    %s" % (before,))
        print("      folded %s" % (after,))

    print()
    print("  of the 6, the parse changes for: %d" % moved)

    print()
    print("=== the whole corpus: parse_name_id before and after folding ===")
    changed = []
    for r in rows:
        name = r["name"]
        before = parse_name_id(name)
        after = parse_name_id(unicodedata.normalize("NFKC", name))
        if before != after:
            changed.append((r["recno"], before, after))
    print("  rows whose parse changes: %d of %d" % (len(changed), len(rows)))
    for recno, before, after in changed[:10]:
        print("    recno %-5s %s -> %s" % (recno, before, after))

    # what the index core would become for the affected records
    print()
    print("=== the index core for the 6 ===")
    print("  (the core the national portal index is keyed on)")
    for r in rows:
        name = r["name"]
        bad = [c for c in name
               if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "")]
        if not bad:
            continue
        district, section, parcel, count = parse_name_id(name)
        folded = parse_name_id(unicodedata.normalize("NFKC", name))
        core_now = "".join([district, section, parcel]) + (
            "地號等%s筆" % count if count else "")
        core_folded = "".join([folded[0], folded[1], folded[2]]) + (
            "地號等%s筆" % folded[3] if folded[3] else "")
        print("    recno %-5s now    %r" % (r["recno"], core_now))
        print("              folded %r" % core_folded)


if __name__ == "__main__":
    main()
