import json
from pathlib import Path
from collections import Counter

with open("data/p168_all.json", encoding="utf-8") as f:
    rows = json.load(f)

print(f"Total cases: {len(rows)}")
stage_counts = Counter(r.get("stage", "") for r in rows)
for stage, cnt in stage_counts.most_common():
    print(f"  {stage!r}: {cnt}")

# In processing = any stage that is NOT 核定階段 and NOT '-'
in_process = [r for r in rows if r.get("stage") not in ("核定階段", "-")]
print(f"\nIn processing (not yet approved): {len(in_process)}\n")

for r in in_process:
    print(f"{r['case_id']} | {r['stage']} | {r['progress']} | {r['MEMO']}")
    print(f"    {r['T_name']}")

with open("data/p168_in_processing.json", "w", encoding="utf-8") as f:
    json.dump(in_process, f, ensure_ascii=False, indent=2)
print("\nWrote data/p168_in_processing.json")
