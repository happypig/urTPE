"""The stage ordinal disambiguates the name-only match.

The name-only rule leaves 10 of 23 rows ambiguous: the candidates are the
unit's successive revisions, each with its own approval date. But the row's
案名 carries the stage ordinal — 擬訂 / 變更 / 變更(第二次) / 變更(第三次) —
and the candidates carry it too.

This probe re-runs the uniqueness measurement with the ordinal added to the
name-hit rule, and reports how many rows become unambiguous.

Read-only, live. The cost is one parcel search per row plus one header per
candidate.
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
from urtpe.recovery_sources import AshxClient  # noqa: E402

# the stage ordinal, as the city writes it at the head of the 案名
_ORD_RE = re.compile(r"^(擬訂|變更(?:\(第[一二三四五六七八九十]+次\))?)")


def ordinal(name: str) -> str:
    m = _ORD_RE.match(R.normalize_name(name or ""))
    return m.group(1) if m else ""


def name_hit(identity, cand, with_ordinal: bool) -> bool:
    name = R.normalize_name(cand.get("case_name") or "")
    if not (identity.district in name and identity.section in name):
        return False
    if not (identity.count_fragment and identity.count_fragment in name):
        return False
    if with_ordinal:
        row_ord = ordinal(identity.name)
        cand_ord = ordinal(name)
        if row_ord and cand_ord and row_ord != cand_ord:
            return False
    if identity.address_core and identity.address_core in name:
        return True
    return R.name_similarity(identity.name, name) >= R.LINK_THRESHOLD


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args(argv)

    rows = list(csv.DictReader((ROOT / "data" / "clean.tsv").open(encoding="utf-8"),
                                delimiter="\t"))[: args.limit]
    ashx = AshxClient()
    stats = Counter()
    still_ambiguous = []
    for r in rows:
        identity = R.parse_identity(r["name"])
        if identity is None:
            stats["no identity"] += 1
            continue
        time.sleep(1.2)
        family = ashx.case_family(identity.section, identity.mono, identity.suno)
        hits = [c for c in family if name_hit(identity, c, with_ordinal=True)]
        stats["rows tested"] += 1
        if not hits:
            stats["no name hit (with the ordinal)"] += 1
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
            stats["name hits, none approved"] += 1
        elif len(dates) == 1:
            stats["one date — RECOVERABLE"] += 1
            if len(hits) > 1:
                stats["  (several name hits, all one date)"] += 1
        else:
            stats["several dates — STILL AMBIGUOUS"] += 1
            still_ambiguous.append((r["recno"], r["name"][:44],
                                    [(c, v) for c, v in approved]))
    print()
    for k, v in sorted(stats.items()):
        print("   %-42s %d" % (k, v))
    print()
    for a in still_ambiguous:
        print("   recno %-6s %s -> %s" % a)


if __name__ == "__main__":
    main()
