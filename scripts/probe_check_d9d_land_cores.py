"""Check whether the D9d ledger entries' land cores match a gazette record.

A `confirm_merge` entry names the second record by its content key. If no
gazette record carries that land core, the entry is unmatched and does nothing.
"""
import json

with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)

targets = [
    ("大安段三小段", "260", "10112154"),
    ("豐年段四小段", "479-2", "10702271"),
    ("玉成段一小段", "36", "10904071"),
]

# Build a set of every land string the gazette holds, and every (section, parcel)
for proj in data.get("projects", []):
    for node in proj.get("nodes", []):
        section = node.get("section", "")
        parcels = node.get("parcels", [])
        land = node.get("land", "")
        for t_sec, t_parcel, cid in targets:
            if t_sec in section:
                print(f"=== gazette project: {proj.get('project_id')} ===")
                print(f"  case under test: {cid} (platform says {t_sec} / parcel {t_parcel})")
                print(f"  recno={node.get('recno')} date={node.get('date')} stage={node.get('stage')}")
                print(f"  land (raw) = {land}")
                print(f"  parcels ({len(parcels)}) = {parcels}")
                print(f"  first_parcel = {node.get('first_parcel')}  land_count = {node.get('land_count')}")
                has = t_parcel in parcels
                print(f"  --> parcel {t_parcel} in this project's parcels? {has}")
                print(f"  --> links.taipei = {node.get('links', {}).get('taipei')}")
                print()
