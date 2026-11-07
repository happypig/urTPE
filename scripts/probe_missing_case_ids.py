"""Can the 7 unplaced projects find their city case id? Read-only, live.

問題一 of docs/coverage-report.html names 7 projects that carry no case id at
all. Their 11 nodes carry the flag 節點未能對應平台案件. Two shapes cause it:

  A. the case is filed under a DIFFERENT parcel than the one the gazette
     prints first (臨沂段三小段412 — the search for 412 finds nothing, but the
     unit's other parcels may carry the case);
  B. the case is filed under a DIFFERENT section string than the gazette's
     案名 (河堤五小段 in the 案名, 河堤段五小段 in the 地號 cell — and in the
     city's own case name).

This probe asks the city's parcel search directly, one request per (section,
parcel) pair, and prints what comes back. It writes nothing — not to
data/.link_cache, not anywhere. It only reads the city.

    python scripts/probe_missing_case_ids.py [target]

Live: the city's search endpoint. >= 1.2 s between requests. The request
carries a generic browser User-Agent and no contact address.
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

SEARCH_API = "https://gis.uro.taipei/ashx/Get_updcase_list.ashx"
TOP_API = "https://gis.uro.taipei/ashx/get_project168_top.ashx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Connection": "keep-alive",
}

# every parcel of each unit, from clean.tsv
LAND = {
    "臨沂段三小段": "412|412-1|413|413-1|414|414-1|415|415-1|418|419|420|421",
    "河堤五小段": "399|400|403",
    "吳興一小段": ("330|331|332|333|334|335|336|337|338|339|340|341|342|343|344|345|"
                   "346|347|348|349|350|351|352|353|354|355|356|357|358|359|360|354-3|"
                   "361|361-1|362|391|440|441|442|442-1|446|448|451"),
    "吳興段二小段": "163-2|247",
    "復興段一小段": "3|3-2|7|7-1|20-3",
    "懷生段一小段": "928",
    "萬華段一小段": ("519-2|522|523|524|525|526|527|528|529|530|531|532|533|534|535|"
                      "536|537|538|539|540|548|549|550|551|552|553|564|565|566|567|568|569|596"),
}

# the section strings to try, per unit. The first is the gazette's 案名
# section; the others are the forms the city is known to index under.
SECTIONS = {
    "臨沂段三小段": ["臨沂段三小段"],
    "河堤五小段": ["河堤段五小段", "河堤五小段"],
    "吳興一小段": ["吳興段一小段", "吳興一小段"],
    "吳興段二小段": ["吳興段二小段"],
    "復興段一小段": ["復興段一小段"],
    "懷生段一小段": ["懷生段一小段"],
    "萬華段一小段": ["萬大段一小段", "萬華段一小段"],
}

REQUESTED: list[tuple[str, str, str]] = []


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


def search(section: str, parcel: str) -> list[dict]:
    """One parcel search. The city's own form is a 4-digit 主號 plus 0000."""
    mono, _, suno = parcel.partition("-")
    body = _post(SEARCH_API, {
        "qitem": "qland", "sectstr": section,
        "monobuf": mono.zfill(4), "sunobuf": (suno or "0").zfill(4),
    })
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return []
    out = []
    for r in rows or ():
        details = r.get("details") or ""
        out.append({
            "case_id": details.split("case_id=")[1].split("&")[0]
            if "case_id=" in details else "",
            "case_name": r.get("case_name") or "",
            "schedule": r.get("schedule") or "",
        })
    return out


def header(case_id: str) -> dict:
    body = _post(TOP_API, {"case_id": case_id})
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return rows[0] if isinstance(rows, list) and rows else {}


def probe_section(unit: str, section: str) -> list[dict]:
    """Every parcel of the unit under one section string."""
    found = []
    for parcel in LAND[unit].split("|"):
        time.sleep(1.2)
        hits = search(section, parcel)
        mark = ""
        if hits:
            mark = "  <== %d hit(s)" % len(hits)
            found.append({"parcel": parcel, "section": section, "hits": hits})
        print("    %-14s %-8s -> %d%s" % (section, parcel, len(hits), mark))
        for h in hits:
            print("        %-10s %-6s %s" % (h["case_id"], h["schedule"], h["case_name"][:70]))
    return found


def main() -> int:
    want = sys.argv[1] if len(sys.argv) > 1 else None
    units = [want] if want else list(SECTIONS)
    for unit in units:
        print()
        print("=" * 78)
        print("%s" % unit)
        print("=" * 78)
        for section in SECTIONS[unit]:
            probe_section(unit, section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
