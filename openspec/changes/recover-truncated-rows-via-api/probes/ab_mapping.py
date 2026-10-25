# -*- coding: utf-8 -*-
"""Parcel mapping for all A/B cases: WFS polygon existence + cadastral intersection.

Per unit: zone -> parcel set; then A/B overlap analysis against the declared count.
"""
import csv
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
WFS = "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs"
B = {"service": "WFS", "request": "GetFeature", "version": "1.1.0",
     "outputFormat": "json", "srsName": "EPSG:4326"}


def wfs_json(params, timeout=600):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{WFS}?{qs}", headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def pip(x, y, polys):
    inside = False
    for poly in polys:
        for ring in poly:
            n = len(ring); j = n - 1; c = False
            for i in range(n):
                xi, yi = ring[i][0], ring[i][1]
                xj, yj = ring[j][0], ring[j][1]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    c = not c
                j = i
            if c:
                inside = not inside
    return inside


def ring_centroid(ring):
    a = cx = cy = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i][:2]
        x1_, y1_ = ring[i + 1][:2]
        cross = x0 * y1_ - x1_ * y0
        a += cross; cx += (x0 + x1_) * cross; cy += (y0 + y1_) * cross
    if abs(a) < 1e-15:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def boundary(cid):
    d = wfs_json({**B, "typename": "Taipei:uro-redevelop-ALL-5", "maxFeatures": "3",
                  "cql_filter": f"ID='{cid}'"})
    return d.get("features", [])


def section_parcels(sect):
    d = wfs_json({**B, "typename": "Taipei:LAND-ALL-TWD97", "maxFeatures": "12000",
                  "cql_filter": f"sect_name='{sect}'"})
    out = {}
    for f in d.get("features", []):
        out.setdefault(f["properties"]["land_no"], f["geometry"])
    return out


def zone_set(geom, parcels):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    got = set()
    for land_no, g in parcels.items():
        if not g:
            continue
        parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in parts:
            hit = False
            for ring in poly:
                cx, cy = ring_centroid(ring)
                if pip(cx, cy, polys) or any(pip(x, y, polys) for x, y in ring):
                    hit = True
                    break
            if hit:
                got.add(land_no)
                break
    return got


# unit table from the census: (label, LAND-ALL sect_name, [(case_id, zone, declared)])
UNITS = [
    ("逸仙段二小段151", "逸仙段二小段",
     [("09912102", "B", 21), ("10306302", "B", 21), ("10306303", "B", 21)]),
    ("南港段二小段528", "南港段二小段",
     [("R089004-03", "A", 16), ("R089004-07", "B", 16), ("R089004-08", "A", 16), ("R089004-09", "B", 16)]),
    ("大龍段一小段265", "大龍段一小段",
     [("R109301-01", "A", 27), ("R109301-02", "B", 27), ("R109301-03", "A", 30), ("R109301-04", "B", 30)]),
    ("懷生段二小段16", "懷生段二小段",
     [("09503203", "B", 6), ("09503204", "B", 6), ("09503205", "A", 6), ("09503206", "B", 6),
      ("09503208", "B", 6), ("09503210", "B", 6), ("11301151", "B", 6)]),
    ("木柵段三小段623", "木柵段三小段",
     [("R098803-01", "A", 39), ("R098803-02", "A", 39)]),
    ("萬慶段二小段6", "萬慶段二小段",
     [("10103091", "A", 41), ("10103092", "B", 41), ("10712251", "A", 45), ("10712252", "B", 45)]),
    ("敦化段四小段363-1", "敦化段四小段",
     [("10503042", "A", 4), ("10503043", "B", 4), ("10906101", "A", 5), ("10906102", "B", 5),
      ("10906103", "A", 5), ("10906104", "B", 5)]),
    ("民生段134-6", "民生段",
     [("R103504", "B", 5), ("R103504-01", "A", 5), ("R103504-02", "B", 5),
      ("R103504-03", "A", 5), ("R103504-04", "B", 5)]),
    ("莒光段二小段83", "莒光段二小段", [("R115106", "B", 22)]),
    ("華中段一小段201-2、352", "華中段一小段",
     [("R089113", "B", 26), ("R089113-01", "A", 26), ("R089113-03", "A", 26), ("R089113-05", "A", 26)]),
    ("玉成段二小段166", "玉成段二小段",
     [("P101006-12", "B", 12), ("P101006-13", "A", 12), ("P101007-02", "A", 12)]),
    ("吉林段四小段508", "吉林段四小段", [("R110401", "B", 17)]),
    ("玉成段三小段560", "玉成段三小段", [("R103004", "B", 5)]),
    ("雙園段二小段505", "雙園段二小段",
     [("09610233", "A", 77), ("09610234", "B", 77), ("09610235", "A", 77),
      ("09610236", "B", 77), ("09610237", "B", 77)]),
]

