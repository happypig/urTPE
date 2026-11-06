"""CJK compatibility ideographs in the city's case names.

Found 2026-11-06 while measuring the name-only rule for a truncated DATE cell:
the city's live case name for 復興段三小段3 writes 利 as U+F9DD (CJK
COMPATIBILITY IDEOGRAPH-F9DD), not U+5229 (CJK UNIFIED IDEOGRAPH-5229). The
character looks identical; the pipeline's track reader misses it, so the row
reads as 事業計畫 alone.

This probe measures the population: how many of the city's case names carry a
compatibility ideograph, which ones, and what NFKC does to them. NFKC folds
every compatibility ideograph to its unified form, so it is the folding the
reader needs — but the corpus's own 案名 (read from the PDF) uses the unified
form, so the two sides only agree after folding.

Read-only, live.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.recovery_sources import AshxClient  # noqa: E402


def compat_chars(text: str) -> list[str]:
    out = []
    for ch in text:
        if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(ch, ""):
            out.append(ch)
    return out


def main() -> None:
    # 1. the corpus's own 案名 (from the PDF) — does it carry any?
    rows = list(csv.DictReader((ROOT / "data" / "clean.tsv").open(encoding="utf-8"),
                                delimiter="\t"))
    corpus_hits = Counter()
    for r in rows:
        for ch in compat_chars(r["name"]):
            corpus_hits[ch] += 1
    print("the corpus's own 案名 (%d rows, from the PDF):" % len(rows))
    print("   rows carrying a compatibility ideograph:",
          sum(1 for r in rows if compat_chars(r["name"])))
    print("   the characters:", {c: n for c, n in corpus_hits.items()})
    print()

    # 2. the city's live case names — the parcel search over a SAMPLE of units.
    #    The figure below is a sample, not a population: it reads the names
    #    the first 60 units' searches return. The population we HOLD is the
    #    link cache — see scripts/probe_compat_population.py, which counts it
    #    offline. Both reach the same single affected case.
    print("the city's live case names (one parcel search per unit, a SAMPLE):")
    ashx = AshxClient()
    units = []
    seen = set()
    for r in rows[:60]:
        key = (r["district"], r["section"], r["first_parcel"])
        if key in seen:
            continue
        seen.add(key)
        units.append(key)
    hits = Counter()
    affected = []
    names_read = 0
    for district, section, parcel in units:
        mono = str(parcel).partition("-")[0].zfill(4)
        time.sleep(1.2)
        try:
            fam = ashx.case_family(section, mono, "0000")
        except Exception:
            continue
        for c in fam:
            name = c.get("case_name") or ""
            names_read += 1
            bad = compat_chars(name)
            if bad:
                for ch in bad:
                    hits[ch] += 1
                affected.append((c.get("api_case_id"), name))
    print("   case names read:", names_read)
    print("   names carrying a compatibility ideograph:", len(affected))
    print("   the characters:", {c: n for c, n in hits.items()})
    print()
    for cid, name in affected[:10]:
        bad = compat_chars(name)
        print("   %-11s %s" % (cid, name))
        print("        the characters: %s -> NFKC %s"
              % ([hex(ord(c)) for c in bad],
                 [hex(ord(c)) for c in unicodedata.normalize("NFKC", name)
                  if ord(c) > 0xF000]))
        print("        the track as read now: %s"
              % _tracks_of(name))
        print("        the track after NFKC: %s"
              % _tracks_of(unicodedata.normalize("NFKC", name)))


def _tracks_of(name: str) -> list[str]:
    from urtpe.cleanse import _tracks
    return _tracks(name)


if __name__ == "__main__":
    main()
