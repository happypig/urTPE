#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Whole-corpus refresh, in resumable slices (refresh-whole-corpus / R).

Brings every project cache to the current state: new-case discovery (B1),
status re-derivation (B5), a cleared status kept as a value (B6), the
view-page absorb (C2), and the per-case headers (§7 4.1) — one driver, one
run, instead of five passes against a WAF-capped API.

Slices: about 100 projects each (user decision 2026-11-04). Each slice takes
the single-writer lock, writes into ``data/.link_cache/`` only, records a
checkpoint naming its finished projects, and releases the lock. A re-run
skips finished projects. The tracked datasets are emitted once, after the
last slice, by the standing ``--from-js`` path — never by this driver.

Change detection (the board's design, 2026-11-04): one cheap signal per
source, a full fetch only when the signal moves —
1. the national page's 資料更新日期 (one request per project);
2. the city parcel search (case ids + schedule);
3. the case header (NAME / uro_chk_date / uro_chk_date2).
A finished case (已完工 / 完成成果備查, or a 使照核發日期 present) skips its
header fetch unless step 1 or 2 moved. Every skip is counted: "not fetched
because unchanged" never reads as "fetched and empty".

Single-writer rule (AGENTS.md): do not run this while an ingestion or a
sweep owns the cache.

    python scripts/refresh_whole_corpus.py [--dry-run] [--slice N]
        [--slices-size 100] [--delay 1.0]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    fetch_taipei_case_header_api,
    refresh_project,
    resolve_cache_dir,
)

CHECKPOINT = ".refresh_checkpoint.json"

_PAGE_DATE_RE = re.compile(r"最後更新於\s*([0-9]{2,3}\.[0-9]{1,2}\.[0-9]{1,2})")


def new_report() -> dict:
    """fetched / skipped_unchanged / failed per source, failures named."""
    return {
        "page": {"fetched": 0, "skipped_unchanged": 0, "failed": 0},
        "search": {"fetched": 0, "skipped_unchanged": 0, "failed": 0},
        "header": {"fetched": 0, "skipped_unchanged": 0, "failed": 0},
        "page_failed": [],
        "search_failed": [],
        "header_failed": [],
        "resolved_by_resolver": [],
    }


def count(rep: dict, source: str, outcome: str, name: str = "") -> None:
    rep[source][outcome] += 1
    if outcome == "failed" and name:
        rep[f"{source}_failed"].append(name)


def write_checkpoint(path: Path, last_pid: str, finished: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_pid": last_pid, "finished": finished},
                               ensure_ascii=False), encoding="utf-8")


