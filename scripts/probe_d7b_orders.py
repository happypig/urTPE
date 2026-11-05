"""D7b: does a different merge ORDER explain the 50? Read-only.

The discovery path merges the cases in the order the parcel search returned
them (`city_ids`, `urtpe/links.py:661-673`). The refresh appends a case to
`city_case_ids` but never re-merges. This probe asks whether the stored dict
is a merge over the SAME ids in a DIFFERENT order — the orderings the
pipeline could plausibly produce:

  search_order    — city_case_ids as stored
  reversed        — the reverse
  by_approval     — sorted by the case's 核定日期 (the city lists a project's
                     cases in approval order)
  by_case_id      — sorted by the numeric case id (the city's daily serial)
  by_label_count  — sorted by how many labels the case carries

and, for the subset shape, the same orderings over every prefix.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import _APPROVAL_FIELDS, merge_stage_milestones  # noqa: E402

CACHE = ROOT / "data" / ".link_cache"


def merge_over(ids, cm):
    out, src = {}, {}
    for cid in ids:
        merge_stage_milestones(out, src, cid, cm.get(cid) or {})
    return out


def approval_of(cid, cm):
    ms = cm.get(cid) or {}
    for f in _APPROVAL_FIELDS:
        if ms.get(f):
            return ms[f]
    return ""


def orderings(ids, cm):
    yield "search_order", list(ids)
    yield "reversed", list(reversed(ids))
    yield "by_approval", sorted(ids, key=lambda c: (approval_of(c, cm), c))
    yield "by_case_id", sorted(ids, key=lambda c: c)
    yield "by_label_count", sorted(ids, key=lambda c: -len(cm.get(c) or {}))


def subset_hit(ids, cm, stored):
    """Any ordered subset (full permutation space up to 8 ids; prefixes and
    single-id drops beyond)."""
    import itertools
    n = len(ids)
    if n <= 8:
        for k in range(n, 0, -1):
            for combo in itertools.permutations(range(n), k):
                if merge_over([ids[i] for i in combo], cm) == stored:
                    return [ids[i] for i in combo]
        return None
    for k in range(n, 0, -1):
        if merge_over(ids[:k], cm) == stored:
            return ids[:k]
    for i in range(n):
        sub = [x for j, x in enumerate(ids) if j != i]
        if merge_over(sub, cm) == stored:
            return sub
    return None


def main():
    counts = Counter()
    detail = []
    for d in sorted(CACHE.iterdir()):
        f = d / "result.json"
        if not f.is_file():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        cm = r.get("case_milestones") or {}
        if not cm:
            continue
        stored = r.get("taipei_milestones") or {}
        ids = list(r.get("city_case_ids") or [])
        if not ids:
            continue
        if merge_over(ids, cm) == stored:
            counts["IN_SYNC"] += 1
            continue
        if subset_hit(ids, cm, stored) is not None:
            counts["EXPLAINED_SUBSET"] += 1
            continue
        # now the orderings
        hit = None
        for name, order in orderings(ids, cm):
            if merge_over(order, cm) == stored:
                hit = name
                break
        if hit:
            counts["EXPLAINED_ORDER:" + hit] += 1
            detail.append((d.name, hit, order))
            continue
        counts["STILL_UNEXPLAINED"] += 1
    for k, v in sorted(counts.items()):
        print("   %-28s %d" % (k, v))
    print()
    for name, hit, order in detail:
        print("ORDER %-14s %s" % (hit, name))
        print("      %s" % ", ".join(order))


if __name__ == "__main__":
    main()
