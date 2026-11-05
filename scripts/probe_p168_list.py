"""Probe Get_project168.ashx pagination + transition filter, then dump all pages."""
from __future__ import annotations

import gzip
import json
import sys
from urllib import parse, request

BASE = "https://gis.uro.taipei/ashx/Get_project168.ashx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Origin": "https://gis.uro.taipei",
    "Referer": "https://gis.uro.taipei/P_project168.aspx",
}


def post(params: dict) -> bytes:
    body = parse.urlencode(params).encode("utf-8")
    req = request.Request(BASE, data=body, headers=HEADERS, method="POST")
    with request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    if resp.headers.get("Content-Encoding", "") == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def try_page(page_index: int, page_size: int = 50, transition: str | None = None):
    params = {"type": "project168", "pageIndex": str(page_index), "pageSize": str(page_size)}
    if transition is not None:
        for key in ("transition", "dlstTransition", "track", "type2", "isTransfer"):
            params2 = dict(params)
            params2[key] = transition
            try:
                raw = post(params2)
                return key, raw
            except Exception as e:
                last = e
                continue
        raise last
    return None, post(params)


def main():
    # 1. Probe page 0 without a transition filter
    print("=== Page 0, no transition filter ===")
    key, raw = try_page(0, 50)
    txt = raw.decode("utf-8", "replace")
    print(txt[:2000])
    print("...")

    # 2. Try to detect total count
    try:
        data = json.loads(txt)
        print("\nParsed JSON type:", type(data).__name__)
        if isinstance(data, dict):
            print("Parsed JSON keys:", list(data.keys()))
            print("TotalCount:", data.get("TotalCount"))
        else:
            print("list length:", len(data))
    except Exception as e:
        print("\nNot pure JSON:", e)

    # 3. Probe transition=0 (正軌) and transition=1 (轉軌)
    for t in ("0", "1"):
        print(f"\n=== Page 0, transition={t} ===")
        try:
            k, raw = try_page(0, 5, transition=t)
            print(f"used key={k}")
            print(raw.decode("utf-8", "replace")[:1500])
        except Exception as e:
            print(f"transition={t} failed: {e}")


if __name__ == "__main__":
    main()
