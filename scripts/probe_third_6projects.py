#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from urtpe.links import _post_taipei_api

THIRD = "https://gis.uro.taipei/ashx/Get_project168_third.ashx"
TOP = "https://gis.uro.taipei/ashx/get_project168_top.ashx"

projects = {
    "中正區-河堤段四小段-263-19地號等25筆": ["10204032", "10707031"],
    "中山區-長春段二小段-775地號等3筆": ["09904301", "10612221", "09012312", "09506100", "09506102", "09904300", "09904302", "09904303", "11301261"],
    "北投區-奇岩段五小段-444地號等7筆": ["10007261", "10012261", "10012263", "10012264", "10012265"],
    "大安區-金華段四小段-513-3地號等13筆": ["08912160", "09201072", "10011041", "10011042", "10912111"],
    "大同區-圓環段一小段-103-2地號等48筆": ["09711191", "09907161", "09907271", "10012151", "10106081", "10106082", "10908241"],
    "中正區-南海段二小段-41-4地號等55筆": ["09902092", "10112121", "11103111", "11412001"],
}

out = {}
for pid, cases in projects.items():
    print("=" * 70)
    print(pid)
    out[pid] = {}
    for cid in cases:
        rec = {}
        try:
            body = _post_taipei_api(THIRD, {"case_id": cid})
            rows = json.loads(body)
            row = rows[0] if isinstance(rows, list) and rows else (rows if isinstance(rows, dict) else {})
            rec = {
                "Eng_Start_Date": row.get("Eng_Start_Date", ""),
                "Ulic_Date": row.get("Ulic_Date", ""),
                "Exe_Way": row.get("Exe_Way", ""),
            }
        except Exception as e:
            rec = {"error": str(e)}
        time.sleep(0.6)
        out[pid][cid] = rec
        print(f"  {cid}: {rec}")

Path("data/.link_cache/probe_third_6projects.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nsaved -> data/.link_cache/probe_third_6projects.json")
