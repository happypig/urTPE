"""Is the 都市更新計畫 keyword exposed to the compatibility 更? Read-only.

The peer session raised the edge my framing puts me closest to: the keyword
都市更新計畫 contains 更, and the corpus's 更 (U+F901) also sits inside
都市更新. If a name held BOTH — the keyword in its unified form and the
compat 更 inside 都市更新 — the substring test could in principle match the
keyword across the boundary.

This measures whether that exposure exists in the corpus or the payload.

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
CACHE = ROOT / "data" / ".link_cache"

KEYWORD = "都市更新計畫"


def compat(text) -> list[str]:
    if not isinstance(text, str):
        return []
    return [c for c in text
            if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "")]


def main() -> None:
    print("the keyword the reader tests: %r" % KEYWORD)
    print("  its 更 is U+%04X — the unified form, not a compatibility one"
          % ord(KEYWORD[2]))
    print()

    # --- the corpus -------------------------------------------------------
    rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))
    hits = [r for r in rows if KEYWORD in r["name"]]
    print("=== the corpus (%d rows) ===" % len(rows))
    print("  names containing the literal %s: %d" % (KEYWORD, len(hits)))
    # the boundary shape: the keyword's 更 adjacent to a compat 更
    exposed = []
    for r in rows:
        name = r["name"]
        if KEYWORD not in name:
            continue
        for i, c in enumerate(name):
            if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "") \
                    and i + 1 < len(name) and name[i + 1] == "更":
                exposed.append((r["recno"], name, i))
    print("  names where a compat char sits immediately before a 更: %d"
          % len(exposed))

    # what the corpus actually holds around 都市更新
    with_update = [r for r in rows if "都市更新" in r["name"]]
    print("  names containing 都市更新: %d" % len(with_update))
    tails = {}
    for r in with_update:
        i = r["name"].index("都市更新")
        tail = r["name"][i + 4:i + 12]
        tails[tail] = tails.get(tail, 0) + 1
    for tail, n in sorted(tails.items(), key=lambda kv: -kv[1])[:6]:
        print("      %-14s %d" % (tail, n))

    # --- the payload ------------------------------------------------------
    doc = json.loads(PROJECTS.read_text(encoding="utf-8"))
    payload_hits = 0
    payload_exposed = 0
    for p in doc["projects"]:
        for field in ("case_name", "name_raw"):
            for nd in p.get("nodes") or ():
                v = nd.get(field) or ""
                if KEYWORD in v:
                    payload_hits += 1
                for i, c in enumerate(v):
                    if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "") \
                            and i + 1 < len(v) and v[i + 1] == "更":
                        payload_exposed += 1
    print()
    print("=== the payload ===")
    print("  node names containing the literal %s: %d" % (KEYWORD, payload_hits))
    print("  the boundary shape anywhere in the node names: %d" % payload_exposed)

    # --- the cache --------------------------------------------------------
    cache_hits = 0
    cache_exposed = 0
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
            for name in names.values():
                if not isinstance(name, str):
                    continue
                if KEYWORD in name:
                    cache_hits += 1
                for i, c in enumerate(name):
                    if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "") \
                            and i + 1 < len(name) and name[i + 1] == "更":
                        cache_exposed += 1
    print("=== the link cache ===")
    print("  case names containing the literal %s: %d" % (KEYWORD, cache_hits))
    print("  the boundary shape: %d" % cache_exposed)

    print()
    print("=== the counterfactual, for the record ===")
    counter = "變更臺北市大安區某段" + chr(0xF901) + "計畫案"
    print("  %r" % counter)
    print("    contains the keyword: %s" % (KEYWORD in counter))
    print("    the track: %s" % _tracks(counter))
    print("    after NFKC: %s" % _tracks(unicodedata.normalize("NFKC", counter)))


if __name__ == "__main__":
    main()
