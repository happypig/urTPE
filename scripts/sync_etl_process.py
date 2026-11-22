"""Synchronise current-payload regions of docs/etl_process.html.

Usage: python scripts/sync_etl_process.py [--check]
The authored HTML and its historical examples remain the source document.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.doc_measurements import (DocSyncError, load_payload, measure_etl,
                                      sync_config, write_or_check)


def collected_test_count(root: Path) -> int:
    proc = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                          cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode:
        raise DocSyncError("pytest collection failed: " + (proc.stderr or proc.stdout)[-1600:])
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if "collected" in line:
            try:
                return int(line.split()[0])
            except ValueError:
                pass
    raise DocSyncError("pytest did not report a collected test count")


def stored_measurement_date(html: str) -> str | None:
    """The sync date the page's footer already carries, or None.

    The footer's "synchronised <date>" is a generation timestamp. documentation-dataset-sync
    permits it to differ between two runs over unchanged inputs, so `--check` reads it back
    from the page instead of comparing it with today. Before this, the check went STALE on
    the next calendar day with no fact changed (measured 2026-11-22: footer 2026-11-20), and
    post_ingest_check.py --check-only, which runs it, failed with it.
    """
    match = re.search(r'data-doc-field="footer-provenance-en"[^>]*>[^<]*?synchronised '
                      r'(\d{4}-\d{2}-\d{2})', html)
    return match.group(1) if match else None


def fields_for(doc: dict, root: Path, test_count: int | None = None,
               measurement_date: str | None = None) -> dict[str, str]:
    m = measure_etl(doc, root)
    if measurement_date:
        m["measurement_date"] = measurement_date
    tests = collected_test_count(root) if test_count is None else test_count
    values = {
        "dataset-summary-en": (f"Measured on the {m['published_date']} gazette: "
            f"<strong>{m['records']:,} records → {m['projects']} projects</strong>,\n"
            f"      {m['date_first']} → {m['date_last']}."),
        "dataset-summary-zh": (f"量測自 {m['published_date']} 公報："
            f"<strong>{m['records']:,} 筆紀錄 → {m['projects']} 個專案</strong>，\n"
            f"      {m['date_first']} → {m['date_last']}。"),
        "schema-date": m["published_date"],
        "schema-projects": str(m["projects"]), "schema-records": str(m["records"]),
        "viewer-badge": (f"{m['projects']} 個專案 / {m['records']} 筆記錄 · "
                         f"統計至 {m['published_date']}"),
        "footer-provenance-en": (f"Measured figures from the {m['published_date']} payload, "
                                 f"synchronised {m['measurement_date']}."),
        "footer-provenance-zh": (f"量測數字取自 {m['published_date']} payload，"
                                 f"於 {m['measurement_date']} 同步。"),
    }
    for name, key in [("ledger-count", "corrections"),
                      ("count-disagreements", "count_disagreements"),
                      ("flagged-nodes", "flagged_nodes"),
                      ("repeat-percent", "repeat_percent"),
                      ("links-lines", "links_lines"), ("cache-dirs", "cache_dirs")]:
        for lang in ("en", "zh"):
            values[f"{name}-{lang}"] = f"{m[key]:,}"
    for lang in ("en", "zh"):
        values[f"test-count-{lang}"] = f"{tests:,}"
    return values


def render_current(doc: dict, root: Path = ROOT, test_count: int | None = None):
    path = root / "docs" / "etl_process.html"
    source = path.read_text(encoding="utf-8")
    from scripts.doc_measurements import replace_fields
    return replace_fields(source, fields_for(doc, root, test_count))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report stale fields without writing")
    args = parser.parse_args(argv)
    try:
        doc = load_payload(ROOT / "viewer" / "projects.data.js")
        page = ROOT / "docs" / "etl_process.html"
        # Check mode compares facts. The sync date is read back from the page; a write run
        # stamps today. A page with no readable date falls back to today and reports stale.
        stored = stored_measurement_date(page.read_text(encoding="utf-8")) if args.check else None
        fields = fields_for(doc, ROOT, measurement_date=stored)
        changed = write_or_check(page, fields, args.check)
        if not args.check:
            sync_config(doc, ROOT)
    except (DocSyncError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    if args.check and changed:
        return 1
    print(f"[OK] etl_process.html: {doc['published_date']}; "
          f"{'stale' if changed else 'current' if args.check else 'updated' if changed else 'unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
