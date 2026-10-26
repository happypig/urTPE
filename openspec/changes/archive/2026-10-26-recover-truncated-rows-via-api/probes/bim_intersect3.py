# -*- coding: utf-8 -*-
"""Confirm on R098505 (74筆, PDF visible 72) + probe alternative layers for numeric ids."""
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


def intersect_unit(case_id, sect):
    case = wfs_json({**B, "typename": "Taipei:uro-redevelop-ALL-5",
                     "cql_filter": f"ID='{case_id}'"})
    feats = case.get("features", [])
    if not feats:
        return None
    geom = feats[0]["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    d = wfs_json({**B, "typename": "Taipei:LAND-ALL-TWD97", "maxFeatures": "5000",
                  "cql_filter": f"sect_name='{sect}'"})
    out = set()
    for f in d.get("features", []):
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        hit = False
        for poly in parts:
            for ring in poly:
                cx, cy = ring_centroid(ring)
                if pip(cx, cy, polys) or any(pip(x, y, polys) for x, y in ring):
                    hit = True
                    break
            if hit:
                break
        if hit:
            out.add(f["properties"]["land_no"])
    return out


def key(t):
    a, _, b = t.partition("-")
    return (int(a), int(b) if b else -1)


# --- R098505 (美仁段二小段694地號等74筆; PDF visible = 72)
pdf79 = ("694、695、695-3、695-4、696、696-1、696-2、697、697-1、697-2、698、699、699-1、699-2、699-3、700、702、703、"
         "704、705、706、707、708、708-1、708-2、709、709-1、709-2、710、710-1、711、711-1、712、713、713-1、714、714-1、"
         "715、715-1、716、716-1、717、717-1、717-2、718、78-1、719、719-2、719-3、719-5、719-6、719-7、719-8、719-9、"
         "719-10、735、735-1、735-2、735-3、735-5、735-6、736、736-1、736-2、737、737-1、738、738-1、739、739-1、740、740-1")
pdf_set = set(re.findall(r"\d+(?:-\d+)?", pdf79))
gis = intersect_unit("R098505", "美仁段二小段")
if gis is not None:
    gs = sorted(gis, key=key)
    print(f"R098505 (declared 74, pdf visible {len(pdf_set)}): gis={len(gs)}")
    print(f"  pdf ⊆ gis: {pdf_set <= gis}")
    print(f"  gis − pdf: {sorted(gis - pdf_set, key=key)}")
    print(f"  pdf − gis: {sorted(pdf_set - gis, key=key)}")
    print(f"  full list: {gs}")

# --- alternative layers for numeric-form case ids
print("\n=== alternative layers for numeric ids ===")
for layer in ("Taipei:plan-all-5", "Taipei:designland-Approved", "Taipei:designland",
              "Taipei:design", "Taipei:uro-redevelop-ALL-5"):
    for cid in ("09902025", "09610233"):
        try:
            d = wfs_json({**B, "typename": layer, "maxFeatures": "2",
                          "cql_filter": f"ID='{cid}'"})
            n = len(d.get("features", []))
            tot = d.get("totalFeatures")
            if n:
                props = list(d["features"][0].get("properties", {}).keys())
                print(f"   {layer} / {cid}: {n} (total {tot}) props={props[:8]}")
            else:
                print(f"   {layer} / {cid}: 0")
        except Exception as e:  # noqa: BLE001
            print(f"   {layer} / {cid}: ERR {str(e)[:60]}")
