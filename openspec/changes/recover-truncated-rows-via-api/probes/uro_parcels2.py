# -*- coding: utf-8 -*-
"""Which endpoint, if any, carries the full 22-parcel list? Literal substring test."""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = "https://gis.uro.taipei/"

import csv
rows = list(csv.DictReader(open(r"C:\Users\jeffw\AppData\Local\Temp\opencode\g1021\out\merged.tsv",
                                encoding="utf-8-sig"), delimiter="\t"))
row = next(r for r in rows if r["district_land"] == "南港區" and r["section"] == "新光段二小段"
           and r["first_parcel"] == "89")
truth = row["parcels"].split("|")
print(f"ground truth ({len(truth)}): {truth}")

def post_raw(name, params):
    req = urllib.request.Request(BASE + "ashx/" + name,
                                 data=urllib.parse.urlencode(params).encode(), headers=UA)
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                  timeout=60).read().decode("utf-8", "replace")

cid = "09309221"  # the 事業計畫+權變 case, 完成成果備查
hits = {}
for name, body in [
    ("get_project168_top", post_raw("get_project168_top.ashx", {"case_id": cid})),
    ("Get_project168_second", post_raw("Get_project168_second.ashx", {"case_id": cid})),
    ("Get_project168_third", post_raw("Get_project168_third.ashx", {"case_id": cid})),
    ("Get_project168_fourth", post_raw("Get_project168_fourth.ashx", {"case_id": cid})),
    ("Get_project168_fifth", post_raw("Get_project168_fifth.ashx", {"case_id": cid})),
    ("Get_project168_First", post_raw("Get_project168_First.ashx", {"case_id": cid})),
    ("Get_project168_sixth", post_raw("Get_project168_sixth.ashx", {"case_id": cid})),
    ("Get_project168_seventhbefore", post_raw("Get_project168_seventhbefore.ashx", {"case_id": cid})),
    ("Get_project168_seventhafter", post_raw("Get_project168_seventhafter.ashx", {"case_id": cid})),
    ("Get_project168_eighth", post_raw("Get_project168_eighth.ashx", {"case_id": cid})),
    ("Get_project168_Ninth", post_raw("Get_project168_Ninth.ashx", {"case_id": cid})),
    ("Get_project168_Ninth_bottom", post_raw("Get_project168_Ninth_bottom.ashx", {"case_id": cid})),
    ("Get_project168_ten", post_raw("Get_project168_ten.ashx", {"case_id": cid})),
    ("Get_project168_release", post_raw("Get_project168_release.ashx", {"case_id": cid})),
    ("Get_Stage_plan_top", post_raw("Get_Stage_plan_top.ashx", {"case_id": cid})),
    ("Get_Stage_plan_bottom", post_raw("Get_Stage_plan_bottom.ashx", {"case_id": cid})),
    ("r_progress_detail page", get(BASE + f"r_progress_detail.aspx?case_id={cid}")),
    ("ua_frmEasyCase page", get(BASE + f"ua_frmEasyCase.aspx?case_id={cid}")),
]:
    found = [p for p in truth if p in body]
    hits[name] = (len(body), found)
    print(f"  {name:30s} {len(body):>8,} B   parcels found: {len(found)}/{len(truth)}"
          + (f"  e.g. {found[:4]}" if found else ""))

best = max(hits.items(), key=lambda kv: len(kv[1][1]))
print(f"\nbest: {best[0]} with {len(best[1][1])}/{len(truth)}")
