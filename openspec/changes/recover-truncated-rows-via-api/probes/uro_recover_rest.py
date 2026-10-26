# -*- coding: utf-8 -*-
"""Recovery probe for the remaining 6 excluded units (8 units total incl. 67/79's)."""
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


# (recno, date, section, first_parcel, count-fragment of the 案名)
TARGETS = [
    (672, "2020/7/14", "振興段一小段", ("0002", "0006"), "等101筆"),
    (719, "2020/1/15", "雙連段二小段", ("0203", "0001"), "等98筆"),
    (851, "2018/12/4", "雙連段一小段", ("0197", "0000"), "等72筆"),
    (863, "2018/10/4", "漢中段二小段", ("0328", "0000"), "等110筆"),
    (930, "2017/12/12", "雙園段二小段", ("0505", "0000"), "等77筆"),
    (1131, "2014/4/25", "南港段一小段", ("0720", "0000"), "等105筆"),
]

for recno, date, sect, (mono, suno), frag in TARGETS:
    body = post("Get_updcase_list.ashx", {"qitem": "qland", "sectstr": sect,
                                          "monobuf": mono, "sunobuf": suno})
    try:
        rows = json.loads(body)
    except Exception:  # noqa: BLE001
        rows = []
    hits = [r for r in rows if frag in r["case_name"]]
    print(f"\n== 編號 {recno} ({sect} {'-'.join(x.lstrip('0') or '0' for x in (mono, suno)) if suno != '0000' else mono.lstrip('0')}), "
          f"gazette {date}, filter {frag!r}: {len(rows)} rows, {len(hits)} name hits")
    for r in hits:
        m = re.search(r"case_id=(\d+)", r["details"] or "")
        line = f"   {r['case_id']:>11} {r['schedule']:<7} {r['case_name'][:58]}"
        if m:
            try:
                t = json.loads(post("get_project168_top.ashx", {"case_id": m.group(1)}))[0]
                d1 = (t.get("uro_chk_date") or "")[:10]
                d2 = (t.get("uro_chk_date2") or "")[:10]
                want = date.replace("/", "-")
                # tolerate zero-padded day differences: 2018-12-4 vs 2018-12-04
                norm = lambda s: re.sub(r"-(\d)$", r"-0\1", s)  # noqa: E731
                ok1 = norm(d1) == norm(want)
                ok2 = norm(d2) == norm(want)
                line += f"\n        date check: uro_chk_date={d1} ({'MATCH' if ok1 else 'no'})  " \
                        f"uro_chk_date2={d2} ({'MATCH' if ok2 else 'no'})"
            except Exception as e:  # noqa: BLE001
                line += f"\n        top ERR {e}"
        print(line)
