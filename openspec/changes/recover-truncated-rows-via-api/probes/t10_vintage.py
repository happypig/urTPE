# -*- coding: utf-8 -*-
"""T10 POC: boundary-vintage check for R089305 (雙連段二小段203-1, 大同區).

The design's open question: the boundary layer was expected to hold TWO polygons for
R089305, and the calibration question is which gazette vintage each reflects. The
corpus holds this unit's rows at 2018-02-08 and 2020-01-15 with identical 97-parcel
lists, so the comparison is polygon-set vs published list, plus the case family's
stage dates (looking for a pre-2018 stage the city may have re-dated).
Writes nothing.
"""
import csv
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
WFS = "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs"
BASE = "https://gis.uro.taipei/ashx/"

B = {"service": "WFS", "request": "GetFeature", "version": "1.1.0",
     "outputFormat": "json", "srsName": "EPSG:4326"}


def wfs_json(params, timeout=600):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{WFS}?{qs}", headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def post(name, params):
    req = urllib.request.Request(BASE + name,
                                 data=urllib.parse.urlencode(params).encode(), headers=UA)
    return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")


def pip(x, y, polys):
    inside = False
    for poly in polys:
        for ring in poly:
            n = len(ring)
            j = n - 1
            c = False
            for i in range(n):
                xi, yi = ring[i][0], ring[i][1]
                xj, yj = ring[j][0], ring[j][1]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    c = not c
                j = i
            if c:
                inside = not inside
    return inside


def geom_polys(g):
    return g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]


def key(t):
    a, _, b = t.partition("-")
    return (int(a), int(b) if b else -1)


for cid in ("R089305", "R089305-07"):
    d = wfs_json({**B, "typename": "Taipei:uro-redevelop-ALL-5",
                  "cql_filter": f"ID='{cid}'"})
    feats = d.get("features", [])
    print(f"{cid} -> features: {len(feats)}")
    for f in feats:
        g = f["geometry"]
        polys = geom_polys(g)
        rings = sum(len(p) for p in polys)
        props = {k: v for k, v in f["properties"].items() if v}
        print(f"   geom={g['type']} polygons={len(polys)} rings={rings} props={props}")

print()
body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": "雙連段二小段",
                                      "monobuf": "0203", "sunobuf": "0001"})
rows = json.loads(body)
print(f"case family for parcel 203-1: {len(rows)} cases")
for r in rows:
    m = re.search(r"case_id=(\d+)", r.get("details") or "")
    d1 = d2 = nm = ""
    if m:
        try:
            t = json.loads(post("get_project168_top.ashx", {"case_id": m.group(1)}))[0]
            d1 = (t.get("uro_chk_date") or "")[:10]
            d2 = (t.get("uro_chk_date2") or "")[:10]
            nm = t.get("CASE_NAME") or ""
        except Exception as e:  # noqa: BLE001
            nm = f"ERR {str(e)[:40]}"
    print(f"  {r.get('case_id'):>10} sched={r.get('schedule'):<8} d1={d1} d2={d2}  {nm[:70]}")

# polygon sets vs the corpus lists
with open(r"D:\project\urTPE\data\merged.tsv", encoding="utf-8") as fh:
    corpus = {r["recno"]: r for r in csv.DictReader(fh, delimiter="\t")}
lists = {rn: set(corpus[rn]["parcels"].split("|")) for rn in ("917", "717")}

d = wfs_json({**B, "typename": "Taipei:uro-redevelop-ALL-5", "cql_filter": "ID='R089305'"})
land = wfs_json({**B, "typename": "Taipei:LAND-ALL-TWD97", "maxFeatures": "3000",
                 "cql_filter": "sect_name='雙連段二小段'"})
print(f"\nsection parcels fetched: {len(land.get('features', []))}")
for fi, f in enumerate(d.get("features", [])):
    polys = geom_polys(f["geometry"])
    cands = set()
    for lf in land.get("features", []):
        g = lf["geometry"]
        hit = False
        for poly in geom_polys(g):
            for ring in poly:
                if any(pip(x, y, polys) for x, y in ring):
                    hit = True
                    break
            if hit:
                break
        if hit:
            cands.add(lf["properties"]["land_no"])
    print(f"\npolygon[{fi}]: {len(cands)} candidate parcels")
    for rn, lst in lists.items():
        inter = cands & lst
        print(f"   vs corpus {rn} ({corpus[rn]['iso_date']}, {len(lst)} parcels): "
              f"|∩|={len(inter)}  list⊆cands={lst <= cands}")
    print(f"   cands − lists: {sorted(cands - set().union(*lists.values()), key=key)[:30]}")
    print(f"   lists − cands: {sorted(set().union(*lists.values()) - cands, key=key)[:30]}")
