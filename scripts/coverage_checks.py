"""Reusable read-only partition and badge checks over emitted data."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def measure(root: Path | str = ROOT) -> dict:
    """Derive partition and badge agreement from files, not pipeline memory."""
    root = Path(root)
    doc = json.loads((root / "data" / "projects.json").read_text(encoding="utf-8"))
    nodes = [n for p in doc["projects"] for n in p.get("nodes") or []]
    recnos = [n["recno"] for n in nodes]
    with (root / "data" / "clean.tsv").open(encoding="utf-8", newline="") as fh:
        clean = {int(row["recno"]) for row in csv.DictReader(fh, delimiter="\t")}
    with (root / "data" / "merged.tsv").open(encoding="utf-8", newline="") as fh:
        merged = list(csv.DictReader(fh, delimiter="\t"))
    seen: set[int] = set()
    duplicates = sorted({r for r in recnos if r in seen or seen.add(r)})
    lost = sorted(clean - set(recnos))
    extra = sorted(set(recnos) - clean)
    unbadged = [(p["project_id"], n["recno"], n.get("date", ""), n.get("case_name", ""))
                for p in doc["projects"] for n in p.get("nodes") or []
                if not (n.get("links") or {}).get("taipei")]
    flagged = sum(any("節點未能對應平台案件" in flag for flag in n.get("review_flags") or [])
                  for n in nodes)
    flagged_with_id = sum(
        bool((n.get("links") or {}).get("taipei"))
        and any("節點未能對應平台案件" in flag for flag in n.get("review_flags") or [])
        for n in nodes)
    return {
        "clean": len(clean), "nodes": len(recnos), "distinct": len(set(recnos)),
        "duplicates": duplicates, "lost": lost, "extra": extra,
        "merged_rows": len(merged), "merged_projects": len({r["project_id"] for r in merged}),
        "unbadged": unbadged, "flagged": flagged, "flagged_with_id": flagged_with_id,
        "partition_ok": not duplicates and not lost and not extra,
        "badge_ok": flagged == len(unbadged) and flagged_with_id == 0,
    }
