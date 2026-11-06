"""The name-only match, corpus-wide: is it unique?

For a truncated 地號 row the recovery pass anchors on the DATE and the name is
a filter. For a truncated DATE row the roles reverse: the name must carry the
identity alone, and the date is what gets recovered. So the question is
whether a name-only match is unique enough to recover a date from.

This probe runs the name-hit rule (checks 1-3 of match_row) over EVERY
published gazette row's 案名, against the city's parcel search for that
row's own unit — and reports, for each row:

  - how many candidates the name-only rule accepts;
  - how many of them are APPROVED (they carry a header approval date);
  - whether the approved ones agree on ONE date.

The last line is the acceptance criterion: the recovery pass may only write a
date when the approved candidates all carry the same one.

    python scripts/probe_recovery_date_uniqueness.py [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import recovery as R  # noqa: E402
from urtpe.recovery_sources import AshxClient  # noqa: E402


def name_hit(identity, cand) -> bool:
    """checks 1-3 of match_row: same unit, the count fragment, containment."""
    name = R.normalize_name(cand.get("case_name") or "")
    if not (identity.district in name and identity.section in name):
        return False
    if not (identity.count_fragment and identity.count_fragment in name):
        return False
    if identity.address_core and identity.address_core in name:
        return True
    return R.name_similarity(identity.name, name) >= R.LINK_THRESHOLD


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=40,
                    help="how many gazette rows to test (the cost is one search "
                         "plus one header per candidate)")
    args = ap.parse_args(argv)

    rows = list(csv.DictReader((ROOT / "data" / "clean.tsv").open(encoding="utf-8"),
                                delimiter="\t"))
    # the newest gazette's rows: the shape a future truncated-date row takes
    rows = rows[: args.limit]

    ashx = AshxClient()
    stats = Counter()
    ambiguous = []
    examples = []
    for r in rows:
        identity = R.parse_identity(r["name"])
        if identity is None:
            stats["no identity"] += 1
            continue
        time.sleep(1.2)
        family = ashx.case_family(identity.section, identity.mono, identity.suno)
        hits = [c for c in family if name_hit(identity, c)]
        stats["rows tested"] += 1
        if not hits:
            stats["no name hit"] += 1
            continue
        if len(hits) > 1:
            stats["more than one name hit"] += 1
        approved = []
        for cand in hits:
            cid = cand.get("api_case_id") or ""
            if not cid:
                continue
            time.sleep(1.2)
            top = ashx.case_top(cid)
            for field in ("uro_chk_date", "uro_chk_date2"):
                v = str(top.get(field) or "")
                if v:
                    approved.append((cid, field, v[:10]))
                    break
        dates = {v for _c, _f, v in approved}
        if not approved:
            stats["name hits, none approved"] += 1
        elif len(dates) == 1:
            stats["one name hit, one date — RECOVERABLE"] += 1
            if len(examples) < 6:
                examples.append((r["recno"], r["name"][:46],
                                 [(c, v) for c, _f, v in approved]))
        else:
            stats["name hits, several dates — AMBIGUOUS"] += 1
            ambiguous.append((r["recno"], r["name"][:46],
                              [(c, v) for c, _f, v in approved]))
        if len(hits) > 1 and len(dates) == 1:
            stats["several name hits, one date"] += 1

    print()
    for k, v in sorted(stats.items()):
        print("   %-42s %d" % (k, v))
    print()
    print("recoverable examples:")
    for e in examples:
        print("   recno %-6s %s -> %s" % e)
    print()
    print("ambiguous examples:")
    for a in ambiguous[:10]:
        print("   recno %-6s %s -> %s" % a)


if __name__ == "__main__":
    main()
