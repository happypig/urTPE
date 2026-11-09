"""Is the cache mtime a fetch time, or a write time?

The dashboard document (§5.2) measures this: `result.json` is newer than
`view.html` for 642 of 727 caches, so the mtime says when the cache was
written and not when its data was fetched. Option C — emit the cache mtime
into the payload — is killed by that measurement.

The counts moved when the
bind-the-unplaced-by-searching-the-cell-section change refreshed 7 caches
and re-emitted the payload, so they are re-measured here.

    python scripts/probe_cache_write_vs_fetch.py

Reads file metadata. Writes nothing, reaches no network.
"""

from __future__ import annotations

import datetime
import pathlib
import statistics
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / ".link_cache"


def main() -> int:
    dirs = [d for d in CACHE.iterdir() if d.is_dir()]
    with_view = 0
    without_view = 0
    rewritten = 0
    together = 0
    result_older = 0
    lags: list[float] = []
    result_dates: Counter = Counter()
    view_dates: Counter = Counter()

    for d in dirs:
        rf = d / "result.json"
        vf = d / "view.html"
        if not rf.is_file():
            continue
        rm = rf.stat().st_mtime
        result_dates[datetime.datetime.fromtimestamp(rm).strftime("%Y-%m-%d")] += 1
        if not vf.is_file():
            without_view += 1
            continue
        with_view += 1
        vm = vf.stat().st_mtime
        view_dates[datetime.datetime.fromtimestamp(vm).strftime("%Y-%m-%d")] += 1
        if rm > vm:
            rewritten += 1
            lags.append((rm - vm) / 86400.0)
        elif rm == vm:
            together += 1
        else:
            result_older += 1

    print("cache directories: %d" % len(dirs))
    print("  with a result.json            : %d"
          % sum(result_dates.values()))
    print("  with a view.html              : %d" % with_view)
    print("  without a view.html           : %d" % without_view)
    print("  result.json NEWER than view.html (rewritten, no fetch): %d" % rewritten)
    print("  written together              : %d" % together)
    print("  result.json older             : %d" % result_older)
    if lags:
        print()
        print("the lag between view.html and result.json, in days:")
        print("   min %.1f   median %.1f   max %.1f"
              % (min(lags), statistics.median(lags), max(lags)))
    print()
    print("result.json write dates:")
    for date, n in sorted(result_dates.items(), reverse=True):
        print("   %s  %d" % (date, n))
    print()
    print("view.html write dates (top 6):")
    for date, n in sorted(view_dates.items(), reverse=True)[:6]:
        print("   %s  %d" % (date, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
