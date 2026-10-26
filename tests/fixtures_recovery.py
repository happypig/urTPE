# -*- coding: utf-8 -*-
"""Shared fixtures for the truncated-row recovery tests.

Two kinds of fixture live here:

* Recorded responses, captured live from the city's APIs on 2026-10-26 by
  ``probes/capture_recordings.py`` (task 2.8/2.9's "offline fixtures + recorded
  responses"). ``recorded_candidates`` assembles them into the candidate dicts
  the pure matcher consumes, exactly as ``urtpe.recovery_sources`` would.
* The acceptance gazette: a synthetic ruled-table PDF whose 16 truncated rows
  carry the real 案名 and the real surviving 地號 fragments of the 2026-10-15
  gazette's 15 excluded rows plus one real residual row (編號 100 of the
  2026-08-11 gazette), so the flagged end-to-end run exercises recovery against
  the recorded responses.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tests.gazette_fixtures import write_gazette

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "recovery"


def _load(name):
    with open(FIXTURE_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


_FAMILIES = None
_TOPS = None
_CANDIDATES = None


def families() -> dict:
    global _FAMILIES
    if _FAMILIES is None:
        _FAMILIES = _load("ashx_families.json")
    return _FAMILIES


def tops() -> dict:
    global _TOPS
    if _TOPS is None:
        _TOPS = _load("ashx_tops.json")
    return _TOPS


def geoserver_candidates() -> dict:
    global _CANDIDATES
    if _CANDIDATES is None:
        _CANDIDATES = _load("geoserver_candidates.json")
    return _CANDIDATES


def recorded_candidates(family_key: str) -> list[dict]:
    """Candidate dicts for one unit, built from the recorded family + top bodies.

    Mirrors what ``urtpe.recovery_sources.AshxClient`` returns: name checks run on
    the family row's ``case_name``; the dates come from the member's recorded
    ``get_project168_top`` body. A family member without a recorded top keeps
    empty dates (the matcher then refuses it on check 4).
    """
    out = []
    for row in json.loads(families()[family_key]):
        m = re.search(r"case_id=(\d+)", row.get("details") or "")
        api_id = m.group(1) if m else ""
        top = {}
        if api_id and api_id in tops():
            body = json.loads(tops()[api_id])
            top = body[0] if isinstance(body, list) and body else {}
        out.append({
            "case_id": str(row.get("case_id") or ""),
            "api_case_id": api_id,
            "schedule": str(row.get("schedule") or ""),
            "case_name": str(row.get("case_name") or ""),
            "uro_chk_date": str(top.get("uro_chk_date") or ""),
            "uro_chk_date2": str(top.get("uro_chk_date2") or ""),
        })
    return out


# ---------------------------------------------------------------------------
# The acceptance gazette
# ---------------------------------------------------------------------------

# The 2026-10-15 gazette's 15 excluded rows, verbatim 案名 and (where the unit's
# list is GIS-completable) the verbatim surviving 地號 fragment. Rows whose unit
# is numeric-form carry a short fragment — their identity rides on the 案名, and
# their lists stay partial regardless of the fragment's length.
LONG = 150.0  # a row band tall enough for a ~700-char fragment at 7pt


FRAGMENT_67 = (
    "臺北市信義區虎林段四小段38、41、45、46、47、48、49、50、51、52、53、54、55、55-1、55-2、55-3、55-4、55-5、55-6"
    "、55-7、55-8、55-9、55-10、55-11、55-12、55-13、55-14、55-15、55-16、56、57、58、59、60、61、62、63、64、65、66、67、67"
    "-1、68、69、71、71-1、71-2、71-3、71-4、71-5、71-6、71-7、71-8、71-9、71-10、71-11、71-12、71-13、71-14、71-15、71-16、"
    "71-17、72、73、74、74-1、75、76、77、77-1、77-2、78、79、80、81、81-1、81-2、82、82-1、83、83-1、83-2、83-3、83-4、83-5"
    "、83-6、83-7、83-8、83-9、83-10、83-11、84、86、88、90、90-1、93、93-1、93-2、93-3、93-4、93-5、93-6、93-7、93-8、93-9"
    "、93-10、93-11、93-12、93-13、93-14、93-15、93-16、"
)
FRAGMENT_79 = (
    "臺北市松山區美仁段二小段694、695、695-3、695-4、696、696-1、696-2、697、697-1、697-2、698、699、699-1、699-2、699-3、700、702、703、"
    "704、705、706、707、708、708-1、708-2、709、709-1、709-2、710、710-1、711、711-1、712、713、713-1、714、714-1、"
    "715、715-1、716、716-1、717、717-1、717-2、718、78-1、719、719-2、719-3、719-5、719-6、719-7、719-8、719-9、"
    "719-10、735、735-1、735-2、735-3、735-5、735-6、736、736-1、736-2、737、737-1、738、738-1、739、739-1、740、740-1、"
)

# (fixture recno, real 編號, date, district, 案名, surviving 地號 fragment)
TRUNCATED_ROWS = [
    (1, 67, "2026/3/12", "信義區",
     "變更(第二次)臺北市信義區虎林段四小段38地號等138筆(原120筆)土地都市更新事業計畫案", FRAGMENT_67),
    (2, 79, "2026/1/14", "松山區",
     "變更臺北市松山區美仁段二小段694地號等74筆(原54筆)土地都市更新事業計畫及擬訂權利變換計畫案", FRAGMENT_79),
    (3, 570, "2021/7/20", "信義區",
     "變更臺北市信義區虎林段四小段38地號等138筆(原120筆)土地都市更新事業計畫案", FRAGMENT_67),
    (4, 672, "2020/7/14", "北投區",
     "擬訂臺北市北投區振興段一小段2-6地號等101筆土地都市更新事業計畫案",
     "臺北市北投區振興段一小段2-6、2-12、2-17、2-18、297、297-2、297-4、297-5、297-6、297-7、297-8、"),
    (5, 719, "2020/1/15", "大同區",
     "變更臺北市大同區雙連段二小段203-1地號等98筆土地都市更新事業計畫案",
     "臺北市大同區雙連段二小段203-1、203-2、203-6、203-7、203-8、231-1、231-2、232-1、233、233-1、233-3、233-4、"),
    (6, 796, "2019/5/28", "信義區",
     "擬訂臺北市信義區虎林段四小段38地號等138筆(原120筆)土地都市更新事業計畫案", FRAGMENT_67),
    (7, 851, "2018/12/4", "大同區",
     "變更(第三次)臺北市大同區雙連段一小段197地號等72筆土地都市更新權利變換計畫案",
     "臺北市大同區雙連段一小段197、198、199、200、201、202、203、204、205、206、207、208、208-1、209、210、210-1、"),
    (8, 863, "2018/10/4", "萬華區",
     "變更(第三次)臺北市萬華區漢中段二小段328地號等110筆土地都市更新權利變換計畫案",
     "臺北市萬華區漢中段二小段328、328-1、329、329-1、330、331、332、333、334、335、336、337、337-1、338、338-1、"),
    (9, 902, "2018/5/3", "萬華區",
     "變更(第二次)臺北市萬華區漢中段二小段328地號等110筆土地都市更新權利變換計畫案",
     "臺北市萬華區漢中段二小段328、328-1、329、329-1、330、331、332、333、334、335、336、337、337-1、338、338-1、"),
    (10, 912, "2018/3/27", "大同區",
     "變更(第二次)臺北市大同區雙連段一小段197地號等72筆土地都市更新權利變換計畫案(含釐正圖冊)",
     "臺北市大同區雙連段一小段197、198、199、200、201、202、203、204、205、206、207、208、208-1、209、210、210-1、"),
    (11, 919, "2018/2/8", "大同區",
     "擬訂臺北市大同區雙連段二小段203-1地號等98筆土地都市更新事業計畫案",
     "臺北市大同區雙連段二小段203-1、203-2、203-6、203-7、203-8、231-1、231-2、232-1、233、233-1、233-3、233-4、"),
    (12, 930, "2017/12/12", "萬華區",
     "變更(第二次)臺北市萬華區雙園段二小段505地號等77筆土地都市更新權利變換計畫案",
     "臺北市萬華區雙園段二小段505、506、507、508、509、510、511-1、512、513、514、514-1、514-2、515、516、516-1、"),
    (13, 944, "2017/11/14", "萬華區",
     "變更臺北市萬華區漢中段二小段328地號等110筆土地都市更新事業計畫及權利變換計畫案",
     "臺北市萬華區漢中段二小段328、328-1、329、329-1、330、331、332、333、334、335、336、337、337-1、338、338-1、"),
    (14, 997, "2017/3/16", "大同區",
     "變更臺北市大同區雙連段一小段197地號等72筆土地都市更新權利變換計畫案",
     "臺北市大同區雙連段一小段197、198、199、200、201、202、203、204、205、206、207、208、208-1、209、210、210-1、"),
    (15, 1131, "2014/4/25", "南港區",
     "擬訂臺北市南港區南港段一小段720地號等105筆土地都市更新事業計畫案",
     "臺北市南港區南港段一小段710-3、710-4、716、717、718-2、719、720、720-1、720-2、720-3、720-4、"),
]

# The real residual: 編號 100 of 核定案件-2026-08-11.pdf — its family (recorded
# under 南港段一小段|0561|0000) holds no case carrying its declared-count
# fragment, so the recovery pass must leave it excluded and named.
RESIDUAL_ROW = (16, "2025/7/15", "南港區",
                "擬訂臺北市南港區南港段一小段561地號1筆(原5筆)土地都市更新事業計畫案",
                "臺北市南港區南港段一小段561、562、")

# Filler approvals: small complete rows, each in its own unit, dated below the
# oldest recovered row (2014-04-25) so the flagged run stays cleanly descending.
FILLER_ROWS = [
    (17, "2013/6/20", "中山區",
     "擬訂臺北市中山區中山段一小段254地號等13筆土地都市更新事業計畫案",
     "臺北市中山區中山段一小段254、255、256、261、262、263、264、265、266、267、268、269、270地號等13筆土地"),
    (18, "2012/11/8", "大安區",
     "變更臺北市大安區學府段二小段118地號等4筆土地都市更新權利變換計畫案",
     "臺北市大安區學府段二小段118、119、120、121地號等4筆土地"),
    (19, "2011/9/13", "士林區",
     "擬訂臺北市士林區福德段一小段32地號等6筆土地都市更新事業計畫案",
     "臺北市士林區福德段一小段32、33、34、35、36、37地號等6筆土地"),
    (20, "2010/12/2", "中正區",
     "變更臺北市中正區永昌段三小段159地號等3筆土地都市更新權利變換計畫案",
     "臺北市中正區永昌段三小段159、161、162地號等3筆土地"),
    (21, "2009/7/30", "萬華區",
     "擬訂臺北市萬華區西園段二小段100地號等9筆土地都市更新事業計畫案",
     "臺北市萬華區西園段二小段100、101、102、103、104、105、106、107、108地號等9筆土地"),
    (22, "2008/5/15", "北投區",
     "變更臺北市北投區立農段五小段163-2地號等4筆土地都市更新權利變換計畫案",
     "臺北市北投區立農段五小段163-2、171-2、172、173地號等4筆土地"),
    (23, "2006/10/4", "信義區",
     "擬訂臺北市信義區黎忠段五小段66地號等2筆土地都市更新事業計畫案",
     "臺北市信義區黎忠段五小段66、67地號等2筆土地"),
    (24, "2002/3/21", "大同區",
     "變更臺北市大同區延平段二小段31地號等3筆土地都市更新權利變換計畫案",
     "臺北市大同區延平段二小段31、32、33地號等3筆土地"),
]

IMPLEMENTER = "測試建設股份有限公司"
PLANNER = "測試都市規劃股份有限公司"

ALL_ROWS = [(r[0], r[2], r[3], r[4], r[5], IMPLEMENTER, PLANNER)
            for r in TRUNCATED_ROWS] + \
           [(*RESIDUAL_ROW, IMPLEMENTER, PLANNER)] + \
           [(*r, IMPLEMENTER, PLANNER) for r in FILLER_ROWS]

# Tall bands for the fragment rows so each verbatim fragment survives intact.
ROW_HEIGHTS = {row[0] - 1: LONG for row in ALL_ROWS if row[0] <= 16}


def build_fixture_pdf(path: str) -> str:
    """Write the acceptance gazette; deterministically, for golden comparison."""
    return write_gazette(
        path, ALL_ROWS,
        published="統計至2026年10月15日",
        calendar="roc",  # dates pass through as written (Gregorian strings)
        rows_per_page=3,  # three 150pt bands fill a page; more would fall off it
        row_heights=ROW_HEIGHTS,
    )


def family_key_for(name: str) -> str:
    """The recorded family key for a fixture row, from its own 案名."""
    m = re.search(r"臺北市\w+區(\S+?段(?:[一二三四五]小段)?)(\d+)(?:-(\d+))?地號", name)
    sect = m.group(1)
    mono = m.group(2).zfill(4)
    suno = (m.group(3) or "0").zfill(4)
    return f"{sect}|{mono}|{suno}"
