"""Confirm a candidate case id against the node it would bind. Read-only, live.

A parcel search returns the cases touching a parcel; it does not prove which
one the node is. The acceptance test is the resolver's own: the case's 案名
must match the node's 案名, and the case's approval date must match the
node's date.

This reads the header (核定日期 / 權變核定日期) and the stage milestones of
each candidate and prints the comparison side by side.

Writes nothing — not to data/.link_cache, not anywhere. It only reads the
city.

    python scripts/probe_confirm_candidates.py

Live: the city's header and stage endpoints. >= 1.2 s between requests. The
request carries a generic browser User-Agent and no contact address.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TOP_API = "https://gis.uro.taipei/ashx/get_project168_top.ashx"
STAGE_API = "https://gis.uro.taipei/ashx/Get_project168_second.ashx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Connection": "keep-alive",
}

# recno -> (node date, node 案名, candidate case ids found by the parcel search)
CANDIDATES = {
    122: ("2025/07/22",
          "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案",
          ["10305021", "11410026"]),
    204: ("2024/10/29",
          "變更(第三次)臺北市中正區河堤五小段399地號等3筆土地都市更新權利變換計畫案",
          ["10601031", "10601032", "11005051", "11005052", "11005053"]),
    551: ("2021/09/15",
          "擬訂臺北市信義區吳興一小段330地號等43筆土地都市更新事業計畫及權利變換計畫案",
          ["10611051", "09907111"]),
    1433: ("2004/06/24",
           "擬訂臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫案",
           ["09102220", "09102222"]),
    1333: ("2009/06/10",
           "變更臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及擬訂權利變換計畫案",
           ["09102221"]),
    706: ("2020/03/19",
          "變更(第二次)臺北市信義區吳興街二期整宅地區都市更新事業計畫及變更權利變換計畫案",
          ["10405235", "10103231"]),
    1081: ("2015/11/04",
           "擬訂臺北市大安區復興段一小段3地號等5筆土地都市更新事業計畫案",
           ["10111171", "09909292", "09904101"]),
    669: ("2020/07/30",
          "變更臺北市大安區復興段一小段3地號等2筆(原5筆)土地都市更新事業計畫案",
          ["10111171", "09909292", "09904101"]),
    993: ("2017/04/18",
          "擬訂臺北市萬華區萬華段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案",
          ["10011301", "09809101"]),
    483: ("2022/04/19",
          "變更臺北市萬華區萬華段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案",
          ["10903061", "10903062", "10903063"]),
}


def _post(url: str, params: dict) -> str:
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if raw[:2] == b"\x1f\x8b":
            import gzip
            import io
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return raw.decode("utf-8", errors="replace")


def header(case_id: str) -> dict:
    try:
        rows = json.loads(_post(TOP_API, {"case_id": case_id}))
    except Exception as exc:
        return {"_error": type(exc).__name__}
    return rows[0] if isinstance(rows, list) and rows else {}


def milestones(case_id: str) -> dict:
    try:
        rows = json.loads(_post(STAGE_API, {"case_id": case_id}))
    except Exception:
        return {}
    out = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            for field, label in (("uro_apply_date", "申請日期"),
                                 ("uro_plan_chk_date", "核定日期"),
                                 ("uro_chk_date", "核定日期"),
                                 ("uro_chk_date2", "權變核定日期"),
                                 ("uro_exch_chk_date", "權變核定日期")):
                val = row.get(field)
                if val and label not in out:
                    out[label] = str(val).split("T")[0]
    return out


def iso(date: str) -> str:
    """A date as YYYY-MM-DD, from either the city's ISO form or the
    gazette's own M/D/YYYY form. A date the city gives in ROC form
    (114.07.22) is converted; anything else is returned as it came."""
    s = str(date or "").strip()
    if not s:
        return ""
    if "T" in s:
        s = s.split("T")[0]
    if "/" in s:
        y, m, d = (int(x) for x in s.replace("/", "-").split("-"))
        return "%04d-%02d-%02d" % (y, m, d)
    if "." in s:
        parts = s.split(".")
        if len(parts) == 3:
            roc, m, d = (int(x) for x in parts)
            return "%04d-%02d-%02d" % (roc + 1911, m, d)
    return s


def main() -> int:
    for recno in sorted(CANDIDATES):
        date, name, cands = CANDIDATES[recno]
        print()
        print("=" * 78)
        print("recno %-5s %s" % (recno, date))
        print("  node 案名 %s" % name)
        print("=" * 78)
        for cid in cands:
            time.sleep(1.2)
            hdr = header(cid)
            if hdr.get("_error"):
                print("  %-10s (read failed: %s)" % (cid, hdr["_error"]))
                continue
            time.sleep(1.2)
            ms = milestones(cid)
            case_name = str(hdr.get("CASE_NAME", "") or "").strip()
            chk = hdr.get("uro_chk_date", "") or ""
            chk2 = hdr.get("uro_chk_date2", "") or ""
            dates = [d for d in (chk, chk2) if d]
            hit = iso(date) in [iso(d) for d in dates if d]
            print("  %-10s %s" % (cid, case_name[:62]))
            print("             核定 %s | 權變核定 %s | 狀態 %s"
                  % (chk, chk2, hdr.get("URO_STATUS", "") or hdr.get("STATUS", "")))
            if ms:
                print("             milestones %s"
                      % json.dumps(ms, ensure_ascii=False))
            print("             node date %s -> %s"
                  % (date, "DATE MATCHES" if hit else "no date match"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
