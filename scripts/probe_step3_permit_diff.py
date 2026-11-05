"""D9g step 3: the permit-witness effect. Read-only.

Compares the emitted `links.permit` before and after the D10 change and
reports:
  - how many projects' witness moved
  - how many became ambiguous (no single permit)
  - how many still show a witness whose date differs from the city's 使照
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    before = load(ROOT / "data" / "_projects_before_step2.json")
    after = load(ROOT / "data" / "projects.json")
    b = {p["project_id"]: p for p in before["projects"]}
    a = {p["project_id"]: p for p in after["projects"]}

    moved, became_amb, became_single, dropped = [], [], [], []
    wrong_before = wrong_after = 0
    for pid, bp in b.items():
        ap = a.get(pid)
        if ap is None:
            continue
        bperm = (bp.get("links") or {}).get("permit")
        aperm = (ap.get("links") or {}).get("permit")
        if bperm == aperm:
            continue
        if aperm is None:
            dropped.append(pid)
        elif aperm.get("ambiguous"):
            became_amb.append(pid)
        elif bperm and bperm.get("ambiguous"):
            became_single.append(pid)
        else:
            moved.append((pid, bperm.get("permit_no"), aperm.get("permit_no")))

    print("projects whose permit entry changed:", len(moved) + len(became_amb)
          + len(became_single) + len(dropped))
    print("   the witness moved to another permit:", len(moved))
    print("   became ambiguous (no single permit):", len(became_amb))
    print("   became a single permit (was ambiguous):", len(became_single))
    print("   the permit entry was dropped:", len(dropped))
    print()
    print("the moved witnesses:")
    for pid, old, new in moved:
        print("   %-46s %s -> %s" % (pid, old, new))
    print()
    print("the ambiguous ones:")
    for pid in became_amb:
        aperm = (a[pid].get("links") or {}).get("permit")
        print("   %-46s %s" % (pid, ", ".join((aperm or {}).get("permits") or [])))

    # the city's 使照 vs the witness's date
    def wrong(doc):
        n = 0
        for p in doc["projects"]:
            links = p.get("links") or {}
            perm = links.get("permit") or {}
            if not perm.get("permit_no"):
                continue
            city = (links.get("milestones_taipei") or {}).get("使照核發日期", "")
            if not city:
                continue
            c = city.replace("/", "-")
            parts = c.split("-")
            if len(parts) == 3:
                c = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            if perm.get("date") and perm["date"] != c:
                n += 1
        return n

    print()
    print("projects whose witness date differs from the city's 使照:")
    print("   before:", wrong(before))
    print("   after: ", wrong(after))


if __name__ == "__main__":
    main()
