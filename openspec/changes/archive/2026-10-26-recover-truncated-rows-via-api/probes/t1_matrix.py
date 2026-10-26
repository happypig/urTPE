# -*- coding: utf-8 -*-
"""T1/T2/T5 POC: four-check identity matrix for all 15 truncated rows (2026-10-15 gazette).

Per row: parse identity from the row's own 案名 (district, section, first parcel
hyphen-split, declared-count fragment), query Get_updcase_list(sectstr, monobuf, sunobuf),
then get_project168_top per name candidate, and evaluate:
  check 1 same unit          — district+section appear in the candidate name
  check 2 name contained     — surviving 案名 address core ⊆ CASE_NAME (raw and normalised)
  check 3 count fragment     — 等<N>筆[(原M筆)] appears in CASE_NAME
  check 4 date closes        — gazette date == uro_chk_date or uro_chk_date2 (exact / ±1)
Also records normalised CASE_NAME == 案名 equality and similarity scores (T2 calibration
data) and counts requests + wall time (T5 budget).

Run from anywhere; edits constants only. Writes nothing.
"""
import difflib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = "https://gis.uro.taipei/"
PDF = r"C:\Users\jeffw\AppData\Local\Temp\opencode\g1021.pdf"
ROWS = {67: 11, 79: 13, 570: 95, 672: 112, 719: 121, 796: 134, 851: 144, 863: 146,
        902: 152, 912: 154, 919: 155, 930: 157, 944: 160, 997: 169, 1131: 192}

_reqs = {"n": 0}


def post(name, params):
    _reqs["n"] += 1
    data = urllib.parse.urlencode(params).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(BASE + "ashx/" + name, data=data, headers=UA)
            return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
        except (TimeoutError, urllib.error.URLError, OSError) as e:  # transient city-side
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


# --- normalisation (T2 candidate table) -------------------------------------

def normalize(s):
    """Presentation-level normalisation only: spacing, parens, calendar-safe typos."""
    s = re.sub(r"\s+", "", s or "")
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("計劃", "計畫")      # city-side drift, in every gazette (config context)
    s = s.replace("ㄧ", "一")
    return s


STAGE_PREFIX = re.compile(r"^(?:變更|擬訂|修訂)(?:第[一二三四五六七八九十]+次)?")


def strip_stage(s):
    return STAGE_PREFIX.sub("", s, count=1)


def name_core(name):
    """The address core: 臺北市<區><段…><parcel>地號等<N>筆[(原<M>筆)]."""
    m = re.search(r"臺北市\w+區.*?地號等\d+筆(?:\(原\d+筆\))?", name)
    return m.group(0) if m else ""


def parse_name(name):
    m = re.search(r"臺北市(\w+區)(\S+?段(?:[一二三四五]小段)?)(\d+)(?:-(\d+))?地號", name)
    if not m:
        return None
    dist, sect, mono, suno = m.group(1), m.group(2), m.group(3), m.group(4) or ""
    cf = re.search(r"等\d+筆(?:\(原\d+筆\))?", name)
    return dist, sect, mono.zfill(4), (suno or "0").zfill(4), cf.group(0) if cf else ""


def iso(s):
    """API date -> ISO; also accepts 2018-12-4 sloppiness."""
    s = (s or "")[:10]
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def gaz_iso(cell):
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", cell)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def date_check(d1, d2, want):
    """Returns (result, field): exact / pm1 / none."""
    for field, val in (("uro_chk_date", d1), ("uro_chk_date2", d2)):
        v = iso(val)
        if not v:
            continue
        if v == want:
            return "exact", field
    for field, val in (("uro_chk_date", d1), ("uro_chk_date2", d2)):
        v = iso(val)
        if not v:
            continue
        try:
            delta = abs((date.fromisoformat(v) - date.fromisoformat(want)).days)
        except ValueError:
            continue
        if delta == 1:
            return "pm1", field
    return "none", ""


# --- pull the 15 rows from the PDF ------------------------------------------

