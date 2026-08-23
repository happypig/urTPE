"""Backfill the 10 PDF-last-records portal milestones into project caches."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import _project_cache_dir

ROOT = Path("data/.link_cache")

# Milestones extracted (ROC dates as returned by parser)
MILESTONES = {
    "大安區-仁愛段四小段-114地號等2筆": {
        "事業計畫核定日期": "89.09.29"
    },
    "大安區-仁愛段四小段-54地號等3筆": {
        "事業計畫申請日期": "90.03.20",
        "事業計畫核定日期": "91.03.21",
        "使用核發日期": "94.06.03"
    },
    "大安區-龍泉段一小段-712地號等1筆": {
        "事業計畫申請日期": "90.05.12",
        "事業計畫核定日期": "91.06.06",
        "第一次變更事業計畫核定日期": "93.08.20",
        "使用核發日期": "94.11.04"
    },
    "松山區-寶清段二小段-375地號等1筆": {
        "事業計畫申請日期": "90.12.31",
        "事業計畫核定日期": "91.07.17",
        "權利變換計畫申請日期": "90.12.31",
        "權利變換計畫核定日期": "91.07.17",
        "使用核發日期": "93.09.07"
    },
    "松山區-寶清段七小段-688地號等1筆": {
        "事業計畫申請日期": "91.03.26",
        "事業計畫核定日期": "91.08.21",
        "權利變換計畫申請日期": "91.03.26",
        "權利變換計畫核定日期": "91.08.21",
        "第一次變更事業計畫核定日期": "92.11.03",
        "第一次變更權利變換計畫核定日期": "92.11.03",
        "使用核發日期": "98.07.27"
    },
    "松山區-寶清段七小段-678地號等1筆": {
        "事業計畫申請日期": "91.06.10",
        "事業計畫核定日期": "91.12.31",
        "權利變換計畫申請日期": "91.06.10",
        "權利變換計畫核定日期": "91.12.31",
        "第一次變更權利變換計畫核定日期": "96.02.27",
        "使用核發日期": "95.04.24"
    },
    "中山區-長安段一小段-721地號等6筆": {
        "事業計畫申請日期": "91.07.24",
        "事業計畫核定日期": "92.03.03",
        "使用核發日期": "93.03.30"
    },
    "文山區-木柵段二小段-430地號等1筆": {
        "事業計畫申請日期": "91.08.21",
        "事業計畫核定日期": "92.04.03",
        "權利變換計畫申請日期": "91.08.21",
        "權利變換計畫核定日期": "92.04.03"
    },
    "北投區-豐年段三小段-4地號等16筆": {
        "事業計畫申請日期": "91.07.24",
        "事業計畫核定日期": "92.06.20",
        "權利變換計畫申請日期": "91.07.24",
        "權利變換計畫核定日期": "92.06.20",
        "使用核發日期": "94.07.28"
    },
    # recno 1410 same project as 1415 (松山區-寶清段七小段-688地號等1筆) - merge
}

def main():
    for project_id, milestones in MILESTONES.items():
        cache_dir = _project_cache_dir(ROOT, project_id)
        rj = cache_dir / "result.json"
        if not rj.exists():
            print(f"SKIP (no cache): {project_id}")
            continue
        try:
            result = json.loads(rj.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  ERROR reading cache: {project_id}")
            continue

        # Merge milestones (national only; preserve existing taipei milestones)
        existing = result.get("national_milestones", {})
        merged = {**existing, **milestones}  # new wins for any overlap
        result["national_milestones"] = merged

        # Ensure twur_view_id exists if missing (these have view_ids 1-8)
        # We don't have view_id mapping here but result already has twur_view_id from earlier runs
        # If missing, it'll be set on next discovery run

        rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Updated: {project_id} | milestones: {len(merged)}")

if __name__ == "__main__":
    main()