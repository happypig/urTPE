import sys
import json
import re

sys.stdout.reconfigure(encoding="utf-8")

content = open("viewer/projects.data.js", encoding="utf-8").read()
m = re.search(r"window\.PROJECTS\s*=\s*(\{.*?\});", content, re.DOTALL)
data = json.loads(m.group(1))
p = next(p for p in data["projects"] if p["project_id"] == "南港區-南港段一小段-520-2地號等18筆")

neighbors = {"522": "09407110", "467": "09407113", "403-2": "09509071", "561": "09607130"}

for n in p["nodes"]:
    print("recno", n["recno"], n["date"], n["stage"])
    print("  land:", n.get("land"))
    print("  parcels:", n.get("parcels"))
    parcels = set(n.get("parcels") or [])
    for first, cid in neighbors.items():
        base = first.split("-")[0]
        hit = first in parcels or base in parcels
        print("   contains", first, "?", hit)
