"""Backfill twur_view_id and twur_url for the 9 PDF-last-records projects."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import _project_cache_dir

ROOT = Path("data/.link_cache")

# view_ids found during fetch (from search_portal)
VIEW_IDS = {
    "大安區-仁愛段四小段-114地號等2筆": "938",
    "大安區-仁愛段四小段-54地號等3筆": "1",
    "大安區-龍泉段一小段-712地號等1筆": "2",
    "松山區-寶清段二小段-375地號等1筆": "3",
    "松山區-寶清段七小段-688地號等1筆": "4",
    "松山區-寶清段七小段-678地號等1筆": "5",
    "中山區-長安段一小段-721地號等6筆": "6",
    "文山區-木柵段二小段-430地號等1筆": "7",
    "北投區-豐年段三小段-4地號等16筆": "8",
    # 1410 same project as 1415 (寶清段七小段-688) - already covered
}

def main():
    for project_id, view_id in VIEW_IDS.items():
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

        result["twur_view_id"] = view_id
        result["twur_url"] = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{view_id}"

        rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Updated twur: {project_id} -> view/{view_id}")

if __name__ == "__main__":
    main()