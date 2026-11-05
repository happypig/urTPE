"""Check the permit witness (links.permit) and the disagreement flags.

The permit adapter attaches the building authority's 使用執照摘要 record as a
third witness. The flag names a disagreement; it never repairs.
"""
import json
from pathlib import Path

TARGETS = [
    "松山區-寶清段一小段-57-13地號等1筆",
    "大安區-金華段一小段-719地號等1筆",
]

with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)

print("=== links.permit + review_flags on the two projects ===")
for proj in data.get("projects", []):
    if proj.get("project_id") not in TARGETS:
        continue
    links = proj.get("links", {})
    print(f"\n### {proj['project_id']}")
    print(f"  links.permit = {json.dumps(links.get('permit'), ensure_ascii=False)}")
    print(f"  milestones_taipei 使照核發日期 = {links.get('milestones_taipei', {}).get('使照核發日期')}")
    print(f"  milestones_national 使用核發日期 = {links.get('milestones_national', {}).get('使用核發日期')}")
    print(f"  national milestone labels = {sorted(links.get('milestones_national', {}).keys())}")
    print(f"  twur = {links.get('twur')}")
    for node in proj.get("nodes", []):
        if node.get("review_flags"):
            print(f"  node recno={node.get('recno')} flags:")
            for f in node["review_flags"]:
                print(f"      {f}")

print()
print("=== corpus: how many projects carry links.permit, and the flag texts ===")
permit_n = 0
flag_counter = {}
with_permit_no_date = []
for proj in data.get("projects", []):
    links = proj.get("links", {})
    if links.get("permit"):
        permit_n += 1
        p = links["permit"]
        mt = links.get("milestones_taipei", {}).get("使照核發日期", "")
        mn = links.get("milestones_national", {}).get("使用核發日期", "")
        if not mt and not mn:
            with_permit_no_date.append(proj["project_id"])
    for node in proj.get("nodes", []):
        for f in node.get("review_flags", []) or []:
            if "執照" in f or "使照" in f or "許可" in f:
                key = f.split(":")[0][:60]
                flag_counter[key] = flag_counter.get(key, 0) + 1

print(f"  projects with links.permit: {permit_n}")
print(f"  projects with a permit but NO portal date: {len(with_permit_no_date)}")
for pid in with_permit_no_date[:10]:
    print(f"      {pid}")
print("  permit-related flag prefixes:")
for k, v in sorted(flag_counter.items(), key=lambda kv: -kv[1]):
    print(f"      {v:4d}  {k}")

print()
print("=== permit_review_flags source ===")
import sys
sys.path.insert(0, str(Path.cwd()))
from urtpe.links import permit_review_flags
import inspect
print(inspect.getsource(permit_review_flags))
