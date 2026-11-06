"""Measure what NFKC does to the corpus's case names. Read-only.

The peer asked for this before any NFKC change is opened: run the
normalisation over the payload and show that the six corpus records and the
one live case name both come out right, and that nothing else in the corpus
moves.

Three things are measured:

  1. the corpus's own 案名 — which records carry a compatibility ideograph,
     and whether folding them changes the TRACK the cleanser reads
  2. the live case names in links.candidate_names — the one case whose name
     the track reader currently misses
  3. the blast radius — every name in the corpus and the payload, before and
     after folding, to show what else moves

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

CLEAN = ROOT / "data" / "clean.tsv"
PROJECTS = ROOT / "data" / "projects.json"


def compat_chars(text: str) -> list[str]:
    return [c for c in (text or "")
            if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "")]


def main() -> None:
    rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))

    # --- 1. the corpus's own 案名 -----------------------------------------
    print("=== 1. the corpus's own 案名 (%d rows) ===" % len(rows))
    hits = []
    for r in rows:
        bad = compat_chars(r["name"])
        if bad:
            hits.append((r, bad))
    print("  records carrying a compatibility ideograph: %d" % len(hits))
    for r, bad in hits:
        folded = unicodedata.normalize("NFKC", r["name"])
        same_track = _tracks(r["name"]) == _tracks(folded)
        print("    recno %-5s %-4s %s  -> NFKC %s"
              % (r["recno"], r["district"],
                 [hex(ord(c)) for c in bad],
                 [hex(ord(c)) for c in compat_chars(folded)] or "none"))
        print("       the track now %s / after NFKC %s  %s"
              % (_tracks(r["name"]), _tracks(folded),
                 "unchanged" if same_track else "CHANGED"))
        print("       the district comes from the 行政區 column: %r" % r["district"])
    moved = sum(1 for r, _ in hits
                if _tracks(r["name"]) != _tracks(unicodedata.normalize("NFKC", r["name"])))
    print("  the track changes for %d of the %d" % (moved, len(hits)))

    # --- 2. the live case names in the payload ----------------------------
    print()
    print("=== 2. the live case names in links.candidate_names ===")
    doc = json.loads(PROJECTS.read_text(encoding="utf-8"))
    live = []
    for p in doc["projects"]:
        names = (p.get("links") or {}).get("candidate_names") or {}
        if not isinstance(names, dict):
            continue
        for cid, name in names.items():
            if isinstance(name, str) and compat_chars(name):
                live.append((p["project_id"], cid, name))
    print("  live case names carrying a compatibility ideograph: %d" % len(live))
    for pid, cid, name in live:
        folded = unicodedata.normalize("NFKC", name)
        print("    %s  %s" % (cid, pid))
        print("       the characters %s -> NFKC %s"
              % ([hex(ord(c)) for c in compat_chars(name)],
                 [hex(ord(c)) for c in compat_chars(folded)] or "none"))
        print("       the track now %s / after NFKC %s"
              % (_tracks(name), _tracks(folded)))
        from urtpe.links import _PLAN_CASE_RE
        print("       the plan-case matcher now %s / after NFKC %s"
              % (bool(_PLAN_CASE_RE.match(name)),
                 bool(_PLAN_CASE_RE.match(folded))))

    # --- 3. the blast radius ----------------------------------------------
    print()
    print("=== 3. the blast radius: every name in the corpus ===")
    changed = 0
    for r in rows:
        if unicodedata.normalize("NFKC", r["name"]) != r["name"]:
            changed += 1
    print("  corpus 案名 whose NFKC form differs from the original: %d" % changed)
    print("  of those, the ones carrying a compatibility ideograph: %d" % len(hits))

    # the whole payload: every case_name, candidate name and orphan name
    total = names_touched = 0
    for p in doc["projects"]:
        for nd in p.get("nodes") or ():
            for field in ("case_name", "name_raw", "land"):
                v = nd.get(field) or ""
                if v:
                    total += 1
                    if unicodedata.normalize("NFKC", v) != v:
                        names_touched += 1
        for g in (p.get("links") or {}).get("orphan_nodes") or ():
            v = g.get("case_name") or ""
            if v:
                total += 1
                if unicodedata.normalize("NFKC", v) != v:
                    names_touched += 1
    print("  payload strings checked: %d, of which NFKC changes: %d"
          % (total, names_touched))


if __name__ == "__main__":
    main()