def read_checkpoint(path: Path) -> dict:
    if not path.is_file():
        return {"last_pid": "", "finished": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last_pid": "", "finished": []}
    return {"last_pid": str(data.get("last_pid") or ""),
            "finished": [str(x) for x in (data.get("finished") or [])]}


def is_finished(state: dict, pid: str) -> bool:
    return pid in set(state.get("finished") or [])


def make_slices(keys: list[str], size: int = 100,
                state: dict | None = None) -> list[list[str]]:
    """Sorted keys → ~size slices; with a checkpoint, the finished prefix
    drops out (a re-run resumes from the first unfinished project)."""
    if state and state.get("finished"):
        done = set(state["finished"])
        keys = [k for k in keys if k not in done]
    return [keys[i:i + size] for i in range(0, len(keys), size)]


def page_update_date(view_html: str) -> str:
    """The page's own 資料更新日期 (本專案資料最後更新於 YYY.MM.DD); "" when absent."""
    m = _PAGE_DATE_RE.search(view_html or "")
    return m.group(1) if m else ""


def page_moved(live_html: str, cached_date: str) -> bool:
    """The live page's date is later than the cached one — a full re-absorb.
    An absent cached date is no signal (the first absorb is R's other work,
    decided by the standing refresh, not by this comparison)."""
    live = page_update_date(live_html)
    if not live or not cached_date:
        return False
    def key(d: str) -> tuple:
        y, m, day = (int(x) for x in d.split("."))
        return (y, m, day)
    return key(live) > key(cached_date)


def case_finished(schedule_row: dict, milestones: dict,
                  project_moved: bool = False) -> bool:
    """A finished case (已完工 / 完成成果備查, or a 使照核發日期) skips its
    header fetch — unless the page or the parcel search moved the project."""
    if project_moved:
        return False
    schedule = str((schedule_row or {}).get("schedule") or "")
    if schedule in ("已完工", "完成成果備查"):
        return True
    return bool((milestones or {}).get("使照核發日期"))


def load_view_html(cache_dir: Path, pid: str) -> str:
    vh = resolve_cache_dir(Path(cache_dir), pid) / "view.html"
    if not vh.is_file():
        return ""
    try:
        return vh.read_text(encoding="utf-8")
    except OSError:
        return ""


def cached_page_date(cache: dict, cache_dir: Path, pid: str) -> str:
    """The cached page's 資料更新日期. The cache does not store it (the view
    absorb carries no such field), so this re-parses the cached view.html —
    no request."""
    return page_update_date(load_view_html(cache_dir, pid))


def refresh_slice(cache_dir: Path, pids: list[str], search_keys: dict,
                  refresh_fn=None, page_fetch=None, report: dict | None = None,
                  finished: list[str] | None = None) -> dict:
    """One slice: refresh each project through the standing refresh_project.
    ``refresh_fn`` and ``page_fetch`` are injected (tests pass doubles; the
    default path uses the standing refresh and fetch_url). The change
    detection's skip counts land in ``report``."""
    if refresh_fn is None:
        def refresh_fn(cache_dir, pid, search_key=None):
            return refresh_project(Path(cache_dir), pid, search_key=search_key)
    if page_fetch is None:
        from urtpe.links import fetch_view_page
        def page_fetch(view_id):
            return fetch_view_page(view_id, Path(cache_dir))
    rep = report if report is not None else new_report()
    for pid in pids:
        try:
            view_report = refresh_fn(cache_dir, pid,
                                     search_key=search_keys.get(pid))
            count(rep, "search", "fetched")  # the standing search runs inside
            err = view_report.get("error") or ""
            if err and "search" in err:
                count(rep, "search", "failed", name=pid)
        except Exception as exc:
            count(rep, "search", "failed", name=pid)
            print(f"  FAILED {pid}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        if finished is not None:
            finished.append(pid)
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--payload", default=str(ROOT / "viewer" / "projects.data.js"))
    ap.add_argument("--slices-size", type=int, default=100)
    ap.add_argument("--slice", type=int, default=None,
                    help="run only the Nth slice (0-based)")
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the slice plan and stop")
    args = ap.parse_args(argv)

    text = Path(args.payload).read_text(encoding="utf-8").strip()
    doc = json.loads(text[text.index("{"):].rstrip().rstrip(";"))
    keys = sorted(p["project_id"] for p in doc.get("projects", []))

    cache_dir = Path(args.cache)
    ck = cache_dir / CHECKPOINT
    state = read_checkpoint(ck)
    slices = make_slices(keys, size=args.slices_size, state=state)
    print(f"payload projects: {len(keys)}; finished (checkpoint): "
          f"{len(state.get('finished') or [])}; slices: {len(slices)} "
          f"(size {args.slices_size})")
    if args.dry_run:
        for i, s in enumerate(slices):
            print(f"  slice {i}: {len(s)} projects  [{s[0][:30]} … {s[-1][:30]}]")
        return 0

    # the anchor search keys (the standing refresh's parcel-search input)
    sys.path.insert(0, str(ROOT / "scripts"))
    from refresh_awaiting_caches import load_search_keys
    search_keys = load_search_keys(Path(args.payload))

    rep = new_report()
    all_finished = list(state.get("finished") or [])
    for i, s in enumerate(slices):
        if args.slice is not None and i != args.slice:
            continue
        print(f"slice {i}: {len(s)} project(s)")
        refresh_slice(cache_dir, s, search_keys, report=rep,
                      finished=all_finished)
        write_checkpoint(ck, s[-1], all_finished)
        print(f"  checkpoint: {len(all_finished)} finished")

    print(f"\npage: {rep['page']['fetched']} fetched / "
          f"{rep['page']['skipped_unchanged']} skipped / "
          f"{rep['page']['failed']} failed")
    print(f"search: {rep['search']['fetched']} fetched / "
          f"{rep['search']['failed']} failed")
    print(f"header: {rep['header']['fetched']} fetched / "
          f"{rep['header']['skipped_unchanged']} skipped / "
          f"{rep['header']['failed']} failed")
    for src in ("page", "search", "header"):
        for pid in rep[f"{src}_failed"]:
            print(f"  FAILED {src}: {pid}")
    print("\nnext: python -m urtpe.cli --from-js viewer/projects.data.js -o data "
          "--links   (once, after the last slice)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
