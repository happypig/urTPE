# -*- coding: utf-8 -*-
"""T8 POC v2: calibrate the overlap test for GIS list reconstruction.

Fragments are read from the gazette PDF itself (no hand transcription). WFS responses are
cached in the working directory so calibration re-runs cost no requests.

Rule under test (spec: fragment ⊆ GIS precondition; surplus attributable to
boundary-touching neighbours):
    reconstructed = fragment ∪ {candidates outside the fragment whose
                                 vertex-inside fraction >= t}
Calibration: one t must close BOTH anchors — 虎林段 R089601 -> exactly 138, 美仁段
R098505 -> exactly 74 — with a clear separation margin between accepted extras and
rejected surplus. If the closing t-range is empty or not separated, the rule refuses
(fail safe to fragment+partial).
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
WFS = "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs"
PDF = r"C:\Users\jeffw\AppData\Local\Temp\opencode\g1021.pdf"
CACHE = os.path.join(os.getcwd(), "wfs_cache")
ROWS = {"R089601": 67, "R098505": 79}  # any row of the unit works; 67/79 are 虎林/美仁

UNITS = [
    {"label": "虎林段 R089601", "case": "R089601", "sect": "虎林段四小段",
     "recno": 67, "declared": 138, "repairs": {}},
    {"label": "美仁段 R098505", "case": "R098505", "sect": "美仁段二小段",
     "recno": 79, "declared": 74, "repairs": {"78-1": "718-1"}},
]

B = {"service": "WFS", "request": "GetFeature", "version": "1.1.0",
     "outputFormat": "json", "srsName": "EPSG:4326"}


def wfs_json(params, timeout=600):
    os.makedirs(CACHE, exist_ok=True)
    name = re.sub(r"[^\w]", "_", urllib.parse.urlencode(params))[:180] + ".json"
    path = os.path.join(CACHE, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{WFS}?{qs}", headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


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


def key(t):
    a, _, b = t.partition("-")
    return (int(a), int(b) if b else -1)


def geom_polys(g):
    return g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]


def land_cell(recno, pno):
    doc = pymupdf.open(PDF)
    for t in doc[pno - 1].find_tables().tables:
        for r in t.extract():
            if (r[0] or "").strip() == str(recno):
                return (r[4] or "").replace("\n", "").replace(" ", "")
    raise SystemExit(f"row {recno} not found")


# page numbers from probes/pdf_all15.py
PAGES = {67: 11, 79: 13}

results = {}
for unit in UNITS:
    print(f"\n===== {unit['label']} (declared {unit['declared']}) =====")
    cell = land_cell(unit["recno"], PAGES[unit["recno"]])
    frag_raw = re.findall(r"\d+(?:-\d+)?", cell)
    frag_raw_set = set(frag_raw)
    print(f"PDF cell tokens: {len(frag_raw)} printed, {len(frag_raw_set)} unique")
    frag = {unit["repairs"].get(t, t) for t in frag_raw_set}
    repaired = sorted(t for t in frag_raw_set if t in unit["repairs"])

    case = wfs_json({**B, "typename": "Taipei:uro-redevelop-ALL-5",
                     "cql_filter": f"ID='{unit['case']}'"})
    polys = []
    for f in case.get("features", []):
        polys.extend(geom_polys(f["geometry"]))

    d = wfs_json({**B, "typename": "Taipei:LAND-ALL-TWD97", "maxFeatures": "3000",
                  "cql_filter": f"sect_name='{unit['sect']}'"})
    feats = d.get("features", [])
    print(f"section parcels fetched: {len(feats)}")

    cands = []  # (land_no, frac, centroid_in)
    for f in feats:
        p = f["properties"]
        parts = geom_polys(f["geometry"])
        n_in = n_tot = 0
        cin = False
        for poly in parts:
            for ring in poly:
                cx, cy = ring_centroid(ring)
                if pip(cx, cy, polys):
                    cin = True
                for x, y in ring:
                    n_tot += 1
                    if pip(x, y, polys):
                        n_in += 1
        if n_in or cin:
            cands.append((p["land_no"], (n_in / n_tot) if n_tot else 0.0, cin))

    all_in = {c[0] for c in cands}
    extras = sorted((c for c in cands if c[0] not in frag), key=lambda c: key(c[0]))
    print(f"candidates: {len(all_in)}  fragment unique: {len(frag)}  "
          f"fragment⊆cands: {frag <= all_in}  extras: {len(extras)}  "
          f"repairs: {repaired}")

    print("non-fragment candidates by fraction (land_no frac centroid):")
    for no, fr, cin in sorted(extras, key=lambda c: -c[1]):
        pos = "tail" if key(no) > key(sorted(frag, key=key)[-1]) else "gap "
        print(f"   {no:>7}  {fr:.3f}  {str(cin)[0]}  {pos}")
    results[unit["case"]] = {
        "declared": unit["declared"], "frag": sorted(frag, key=key),
        "extras": [(no, round(fr, 3)) for no, fr, _ in extras],
    }

# --- calibrated rule: positional tail + vertex containment + close check -----
# (v1 finding: no pure vertex-fraction threshold closes the anchors — gap parcels
#  at 0.6 interleave with tail members at 0.6. The printed list is complete-sorted
#  up to the cut, so a true member outside the fragment must sort after the last
#  printed parcel. Centroid-only parcels (frac 0.0) are artifacts, not candidates.)
print("\n===== calibrated rule: fragment ∪ tail(≥1 vertex inside) must close =====")
for case_id, r in results.items():
    frag = r["frag"]
    last = frag[-1]
    tail = [no for no, fr in r["extras"] if key(no) > key(last) and fr > 0]
    reconstructed = frag + sorted(tail, key=key)
    verdict = ("CLOSES" if len(reconstructed) == r["declared"]
               else f"REFUSES ({len(reconstructed)} != {r['declared']}) -> partial")
    print(f"{case_id}: fragment {len(frag)} + tail {len(tail)} = {len(reconstructed)}"
          f" (declared {r['declared']}) -> {verdict}")
    print(f"   tail members: {sorted(tail, key=key)}")
    if tail:
        fr_of = dict(r["extras"])
        print(f"   min tail member fraction: {min(fr_of[t] for t in tail):.3f}")