doc = pymupdf.open(PDF)
t0 = time.perf_counter()
matrix = []
for recno, pno in sorted(ROWS.items()):
    cells = None
    for t in doc[pno - 1].find_tables().tables:
        for r in t.extract():
            if (r[0] or "").strip() == str(recno):
                cells = r
                break
    date_cell = (cells[1] or "").strip()
    dist_cell = (cells[2] or "").strip()
    name_flat = (cells[3] or "").replace("\n", "").replace(" ", "")
    parsed = parse_name(name_flat)
    dist, sect, mono, suno, cfrag = parsed
    want = gaz_iso(date_cell)
    core = name_core(name_flat)
    core_n = normalize(core)
    full_n = normalize(name_flat)
    nostage_n = normalize(strip_stage(name_flat))

    body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": sect,
                                          "monobuf": mono, "sunobuf": suno})
    try:
        rows = json.loads(body)
    except Exception:
        rows = []

    cands = []
    for r in rows:
        cn = r.get("case_name") or ""
        cn_n = normalize(cn)
        m = re.search(r"case_id=(\d+)", r.get("details") or "")
        c = {
            "list_case_id": r.get("case_id"), "schedule": r.get("schedule"),
            "case_name": cn[:80], "name_hit": bool(cfrag) and cfrag in cn_n,
            "chk1_same_unit": bool(dist) and dist in cn_n and sect in cn_n,
            "chk2_core_in": bool(core_n) and core_n in cn_n,
            "chk2_core_in_raw": bool(core) and core in cn,
            "chk3_count_frag": bool(cfrag) and cfrag in cn_n,
            "sim_full": round(difflib.SequenceMatcher(None, full_n, cn_n).ratio(), 3),
            "sim_nostage": round(difflib.SequenceMatcher(None, nostage_n, cn_n).ratio(), 3),
            "equal_norm": cn_n == full_n,
            "date_result": "", "date_field": "", "api_case_id": "",
            "d1": "", "d2": "",
        }
        if m:
            c["api_case_id"] = m.group(1)
            try:
                top = json.loads(post("get_project168_top.ashx", {"case_id": m.group(1)}))[0]
                c["d1"] = (top.get("uro_chk_date") or "")[:10]
                c["d2"] = (top.get("uro_chk_date2") or "")[:10]
                c["date_result"], c["date_field"] = date_check(c["d1"], c["d2"], want)
            except Exception as e:  # noqa: BLE001
                c["date_result"] = f"ERR {str(e)[:40]}"
        cands.append(c)

    hits = [c for c in cands if c["name_hit"]]
    exact = [c for c in hits if c["date_result"] == "exact"]
    pm1 = [c for c in hits if c["date_result"] == "pm1"]
    accepted = exact or pm1  # ±1 only when no exact candidate exists (D4)
    matrix.append({
        "recno": recno, "gazette_date": want, "district": dist, "section": sect,
        "mono": mono, "suno": suno, "count_frag": cfrag, "core": core,
        "n_candidates": len(cands), "n_name_hits": len(hits),
        "n_exact": len(exact), "n_pm1": len(pm1),
        "accepted": [{k: c[k] for k in ("list_case_id", "api_case_id", "schedule",
                                        "case_name", "chk2_core_in", "chk2_core_in_raw",
                                        "equal_norm", "sim_full", "sim_nostage",
                                        "date_result", "date_field", "d1", "d2")}
                     for c in accepted],
        "candidates": cands,
    })
    flag = "EXACT" if exact else ("PM1" if pm1 else "RESIDUAL")
    print(f"編號 {recno:>5} {want}  {dist}{sect} {mono.lstrip('0')}"
          f"{'-' + suno.lstrip('0') if suno != '0000' else ''}  frag={cfrag}"
          f"  cands={len(cands)} hits={len(hits)} exact={len(exact)} pm1={len(pm1)}  -> {flag}")
    for c in accepted:
        print(f"      {c['api_case_id'] or c['list_case_id']:>12} {c['schedule']:<7}"
              f" d1={c['d1']} d2={c['d2']} [{c['date_field'] or '-'}]"
              f" core_in={c['chk2_core_in']}(raw:{c['chk2_core_in_raw']})"
              f" eq={c['equal_norm']} sim={c['sim_full']}/{c['sim_nostage']}")
        print(f"        {c['case_name']}")

elapsed = time.perf_counter() - t0
print(f"\n=== T5 budget: {_reqs['n']} requests, {elapsed:.1f}s wall for the full 15-row pass")
print(f"=== rows with an exact-date accepted candidate: "
      f"{sum(1 for m_ in matrix if m_['n_exact'])}/15")
