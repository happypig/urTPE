# -*- coding: utf-8 -*-
"""Two real nodes sharing one anchored case render in approval-date order
(fix-row-order-tiebreak-and-view-badges task 1.1).

The defect, measured live on 北投區-關渡段二小段-303地號等5筆 and reported by
the maintainer 2026-11-02: the D12 Amendment 3 row sort (allMembers) orders by
effective case_id ascending, then String(recno) — and 編號 is a newest-first
coordinate, so a newer gazette row renders ABOVE an older one whenever both
carry the same case_id. Corpus census: 39 same-case groups with differing
dates, 30 rendering newer-above-older.

The chip fixture already carries three such families — the probe renders all
three inverted today (verified before writing these tests):
254地號 1232(2012)+1039(2016) on 09811141; 614地號 1216+1098+906 on 09812231;
639地號 862(2018)+580(2021) on 10511291.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "viewer" / "chip_fixture.data.js"


def _rendered_rows(pid_part: str) -> list[str]:
    """Run the smoke harness against the fixture and capture the SVG rows
    top-to-bottom for the first project whose id contains pid_part."""
    probe = ROOT / "tests" / "fixtures" / "viewer" / "_timeline_probe.js"
    result = subprocess.run(
        ["node", str(probe), str(FIXTURE), pid_part],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return [line for line in result.stdout.splitlines() if line.strip()]


def _approval_dates_in_row_order(rows: list[str]) -> list[tuple[int, str]]:
    """(recno, ISO date) pairs in rendered top-to-bottom order."""
    out = []
    for r in rows:
        m = re.match(r"y=[\d.]+ (\d+) · (\d{4}-\d{2}-\d{2})", r)
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def test_two_real_nodes_sharing_a_case_render_chronologically():
    """The 254 shape: nodes 1232 (2012-08-27) and 1039 (2016-08-23) both anchor
    09811141 — the 2012 approval must render above the 2016 one."""
    rows = _rendered_rows("254地號")
    pairs = _approval_dates_in_row_order(rows)
    order = [recno for recno, _d in pairs]
    assert order.index(1232) < order.index(1039), (
        f"2012-08-27 (node 1232) must render above 2016-08-23 (node 1039); "
        f"got rows:\n" + "\n".join(rows))


def test_three_real_nodes_sharing_a_case_render_chronologically():
    """The 614 shape: 1216 (2013-01-02), 1098 (2015-06-16), 906 (2018-04-17)
    all anchor 09812231 — the rows must ascend by date."""
    rows = _rendered_rows("614地號")
    pairs = _approval_dates_in_row_order(rows)
    order = [recno for recno, _d in pairs]
    assert order.index(1216) < order.index(1098) < order.index(906), (
        f"rows must ascend 2013 → 2015 → 2018; got:\n" + "\n".join(rows))


def test_the_pair_on_the_second_case_also_ascends():
    """The 639 shape: 862 (2018-10-09) and 580 (2021-05-13) both anchor
    10511291 — 2018 above 2021."""
    rows = _rendered_rows("639地號")
    pairs = _approval_dates_in_row_order(rows)
    order = [recno for recno, _d in pairs]
    assert order.index(862) < order.index(580), (
        f"2018-10-09 (node 862) must render above 2021-05-13 (node 580); "
        f"got rows:\n" + "\n".join(rows))


def test_the_336_target_order_is_unchanged():
    """The distinct-case families keep the D12 interleave exactly: 453
    (2022-08-02) → 建照 → 開工 → 1 (2026-10-15), with 370 between the two
    approvals. The same-key tie-break must never fire here."""
    rows = _rendered_rows("336地號")
    joined = "\n".join(rows)
    y_2022 = next((i for i, r in enumerate(rows) if "2022-08-02" in r), None)
    y_2023 = next((i for i, r in enumerate(rows) if "2023-03-21" in r), None)
    y_jianzhao = next((i for i, r in enumerate(rows) if "建照" in r), None)
    y_kaigong = next((i for i, r in enumerate(rows) if "開工" in r), None)
    y_2026 = next((i for i, r in enumerate(rows) if "2026-10-15" in r), None)
    assert None not in (y_2022, y_2023, y_jianzhao, y_kaigong, y_2026), joined
    assert y_2022 < y_2023 < y_jianzhao < y_kaigong < y_2026, (
        "the 336 target order is 453 → 370 → 建照 → 開工 → 1; got:\n" + joined)
