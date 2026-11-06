"""Does NFKC change which cases the plan-case matcher selects? Read-only.

`_PLAN_CASE_RE` gates `pick_implementation_payload`: the dates come from the
 city's 擬訂 plan case. The claim under test is that NFKC changes that
selection — that a compat-form title the matcher currently misses would match
after folding.

This walks the WHOLE link cache, not just the emitted payload, because the
candidate names live there. It answers:

  1. how many case names carry a compatibility ideograph
  2. for each, does the plan-case matcher match before and after folding
  3. how many names the matcher would NEWLY match after folding
  4. which payloads would therefore contribute dates they do not now

Read-only, offline.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import _PLAN_CASE_RE  # noqa: E402

CACHE = ROOT / "data" / ".link_cache"


def compat_chars(text: str) -> list[str]:
    return [c for c in (text or "")
            if "COMPATIBILITY IDEOGRAPH" in unicodedata.name(c, "")]


def main() -> None:
    total_names = 0
    compat_names = []
    newly_matched = []
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
        names = r.get("case_case_names") or {}
        if not isinstance(names, dict):
            names = {}
        payloads = r.get("implementation") or {}
        for cid, name in names.items():
            if not isinstance(name, str) or not name:
                continue
            total_names += 1
            folded = unicodedata.normalize("NFKC", name)
            raw_match = bool(_PLAN_CASE_RE.match(name))
            fold_match = bool(_PLAN_CASE_RE.match(folded))
            bad = compat_chars(name)
            if bad:
                compat_names.append((d.name, cid, name, bad, raw_match, fold_match))
            if fold_match and not raw_match:
                newly_matched.append((d.name, cid, name, payloads.get(cid)))

    print("case names in the caches: %d" % total_names)
    print("names carrying a compatibility ideograph: %d" % len(compat_names))
    for pid, cid, name, bad, raw, fold in compat_names:
        print("  %s  %s" % (cid, pid))
        print("     the characters %s" % [hex(ord(c)) for c in bad])
        print("     the plan-case matcher: now %s / after NFKC %s" % (raw, fold))
        print("     the name: %s" % name[:70])

    print()
    print("names the plan-case matcher would NEWLY match after folding: %d"
          % len(newly_matched))
    for pid, cid, name, payload in newly_matched:
        print("  %s  %s" % (cid, pid))
        print("     %s" % name[:70])
        print("     it carries a payload: %s" % (bool(payload)))

    # the same question for the TRACK reader, over the corpus
    print()
    from urtpe.cleanse import _tracks
    rows = list(__import__("csv").DictReader(
        (ROOT / "data" / "clean.tsv").open(encoding="utf-8"), delimiter="\t"))
    track_moves = 0
    for r in rows:
        name = r["name"]
        if _tracks(name) != _tracks(unicodedata.normalize("NFKC", name)):
            track_moves += 1
            print("  recno %s  %s -> %s" % (
                r["recno"], _tracks(name),
                _tracks(unicodedata.normalize("NFKC", name))))
    print("corpus rows whose TRACK changes after folding: %d of %d"
          % (track_moves, len(rows)))


if __name__ == "__main__":
    main()
