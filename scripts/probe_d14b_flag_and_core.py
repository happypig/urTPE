"""D14(b): what else changes when district_land reads the collected enum.

Read-only. Measures, over all 1,442 clean.tsv rows:
  - the 行政區與地號行政區不一致 flag: which rows gain or lose it
  - the land core (build_land_core_key shape): which rows change
  - the anchor of each affected family, and the cache dir name it implies
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
csv.field_size_limit(10**8)

from urtpe.cleanse import DISTRICT_RE  # noqa: E402

CLEAN = ROOT / "data" / "clean.tsv"

rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))
dist = Counter(r.get("district", "") for r in rows)
enum = sorted(k for k in dist if k and k.endswith("區"))
ENUM_RE = re.compile("|".join(map(re.escape, enum)))


def raw_token(land: str) -> str:
    m = DISTRICT_RE.search(land)
    return m.group(1) if m else ""


def enum_token(land: str) -> str:
    m = ENUM_RE.search(land)
    return m.group(0) if m else ""


def core(district_land: str, section: str, first_parcel: str, count) -> str:
    parts = []
    if district_land:
        parts.append(district_land)
    if section:
        parts.append(section)
    s = "".join(parts)
    if first_parcel:
        s += first_parcel
    if count:
        s += f"地號等{count}筆"
    return s


flag_gain, flag_loss, core_change = [], [], []
for r in rows:
    land = r.get("land", "")
    district = r.get("district", "")
    raw, enumv = raw_token(land), enum_token(land)
    old_dl = raw
    new_dl = enumv
    # the flag: the cell prints a district token (raw); the enum read is the
    # normalized district_land. The flag fires when the quoted token differs
    # from the row's district.
    old_flag = bool(old_dl and district and old_dl != district)
    quoted = raw or new_dl
    new_flag = bool(quoted and district and quoted != district)
    if old_flag != new_flag:
        (flag_gain if new_flag else flag_loss).append(
            (r.get("recno"), district, old_dl, new_dl, quoted))
    if old_dl != new_dl:
        c_old = core(old_dl, r.get("section", ""), r.get("first_parcel", ""),
                     r.get("land_count"))
        c_new = core(new_dl, r.get("section", ""), r.get("first_parcel", ""),
                     r.get("land_count"))
        if c_old != c_new:
            core_change.append((r.get("recno"), c_old, c_new))

print("rows:", len(rows))
print("flag GAIN:", len(flag_gain), flag_gain)
print("flag LOSS:", len(flag_loss), flag_loss)
print("land-core change:", len(core_change))
for c in core_change:
    print("  recno=%s  %r -> %r" % c)

# which emitted project carries each affected recno?
data = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
affected = {c[0] for c in core_change} | {r[0] for r in flag_gain + flag_loss}
print()
print("affected recnos in the emitted dataset:")
for p in data["projects"]:
    hit = [n for n in p["nodes"] if str(n["recno"]) in affected]
    if hit:
        print("  project=%s anchor=%s" % (p["project_id"], p["anchor_recno"]))
        for n in hit:
            print("      recno=%s district=%s district_land=%r land=%r" % (
                n["recno"], n.get("district"), n.get("district_land"),
                (n.get("land") or "")[:30]))

# the cache dir names that hold those land cores
cache = ROOT / "data" / ".link_cache"
print()
print("cache dirs matching the affected sections:")
for d in sorted(cache.iterdir()):
    if any(k in d.name for k in ("崇仰", "辛亥", "百齡")):
        print("  ", d.name)
