"""BDD tests for virtual-node ordering + chain edges (D12, add-virtual-node-ordering-and-chain).

Harness: the pure helpers are marked in viewer/app.js between D12-BEGIN/END
comments; this test extracts them and evaluates the scenarios under node.
Structural precedence assertions live in test_viewer_labels.py (task 1.1).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parents[1] / "viewer" / "app.js"


def _helpers_source() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    m = re.search(r"// D12-BEGIN.*?\n(.*?)// D12-END", src, re.S)
    assert m, "app.js must carry the D12 helper block (effectiveCaseKey/compareClusterMembers/virtualChainPairs)"
    return m.group(1)


def _run_scenario(script: str) -> dict:
    js = (
        _helpers_source()
        + "\nconst fixtures = "
        + json.dumps(json.loads(script))
        + ";\n"
        + "console.log(JSON.stringify(runScenarios(fixtures)));"
    )
    out = subprocess.run(
        ["node", "-e", js], capture_output=True, text=True, encoding="utf-8",
        cwd=str(APP_JS.parent),
    )
    assert out.returncode == 0, f"node failed: {out.stderr[:400]}"
    return json.loads(out.stdout.strip().splitlines()[-1])


def _make(member, virtual=False, cid="", anchored=()):
    m = dict(member)
    m["virtual"] = virtual
    if virtual:
        m["case_id"] = cid
        m["recno"] = "v" + cid
        m["links"] = {"taipei": [cid]}
    else:
        m["links"] = {"taipei": list(anchored)}
    return m


class TestClusterOrdering:
    """Task 1.2 — effective case_id ascending; real compared via anchored case."""

    def test_attempt_twins_order_by_case_id(self):
        members = [
            _make({"stage": "擬訂", "date": "2010-09-21", "track": "事業概要", "case_name": "擬訂…概要案B"}, virtual=True, cid="10201171"),
            _make({"stage": "擬訂", "date": "2010-09-21", "track": "事業概要", "case_name": "擬訂…概要案A"}, virtual=True, cid="09902261"),
        ]
        out = _run_scenario(json.dumps({"cluster": {"stage": "擬訂", "members": members}}))
        ids = [m["case_id"] for m in out["ordered"][0]]
        assert ids == ["09902261", "10201171"]

    def test_earlier_virtual_attempt_precedes_later_real_approval(self):
        members = [
            _make({"stage": "擬訂", "date": "2009-08-27", "track": "事業計畫", "case_name": "擬訂…計畫案(gazette)", "recno": 1219},
                  anchored=["09811141"]),
            _make({"stage": "擬訂", "date": "2009-08-27", "track": "事業計畫", "case_name": "擬訂…計畫案(withdrawn 095 attempt)"},
                  virtual=True, cid="09506200"),
        ]
        out = _run_scenario(json.dumps({"cluster": {"stage": "擬訂", "members": members}}))
        row = out["ordered"][0]
        assert row[0]["virtual"] is True and row[0]["case_id"] == "09506200"
        assert row[1]["virtual"] is False

    def test_case_less_real_node_sorts_first(self):
        members = [
            _make({"stage": "擬訂", "date": "2025-12-09", "track": "事業概要", "case_name": "擬訂…概要案", "recno": 65}),
            _make({"stage": "擬訂", "date": "2025-12-09", "track": "事業概要", "case_name": "擬訂…概要案"}, virtual=True, cid="11207021"),
        ]
        out = _run_scenario(json.dumps({"cluster": {"stage": "擬訂", "members": members}}))
        row = out["ordered"][0]
        assert row[0]["virtual"] is False  # empty key first


class TestChainEdges:
    """Task 1.3 — virtual chain edges: within cluster, cross-stage never, real↔real never."""

    def test_attempt_pair_chained(self):
        # D4b (viewer-deadend-and-filters): the original example pair
        # (吉林1021 09902261 已失效 → 10201171) no longer chains — no chain
        # edge starts at a dead end. A live pair still chains.
        members = [
            _make({"stage": "擬訂", "date": "2010-09-21"}, virtual=True, cid="10201171"),
            _make({"stage": "擬訂", "date": "2011-05-01"}, virtual=True, cid="10402261"),
        ]
        out = _run_scenario(json.dumps({"clusters": [{"stage": "擬訂", "members": members}]}))
        pairs = out["chainPairs"]
        assert len(pairs) == 1
        assert {pairs[0][0]["case_id"], pairs[0][1]["case_id"]} == {"10201171", "10402261"}

    def test_chain_edge_never_starts_at_a_dead_end(self):
        # D4b: 09902261 已失效 → 10201171 (吉林1021) — the shipped spec
        # scenario's own example, removed with 35 others (36 of 48 corpus pairs).
        members = [
            _make({"stage": "擬訂", "date": "2010-09-21", "schedule": "已失效"}, virtual=True, cid="09902261"),
            _make({"stage": "擬訂", "date": "2010-09-21"}, virtual=True, cid="10201171"),
        ]
        out = _run_scenario(json.dumps({"clusters": [{"stage": "擬訂", "members": members}]}))
        assert out["chainPairs"] == []

    def test_cross_stage_same_day_not_chained(self):
        out = _run_scenario(json.dumps({"clusters": [
            {"stage": "擬訂", "members": [_make({"stage": "擬訂", "date": "2007-04-19"}, virtual=True, cid="09601260")]},
            {"stage": "擬訂", "members": [_make({"stage": "擬訂", "date": "2007-04-19", "track": "事業計畫"}, virtual=True, cid="09601262")]},
        ]}))
        assert out["chainPairs"] == []

    def test_real_real_pair_never_chained(self):
        members = [
            _make({"stage": "擬訂", "date": "2012-08-27", "recno": 1219}, anchored=["09811141"]),
            _make({"stage": "擬訂", "date": "2016-08-23", "recno": 1037}, anchored=["09811142"]),
        ]
        out = _run_scenario(json.dumps({"clusters": [{"stage": "擬訂", "members": members}]}))
        assert out["chainPairs"] == []

    def test_real_virtual_pair_never_chained(self):
        # §4 amendment: the attempt-succession chain is virtual↔virtual only.
        # A real↔virtual consecutive pair (南海段-687: cluster [變更] holds
        # 393 real + 11012301 withdrawn-orphan virtual) gains no chain edge —
        # its only recno connector is the §4 dotted edge to the branch-off
        # node (734). A chain edge here reads as "the approval leads to the
        # withdrawn application" and duplicates or contradicts the §4 edge:
        # corpus 2026-11-04: 67 pairs stacked on the §4 edge, 30 to the row
        # below (dead end flows onward), 22 to a wrong branch point.
        members = [
            _make({"stage": "變更", "date": "2022-12-29", "recno": 393, "track": "事業計畫、權利變換"}, anchored=["11012302"]),
            _make({"stage": "變更", "date": "", "track": "事業計畫、權利變換"}, virtual=True, cid="11012301"),
        ]
        out = _run_scenario(json.dumps({"clusters": [{"stage": "變更", "members": members}]}))
        assert out["chainPairs"] == []
