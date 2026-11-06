"""The one live case name, exactly as the payload holds it. Read-only.

The character that matters is U+F9DD (CJK COMPATIBILITY IDEOGRAPH-F9DD),
which is the compatibility form of 利. A string typed by hand carries the
unified form, so the name is read from the payload rather than written out.
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

doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
found = []
for p in doc["projects"]:
    names = (p.get("links") or {}).get("candidate_names") or {}
    if not isinstance(names, dict):
        continue
    for cid, name in names.items():
        if isinstance(name, str) and any(
                "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "") for c in name):
            found.append((p["project_id"], cid, name))

for pid, cid, name in found:
    print("case %s   project %s" % (cid, pid))
    print("  the name: %s" % name)
    print("  the compatibility character sits at index %d of %d"
          % (name.index(chr(0xF9DD)), len(name)))
    print("  its codepoint: %s" % hex(ord(chr(0xF9DD))))
    print("  NFKC folds it to: %s" % hex(ord(unicodedata.normalize("NFKC", chr(0xF9DD)))))
    print()
    folded = unicodedata.normalize("NFKC", name)
    print("  the TRACK the cleanser reads:")
    print("    now    %s" % _tracks(name))
    print("    folded %s" % _tracks(folded))
    print()
    print("  the plan-case matcher:")
    print("    now    %s" % bool(_PLAN_CASE_RE.match(name)))
    print("    folded %s" % bool(_PLAN_CASE_RE.match(folded)))
    print("    (the matcher requires the name to START with 擬訂; this one starts with 變更)")
    print()

print("the corpus records for the same unit:")
rows = list(csv.DictReader((ROOT / "data" / "clean.tsv").open(encoding="utf-8"),
                            delimiter="\t"))
for r in rows:
    if "復興段三小段3" in r["name"]:
        print("  recno %-5s track %-16s stage %s" % (r["recno"], r["track"], r["stage"]))
        print("     %s" % r["name"])
