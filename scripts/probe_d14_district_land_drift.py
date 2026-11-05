"""D14 check: district_land of recnos 926/928/382/153 now vs at 1517300. Read-only."""
import json, subprocess
want = {926, 928, 382, 153}

def scan(doc):
    out = {}
    for p in doc["projects"]:
        for n in p.get("nodes", []):
            if n.get("recno") in want:
                out[n["recno"]] = (n.get("district_land"), n.get("district"), (n.get("land") or "")[:20])
    return out

now = json.load(open(r"D:\project\urTPE\data\projects.json", encoding="utf-8"))
old = json.loads(subprocess.run(["git", "-C", r"D:\project\urTPE", "show", "1517300:data/projects.json"],
                                capture_output=True).stdout.decode("utf-8"))
a, b = scan(old), scan(now)
for r in sorted(want):
    print(r, "1517300:", a.get(r), " now:", b.get(r))
