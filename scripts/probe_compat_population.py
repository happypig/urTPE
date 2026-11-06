"""The population of city case names we actually hold. Read-only.

The peer session is right that "1 in 360" was a sample, not a population:
`scripts/probe_compat_ideographs.py` queries the city for the first 60 units
and reads the names they return. The population we HOLD is the whole link
cache.

This counts the distinct city case names in the cache — both name fields,
deduplicated by case id — and how many carry a compatibility ideograph. It
also confirms the corpus's row count, so the figure in the board is read
rather than hard-coded.

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

CLEAN = ROOT / "data" / "clean.tsv"
CACHE = ROOT / "data" / ".link_cache"


def compat(text) -> list[str]:
    if not isinstance(text, str):
        return []
    return [c for c in text
            if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "")]


def main() -> None:
    rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))
    corpus_compat = [r for r in rows if compat(r["name"])]
    print("=== the corpus ===")
    print("  rows: %d" % len(rows))
    print("  rows whose 案名 carries a compatibility ideograph: %d"
          % len(corpus_compat))
    corpus_chars = set()
    for r in corpus_compat:
        corpus_chars.update(corrupt := compat(r["name"]))
    print("  the characters: %s"
          % sorted({hex(ord(c)) for c in corpus_chars}))
    print("  rows carrying a compatibility 利: %d"
          % sum(1 for r in rows if chr(0x5229) in "".join(compat(r["name"]))))

    print()
    print("=== the city's case names we hold (the link cache) ===")
    by_case: dict[str, str] = {}
    per_field = {"candidate_names": 0, "case_case_names": 0}
    entries = 0
    for d in sorted(CACHE.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        rf = d / "result.json"
        if not rf.is_file():
            continue
        try:
            r = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entries += 1
        for field in per_field:
            names = r.get(field) or {}
            if not isinstance(names, dict):
                continue
            for cid, name in names.items():
                if isinstance(name, str) and name:
                    per_field[field] += 1
                    by_case.setdefault(cid, name)

    print("  cache entries read: %d" % entries)
    print("  name entries per field: %s" % per_field)
    print("  distinct city case ids we hold: %d" % len(by_case))
    hits = {cid: name for cid, name in by_case.items() if compat(name)}
    print("  distinct cases carrying a compatibility ideograph: %d" % len(hits))
    for cid, name in hits.items():
        print("    %s  %s" % (cid, [hex(ord(c)) for c in compat(name)]))
        print("       %s" % name[:70])

    print()
    print("=== the sample the original probe read ===")
    print("  scripts/probe_compat_ideographs.py queries the city for the first")
    print("  60 units and reads the names those searches return. The count")
    print("  varies a little between runs (357 read on 2026-11-07), which is")
    print("  itself the reason it is a SAMPLE and not a denominator.")
    print("  The figures above are the population we hold.")


if __name__ == "__main__":
    main()
