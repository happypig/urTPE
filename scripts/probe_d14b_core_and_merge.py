"""D14(b): the land-core and project_id effect of the enum read.

Read-only. Simulates the enum read over all 1,442 raw rows of the current
gazette corpus and reports:
  - which rows' land core (build_land_core_key shape) changes
  - which cache dirs hold a project whose anchor is one of those rows, and
    the land_core the cache stores for it
  - whether any project_id changes (slug_for uses the 行政區 column, so the
    enum must not move it)
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
ENUM_RE = re.compile("臺北市?(?:" + "|".join(map(re.escape, enum)) + ")")


def core(dl, section, first_parcel, count):
    parts = []
    if dl:
        parts.append(dl)
    if section:
        parts.append(section)
    s = "".join(parts)
    if first_parcel:
        s += first_parcel
    if count:
        s += f"地號等{count}筆"
    return s


changed = []
for r in rows:
    m = DISTRICT_RE.search(r.get("land", ""))
    old_dl = m.group(1) if m else ""
    m2 = ENUM_RE.search(r.get("land", ""))
    new_dl = m2.group(0)[2:] if m2 and m2.group(0).startswith("臺北市") else (
        m2.group(0)[2:] if m2 else "")
    # strip the 臺北 / 臺北市 prefix
    if m2:
        new_dl = re.sub(r"^臺北市?", "", m2.group(0))
    else:
        new_dl = ""
    if old_dl == new_dl:
        continue
    c_old = core(old_dl, r["section"], r["first_parcel"], r["land_count"])
    c_new = core(new_dl, r["section"], r["first_parcel"], r["land_count"])
    changed.append((r["recno"], old_dl, new_dl, c_old, c_new, r["district"]))

print("rows whose land core changes:", len(changed))
for c in changed:
    print("  recno=%s  dl %r->%r  core %r -> %r" % (c[0], c[1], c[2], c[3], c[4]))

# the anchors of the affected families
anchors = {c[0] for c in changed}
data = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
print()
print("affected anchors and their project_id (slug_for uses 行政區, so it must "
      "not move):")
for p in data["projects"]:
    if str(p["anchor_recno"]) in anchors:
        print("  anchor=%s project_id=%s" % (p["anchor_recno"], p["project_id"]))

# the cache dir's stored land_core
print()
cache = ROOT / "data" / ".link_cache"
for d in sorted(cache.iterdir()):
    f = d / "result.json"
    if not f.is_file():
        continue
    try:
        r = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    if any(str(a) in {str(x["recno"]) for x in
                      data["projects"][0]["nodes"]} for a in [0]):
        pass
    lc = r.get("land_core") or ""
    if any(c[3] == lc or c[4] == lc for c in changed):
        print("  cache %s" % d.name)
        print("      stored land_core=%r" % lc)
        print("      anchor_recno=%r" % r.get("anchor_recno"))
        print("      city_case_ids=%r" % (r.get("city_case_ids") or [])[:5])
