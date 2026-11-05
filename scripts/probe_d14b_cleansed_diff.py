"""D14(b): the real corpus effect. Read-only.

Re-cleanses data/raw.tsv with the enum read and against the strict read, and
reports every field that differs. The board requires: 7 rows change, no other
row, the section and parcels of all 7 unchanged, and the mismatch flag keeps
firing on 488/558/927.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
csv.field_size_limit(10**8)

from urtpe.cleanse import cleanse, cleanse_all, collect_districts  # noqa: E402
from urtpe.models import RawRecord  # noqa: E402

RAW = ROOT / "data" / "raw.tsv"
rows = list(csv.DictReader(RAW.open(encoding="utf-8"), delimiter="\t"))
print("raw.tsv rows:", len(rows))
recs = [
    RawRecord(
        recno=int(r["編號"]), date=r["核定日期"], district=r["行政區"],
        name=r["案名"], land=r["地號"], implementer=r["實施者"],
        planner=r["更新規劃單位"], parse_error=r.get("parse_error", "") or "",
        gazette_id=r.get("gazette_id", "") or "",
    )
    for r in rows
]

enum = collect_districts(recs)
print("enum (%d): %s\n" % (len(enum), " ".join(enum)))

old = {r.recno: r for r in cleanse_all(recs, districts=())}
new = {r.recno: r for r in cleanse_all(recs, districts=enum)}

dl, sec, par, flg, cnt, name, other = [], [], [], [], [], [], []
for recno in sorted(old):
    a, b = old[recno], new[recno]
    if a.district_land != b.district_land:
        dl.append((recno, a.district_land, b.district_land))
    if a.section != b.section:
        sec.append((recno, a.section, b.section))
    if a.parcels != b.parcels:
        par.append((recno, a.parcels, b.parcels))
    if a.review_flags != b.review_flags:
        flg.append((recno, a.review_flags, b.review_flags))
    if a.land_count != b.land_count:
        cnt.append((recno, a.land_count, b.land_count))
    if a.name != b.name:
        name.append((recno, a.name, b.name))
    for f in ("first_parcel", "aliases", "orig_count", "named_anchor",
              "area_section", "stage", "stage_index", "track", "implementer",
              "planner", "auto_fixes", "gazette_id"):
        if getattr(a, f) != getattr(b, f):
            other.append((recno, f, getattr(a, f), getattr(b, f)))

print("district_land changes:", len(dl))
for x in dl:
    print("   recno=%s  %r -> %r" % x)
print()
print("section changes:", len(sec), sec)
print("parcel changes:", len(par), par)
print("land_count changes:", len(cnt), cnt)
print("name changes:", len(name))
print("review_flag changes:", len(flg))
for x in flg:
    print("   recno=%s" % x[0])
    print("      old:", x[1])
    print("      new:", x[2])
print("other field changes:", len(other), other[:10])

# the flag must still fire on 488/558/927
print()
for recno in (488, 558, 927):
    r = new[recno]
    hit = [f for f in r.review_flags if "行政區與地號行政區不一致" in f]
    print("recno=%s district_land=%r flag=%r" % (recno, r.district_land, hit))
