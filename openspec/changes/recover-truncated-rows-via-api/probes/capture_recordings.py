# -*- coding: utf-8 -*-
"""Capture live API responses as offline fixtures for tests/test_recovery_*.py.

One-shot (2026-10-26). Writes ONLY into tests/fixtures/recovery/:
  ashx_families.json   {"<sectstr>|<mono>|<suno>": raw body}   for the 8 truncated units
  ashx_tops.json       {"<api_case_id>": raw body}             for every family member
  geoserver_boundary_*.json                                    raw WFS replies (small)
  geoserver_candidates.json                                    live-computed membership
  residual_row.json                                            the real residual row's cells

The residual (編號 100 of 核定案件-2026-08-11.pdf) is captured too, so the offline
acceptance test exercises the residual path against a response recorded from the city.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

OUT = r"D:\project\urTPE\tests\fixtures\recovery"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
WFS = "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs"
B = {"service": "WFS", "request": "GetFeature", "version": "1.1.0",
     "outputFormat": "json", "srsName": "EPSG:4326"}

os.makedirs(OUT, exist_ok=True)


def post(name, params):
    data = urllib.parse.urlencode(params).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://gis.uro.taipei/ashx/" + name,
                                         data=data, headers=UA)
            return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
        except (TimeoutError, urllib.error.URLError, OSError) as e:  # noqa: PERF203
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def wfs(params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{WFS}?{qs}", headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def parse_name(name):
    m = re.search(r"臺北市(\w+區)(\S+?段(?:[一二三四五]小段)?)(\d+)(?:-(\d+))?地號", name)
    if not m:
        return None
    dist, sect, mono, suno = m.group(1), m.group(2), m.group(3), m.group(4) or ""
    return sect, mono.zfill(4), (suno or "0").zfill(4)


UNITS = {  # from the 15 truncated rows of the 2026-10-15 gazette (t1_matrix.py)
    "虎林段四小段|0038|0000": ("虎林段四小段", "0038", "0000"),
    "美仁段二小段|0694|0000": ("美仁段二小段", "0694", "0000"),
    "振興段一小段|0002|0006": ("振興段一小段", "0002", "0006"),
    "雙連段二小段|0203|0001": ("雙連段二小段", "0203", "0001"),
    "雙連段一小段|0197|0000": ("雙連段一小段", "0197", "0000"),
    "漢中段二小段|0328|0000": ("漢中段二小段", "0328", "0000"),
    "雙園段二小段|0505|0000": ("雙園段二小段", "0505", "0000"),
    "南港段一小段|0720|0000": ("南港段一小段", "0720", "0000"),
}

families, tops = {}, {}
for key, (sect, mono, suno) in UNITS.items():
    body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": sect,
                                          "monobuf": mono, "sunobuf": suno})
    families[key] = body
    try:
        rows = json.loads(body)
    except Exception:
        rows = []
    for r in rows:
        m = re.search(r"case_id=(\d+)", r.get("details") or "")
        if m and m.group(1) not in tops:
            tops[m.group(1)] = post("get_project168_top.ashx", {"case_id": m.group(1)})
    print(f"family {key}: {len(rows)} rows")

with open(os.path.join(OUT, "ashx_families.json"), "w", encoding="utf-8") as f:
    json.dump(families, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "ashx_tops.json"), "w", encoding="utf-8") as f:
    json.dump(tops, f, ensure_ascii=False, indent=1)
print(f"captured {len(families)} families, {len(tops)} tops")

# --- GeoServer: raw boundaries + live-computed membership --------------------

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


cands = {}
for case_id, sect in (("R089601", "虎林段四小段"), ("R098505", "美仁段二小段")):
    case = wfs({**B, "typename": "Taipei:uro-redevelop-ALL-5",
                "cql_filter": f"ID='{case_id}'"})
    with open(os.path.join(OUT, f"geoserver_boundary_{case_id}.json"), "w",
              encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False)
    polys = []
    for feat in case.get("features", []):
        polys.extend(geom_polys(feat["geometry"]))
    land = wfs({**B, "typename": "Taipei:LAND-ALL-TWD97", "maxFeatures": "3000",
                "cql_filter": f"sect_name='{sect}'"})
    rows = []
    for feat in land.get("features", []):
        n_in = 0
        for poly in geom_polys(feat["geometry"]):
            for ring in poly:
                if any(pip(x, y, polys) for x, y in ring):
                    n_in += 1
        if n_in:
            n_tot = sum(len(r) for p in geom_polys(feat["geometry"]) for r in p)
            rows.append([feat["properties"]["land_no"], round(n_in / n_tot, 3)])
    cands[case_id] = sorted(rows)
    print(f"{case_id}: {len(rows)} candidates")

for numeric in ("09610233", "09902025", "10506132", "09412311"):
    d = wfs({**B, "typename": "Taipei:uro-redevelop-ALL-5",
             "cql_filter": f"ID='{numeric}'"})
    cands[numeric] = []
    if not d.get("features") and numeric == "09610233":
        with open(os.path.join(OUT, "geoserver_boundary_empty.json"), "w",
                  encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)

with open(os.path.join(OUT, "geoserver_candidates.json"), "w", encoding="utf-8") as f:
    json.dump(cands, f, ensure_ascii=False, indent=1)

# --- the real residual row (編號 100 of the oldest archived gazette) ----------

doc = pymupdf.open(r"D:\project\urtpe-gazettes\核定案件-2026-08-11.pdf")
cells = None
for t in doc[13].find_tables().tables:
    for r in t.extract():
        if (r[0] or "").strip() == "100":
            cells = r
            break
date, dist, name, land = ((c or "").replace("\n", "").replace(" ", "") for c in cells[1:5])
sect, mono, suno = parse_name(name)
body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": sect,
                                      "monobuf": mono, "sunobuf": suno})
families[f"{sect}|{mono}|{suno}"] = body
try:
    for r in json.loads(body):
        m = re.search(r"case_id=(\d+)", r.get("details") or "")
        if m and m.group(1) not in tops:
            tops[m.group(1)] = post("get_project168_top.ashx", {"case_id": m.group(1)})
except Exception:
    pass
with open(os.path.join(OUT, "ashx_families.json"), "w", encoding="utf-8") as f:
    json.dump(families, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "ashx_tops.json"), "w", encoding="utf-8") as f:
    json.dump(tops, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "residual_row.json"), "w", encoding="utf-8") as f:
    json.dump({"date": date, "district": dist, "name": name, "land": land,
               "family_key": f"{sect}|{mono}|{suno}"}, f, ensure_ascii=False, indent=1)
print(f"residual row 100: {date} {dist} {name[:60]} family={sect}|{mono}|{suno}")
print("done")
