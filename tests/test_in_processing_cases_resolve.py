# -*- coding: utf-8 -*-
"""Every in-processing case id resolves in the dataset (D9e).

The 168 list's in-processing cases (`專案審查階段`, `審議階段`, `報核-公展階段`,
`聽證階段`) are the cases awaiting a decision. Measured 2026-11-05: **54 of
54** resolve — 52 in a node's `links.taipei`, all 54 in the project-level
`links.taipei`, 0 in neither. The node-level figure is 53 since the
bind-the-unplaced-by-searching-the-cell-section re-emit (2026-11-09); the
project-level and the "none" figures are unchanged.

The measurement is locked in here, offline: no network, no cache. The list of
54 comes from `data/p168_in_processing.json`, the cross-reference snapshot the
D9 probe wrote.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

IN_PROCESSING = ROOT / "data" / "p168_in_processing.json"
DATASET = ROOT / "data" / "projects.json"

# the stages the city writes for a case that is still in process
IN_PROCESSING_STAGES = ("專案審查階段", "審議階段", "報核-公展階段", "聽證階段")


def _cases() -> list[dict]:
    if not IN_PROCESSING.exists():
        pytest.skip("the 168 cross-reference snapshot is not present")
    rows = json.loads(IN_PROCESSING.read_text(encoding="utf-8"))
    return [r for r in rows if r.get("stage") in IN_PROCESSING_STAGES]


def _dataset() -> dict:
    if not DATASET.exists():
        pytest.skip("the dataset is not present")
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_the_snapshot_holds_54_in_processing_cases():
    """The measurement's population — if the snapshot changes, the count below
    is read from it, not asserted."""
    cases = _cases()
    assert cases, "the snapshot holds no in-processing case"
    assert len(cases) == 54, (
        f"the measured population was 54 in-processing cases, got {len(cases)}")


def test_every_in_processing_case_resolves_in_the_dataset():
    """Each of the 54 appears in some project's `links.taipei` — at the node
    level or the project level. 0 in neither (measured 2026-11-05)."""
    cases = _cases()
    doc = _dataset()

    node_level: set[str] = set()
    project_level: set[str] = set()
    for p in doc["projects"]:
        links = p.get("links") or {}
        project_level.update(links.get("taipei") or [])
        for n in p.get("nodes") or []:
            node_level.update((n.get("links") or {}).get("taipei") or [])

    missing = [c["case_id"] for c in cases
               if c["case_id"] not in node_level
               and c["case_id"] not in project_level]
    assert not missing, (
        "these in-processing cases resolve nowhere: %s" % ", ".join(missing))


def test_most_in_processing_cases_bind_at_the_node_level():
    """The node-level binding is what the viewer draws. 53 of the 54 bound
    there; the other one is project-level only.

    The count was 52 until the bind-the-unplaced-by-searching-the-cell-section
    re-emit (2026-11-09): the 萬華 project's node 483 gained the case
    10903061, which the 168 list names and which the city had filed under the
    地號 cell's form 萬大段一小段. The project-level binding already carried it;
    the node-level binding is what the viewer draws."""
    cases = _cases()
    doc = _dataset()

    node_level: set[str] = set()
    for p in doc["projects"]:
        for n in p.get("nodes") or []:
            node_level.update((n.get("links") or {}).get("taipei") or [])

    bound = [c["case_id"] for c in cases if c["case_id"] in node_level]
    assert len(bound) == 53, (
        f"53 of the 54 bind at the node level, got {len(bound)}")
