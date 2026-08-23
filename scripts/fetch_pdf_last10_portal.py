"""Fetch national portal view pages for the last 10 PDF records (recno 1410-1419)."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import (
    fetch_url,
    extract_tuidui_history_from_view,
    extract_case_ids_from_view,
    SEARCH_URL,
    BROWSER_HEADERS,
)
import urllib.parse
import urllib.request

ROOT = Path("data/.link_cache")

# The 10 records: recno, project_id, section, parcel
TARGETS = [
    {"recno": 1419, "project_id": "大安區-仁愛段四小段-114地號等2筆", "section": "仁愛段四小段", "parcel": "114"},
    {"recno": 1418, "project_id": "大安區-仁愛段四小段-54地號等3筆", "section": "仁愛段四小段", "parcel": "54"},
    {"recno": 1417, "project_id": "大安區-龍泉段一小段-712地號等1筆", "section": "龍泉段一小段", "parcel": "712"},
    {"recno": 1416, "project_id": "松山區-寶清段二小段-375地號等1筆", "section": "寶清段二小段", "parcel": "375"},
    {"recno": 1415, "project_id": "松山區-寶清段七小段-688地號等1筆", "section": "寶清段七小段", "parcel": "688"},
    {"recno": 1414, "project_id": "松山區-寶清段七小段-678地號等1筆", "section": "寶清段七小段", "parcel": "678"},
    {"recno": 1413, "project_id": "中山區-長安段一小段-721地號等6筆", "section": "長安段一小段", "parcel": "721"},
    {"recno": 1412, "project_id": "文山區-木柵段二小段-430地號等1筆", "section": "木柵段二小段", "parcel": "430"},
    {"recno": 1411, "project_id": "北投區-豐年段三小段-4地號等16筆", "section": "豐年段三小段", "parcel": "4"},
    {"recno": 1410, "project_id": "松山區-寶清段七小段-688地號等1筆", "section": "寶清段七小段", "parcel": "688"},
]

def search_portal(section: str, parcel: str) -> list[str]:
    """Search portal list page with title keyword, return view_ids."""
    # Use the list page search: ?title=關鍵字
    keyword = f"{section}{parcel}"
    params = {"title": keyword, "page": "1"}
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        html = fetch_url(url, None, True)
    except Exception as e:
        print(f"  search failed: {e}")
        return []
    # Parse view_ids from results table
    ids = []
    m = re.findall(r'/view/(\d+)', html)
    for vid in m:
        if vid not in ids:
            ids.append(vid)
    return ids

def fetch_and_parse_view(view_id: str, project_id: str):
    url = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{view_id}"
    try:
        html = fetch_url(url, None, True)
    except Exception as e:
        print(f"  fetch view/{view_id} failed: {e}")
        return None, None
    milestones = extract_tuidui_history_from_view(html)
    city_ids = extract_case_ids_from_view(html)
    return milestones, city_ids

def main():
    for i, t in enumerate(TARGETS):
        print(f"\n[{i+1}/10] recno {t['recno']} | {t['project_id']} | section={t['section']} parcel={t['parcel']}")

        # Search portal
        vids = search_portal(t['section'], t['parcel'])
        if not vids:
            print("  no view_id found")
            continue
        print(f"  found view_ids: {vids}")

        for vid in vids[:3]:  # try first few matches
            print(f"  trying view/{vid}...")
            milestones, city_ids = fetch_and_parse_view(vid, t['project_id'])
            if milestones is None:
                continue
            if milestones:
                print(f"  milestones: {len(milestones)}")
                for k, v in milestones.items():
                    print(f"    {k} = {v}")
                if "使用核發日期" in milestones:
                    print(f"  *** 使用核發日期 = {milestones['使用核發日期']} ***")
            if city_ids:
                print(f"  city case_ids: {city_ids}")

        if i < len(TARGETS) - 1:
            print("  sleeping 180s...")
            time.sleep(180)

if __name__ == "__main__":
    main()