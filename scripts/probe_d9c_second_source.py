"""D9c-2a: the second id source, measured offline. Read-only.

Reports:
  - the nodes that carry the unplaced flag, and the projects they belong to
  - which of those projects' sections the 168 list names a case for
  - whether that case's header confirms it (a live check, read-only)

The list is the city's own register of the 168 fast-track programme's cases
(466 rows). A row's `T_name` names the case, so the list can be scoped by the
project's section before a header request is spent.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LIST = ROOT / "data" / "p168_all.json"


def main():
    d = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    rows = json.loads(LIST.read_text(encoding="utf-8"))
    by_section: dict[str, list[dict]] = {}
    for r in rows:
        name = str(r.get("T_name") or "")
        m = __import__("re").search(r"([一-鿿A-Za-z]+段[一二三四五六七八九十]*小段|[一-鿿A-Za-z]+段)", name)
        if m:
            by_section.setdefault(m.group(1), []).append(r)

    unplaced = []
    for p in d["projects"]:
        for n in p["nodes"]:
            for f in (n.get("review_flags") or []):
                if "節點未能對應平台案件" in f:
                    unplaced.append((p["project_id"], n["recno"], n.get("section", ""),
                                     n.get("district", ""), f))
    print("nodes carrying the unplaced flag:", len(unplaced))
    print("projects:", len(set(x[0] for x in unplaced)))
    print()
    print("=== the unplaced nodes, and what the 168 list holds for their section ===")
    for pid, recno, section, district, flag in unplaced:
        cands = by_section.get(section, [])
        names = ", ".join("%s(%s)" % (c.get("case_id"), (c.get("T_name") or "")[:34])
                          for c in cands)
        print("%-40s recno=%-6s section=%-14s" % (pid, recno, section))
        print("    list rows for that section: %s" % (names or "(none)"))
        print("    flag: %s" % flag[:110])


if __name__ == "__main__":
    main()
