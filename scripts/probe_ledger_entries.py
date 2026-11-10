"""Why does the live ledger hold three entries, and why does 吉林676 keep two?

Read-only. Rebuilds the 676 family from the real cleansed rows and replays the
merge rule with and without each ledger entry, so the answer comes from the
pipeline's own functions rather than from prose.

    python scripts/probe_ledger_entries.py
"""
from __future__ import annotations

import csv
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import ledger as ledger_mod  # noqa: E402
from urtpe.merge import merge, score, slug_for  # noqa: E402
from urtpe.models import RawRecord  # noqa: E402
from urtpe.cleanse import cleanse  # noqa: E402

LEDGER = pathlib.Path("D:/project/urtpe-gazettes/corrections.jsonl")


def all_records() -> list:
    """Re-cleanse every raw row — the ledger's own input shape."""
    recs = []
    with (ROOT / "data" / "raw.tsv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            recs.append(cleanse(RawRecord(
                recno=int(r["編號"]), date=r["核定日期"], district=r["行政區"],
                name=r["案名"], land=r["地號"], implementer=r["實施者"],
                planner=r["更新規劃單位"])))
    return recs


def temp_ledger(entries) -> ledger_mod.CorrectionLedger:
    """A ledger holding exactly the entries given, in a throwaway file."""
    path = pathlib.Path(tempfile.mkdtemp()) / "corrections.jsonl"
    led = ledger_mod.CorrectionLedger(path)
    for e in entries:
        led.append(e)
    return led


def main() -> int:
    led = ledger_mod.CorrectionLedger(LEDGER)
    entries = led.entries()
    print("=== the live ledger: %d entries ===" % len(entries))
    for i, e in enumerate(entries, 1):
        kind = ("confirm_merge" if e.confirm_merge else
                "accept_removal" if e.accept_removal else
                "set %s -> %r" % (e.field, e.to))
        print("%d. %s" % (i, kind))
        print("   key  : %s..." % e.match_land_core[:44])
        if e.confirm_merge:
            print("   with : %s..." % e.with_land_core[:44])

    recs = all_records()
    by_recno = {r.recno: r for r in recs}
    a, b = by_recno[1305], by_recno[1349]

    print()
    print("=== 吉林676, as the gazette prints it ===")
    print("recno 1305  land_count=%s  parcels=%d" % (a.land_count, len(a.parcels)))
    print("recno 1349  land_count=%s  parcels=%d" % (b.land_count, len(b.parcels)))
    print("score(1305, 1349) = %.4f" % score(a, b))

    # --- entry 1 alone: does it set a field? does it link? ---
    print()
    print("=== entry 1 (confirm_merge) alone ===")
    c = all_records()
    c_by = {r.recno: r for r in c}
    out = temp_ledger([entries[0]]).apply(c, key_of=ledger_mod.default_key)
    print("applied   : %d" % len(out.applied))
    print("confirmed : %s" % out.confirmed_pairs)
    print("recno 1305 land_count after : %s (unchanged)" % c_by[1305].land_count)
    fam1 = [p for p in merge(c, confirmed_pairs=out.confirmed_pairs)
            if 1305 in [m.recno for m in p.members]]
    for p in fam1:
        print("family   : %s  members=%s" %
              (p.project_id, [m.recno for m in p.members]))
    print("-> the entry links the pair and sets no field")

    # --- entry 2 alone: does it link? does it fix the name? ---
    print()
    print("=== entry 2 (land_count -> 18) alone ===")
    c2 = all_records()
    c2_by = {r.recno: r for r in c2}
    out2 = temp_ledger([entries[1]]).apply(c2, key_of=ledger_mod.default_key)
    print("applied   : %d" % len(out2.applied))
    print("confirmed : %s  (empty: the entry links nothing)" % out2.confirmed_pairs)
    print("score after the entry       : %.4f" % score(c2_by[1305], c2_by[1349]))
    print("slug with the entry         : %s" % slug_for(c2_by[1305], family=[c2_by[1305], c2_by[1349]]))
    print("slug without it             : %s" % slug_for(a, family=[a, b]))
    print("-> the entry fixes the family NAME and still does not link")

    # --- both: the family holds two records ---
    print()
    print("=== both 吉林676 entries ===")
    c3 = all_records()
    out3 = temp_ledger(entries[0:2]).apply(c3, key_of=ledger_mod.default_key)
    print("confirmed : %s" % out3.confirmed_pairs)
    fams = [p for p in merge(c3, confirmed_pairs=out3.confirmed_pairs)
            if 1305 in [m.recno for m in p.members]]
    for p in fams:
        print("family    : %s" % p.project_id)
        print("members   : %s" % [m.recno for m in p.members])
        print("anchor    : %d" % p.anchor_recno)

    # --- the whole dataset, ledger off vs on ---
    print()
    print("=== the whole dataset ===")
    for label, ents in (("no ledger", []),
                        ("entry 1 only (吉林 merge)", entries[0:1]),
                        ("entries 1+2 (吉林 merge + count)", entries[0:2]),
                        ("all three", entries)):
        cc = all_records()
        o = temp_ledger(ents).apply(cc, key_of=ledger_mod.default_key)
        ps = merge(cc, confirmed_pairs=o.confirmed_pairs)
        print("%-34s projects=%d  confirmed=%s" % (label, len(ps), o.confirmed_pairs))

    # --- 萬隆: one entry, no count entry ---
    print()
    print("=== 萬隆519: why one entry is enough ===")
    w = by_recno[410]
    print("anchor recno 410  land_count=%s  date=%s" % (w.land_count, w.iso_date))
    print("score(970, 1208) = %.4f  (below 0.7: the rule alone does not link)"
          % score(by_recno[970], by_recno[1208]))
    print("slug of the merged family     : %s" %
          slug_for(w, family=[by_recno[410], by_recno[970], by_recno[1208]]))
    print("recno 1208 land_count (printed): %s" % by_recno[1208].land_count)
    print("-> the anchor is not the truncated row, so the count needs no entry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
