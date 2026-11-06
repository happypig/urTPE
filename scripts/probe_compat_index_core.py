"""What does the compatibility form cost in the portal index core? Read-only.

`build_portal_index` builds each index entry's `core` from the PORTAL's own
title: `parse_name_id(title)` when it parses, else a crude string-strip
fallback. The corpus's 6 records have compat 北/都/更 in their 案名, so their
OWN parse fails — but the index core is built from the portal's title, which
is a different string.

So the question is: does the portal's title for these 3 units carry a
compatibility form, and does the index core for those units differ from the
core the corpus computes?

This compares the index's cores with the cores the corpus would compute for
the 3 affected projects, and reports what the lookup does.

Read-only, offline.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.cleanse import parse_name_id  # noqa: E402
from urtpe.links import load_portal_index, lookup_in_portal_index  # noqa: E402

CACHE = ROOT / "data" / ".link_cache"
CLEAN = ROOT / "data" / "clean.tsv"

AFFECTED = {
    "北投區-桃源段四小段-424-8地號等15筆",
    "信義區-三興段一小段-972地號等9筆",
    "南港區-南港段三小段-274地號等16筆",
}


def core_from_name(name: str) -> str:
    """The core the cleanser's fields would build."""
    district, section, parcel, count = parse_name_id(name)
    if district and section and parcel:
        core = district + section + parcel
        if count:
            core += "地號等%s筆" % count
        return core
    return ""


def main() -> None:
    index = load_portal_index(CACHE)
    cores = {e["core"] for e in index}
    print("the portal index holds %d entries" % len(index))
    print()

    print("=== the index's cores for the 3 affected units ===")
    for core in sorted(cores):
        if any(k in core for k in ("桃源段四小段", "三興段一小段", "南港段三小段")):
            hit = lookup_in_portal_index(core, index)
            print("  %-40s view %s" % (core, hit))

    print()
    print("=== the cores the CORPUS computes for the 3 affected projects ===")
    rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))
    for pid in sorted(AFFECTED):
        names = [r["name"] for r in rows
                 if r["district"] and r["section"]
                 and pid.replace(r["district"] + "-", "").replace(
                     r["section"] + "-", "").replace("地號等", "")[:4] in r["name"]]
        for name in names[:1]:
            now = core_from_name(name)
            folded = core_from_name(unicodedata.normalize("NFKC", name))
            print("  %s" % pid)
            print("     the corpus's own parse   now    %r" % now)
            print("                            folded %r" % folded)
            print("     the index holds that core: %s" % (folded in cores))
            if folded:
                print("     the lookup on the folded core: %s"
                      % lookup_in_portal_index(folded, index))

    print()
    print("=== the reverse: does the index hold a core the corpus cannot make? ===")
    corpus_cores = set()
    for r in rows:
        c = core_from_name(r["name"])
        if c:
            corpus_cores.add(c)
    orphan = [c for c in cores
              if c and c not in corpus_cores
              and any(k in c for k in ("桃源段四小段", "三興段一小段", "南港段三小段"))]
    print("  index cores for the 3 units that the corpus cannot compute: %d"
          % len(orphan))
    for c in orphan:
        print("     %r" % c)


if __name__ == "__main__":
    main()
