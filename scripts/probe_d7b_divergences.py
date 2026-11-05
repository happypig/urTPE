"""D7b: name the divergences the subset/permutation check does not explain.

Read-only over data/.link_cache. For every cache with per-case milestones,
re-derive the merged projection from case_milestones over city_case_ids (the
rule merge_stage_milestones applies) and compare with the stored dict.

The board's test: the stored dict must be reproducible by (a) a SUBSET of
city_case_ids, or (b) a PERMUTATION of city_case_ids. A subset is tested in
every order (the merge is order-sensitive), a permutation is the full set
reordered. What neither explains is the D7b population.

For each unexplained divergence the probe names the differing labels and the
case that holds each value, so the cause can be read off.
"""
import json
import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import merge_stage_milestones  # noqa: E402

CACHE = ROOT / "data" / ".link_cache"
MAX_IDS = 6          # beyond this the permutation space is too large to scan


def merge_over(ids, cm):
    out, src = {}, {}
    for cid in ids:
        merge_stage_milestones(out, src, cid, cm.get(cid) or {})
    return out


def any_subset_order(ids, cm, stored):
    """Does SOME ordered subset of ids reproduce the stored dict?

    The order matters (the merge is order-sensitive), so every ordered subset
    is tried. The full permutation space is too large beyond ~8 ids, so for
    more the common shapes are tried directly: every prefix, and every
    single-id drop. Both are the shapes the pipeline actually produces — a
    case appended at the end, or one case's milestones read after the merge.
    """
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


def any_permutation(ids, cm, stored):
    """Does SOME permutation of ALL ids reproduce the stored dict?"""
    n = len(ids)
    if n > MAX_IDS:
        return None
    for p in permutations(ids):
        if merge_over(list(p), cm) == stored:
            return list(p)
    return None


def holders(label, ids, cm):
    return [(cid, (cm.get(cid) or {}).get(label))
            for cid in ids if (cm.get(cid) or {}).get(label)]


def main():
    rows = []
    counts = defaultdict(int)
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
        derived = merge_over(ids, cm)
        if derived == stored:
            counts["IN_SYNC"] += 1
            continue

        sub = any_subset_order(ids, cm, stored)
        perm = None if sub else any_permutation(ids, cm, stored)
        if sub is not None:
            kind = "SUBSET"
        elif perm is not None:
            kind = "PERMUTATION"
        else:
            kind = "UNEXPLAINED"
        counts[kind] += 1

        only_stored = sorted(set(stored) - set(derived))
        only_derived = sorted(set(derived) - set(stored))
        value_diff = sorted(l for l in set(stored) & set(derived)
                             if stored[l] != derived[l])
        rows.append({
            "dir": d.name, "kind": kind, "ids": ids, "cm": cm,
            "stored": stored, "derived": derived,
            "only_stored": only_stored, "only_derived": only_derived,
            "value_diff": value_diff,
        })

    print("caches with per-case milestones:", counts["IN_SYNC"] + len(rows))
    print("  in sync with a merge over city_case_ids:", counts["IN_SYNC"])
    for k in ("SUBSET", "PERMUTATION", "UNEXPLAINED"):
        print("  %-12s %d" % (k, counts[k]))
    print()

    unexpl = [r for r in rows if r["kind"] == "UNEXPLAINED"]
    print("=== UNEXPLAINED (%d) ===" % len(unexpl))
    for r in unexpl:
        print()
        print(r["dir"])
        print("   ids: %s" % ", ".join(r["ids"]))
        print("   labels stored=%d derived=%d" % (len(r["stored"]), len(r["derived"])))
        for l in r["value_diff"]:
            print("   VALUE  %-14s stored=%-12r derived=%-12r holders=%r"
                  % (l, r["stored"][l], r["derived"][l],
                     holders(l, r["ids"], r["cm"])))
        for l in r["only_stored"]:
            print("   STORED-ONLY %-14s = %-12r holders=%r"
                  % (l, r["stored"][l], holders(l, r["ids"], r["cm"])))
        for l in r["only_derived"]:
            print("   DERIVED-ONLY %-14s = %-12r holders=%r"
                  % (l, r["derived"][l], holders(l, r["ids"], r["cm"])))

    print()
    print("=== EXPLAINED (%d) ===" % (len(rows) - len(unexpl)))
    for r in rows:
        if r["kind"] == "UNEXPLAINED":
            continue
        print("%-12s %s  ids=%d labels %d->%d" % (
            r["kind"], r["dir"], len(r["ids"]), len(r["stored"]), len(r["derived"])))


if __name__ == "__main__":
    main()
