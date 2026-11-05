"""D14(b): district values collected from clean.tsv; what an enum match reads vs DISTRICT_RE. Read-only."""
import csv, re, sys
from collections import Counter
csv.field_size_limit(10**8)
rows = list(csv.DictReader(open(r"D:\project\urTPE\data\clean.tsv", encoding="utf-8"), delimiter="\t"))
print("columns:", list(rows[0].keys())[:25])
dist = Counter(r.get("district", "") for r in rows)
print("collected district values:", dict(dist))
enum = sorted(k for k in dist if k and k.endswith("區"))
STRICT = re.compile(r"臺北市(.{1,4}?區)")
alt = re.compile("|".join(map(re.escape, enum)))
changed = []
for r in rows:
    land = r.get("land", "")
    s = STRICT.search(land); old = s.group(1) if s else ""
    m = alt.search(land); new = m.group(0) if m else ""
    if old != new:
        changed.append((r.get("recno"), old, new, r.get("district"), land[:24]))
print("enum size:", len(enum), enum)
print("rows that change:", len(changed))
for c in changed:
    print(" ", c)
