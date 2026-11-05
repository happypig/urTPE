"""D13: what schedule does the city's parcel search give the two cases now? 1 request, read-only."""
import sys
sys.path.insert(0, r"D:\project\urTPE")
from urtpe.links import _search_taipei_raw
rows = _search_taipei_raw("青年段一小段", "130", guard=False, dropped_out={},
                          anchor_name="擬訂臺北市萬華區青年段一小段130地號等3筆土地都市更新事業計畫案")
for r in rows:
    print(r.get("case_id"), r.get("schedule", ""), (r.get("case_name") or "")[:60])
