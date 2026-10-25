# -*- coding: utf-8 -*-
"""POC: re-identify excluded 編號 67 via the API.

What the PDF gives us: 信義區, 2026/3/12, name fragment "小段38地號等138筆(原120筆)土地都".
Section unknown -> enumerate 信義區's sections, query parcel 38 in each,
filter case names containing 138筆, then date-check via get_project168_top.
"""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = "https://gis.uro.taipei/"


def post(name, params):
    req = urllib.request.Request(BASE + "ashx/" + name,
                                 data=urllib.parse.urlencode(params).encode(), headers=UA)
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


sections = json.loads(post("getSectionList.ashx", {"qitem": "SectionList_20", "sec": "信義區"}))
print(f"信義區 sections: {len(sections)}")

FRAGMENT = "138筆(原120筆)"     # the surviving, unambiguous part of the gazette 案名
GAZETTE_DATE = "2026/3/12"

candidates = []
for s in sections:
    landname = s["landname"]
    body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": landname,
                                          "monobuf": "0038", "sunobuf": "0000"})
    if not body.strip():
        continue
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        continue
    for r in rows:
        if FRAGMENT in r["case_name"]:
            candidates.append((landname, r))

print(f"\ncase candidates for parcel 38 matching {FRAGMENT!r}: {len(candidates)}")
for landname, r in candidates:
    detail_cid = re.search(r"case_id=(\d+)", r["details"] or "")
    cid = detail_cid.group(1) if detail_cid else ""
    print(f"   [{landname}] {r['case_id']:>10} {r['schedule']:<7} {r['case_name'][:64]}")
    if cid:
        top = post("get_project168_top.ashx", {"case_id": cid})
        try:
            t = json.loads(top)[0]
            print(f"        top.NAME={t.get('NAME')!r}  uro_chk_date={t.get('uro_chk_date')!r}  "
                  f"uro_chk_date2={t.get('uro_chk_date2')!r}  phase={t.get('phase')!r}")
            print(f"        CASE_NAME={t.get('CASE_NAME')!r}")
        except Exception as e:  # noqa: BLE001
            print("        top parse fail:", top[:120])
