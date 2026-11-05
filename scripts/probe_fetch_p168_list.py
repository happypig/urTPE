"""Fetch the full P_project168 case list from gis.uro.taipei.

Usage (PowerShell):
    C:\Python314\python.exe scripts/fetch_p168_list.py

Outputs:
    data/p168_all.json      -- 顯示所有168案件 (no transition filter)
    data/p168_正軌.json     -- transition=0
    data/p168_轉軌.json     -- transition=1
    data/p168_summary.txt   -- distinct stage values + counts per file

Each row: case_id, T_name, stage, progress, reason, COMPLETION_RATE, MEMO
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from urllib import parse, request
from collections import Counter

BASE = "https://gis.uro.taipei/ashx/Get_project168.ashx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Origin": "https://gis.uro.taipei",
    "Referer": "https://gis.uro.taipei/P_project168.aspx",
}

OUT_DIR = Path("data")
PAGE_SIZE = 50


def post(params: dict) -> bytes:
    body = parse.urlencode(params).encode("utf-8")
    req = request.Request(BASE, data=body, headers=HEADERS, method="POST")
    with request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    if resp.headers.get("Content-Encoding", "") == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def fetch_page(page_index: int, page_size: int, transition: str | None) -> list[dict]:
    params = {"type": "project168", "pageIndex": str(page_index), "pageSize": str(page_size)}
    if transition is not None:
        params["transition"] = transition
    raw = post(params)
    return json.loads(raw.decode("utf-8", "replace"))


def fetch_all(transition: str | None, label: str) -> list[dict]:
    all_rows: list[dict] = []
    page = 0
    total_count = None
    while True:
        rows = fetch_page(page, PAGE_SIZE, transition)
        if not rows:
            break
        # TotalCount is repeated on every row
        if total_count is None:
            total_count = rows[0].get("TotalCount")
            print(f"[{label}] TotalCount reported: {total_count}")
        all_rows.extend(rows)
        print(f"[{label}] page {page}: {len(rows)} rows (cumulative {len(all_rows)})")
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return all_rows, total_count


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    views = [
        (None, "all", "p168_all.json"),
        ("0", "正軌", "p168_正軌.json"),
        ("1", "轉軌", "p168_轉軌.json"),
    ]

    summaries: list[str] = []
    for transition, label, fname in views:
        print(f"\n===== Fetching {label} ({'no filter' if transition is None else f'transition={transition}'}) =====")
        rows, total_count = fetch_all(transition, label)
        print(f"[{label}] total fetched: {len(rows)}")

        # Dedup by case_id (TotalCount repeats on each row but rows are unique cases)
        by_id = {r["case_id"]: r for r in rows}
        print(f"[{label}] unique case_ids: {len(by_id)}")

        out_path = OUT_DIR / fname
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(list(by_id.values()), f, ensure_ascii=False, indent=2)
        print(f"[{label}] wrote {out_path}")

        # Stage distribution
        stage_counts = Counter(r.get("stage", "") for r in by_id.values())
        summaries.append(f"--- {label} ({'no filter' if transition is None else f'transition={transition}'}): {len(by_id)} cases ---")
        for stage, cnt in stage_counts.most_common():
            summaries.append(f"    {stage!r}: {cnt}")
        summaries.append("")

    summary_path = OUT_DIR / "p168_summary.txt"
    summary_path.write_text("\n".join(summaries), encoding="utf-8")
    print(f"\nWrote summary to {summary_path}")
    print("\n".join(summaries))


if __name__ == "__main__":
    main()
