"""D7b: why the 50 divergences happen. Read-only.

The decisive test: the stored dict carries a `milestones_source` map (the case
that won each label). If that map still names the case that holds the stored
value TODAY, then the stored dict is a stale MERGE over the same cases — the
cases' data2 changed and the refresh wrote the change into case_milestones
without re-merging.

For each divergence the probe reports:
  - how many labels' source maps still agree with the current case data
  - for each disagreeing label: who holds the stored value now, who holds the
    derived value now, and whether the stored value equals the value the
    winning case holds today
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


def main():
    kinds = Counter()
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
        src = r.get("milestones_source") or {}
        ids = list(r.get("city_case_ids") or [])
        if not ids:
            continue
        derived, dsrc = merge_over(ids, cm)
        if derived == stored:
            continue

        # does the stored SOURCE map still point at a case holding the stored
        # value today?
        agree, stale = [], []
        for label, value in stored.items():
            cid = src.get(label)
            if cid is None:
                continue
            if (cm.get(cid) or {}).get(label) == value:
                agree.append(label)
            else:
                stale.append(label)

        # the labels the derived merge disagrees on
        value_diff = sorted(l for l in set(stored) & set(derived)
                             if stored[l] != derived[l])
        only_stored = sorted(set(stored) - set(derived))
        only_derived = sorted(set(derived) - set(stored))

        # for each differing label: does the stored value survive anywhere in
        # the current case data?
        stored_value_gone = []
        for l in value_diff + only_stored:
            holders_now = [(c, (cm.get(c) or {}).get(l))
                           for c in ids if (cm.get(c) or {}).get(l)]
            if not any(v == stored[l] for _, v in holders_now):
                stored_value_gone.append(l)

        if value_diff and not only_stored and not only_derived:
            kind = "RE_DATED"
        elif only_derived and not only_stored and not value_diff:
            kind = "NEW_CASE"
        elif only_stored and not only_derived and not value_diff:
            kind = "DROPPED"
        elif value_diff and only_derived:
            kind = "RE_DATED+NEW_CASE"
        elif only_stored and only_derived:
            kind = "DROPPED+NEW_CASE"
        else:
            kind = "MIXED"
        kinds[kind] += 1
        detail.append({
            "dir": d.name, "kind": kind, "ids": ids, "cm": cm,
            "stored": stored, "derived": derived, "src": src, "dsrc": dsrc,
            "value_diff": value_diff, "only_stored": only_stored,
            "only_derived": only_derived,
            "agree": agree, "stale": stale,
            "stored_value_gone": stored_value_gone,
        })

    print("shape counts:", dict(kinds))
    print()
    tot_stale = sum(len(x["stale"]) for x in detail)
    tot_labels = sum(len(x["stored"]) for x in detail)
    print("labels whose stored source map still agrees with the case data: %d of %d"
          % (tot_labels - tot_stale, tot_labels))
    print()
    print("=== the detail ===")
    for x in detail:
        print()
        print("%-52s %s" % (x["dir"], x["kind"]))
        print("   ids: %s" % ", ".join(x["ids"]))
        print("   labels stored=%d derived=%d  source-map agrees on %d, stale on %d"
              % (len(x["stored"]), len(x["derived"]), len(x["agree"]), len(x["stale"])))
        for l in x["value_diff"]:
            hs = [(c, (x["cm"].get(c) or {}).get(l))
                  for c in x["ids"] if (x["cm"].get(c) or {}).get(l)]
            gone = "  <-- the stored value is GONE from every case" \
                if l in x["stored_value_gone"] else ""
            print("   RE-DATED  %-14s stored=%-11r now=%-11r source=%s holders=%r%s"
                  % (l, x["stored"][l], x["derived"][l], x["src"].get(l), hs, gone))
        for l in x["only_derived"]:
            hs = [(c, (x["cm"].get(c) or {}).get(l))
                  for c in x["ids"] if (x["cm"].get(c) or {}).get(l)]
            print("   NEW-CASE  %-14s = %-11r holders=%r" % (l, x["derived"][l], hs))
        for l in x["only_stored"]:
            hs = [(c, (x["cm"].get(c) or {}).get(l))
                  for c in x["ids"] if (x["cm"].get(c) or {}).get(l)]
            print("   DROPPED   %-14s stored=%-11r holders-now=%r" % (l, x["stored"][l], hs))
        if x["stale"]:
            print("   source-map stale labels: %s" % ", ".join(x["stale"]))


if __name__ == "__main__":
    main()
