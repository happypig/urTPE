"""Re-probe the 3 cases on the live platform to confirm their status (D9c-1 gate).

Calls get_project168_top.ashx for each case_id and prints schedule + key dates.
"""
from __future__ import annotations

import gzip
import json
from urllib import parse, request

BASE = "https://gis.uro.taipei/ashx/get_project168_top.ashx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Origin": "https://gis.uro.taipei",
    "Referer": "https://gis.uro.taipei/P_project168.aspx",
}

CASES = [
    ("10112154", "大安區大安段三小段260地號等15筆"),
    ("10702271", "北投區豐年段四小段479-2地號等3筆"),
    ("10904071", "南港區玉成段一小段36地號1筆"),
]


def post(case_id: str) -> dict:
    body = parse.urlencode({"case_id": case_id}).encode("utf-8")
    req = request.Request(BASE, data=body, headers=HEADERS, method="POST")
    with request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8", "replace"))


def main():
    for cid, label in CASES:
        print(f"=== case_id={cid} ({label}) ===")
        try:
            data = post(cid)
            if isinstance(data, list):
                for row in data:
                    print(f"  CASE_ID={row.get('CASE_ID')}")
                    print(f"  CASE_NAME={row.get('CASE_NAME')}")
                    print(f"  NAME={row.get('NAME')}")
                    print(f"  phase={row.get('phase')}")
                    print(f"  schedule={row.get('schedule')}")
                    print(f"  uro_chk_date={row.get('uro_chk_date')}")
                    print(f"  uro_chk_date2={row.get('uro_chk_date2')}")
                    print(f"  plan_app_date={row.get('plan_app_date')}")
                    print()
            else:
                print(f"  {data}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()


if __name__ == "__main__":
    main()
