"""Fetch 階段辦理過程 (milestones) for all 54 in-processing cases.

POST https://gis.uro.taipei/ashx/Get_project168_second.ashx  case_id=<numeric>

Outputs:
    data/p168_milestones/<case_id>.json  -- raw milestone response per case
    data/p168_milestones_summary.json    -- case_id -> key dates (核定日期, etc.)
    data/p168_missing_milestones.txt     -- case_ids that returned empty/error
"""
from __future__ import annotations

import gzip
import json
import time
from pathlib import Path
from urllib import parse, request

BASE = "https://gis.uro.taipei/ashx/Get_project168_second.ashx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Origin": "https://gis.uro.taipei",
    "Referer": "https://gis.uro.taipei/P_project168.aspx",
}

OUT_DIR = Path("data/p168_milestones")
DELAY_SEC = 1.0  # politeness delay between calls


def post(case_id: str) -> bytes:
    body = parse.urlencode({"case_id": case_id}).encode("utf-8")
    req = request.Request(BASE, data=body, headers=HEADERS, method="POST")
    with request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    if resp.headers.get("Content-Encoding", "") == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def extract_key_dates(raw: list[dict]) -> dict:
    """Pull the most useful dates from the milestone list."""
    dates: dict[str, str] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        for key, val in row.items():
            if val and key not in dates:
                dates[key] = val
    return dates


def main():
    src = Path("data/p168_in_processing.json")
    if not src.exists():
        print("data/p168_in_processing.json not found. Run fetch_p168_list.py + extract_in_processing.py first.")
        return

    with src.open(encoding="utf-8") as f:
        cases = json.load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, dict] = {}
    missing: list[str] = []

    for i, case in enumerate(cases, 1):
        cid = case["case_id"]
        name = case["T_name"][:60]
        stage = case["stage"]
        print(f"[{i}/{len(cases)}] case_id={cid} stage={stage} ... {name}", end=" ")

        try:
            raw = post(cid)
            txt = raw.decode("utf-8", "replace")
            data = json.loads(txt)

            out_path = OUT_DIR / f"{cid}.json"
            out_path.write_text(txt, encoding="utf-8")

            if data:
                key_dates = extract_key_dates(data)
                summary[cid] = {
                    "stage": stage,
                    "progress": case.get("progress", ""),
                    "memo": case.get("MEMO", ""),
                    "name": case["T_name"],
                    "key_dates": key_dates,
                }
                print(f"OK ({len(key_dates)} date fields)")
            else:
                missing.append(cid)
                print("EMPTY")
        except Exception as e:
            missing.append(cid)
            print(f"ERROR: {e}")

        time.sleep(DELAY_SEC)

    with open("data/p168_milestones_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with open("data/p168_missing_milestones.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(missing))

    print(f"\nDone. {len(summary)} with milestones, {len(missing)} missing/empty.")
    print(f"Wrote data/p168_milestones_summary.json")
    print(f"Wrote data/p168_missing_milestones.txt")


if __name__ == "__main__":
    main()
