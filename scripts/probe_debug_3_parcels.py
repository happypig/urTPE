import json

with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)

targets = [
    ("大安段三小段", "260"),
    ("豐年段四小段", "479-2"),
    ("玉成段一小段", "36"),
]

print("=== Searching for section substrings ===")
for proj in data.get("projects", []):
    for node in proj.get("nodes", []):
        section = node.get("section", "")
        for t_sec, t_parcel in targets:
            if t_sec in section:
                links = node.get("links", {}).get("taipei")
                print("section contains", t_sec)
                print("  project_id =", proj.get("project_id"))
                print("  recno =", node.get("recno"), "date =", node.get("date"), "stage =", node.get("stage"))
                print("  section =", section, "parcel =", node.get("first_parcel"))
                print("  taipei links =", links)
                print()

print("=== Searching for exact parcel as first_parcel ===")
for proj in data.get("projects", []):
    for node in proj.get("nodes", []):
        parcel = node.get("first_parcel", "")
        for t_sec, t_parcel in targets:
            if parcel == t_parcel:
                print("first_parcel =", parcel)
                print("  project_id =", proj.get("project_id"))
                print("  recno =", node.get("recno"), "section =", node.get("section"))
                print()

print("=== Searching for parcel anywhere in parcels list ===")
for proj in data.get("projects", []):
    for node in proj.get("nodes", []):
        parcels = node.get("parcels", [])
        for t_sec, t_parcel in targets:
            if t_parcel in parcels:
                print("parcel", t_parcel, "in parcels list")
                print("  project_id =", proj.get("project_id"))
                print("  recno =", node.get("recno"), "section =", node.get("section"), "first_parcel =", node.get("first_parcel"))
                print()
