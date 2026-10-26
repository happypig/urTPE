# -*- coding: utf-8 -*-
"""T4 POC: ROC-era coverage of the ashx APIs for truncated-row recovery.

The archive holds no ROC-era *publication* (oldest: 2026-08-11), so this probe adapts:
  Part A — the oldest archived gazette, whose cells are ROC-dated (the city switched
           to Gregorian only at the 1151002 publication). Its truncated rows are
           recovered with the four-check flow, exercising the ROC->ISO path end to end.
  Part B — direct API probes of pre-2006 approvals sampled from the corpus
           (data/merged.tsv), which answer API coverage of 2002-2005 cases outright.
Writes nothing.
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

from urtpe.extract import (closing_phrase_present, declared_parcel_count,  # noqa: E402
                           land_cell_is_complete, to_iso, calendar_of,
                           parcel_token_count, TRUNCATED_TAIL_RE)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = "https://gis.uro.taipei/"
GAZETTE = r"D:\project\urtpe-gazettes\核定案件-2026-08-11.pdf"


def post(name, params):
    data = urllib.parse.urlencode(params).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(BASE + "ashx/" + name, data=data, headers=UA)
            return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
        except (TimeoutError, urllib.error.URLError, OSError) as e:  # noqa: PERF203
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def normalize(s):
    s = re.sub(r"\s+", "", s or "")
    return (s.replace("（", "(").replace("）", ")")
             .replace("計劃", "計畫").replace("ㄧ", "一"))


def parse_name(name):
    m = re.search(r"臺北市(\w+區)(\S+?段(?:[一二三四五]小段)?)(\d+)(?:-(\d+))?地號", name)
    if not m:
        return None
    dist, sect, mono, suno = m.group(1), m.group(2), m.group(3), m.group(4) or ""
    cf = re.search(r"等\d+筆(?:\(原\d+筆\))?", name)
    return dist, sect, mono.zfill(4), (suno or "0").zfill(4), cf.group(0) if cf else ""


def iso_api(s):
    s = (s or "")[:10]
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def date_check(d1, d2, want):
    for field, val in (("uro_chk_date", d1), ("uro_chk_date2", d2)):
        if iso_api(val) == want:
            return "exact", field
    return "none", ""


def truncated_rows(path):
    """Rows the pipeline would exclude as publisher-truncated (same detectors)."""
    doc = pymupdf.open(path)
    out = []
    for pno in range(1, doc.page_count + 1):
        for t in doc[pno - 1].find_tables().tables:
            for i, r in enumerate(t.extract()):
                recno = (r[0] or "").strip()
                if not re.match(r"^\d+$", recno):
                    continue
                land = (r[4] or "").replace("\n", "").replace(" ", "")
                name = (r[3] or "").replace("\n", "").replace(" ", "")
                if not land or not name:
                    continue
                tail_fired = bool(TRUNCATED_TAIL_RE.search(land))
                declared = declared_parcel_count(name)
                count_fired = (declared is not None and not tail_fired
                               and not closing_phrase_present(land)
                               and parcel_token_count(land) < declared)
                if (tail_fired or count_fired) and not land_cell_is_complete(land, name):
                    out.append((int(recno), pno, (r[1] or "").strip(), (r[2] or "").strip(),
                                name, land, "tail" if tail_fired else "declared_count"))
    return out


print("=== Part A: truncated rows of the oldest archived gazette (ROC-dated cells) ===")
rows = truncated_rows(GAZETTE)
print(f"{len(rows)} truncated rows")
for recno, pno, dcell, dist, name, land, cause in rows:
    iso, _parts = to_iso(dcell)
    cal = calendar_of(dcell)
    parsed = parse_name(name)
    line = f"  編號 {recno:>5} p{pno:<3} {dcell:>12} -> {iso} ({cal})  cause={cause}"
    if not parsed:
        print(line + "\n      identity parse FAILED")
        continue
    d, sect, mono, suno, cfrag = parsed
    body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": sect,
                                          "monobuf": mono, "sunobuf": suno})
    try:
        cands = json.loads(body)
    except Exception:
        cands = []
    hits = [c for c in cands if cfrag and cfrag in normalize(c.get("case_name") or "")]
    verified = []
    for h in hits:
        m = re.search(r"case_id=(\d+)", h.get("details") or "")
        if not m:
            continue
        try:
            top = json.loads(post("get_project168_top.ashx", {"case_id": m.group(1)}))[0]
        except Exception:
            continue
        res, field = date_check(top.get("uro_chk_date"), top.get("uro_chk_date2"), iso or "")
        if res == "exact":
            verified.append((h.get("case_id"), m.group(1), field))
    print(line + f"  cands={len(cands)} frag_hits={len(hits)} exact={len(verified)}"
          + (f"  cases={[v[0] for v in verified]}" if verified else "  -> RESIDUAL"))

print("\n=== Part B: pre-2006 API coverage, sampled from the corpus ===")
with open(r"D:\project\urTPE\data\merged.tsv", encoding="utf-8") as f:
    corpus = list(csv.DictReader(f, delimiter="\t"))
old = [r for r in corpus if (r["iso_date"] or "") < "2006-01-01"]
print(f"corpus rows dated before 2006: {len(old)}")
sample = sorted(old, key=lambda r: r["iso_date"])[:: max(1, len(old) // 6)][:6]
for r in sample:
    sect, fp = r["section"], r["first_parcel"]
    mono, _, suno = fp.partition("-")
    body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": sect,
                                          "monobuf": mono.zfill(4),
                                          "sunobuf": (suno or "0").zfill(4)})
    try:
        cands = json.loads(body)
    except Exception:
        cands = []
    exact = []
    for c in cands:
        m = re.search(r"case_id=(\d+)", c.get("details") or "")
        if not m:
            continue
        try:
            top = json.loads(post("get_project168_top.ashx", {"case_id": m.group(1)}))[0]
        except Exception:
            continue
        res, field = date_check(top.get("uro_chk_date"), top.get("uro_chk_date2"),
                                r["iso_date"])
        if res == "exact":
            exact.append((c.get("case_id"), field))
    print(f"  {r['iso_date']}  {r['district']}{sect} {fp} (等{r['land_count']}筆)"
          f"  family={len(cands)} exact-date hits={len(exact)}"
          + (f"  {[e[0] for e in exact]}" if exact else ""))
