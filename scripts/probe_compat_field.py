"""Which field carries the compatibility characters? Read-only.

The corpus's 6 compatibility characters and the one live case name are the
same character class in two different places. The peer session reports the
corpus's sit in the 地號 cell and the live case's in the 案名. That
distinction decides what a test must check, so it is measured here rather
than assumed.

This compares every text column of clean.tsv and every name field of the
link cache, and tests the counterfactual the peer named: a 擬訂 title
carrying the compatibility form.

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

from urtpe.cleanse import _tracks  # noqa: E402
from urtpe.links import _PLAN_CASE_RE  # noqa: E402

CLEAN = ROOT / "data" / "clean.tsv"
CACHE = ROOT / "data" / ".link_cache"


def compat(text) -> list[str]:
    if not isinstance(text, str):
        return []
    return [c for c in text
            if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "")]


def main() -> None:
    rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))

    print("=== 1. every text column of clean.tsv (%d rows) ===" % len(rows))
    text_cols = [c for c in rows[0] if c not in ("recno", "iso_date",
                                                 "stage_index", "land_count",
                                                 "orig_count")]
    for col in text_cols:
        hits = [(r["recno"], compat(r.get(col, ""))) for r in rows
                if compat(r.get(col, ""))]
        if hits:
            print("  %-16s %d row(s)" % (col, len(hits)))
            for recno, bad in hits:
                print("      recno %-5s %s" % (recno, [hex(ord(c)) for c in bad]))
        else:
            print("  %-16s 0" % col)

    print()
    print("=== 2. the two fields side by side for the 6 records ===")
    for r in rows:
        if compat(r.get("name", "")) or compat(r.get("land", "")):
            print("  recno %-5s" % r["recno"])
            print("      案名  compat %-28s  %s"
                  % ([hex(ord(c)) for c in compat(r["name"])] or "none",
                     r["name"][:52]))
            print("      地號  compat %-28s  %s"
                  % ([hex(ord(c)) for c in compat(r["land"])] or "none",
                     r["land"][:52]))

    print()
    print("=== 3. the link cache: both name fields ===")
    counts = {"candidate_names": 0, "case_case_names": 0}
    compat_cases = {}
    total = {"candidate_names": 0, "case_case_names": 0}
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
        for field in ("candidate_names", "case_case_names"):
            names = r.get(field) or {}
            if not isinstance(names, dict):
                continue
            for cid, name in names.items():
                if not isinstance(name, str) or not name:
                    continue
                total[field] += 1
                bad = compat(name)
                if bad:
                    counts[field] += 1
                    compat_cases.setdefault(cid, (name, bad, field))
    for field in ("candidate_names", "case_case_names"):
        print("  %-18s %d names, %d carrying a compatibility ideograph"
              % (field, total[field], counts[field]))
    for cid, (name, bad, field) in compat_cases.items():
        print("    case %s  (in %s)  %s" % (cid, field, [hex(ord(c)) for c in bad]))

    print()
    print("=== 4. the counterfactual: a 擬訂 title carrying the form ===")
    compat_li = chr(0xF9DD)
    counter = ("擬訂臺北市大安區復興段三小段3地號等2筆土地都市更新事業計畫及權"
               + compat_li + "變換計畫案")
    folded = unicodedata.normalize("NFKC", counter)
    print("  as-is   plan-case match %s   track %s"
          % (bool(_PLAN_CASE_RE.match(counter)), _tracks(counter)))
    print("  folded  plan-case match %s   track %s"
          % (bool(_PLAN_CASE_RE.match(folded)), _tracks(folded)))
    print("  -> the matcher IS compatibility-blind, but no name in the corpus")
    print("     or the cache is this counterfactual.")


if __name__ == "__main__":
    main()
