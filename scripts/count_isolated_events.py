"""§6.8 isolated-construction-event counter (pre/post fix-comparison).

Counts construction milestone slot values (建照核發日期 / 開工日期 /
使照核發日期) in an emitted projects document whose winning case
(milestones_source) does NOT date-anchor to any node of the same family —
the "isolated render" bucket — plus double-displayed values (same label +
winning case + date rendering in ≥2 family graphs).

Usage: python scripts/count_isolated_events.py [viewer/projects.data.js]
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CONSTRUCTION_LABELS = ("建照核發日期", "開工日期", "使照核發日期")


def load_doc(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(re.sub(r"^window\.PROJECTS\s*=", "", text.strip()).rstrip(";"))


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "viewer/projects.data.js"
    doc = load_doc(path)
    total = 0
    isolated = 0
    iso_families: set[str] = set()
    render_map: dict[tuple, set[str]] = defaultdict(set)

    for pg in doc["projects"]:
        links = pg.get("links", {})
        source = links.get("milestones_source", {})
        milestones = links.get("milestones_taipei", {})
        anchored: set[str] = set()
        for node in pg.get("nodes", []):
            anchored.update((node.get("links") or {}).get("taipei") or [])
        for label in CONSTRUCTION_LABELS:
            if label not in milestones:
                continue
            total += 1
            case_id = source.get(label, "")
            if case_id not in anchored:
                isolated += 1
                iso_families.add(pg["project_id"])
            render_map[(label, case_id, milestones[label])].add(pg["project_id"])

    double_display = sum(1 for fams in render_map.values() if len(fams) >= 2)
    print(f"document: {path}")
    print(f"construction slot values: {total}")
    print(f"isolated (winner case anchors to no node of its family): {isolated} "
          f"across {len(iso_families)} families")
    print(f"double-displayed slot values (same label+case+date, >=2 graphs): {double_display}")


if __name__ == "__main__":
    main()
