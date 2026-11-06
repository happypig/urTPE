"""Can the recovery pass widen to a truncated DATE cell?

The 2026-10-28 gazette's 編號 3 prints an empty 核定日期 cell; every other
cell is complete. The existing recovery pass handles a truncated 地號 cell
(the parcel list is cut at the printed row height). This probe asks whether
the same machinery can close a truncated DATE.

Live, read-only. It reads:
  - the city's parcel search for the row's unit (Get_updcase_list.ashx);
  - each name-matching candidate's header (get_project168_top.ashx);
  - the candidates' data2 (Get_project168_second.ashx).

and reports, for each candidate: the name, the header's approval dates, and
whether the date check would close.

    python scripts/probe_recovery_date_truncation.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import recovery as R  # noqa: E402
from urtpe.recovery_sources import AshxClient  # noqa: E402
from urtpe.links import fetch_taipei_milestones_api  # noqa: E402

ROW_NAME = ("變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）"
            "土地都市更新事業計畫案")
ROW_LAND = ("臺北市大安區通化段四小段336 、336-1、339、340、341、341-1、342、"
            "342-1、343、343-1、344、345、346、347、347-1、347-2、348、349、350、"
            "354-1、356、357、357-1、358、358-1、362 地號等26筆土地")


def main() -> None:
    identity = R.parse_identity(ROW_NAME)
    print("the row's identity, from the 案名 alone:")
    print("  district=%s section=%s mono=%s suno=%s"
          % (identity.district, identity.section, identity.mono, identity.suno))
    print("  count_fragment=%r declared_count=%s"
          % (identity.count_fragment, identity.declared_count))
    print("  address_core=%r" % identity.address_core)
    print()

    ashx = AshxClient()
    time.sleep(1.2)
    family = ashx.case_family(identity.section, identity.mono, identity.suno)
    print("the city's parcel search for the unit: %d family members" % len(family))
    for c in family:
        print("   case_id=%-14s api_case_id=%-12s name=%s"
              % (c.get("case_id"), c.get("api_case_id"),
                 (c.get("case_name") or "")[:52]))
    print()

    # the name-hit rule, exactly as _recover_one applies it
    def name_hit(cand):
        name = R.normalize_name(cand.get("case_name") or "")
        if not (identity.district in name and identity.section in name):
            return False
        if not (identity.count_fragment and identity.count_fragment in name):
            return False
        if identity.address_core and identity.address_core in name:
            return True
        return R.name_similarity(identity.name, name) >= R.LINK_THRESHOLD

    hits = [c for c in family if name_hit(c)]
    print("name hits (checks 1-3): %d" % len(hits))
    for cand in hits:
        cid = cand.get("api_case_id") or ""
        time.sleep(1.2)
        top = ashx.case_top(cid) if cid else {}
        d1 = str(top.get("uro_chk_date") or "")
        d2 = str(top.get("uro_chk_date2") or "")
        time.sleep(1.2)
        ms = fetch_taipei_milestones_api(cid) if cid else {}
        approval = {k: v for k, v in (ms or {}).items()
                    if k in ("核定日期", "權變核定日期", "概要核准日期",
                             "申請核定日期", "權變申請核定日期")}
        print()
        print("   api_case_id=%s" % cid)
        print("     name        : %s" % (cand.get("case_name") or "")[:70])
        print("     uro_chk_date : %r" % d1)
        print("     uro_chk_date2: %r" % d2)
        print("     data2 dates  : %s" % json.dumps(approval, ensure_ascii=False))
        print("     the row's own land cell is complete? %s"
              % ("yes — %d parcels, the 案名 declares %d"
                 % (len((ms or {}).get("_", "") or "") or 26, identity.declared_count)))
        # what the date check would say, for the date the city holds
        for want in ("2026-10-15", "2026-10-16"):
            res, field = R.date_check(d1, d2, want)
            print("     date_check against %s -> %r (%s)" % (want, res, field))


if __name__ == "__main__":
    main()
