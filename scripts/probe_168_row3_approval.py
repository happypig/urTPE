"""Does the 168 list carry the approval date for 編號 3 of the 2026-10-28 gazette?

The case: 變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）土地都市
更新事業計畫案. Its 核定日期 cell is empty in the gazette.

This probe reads the 168 list (the live fetch and the saved snapshot) and
prints every row whose 案名 names that unit, with every field — the list's
`MEMO` field carries the 核定公告 date for the approved cases.

Read-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import fetch_taipei_168_list_api  # noqa: E402

SNAPSHOT = Path(r"D:\project\urtpe-gazettes\p168_snapshots")
UNIT = "通化段四小段336"


def show(rows: list[dict], label: str) -> None:
    print("=== %s (%d rows) ===" % (label, len(rows)))
    hits = [r for r in rows if UNIT in str(r.get("T_name") or "")]
    print("rows naming %s: %d" % (UNIT, len(hits)))
    for r in hits:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    print()


def main() -> None:
    saved = json.loads((ROOT / "data" / "p168_all.json").read_text(encoding="utf-8"))
    show(saved, "the saved snapshot (data/p168_all.json, 2026-11-05)")

    for snap in sorted(SNAPSHOT.glob("p168-*.json")):
        show(json.loads(snap.read_text(encoding="utf-8")),
             "the poller's snapshot %s" % snap.name)

    show(fetch_taipei_168_list_api(), "the live list (2026-11-06)")


if __name__ == "__main__":
    main()
