# -*- coding: utf-8 -*-
"""Intersection v2: pull ALL of 虎林段四小段 (1,076 parcels), PIP against R089601's boundary."""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
WFS = "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs"


def wfs_json(params, timeout=600):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{WFS}?{qs}", headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


B = {"service": "WFS", "request": "GetFeature", "version": "1.1.0",
     "outputFormat": "json", "srsName": "EPSG:4326"}

case = wfs_json({**B, "typename": "Taipei:uro-redevelop-ALL-5", "cql_filter": "ID='R089601'"})
geom = case["features"][0]["geometry"]
polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]


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


def ring_centroid(ring):
    a = cx = cy = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i][:2]
        x1_, y1_ = ring[i + 1][:2]
        cross = x0 * y1_ - x1_ * y0
        a += cross
        cx += (x0 + x1_) * cross
        cy += (y0 + y1_) * cross
    if abs(a) < 1e-15:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


d = wfs_json({**B, "typename": "Taipei:LAND-ALL-TWD97", "maxFeatures": "3000",
              "cql_filter": "sect_name='虎林段四小段'"})
feats = d.get("features", [])
print(f"section parcels fetched: {len(feats)} (totalFeatures={d.get('totalFeatures')})")

cin_l, vin_l = [], []
for f in feats:
    p = f["properties"]
    g = f["geometry"]
    parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    cin = vin = False
    for poly in parts:
        for ring in poly:
            cx, cy = ring_centroid(ring)
            if not cin and pip(cx, cy, polys):
                cin = True
            if not vin and any(pip(x, y, polys) for x, y in ring):
                vin = True
                break
    if cin:
        cin_l.append(p["land_no"])
    if vin:
        vin_l.append(p["land_no"])


def key(t):
    a, _, b = t.partition("-")
    return (int(a), int(b) if b else -1)


cin_s = sorted(set(cin_l), key=key)
vin_s = sorted(set(vin_l), key=key)
print(f"\ncentroid-in: {len(cin_s)}   any-vertex-in: {len(vin_s)}   (gazette: declared 138, visible 113)")

pdf_visible = ("38、41、45、46、47、48、49、50、51、52、53、54、55、55-1、55-2、55-3、55-4、55-5、55-6、55-7、55-8、55-9、55-10、55-11、55-12、55-13、"
               "55-14、55-15、55-16、56、57、58、59、60、61、62、63、64、65、66、67、67-1、68、69、71、71-1、71-2、71-3、71-4、71-5、71-6、71-7、71-8、71-9、71-10、71-11、71-"
               "12、71-13、71-14、71-15、71-16、71-17、72、73、74、74-1、75、76、77、77-1、77-2、78、79、80、81、81-1、81-2、82、82-1、83、83-1、83-2、83-3、83-4、83-5、83-6、83-"
               "7、83-8、83-9、83-10、83-11、84、86、88、90、90-1、93、93-1、93-2、93-3、93-4、93-5、93-6、93-7、93-8、93-9、93-10、93-11、93-12、93-13、93-14、93-15、93-16")
pdf_set = set(re.findall(r"\d+(?:-\d+)?", pdf_visible))
print(f"pdf visible set: {len(pdf_set)}")

gis_set = set(vin_s)
print(f"pdf ⊆ gis: {pdf_set <= gis_set}")
print(f"gis − pdf ({len(gis_set - pdf_set)}): {sorted(gis_set - pdf_set, key=key)}")
print(f"pdf − gis ({len(pdf_set - gis_set)}): {sorted(pdf_set - gis_set, key=key)}")
print(f"\nfull reconstructed list ({len(vin_s)} parcels):")
print(vin_s)
