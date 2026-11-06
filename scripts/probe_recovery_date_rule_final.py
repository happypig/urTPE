"""The name-only rule for a truncated DATE cell — the complete form.

For a truncated 地號 row the recovery pass anchors on the DATE and the name is
a filter. For a truncated DATE row the roles reverse: the name must carry the
identity alone, and the date is what gets recovered.

The rule this probe measures, over gazette rows:

  check 1  same unit (district + 段/小段)
  check 2  the declared count fragment appears
  check 3  the stage ordinal agrees            (擬訂 / 變更 / 變更(第二次)…)
  check 4  the track set EQUALS the row's       (事業計畫 / 權利變換 / both)
  check 5  the approved candidates carry ONE date — the acceptance

Three fixes came out of the measurement (2026-11-06):

  F1  NFKC folding. The city writes 利 as U+F9DD (a CJK compatibility
      ideograph) in one case name (11507018). The keyword 權利變換 then does
      not match, and the row reads as 事業計畫 alone. NFKC folds it.
  F2  the count fragment. A 案名 that writes 地號1筆 (not 等N筆) has no
      count fragment, and the count check then rejects every candidate —
      including the right ones. The fragment falls back to the parcel count
      the 案名 declares.
  F3  the track relation is EQUALITY, not a subset. A subset admits the
      area-split twin and creates new ambiguities.

    python scripts/probe_recovery_date_rule_final.py [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import recovery as R  # noqa: E402
from urtpe.cleanse import _tracks  # noqa: E402
from urtpe.recovery_sources import AshxClient  # noqa: E402

_ORD_RE = re.compile(r"^(擬訂|變更(?:\(第[一二三四五六七八九十]+次\))?)")
# F2: a 案名 that writes the count as 地號N筆 rather than 等N筆
_PLAIN_COUNT_RE = re.compile(r"地號(\d+)筆")


def nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def ordinal(name: str) -> str:
    m = _ORD_RE.match(R.normalize_name(name))
    return m.group(1) if m else ""


def tracks(name: str) -> frozenset:
    return frozenset(_tracks(R.normalize_name(name)))


def declared_count(name: str) -> int | None:
    """F2: the count the 案名 declares, whichever way it writes it."""
    n = R.normalize_name(name)
    m = re.search(r"等(\d+)筆", n)
    if m:
        return int(m.group(1))
    m = _PLAIN_COUNT_RE.search(n)
    if m:
        return int(m.group(1))
    return None


def count_agrees(identity, row_name: str, cand_name: str) -> bool:
    """F2: compare the DECLARED COUNTS, not the fragment strings.

    The city writes the count as 等N筆 in some names and 地號N筆 in others, on
    both sides of the comparison (recno 2: the row writes 地號1筆, the case
    writes 地號1筆; the row writes 等26筆, the case writes 等26筆). A string
    comparison of the fragment fails when the two sides use different forms,
    so the counts are compared instead — and a disagreement (recno 40: the row
    says 等12筆, the city says 等13筆) then refuses, which is correct.
    """
    row_count = declared_count(row_name)
    cand_count = declared_count(cand_name)
    if row_count is None or cand_count is None:
        frag = identity.count_fragment
        return bool(frag) and frag in R.normalize_name(cand_name)
    return row_count == cand_count


def candidates(identity, cand, row_ord, row_tracks, row_name) -> bool:
    name = R.normalize_name(nfkc(cand.get("case_name") or ""))
    if not (identity.district in name and identity.section in name):
        return False
    if not count_agrees(identity, row_name, name):
        return False
    if row_ord and ordinal(name) and ordinal(name) != row_ord:
        return False
    cand_tracks = tracks(name)
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
        identity = R.parse_identity(nfkc(r["name"]))
        if identity is None:
            stats["no identity from the name"] += 1
            continue
        stats["rows tested"] += 1
        time.sleep(1.2)
        family = ashx.case_family(identity.section, identity.mono, identity.suno)
        row_ord = ordinal(identity.name)
        row_tracks = tracks(identity.name)
        hits = [c for c in family
                if candidates(identity, c, row_ord, row_tracks, r["name"])]
        if not hits:
            stats["no candidate survives the name rule"] += 1
            residual.append((r["recno"], r["name"][:42], "no candidate"))
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
            residual.append((r["recno"], r["name"][:42], "none approved"))
        elif len(dates) == 1:
            stats["ONE DATE — recoverable"] += 1
        else:
            stats["several dates — residual"] += 1
            residual.append((r["recno"], r["name"][:42],
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
