"""Does the name-only rule recover the RIGHT date?

The rule's purpose is to replace a missing 核定日期 cell. So it must recover
the date the corpus's own row carries — otherwise it has replaced one wrong
value with another wrong value.

This probe runs the complete rule over gazette rows and compares the recovered
date with the row's own date. The row's date is the ground truth: the corpus
read it from the same document the rule would repair.

    python scripts/probe_recovery_date_accuracy.py [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "scripts"))
from probe_recovery_date_rule_final import (  # noqa: E402
    candidates, nfkc, ordinal, tracks,
)
from urtpe import recovery as R  # noqa: E402
from urtpe.recovery_sources import AshxClient  # noqa: E402


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args(argv)

    rows = list(csv.DictReader((ROOT / "data" / "clean.tsv").open(encoding="utf-8"),
                                delimiter="\t"))[: args.limit]
    ashx = AshxClient()
    stats = Counter()
    wrong = []
    for r in rows:
        identity = R.parse_identity(nfkc(r["name"]))
        if identity is None:
            continue
        stats["rows tested"] += 1
        time.sleep(1.2)
        family = ashx.case_family(identity.section, identity.mono, identity.suno)
        hits = [c for c in family
                if candidates(identity, c, ordinal(identity.name),
                              tracks(identity.name), r["name"])]
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
        if len(dates) != 1:
            stats["not one date"] += 1
            continue
        recovered = dates.pop()
        own = R.to_iso(r["date"])[0] if hasattr(R, "to_iso") else ""
        from urtpe.extract import to_iso
        own = to_iso(r["date"])[0] or ""
        if recovered == own:
            stats["recovered == the corpus's own date"] += 1
        else:
            stats["recovered != the corpus's own date"] += 1
            wrong.append((r["recno"], r["name"][:40], own, recovered,
                          [(c, v) for c, v in approved]))
    print()
    for k, v in sorted(stats.items()):
        print("   %-42s %d" % (k, v))
    print()
    if wrong:
        print("the disagreements:")
        for w in wrong:
            print("   recno %-6s %s" % (w[0], w[1]))
            print("      the corpus's own date : %s" % w[2])
            print("      the recovered date     : %s" % w[3])
            print("      the candidates         : %s" % w[4])


if __name__ == "__main__":
    main()
