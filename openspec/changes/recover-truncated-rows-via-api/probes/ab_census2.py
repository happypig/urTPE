# -*- coding: utf-8 -*-
"""Census v2: sweep all gazette-known parcels; count EVERY zone-marker style; save cache."""
import csv
import json
import re
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
API = "https://gis.uro.taipei/ashx/"
CACHE = r"C:\Users\jeffw\AppData\Local\Temp\opencode\ab_census.json"

# every zone-marker style observed: -A區, (B區段), (甲區段), (A1基地), (基隆路整宅B基地)
ZONE_RE = re.compile(r"[AB]區|甲區|乙區|丙區|區段|基地")
SUFFIX_RE = re.compile(r"[（(][^（）()]*?(?:區段|基地|[AB]區)[^（）()]*?[)）]\s*$|[-－][AB]區\s*$|[-－][甲乙丙]區段?\s*$")


def post(name, params, timeout=45):
    req = urllib.request.Request(API + name, data=urllib.parse.urlencode(params).encode(),
                                 headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


rows = list(csv.DictReader(open(r"C:\Users\jeffw\AppData\Local\Temp\opencode\g1021\out\merged.tsv",
                                encoding="utf-8-sig"), delimiter="\t"))
pairs = {(r["district_land"], r["section"], r["first_parcel"]) for r in rows}
for sect, fp in [("虎林段四小段", "38"), ("美仁段二小段", "694"), ("振興段一小段", "2-6"),
                 ("雙連段二小段", "203-1"), ("雙連段一小段", "197"), ("漢中段二小段", "328"),
                 ("雙園段二小段", "505"), ("南港段一小段", "720")]:
    pairs.add(("", sect, fp))
queries = sorted(pairs)
print(f"queries: {len(queries)}", flush=True)

all_rows = {}
t0 = time.time()
for i, (_d, sect, fp) in enumerate(queries):
    mono, _, suno = fp.partition("-")
    try:
        body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": sect,
                                              "monobuf": mono.zfill(4),
                                              "sunobuf": (suno or "0").zfill(4)})
        cands = json.loads(body) if body.strip() else []
    except Exception:  # noqa: BLE001
        cands = []
    for c in cands:
        all_rows[c["case_id"]] = c
    if (i + 1) % 150 == 0:
        print(f"  {i+1}/{len(queries)}  cases: {len(all_rows)}  {time.time()-t0:.0f}s", flush=True)
    time.sleep(0.08)

print(f"swept: {len(all_rows)} distinct cases in {time.time()-t0:.0f}s", flush=True)
json.dump(all_rows, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
print("cache saved:", CACHE)

ab = {cid: r for cid, r in all_rows.items() if ZONE_RE.search(r["case_name"])}
print(f"\nzone-marked API cases: {len(ab)} (was 50 with the latin-only regex)")

by_style = {"-A/-B區": 0, "區段": 0, "基地": 0}
for r in ab.values():
    n = r["case_name"]
    if re.search(r"[-－][AB]區", n):
        by_style["-A/-B區"] += 1
    elif "區段" in n:
        by_style["區段"] += 1
    elif "基地" in n:
        by_style["基地"] += 1
print("by style:", by_style)

groups = {}
for cid, r in ab.items():
    base = SUFFIX_RE.sub("", r["case_name"]).strip()
    groups.setdefault(base, []).append(cid)
print(f"distinct base names: {len(groups)}")
print("\nnew (non-latin) zone cases not in the first census:")
for base, cids in sorted(groups.items()):
    if not re.search(r"[-－][AB]區", base) and (re.search(r"區段|基地", base)):
        print(f"  {base[:66]}  -> {cids}")