# 1. polygon existence for all 50 ids
print("=== WFS polygon existence ===")
poly = {}
for _, _, cases in UNITS:
    for cid, _, _ in cases:
        if cid in poly:
            continue
        try:
            fs = boundary(cid)
            poly[cid] = fs[0]["geometry"] if fs else None
        except Exception:  # noqa: BLE001
            poly[cid] = None
n_poly = sum(1 for v in poly.values() if v)
print(f"   {n_poly}/{len(poly)} case ids have boundary polygons")
for cid, g in poly.items():
    if g:
        print(f"      {cid}: polygon ✓")

# 2. intersect per unit
print("\n=== zone -> parcel mapping ===")
sets = {}
for label, sect, cases in UNITS:
    if not any(poly.get(cid) for cid, _, _ in cases):
        print(f"\n{label}: no polygons (numeric/other id form) -> mapping not determinable")
        continue
    parcels = section_parcels(sect)
    print(f"\n{label} (section parcels: {len(parcels)}):")
    unit_sets = {}
    for cid, zone, declared in cases:
        if not poly.get(cid):
            print(f"   {cid} {zone}: no polygon")
            continue
        s = zone_set(poly[cid], parcels)
        unit_sets[(cid, zone)] = s
        print(f"   {cid:>12} {zone} (declared {declared}): {len(s)} parcels")
    sets[label] = (sect, cases, unit_sets, parcels)

    # same-stage A/B pair comparison
    for za in ("A", "B"):
        pass
    zones = {}
    for (cid, zone), s in unit_sets.items():
        zones.setdefault(zone, []).append((cid, s))
    if "A" in zones and "B" in zones:
        # use the latest-stage pair: the pair with equal declared counts and both present
        a_all = set().union(*[s for _, s in zones["A"]])
        b_all = set().union(*[s for _, s in zones["B"]])
        print(f"   A union: {len(a_all)}  B union: {len(b_all)}  A∩B: {len(a_all & b_all)}  "
              f"A∪B: {len(a_all | b_all)}  A−B: {sorted(a_all - b_all, key=lambda t: (int(t.split('-')[0]), int(t.split('-')[1]) if '-' in t else -1))[:10]}")
        print(f"   B−A: {sorted(b_all - a_all, key=lambda t: (int(t.split('-')[0]), int(t.split('-')[1]) if '-' in t else -1))[:10]}")

# 3. gazette-row mapping per unit
print("\n=== gazette rows for these units ===")
rows = list(csv.DictReader(open(r"C:\Users\jeffw\AppData\Local\Temp\opencode\g1021\out\merged.tsv",
                                encoding="utf-8-sig"), delimiter="\t"))
for label, sect, cases in UNITS:
    fp = re.search(r"(\d+[\d-]*)", label)
    fp = fp.group(1) if fp else "?"
    pat = re.compile(re.escape(sect.split("段")[0] + "段") if False else re.escape(sect))
    hits = [r for r in rows if sect in r["name"] and fp in r["name"]]
    if hits:
        for r in hits[:6]:
            print(f"   {label}: 編號{r['recno']} {r['iso_date']} {r['name'][:52]}")
    else:
        print(f"   {label}: no gazette rows (unit absent or excluded)")
