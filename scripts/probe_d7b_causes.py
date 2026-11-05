"""D7b: the cause of each unexplained divergence. Read-only.

The 52 divergences that no subset or permutation of city_case_ids explains
fall into named shapes. This probe classifies each one by what the stored dict
holds versus what the cases hold:

  NEW_CASE   — a case holds a value the stored dict lacks, and that case is
               NOT in the stored dict's source map (milestones_source). The
               stored dict was merged before that case was read.
  RE_DATED   — the stored dict holds a value for a label, and the SAME label
               is held by a case, but with a different (later) value. The city
               re-dated the label, and the refresh wrote the new value into
               case_milestones without re-merging.
  DROPPED    — the stored dict holds a label no case carries any more (the
               city withdrew it).
  MIXED      — more than one of the above in the same project.

It also reports, for each divergence, whether the offending case id is in
city_case_ids and whether it carries an approval date (a case the refresh
would have re-fetched).
"""
import json
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import _APPROVAL_FIELDS, merge_stage_milestones  # noqa: E402

CACHE = ROOT / "data" / ".link_cache"


def merge_over(ids, cm):
    out, src = {}, {}
    for cid in ids:
        merge_stage_milestones(out, src, cid, cm.get(cid) or {})
    return out, src


def subset_hit(ids, cm, stored):
    """Does SOME ordered subset of ids reproduce the stored dict?

    Beyond 8 ids the full permutation space is too large, so the two shapes
    the pipeline actually produces are tried directly: every prefix (a case
    appended after the merge) and every single-id drop.
    """
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
    causes = Counter()
    detail = []
    for d in sorted(CACHE.iterdir()):
        f = d / "result.json"
        if not f.is_file():
            continue
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        cm = r.get("case_milestones") or {}
        if not cm:
            continue
        stored = r.get("taipei_milestones") or {}
        ids = list(r.get("city_case_ids") or [])
        if not ids:
            continue
        derived, src = merge_over(ids, cm)
        if derived == stored:
            continue
        if subset_hit(ids, cm, stored) is not None:
            causes["SUBSET"] += 1
            continue
        causes["UNEXPLAINED"] += 1

        # classify the shape
        only_stored = sorted(set(stored) - set(derived))
        only_derived = sorted(set(derived) - set(stored))
        value_diff = sorted(l for l in set(stored) & set(derived)
                             if stored[l] != derived[l])

        # the cases behind each differing label
        new_case_labels, redated_labels, dropped_labels = [], [], []
        for l in only_derived:
            hs = [cid for cid in ids if (cm.get(cid) or {}).get(l)]
            new_case_labels.append((l, hs))
        for l in only_stored:
            hs = [cid for cid in ids if (cm.get(cid) or {}).get(l)]
            dropped_labels.append((l, hs))
        for l in value_diff:
            hs = [cid for cid in ids if (cm.get(cid) or {}).get(l)]
            redated_labels.append((l, hs, stored[l], derived[l]))

        # the case that first carried the label the stored dict has
        older = []
        for l, hs, sv, dv in redated_labels:
            for cid in hs:
                if (cm.get(cid) or {}).get(l) == sv:
                    older.append(cid)

        # is the case holding the NEW value approved?
        new_cases = sorted({cid for l, hs in new_case_labels for cid in hs})
        approved_new = [cid for cid in new_cases
                        if any((cm.get(cid) or {}).get(f) for f in _APPROVAL_FIELDS)]

        if only_stored and not only_derived and not value_diff:
            shape = "DROPPED"
        elif value_diff and not only_stored and not only_derived:
            shape = "RE_DATED"
        elif only_derived and not only_stored and not value_diff:
            shape = "NEW_CASE"
        elif value_diff and only_derived:
            shape = "RE_DATED+NEW_CASE"
        elif only_stored and value_diff:
            shape = "DROPPED+RE_DATED"
        elif only_stored and only_derived:
            shape = "DROPPED+NEW_CASE"
        else:
            shape = "MIXED"
        causes[shape] += 1
        detail.append({
            "dir": d.name, "shape": shape, "ids": ids,
            "only_stored": only_stored, "only_derived": only_derived,
            "value_diff": value_diff, "older": sorted(set(older)),
            "new_cases": new_cases, "approved_new": approved_new,
            "stored": stored, "derived": derived, "cm": cm,
            "src": r.get("milestones_source") or {},
        })

    print("shape counts:")
    for k, v in sorted(causes.items()):
        print("   %-22s %d" % (k, v))
    print()

    # the summary the board needs: the 50 named divergences
    print("=== the %d unexplained divergences ===" % causes["UNEXPLAINED"])
    for d in detail:
        print()
        print("%-52s %s" % (d["dir"], d["shape"]))
        print("   ids: %s" % ", ".join(d["ids"]))
        if d["value_diff"]:
            for l in d["value_diff"]:
                hs = [(cid, (d["cm"].get(cid) or {}).get(l))
                      for cid in d["ids"] if (d["cm"].get(cid) or {}).get(l)]
                print("   RE-DATED  %-14s stored=%-11r now=%-11r holders=%r"
                      % (l, d["stored"][l], d["derived"][l], hs))
        if d["only_derived"]:
            for l in d["only_derived"]:
                hs = [(cid, (d["cm"].get(cid) or {}).get(l))
                      for cid in d["ids"] if (d["cm"].get(cid) or {}).get(l)]
                print("   NEW-CASE  %-14s = %-11r holders=%r" % (l, d["derived"][l], hs))
        if d["only_stored"]:
            for l in d["only_stored"]:
                hs = [(cid, (d["cm"].get(cid) or {}).get(l))
                      for cid in d["ids"] if (d["cm"].get(cid) or {}).get(l)]
                print("   DROPPED   %-14s stored=%-11r holders-now=%r"
                      % (l, d["stored"][l], hs))
        if d["approved_new"]:
            print("   the new-value case is approved: %s" % ", ".join(d["approved_new"]))


if __name__ == "__main__":
    main()
