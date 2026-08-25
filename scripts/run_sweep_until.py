#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the targeted portal sweep NOW until a given local deadline (HH MM).

One-off operational launcher for fix-targeted-portal-matcher task 5.2: the
campaign's built-in deadline is 07:00, which stops a daytime launch instantly.
This wrapper overrides only DEADLINE_HOUR/DEADLINE_MINUTE — intervals, ledger,
cache writes and regeneration behave exactly as an overnight run.

Usage:
    python scripts/run_sweep_until.py 22 30

Single-writer rule (facts §17): nothing else may read/write data/.link_cache
while this runs. Stop = kill this process tree only.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scripts.fetch_remaining_national_portal as mod  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python scripts/run_sweep_until.py HH MM", file=sys.stderr)
        return 2
    mod.DEADLINE_HOUR = int(sys.argv[1])
    mod.DEADLINE_MINUTE = int(sys.argv[2])
    sys.argv = ["fetch_remaining_national_portal.py"]
    return mod.main()


if __name__ == "__main__":
    sys.exit(main())
