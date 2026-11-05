"""D9c-2 probe: does the city's parcel search return the sibling case ids now?

Two projects lack a sibling case id in `links.taipei` and in their caches:
  南港區-南港段四小段-566地號等1筆   -> 10708311 (cache holds 10708312)
  南港區-玉成段二小段-166地號等12筆  -> 11412011 (cache holds 11412012 etc.)

Runs the guarded search (what discovery uses) and the unguarded search, so a
miss can be placed: not returned by the city, or returned and then guarded out.
Four requests in total. Read-only: writes nothing to data/.link_cache.

    python scripts/probe_sibling_search.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import _search_taipei_raw  # noqa: E402

PROBES = [
    ("南港段四小段", "566", "10708311", "擬訂臺北市南港區南港段四小段566地號(原391地號)等6筆土地都市更新事業計畫案"),
    ("玉成段二小段", "166", "11412011", "擬訂臺北市南港區玉成段二小段166地號等12筆土地都市更新事業計畫案"),
]

for section, parcel, want, anchor in PROBES:
    print(f"=== {section} / {parcel}  (looking for {want}) ===")
    for guard in (True, False):
        dropped: dict = {}
        try:
            rows = _search_taipei_raw(section, parcel, guard=guard,
                                      dropped_out=dropped, anchor_name=anchor)
        except Exception as exc:  # report, never retry past a failure
            print(f"  guard={guard}: ERROR {type(exc).__name__}: {exc}")
            continue
        ids = [r.get("case_id") for r in rows]
        print(f"  guard={guard}: {len(rows)} rows; target returned: {want in ids}")
        for r in rows:
            mark = "  <== target" if r.get("case_id") == want else ""
            print(f"    {r.get('case_id')}  {r.get('schedule', '')}  {r.get('case_name', '')[:70]}{mark}")
        if dropped:
            print(f"  guard dropped: {dropped}")
    print()
