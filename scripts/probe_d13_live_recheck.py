"""D13 live re-check: header, data2, data3, data4 for 11501041 and 11510008.
Read-only: 8 requests, 1 s apart, no write to .link_cache. A failure is reported, not retried."""
import sys, time, json
sys.path.insert(0, r"D:\project\urTPE")
from urtpe.links import (fetch_taipei_case_header_api, fetch_taipei_milestones_api,
                         fetch_taipei_implementation_api, fetch_taipei_rewards_api)

for cid in ("11501041", "11510008"):
    print(f"=== {cid} ===")
    for label, fn in (("header", fetch_taipei_case_header_api), ("data2 milestones", fetch_taipei_milestones_api),
                      ("data3 implementation", fetch_taipei_implementation_api), ("data4 rewards", fetch_taipei_rewards_api)):
        try:
            v = fn(cid)
            s = json.dumps(v, ensure_ascii=False)
            print(f"  {label}: {len(v or {})} keys  {s[:300]}")
        except Exception as exc:
            print(f"  {label}: ERROR {type(exc).__name__}: {exc}")
        time.sleep(1.0)
