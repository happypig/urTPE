"""D7b: name the 50 divergences. Read-only, and the board's record.

For every cache with per-case milestones, re-derive the merged projection from
case_milestones over city_case_ids and compare with the stored dict.

A divergence is EXPLAINED when the stored dict is a merge over some ordered
subset of city_case_ids (a case was appended after the merge). It is
UNEXPLAINED when no subset and no permutation reproduces it.

For each unexplained divergence the probe then asks the one question that
names it: for the labels where the stored value differs from the re-derived
one, IS THE STORED VALUE STILL HELD BY A CASE?

  STALE_MERGE — yes for every differing label. The case data changed after
                the merge (a case was appended, or a case's date was added or
                re-dated), the refresh wrote the new case data into
                case_milestones, and the merged projection was never
                recomputed. Re-deriving it reproduces what a fresh discovery
                would produce.
  WITHDRAWN  — no. The stored dict holds a value no case carries any more:
                the city withdrew it. This is a real removal, and it is the
                shape the withdrawn-approval rule (_APPROVAL_FIELDS) exists
                to preserve.
  MIXED      — both.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import merge_stage_milestones  # noqa: E402

CACHE = ROOT / "data" / ".link_cache"


def merge_over(ids, cm):
    out, src = {}, {}
    for cid in ids:
        merge_stage_milestones(out, src, cid, cm.get(cid) or {})
    return out, src


def subset_hit(ids, cm, stored):
    """Does some ordered subset of ids reproduce the stored dict?"""
    import itertools
    n = len(ids)
    if n <= 8:
        for k in range(n, 0, -1):
            for combo in itertools.permutations(range(n), k):
                if merge_over([ids[i] for i in combo], cm)[0] == stored:
                    return [ids[i] for i in combo]
        return None
    for k in range(n, 0, -1):
        if merge_over(ids[:k], cm)[0] == stored:
            return ids[:k]
    for i in range(n):
        sub = [x for j, x in enumerate(ids) if j != i]
        if merge_over(sub, cm)[0] == stored:
            return sub
    return None


def main():
    kinds = Counter()
    named = []
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
        derived, dsrc = merge_over(ids, cm)
        if derived == stored:
            kinds["IN_SYNC"] += 1
            continue
        if subset_hit(ids, cm, stored) is not None:
            kinds["EXPLAINED_SUBSET"] += 1
            continue
        kinds["UNEXPLAINED"] += 1

        # the naming test
        only_stored = sorted(set(stored) - set(derived))
        only_derived = sorted(set(derived) - set(stored))
        value_diff = sorted(l for l in set(stored) & set(derived)
                             if stored[l] != derived[l])

        # a label whose stored value a case STILL holds: the case data did not
        # move for that label, only the merge did (a later case overwrote it).
        still_held = []
        # a label whose stored value no case holds any more: the city withdrew
        # or re-dated it.
        gone = []
        for l in value_diff:
            holders_now = [(c, (cm.get(c) or {}).get(l))
                           for c in ids if (cm.get(c) or {}).get(l)]
            if any(v == stored[l] for _, v in holders_now):
                still_held.append(l)
            else:
                gone.append(l)
        # a label only in the stored dict: the city withdrew it entirely.
        gone.extend(only_stored)
        # a label only in the derived dict: a case carries a label the stored
        # dict never received.
        new_labels = list(only_derived)

        if still_held and not gone and not new_labels:
            name = "STALE_MERGE"
        elif gone and not still_held and not new_labels:
            name = "WITHDRAWN"
        elif new_labels and not still_held and not gone:
            name = "NEW_LABEL"
        else:
            name = "MIXED"
        kinds[name] += 1
        named.append({
            "dir": d.name, "name": name, "ids": ids,
            "still_held": still_held, "gone": gone, "new_labels": new_labels,
            "value_diff": value_diff, "only_stored": only_stored,
            "only_derived": only_derived,
            "stored": stored, "derived": derived, "cm": cm,
            "src": r.get("milestones_source") or {},
        })

    print("caches with per-case milestones: %d" % (kinds["IN_SYNC"] + kinds["UNEXPLAINED"] + kinds["EXPLAINED_SUBSET"]))
    for k in ("IN_SYNC", "EXPLAINED_SUBSET", "UNEXPLAINED",
              "STALE_MERGE", "WITHDRAWN", "NEW_LABEL", "MIXED"):
        print("   %-18s %d" % (k, kinds[k]))
    print()
    print("=== the %d unexplained divergences, named ===" % kinds["UNEXPLAINED"])
    for x in named:
        print()
        print("%-52s %s" % (x["dir"], x["name"]))
        print("   ids: %s" % ", ".join(x["ids"]))
        for l in x["value_diff"]:
            hs = [(c, (x["cm"].get(c) or {}).get(l))
                  for c in x["ids"] if (x["cm"].get(c) or {}).get(l)]
            mark = "STILL HELD" if l in x["still_held"] else "GONE"
            print("   %-11s %-14s stored=%-11r now=%-11r source=%s holders=%r"
                  % (mark, l, x["stored"].get(l), x["derived"].get(l),
                     x["src"].get(l), hs))
        for l in x["only_derived"]:
            hs = [(c, (x["cm"].get(c) or {}).get(l))
                  for c in x["ids"] if (x["cm"].get(c) or {}).get(l)]
            print("   NEW LABEL %-14s = %-11r holders=%r" % (l, x["derived"][l], hs))
        for l in x["only_stored"]:
            hs = [(c, (x["cm"].get(c) or {}).get(l))
                  for c in x["ids"] if (x["cm"].get(c) or {}).get(l)]
            print("   GONE      %-14s stored=%-11r holders-now=%r"
                  % (l, x["stored"][l], hs))


if __name__ == "__main__":
    main()
