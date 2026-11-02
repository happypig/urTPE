# -*- coding: utf-8 -*-
"""The 國 badge renders on view-verified nodes (fix-row-order-tiebreak-and-view-badges
task 1.6).

The maintainer's report: view/621 (北投區-關渡段二小段-303's national page)
names cases 10803151 and 10105152 in its 相關連結 block — the portal asserts
the pairing — yet only the 現況 node links the national page today
(viewer/app.js `is_current` rule). Node 829 (anchored 10105152) carries no path
to the page that names its case.

The fixture (view_badge_fixture.data.js) carries the 303 shape: twur view/621,
view_verified_case_ids [10803151, 10105152], nodes 829 (10105152, 2019-02-14),
669 (10803151, 2020-07-28, NOT view-verified in the fixture), 5 (11505020,
2026-09-30, 現況). Node 5's case is deliberately not view-verified, so the
現況 rule and the view-verified rule are pinned separately; a second fixture
project (北投區-立農段一小段-566-2地號等32筆 shape) covers the both-ways
dedup: its 現況 node anchors a view-verified case and must render one 國.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "viewer" / "view_badge_fixture.data.js"


def _probe_lines() -> list[str]:
    probe = ROOT / "tests" / "fixtures" / "viewer" / "_timeline_probe.js"
    result = subprocess.run(
        ["node", str(probe), str(FIXTURE), "關渡段二小段-303", "badges"],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return [line for line in result.stdout.splitlines() if line.strip()]


def _node_y_by_recno(lines: list[str]) -> dict[int, float]:
    """recno -> rendered y, from the row lines (y=<y> <recno> · <date> ...)."""
    out = {}
    for line in lines:
        m = re.match(r"y=([\d.]+) (\d+) · \d{4}-\d{2}-\d{2}", line)
        if m and " BADGE " not in line:
            out[int(m.group(2))] = float(m.group(1))
    return out


def _badges_by_y(lines: list[str]) -> dict[float, list[tuple[str, str]]]:
    """y -> [(class, destination)] for each BADGE line."""
    out: dict[float, list[tuple[str, str]]] = {}
    for line in lines:
        if " BADGE " not in line:
            continue
        y_part, rest = line[2:].split(" BADGE ", 1)
        cls, dest, _title = rest.split(" ", 2)
        out.setdefault(float(y_part), []).append((cls, dest))
    return out


def _national_at(badges_by_y: dict[float, list[tuple[str, str]]],
                 y: float) -> list[str]:
    return [dest for cls, dest in badges_by_y.get(y, []) if cls == "national"]


def test_a_view_verified_node_carries_the_national_badge():
    """Node 829 anchors 10105152, which view/621 names — it must carry the 國
    badge opening the project's national page."""
    lines = _probe_lines()
    y829 = _node_y_by_recno(lines)[829]
    national = _national_at(_badges_by_y(lines), y829)
    assert national == ["view/621"], (
        f"node 829 (10105152, view-verified) must carry exactly one 國 badge "
        f"to view/621; got {national}")


def test_a_non_view_verified_node_gains_no_national_badge():
    """The 奇岩 contrast project: node 444 anchors 10012273 — NOT in its
    view_verified list (the page names 10012274, a different case) and not
    現況 — so it must carry no 國 badge: the pairing is asserted by the
    portal, not inferred from sharing the project."""
    probe = ROOT / "tests" / "fixtures" / "viewer" / "_timeline_probe.js"
    result = subprocess.run(
        ["node", str(probe), str(FIXTURE), "奇岩段三小段-1-1", "badges"],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    badges = _badges_by_y(lines)
    national = [dest for entries in badges.values()
                for cls, dest in entries if cls == "national"]
    assert national == [], (
        f"a node whose case the page does not name must carry no 國 badge; "
        f"got {badges}")


def test_the_current_node_keeps_its_national_badge():
    """Node 5 (2026-09-30) is 現況 — its 國 badge is the existing rule,
    unchanged by this change."""
    lines = _probe_lines()
    y5 = _node_y_by_recno(lines)[5]
    national = _national_at(_badges_by_y(lines), y5)
    assert national == ["view/621"], (
        f"the 現況 node must keep exactly one 國 badge; got {national}")


def test_a_node_qualifying_both_ways_renders_one_badge():
    """The both-ways node: 現況 whose case IS view-verified (the 566-2 shape,
    second fixture project). One 國 badge, not two."""
    probe = ROOT / "tests" / "fixtures" / "viewer" / "_timeline_probe.js"
    result = subprocess.run(
        ["node", str(probe), str(FIXTURE), "566-2地號", "badges"],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    ys = _node_y_by_recno(lines)
    current_recno = next(r for r, _y in ys.items())
    # the fixture's 現況 node anchors a view-verified case — its y must carry
    # exactly one 國 badge
    badges = _badges_by_y(lines)
    y_cur = ys[current_recno]
    national = _national_at(badges, y_cur)
    assert national == ["view/566"], (
        f"the 現況+view-verified node must render exactly one 國 badge; "
        f"got {national}")
