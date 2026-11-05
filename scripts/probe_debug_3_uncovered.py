import json

with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)

targets = {
    "南港區-南港段四小段-566地號等1筆": "10708311",
    "中正區-臨沂段三小段-412地號等12筆": "11410026",
    "南港區-玉成段二小段-166地號等12筆": "11412011",
}

pub_date = data.get("published_date")

for proj in data.get("projects", []):
    pid = proj.get("project_id")
    if pid in targets:
        case_id = targets[pid]
        links_t = proj.get("links", {}).get("taipei", [])
        print(f"=== Gazette project: {pid} ===")
        print(f"  Looking for platform case_id: {case_id}")
        print(f"  Gazette published_date: {pub_date}")
        print(f"  Project-level links.taipei: {links_t}")
        mt = proj.get("links", {}).get("milestones_taipei", {})
        print(f"  Project-level milestones_taipei keys (first 5): {list(mt.keys())[:5]}")
        print()
        for node in proj.get("nodes", []):
            n_links = node.get("links", {}).get("taipei", [])
            print(f"  Node recno={node.get('recno')}, date={node.get('date')}, stage={node.get('stage')}, track={node.get('track')}")
            print(f"    node links.taipei: {n_links}")
            print(f"    case_name: {node.get('case_name')[:90]}...")
            print(f"    land: {node.get('land')}")
            print(f"    parcels: {node.get('parcels')}")
            print(f"    first_parcel: {node.get('first_parcel')}")
            n_mt = node.get("links", {}).get("milestones_taipei", {})
            if n_mt:
                print(f"    node milestones_taipei keys (first 5): {list(n_mt.keys())[:5]}")
            print()
