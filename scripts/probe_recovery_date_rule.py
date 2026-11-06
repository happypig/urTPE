"""The name-only rule for a truncated DATE cell: ordinal + track. Measured.

For a truncated 地號 row the recovery pass anchors on the DATE and the name is
a filter. For a truncated DATE row the roles reverse: the name must carry the
identity alone, and the date is what gets recovered. So the acceptance rule
has to decide from the name ALONE.

This probe runs the complete candidate rule over gazette rows and reports how
many resolve to exactly one approval date:

  check 1  same unit (district + 段/小段)      — the existing rule
  check 2  the declared count fragment appears  — the existing rule
  check 3  the stage ordinal agrees            — NEW for a date-truncated row
  check 4  the track set agrees                — NEW for a date-truncated row
  check 5  the approved candidates carry ONE date — the acceptance

It reports the outcome per row, so the residual is visible rather than
averaged away.

    python scripts/probe_recovery_date_rule.py [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import recovery as R  # noqa: E402
from urtpe.cleanse import _tracks  # noqa: E402
from urtpe.recovery_sources import AshxClient  # noqa: E402

_ORD_RE = re.compile(r"^(擬訂|變更(?:\(第[一二三四五六七八九十]+次\))?)")


def ordinal(name: str) -> str:
    m = _ORD_RE.match(R.normalize_name(name or ""))
    return m.group(1) if m else ""


def tracks(name: str) -> frozenset:
    return frozenset(_tracks(R.normalize_name(name or "")))


def candidates(identity, cand, row_ord, row_tracks) -> bool:
    """checks 1-4: the name alone must pick the candidate."""
    name = R.normalize_name(cand.get("case_name") or "")
    if not (identity.district in name and identity.section in name):
        return False
    if not (identity.count_fragment and identity.count_fragment in name):
        return False
    if row_ord and ordinal(name) and ordinal(name) != row_ord:
        return False
    cand_tracks = tracks(name)
    # EQUALITY, not a subset relation. Measured 2026-11-06: a subset relation
    # admits the area-split twin (recno 10: 10012274 is 事業計畫, 11507024 is
    # 權利變換, and the row names 權利變換 alone — the subset admits both) and
    # creates a new ambiguity (recno 27). Equality keeps the residual at 0
    # ambiguous rows in the 38-row sample.
    if row_tracks and cand_tracks and cand_tracks != row_tracks:
        return False
    if identity.address_core and identity.address_core in name:
        return True
    return R.name_similarity(identity.name, name) >= R.LINK_THRESHOLD


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args(argv)

    rows = list(csv.DictReader((ROOT / "data" / "clean.tsv").open(encoding="utf-8"),
                                delimiter="\t"))[: args.limit]
    ashx = AshxClient()
    stats = Counter()
    residual = []
    for r in rows:
        identity = R.parse_identity(r["name"])
        if identity is None:
            stats["no identity from the name"] += 1
            continue
        stats["rows tested"] += 1
        time.sleep(1.2)
        family = ashx.case_family(identity.section, identity.mono, identity.suno)
        row_ord = ordinal(identity.name)
        row_tracks = tracks(identity.name)
        hits = [c for c in family
                if candidates(identity, c, row_ord, row_tracks)]
        if not hits:
            stats["no candidate survives the name rule"] += 1
            residual.append((r["recno"], r["name"][:44], "no candidate"))
            continue
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
                    approved.append((cid, v[:10]))
                    break
        dates = {v for _c, v in approved}
        if not approved:
            stats["candidates, none approved"] += 1
            residual.append((r["recno"], r["name"][:44], "none approved"))
        elif len(dates) == 1:
            stats["ONE DATE — recoverable"] += 1
        else:
            stats["several dates — residual"] += 1
            residual.append((r["recno"], r["name"][:44],
                             [(c, v) for c, v in approved]))
    print()
    for k, v in sorted(stats.items()):
        print("   %-42s %d" % (k, v))
    print()
    print("the residual:")
    for x in residual:
        print("   recno %-6s %s -> %s" % x)


if __name__ == "__main__":
    main()
