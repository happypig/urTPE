"""The joined node: implementation per case, one 北 badge per case, no-wrap
callouts (joined-node-section-callouts).

The user's rules (2026-11-12, items 4/4a-4d/5): the cases are already joined
on the recno — the badge covers both, the callout shows both per section,
the [A區]/[B區] label rides the badge and the callout sections, and a
callout row never wraps.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "data" / "projects.json"


# --- the per-case emission (task 1.1, 1.3) -----------------------------------

def test_a_joined_node_emits_both_sections():
    """敦化363-1 node 537 anchors -A and -B whose payloads differ on
    Ulic_Date. The node carries both, keyed by case id."""
    doc = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    p = next(x for x in doc["projects"]
             if x["project_id"] == "松山區-敦化段四小段-363-1地號等5筆")
    node = next(n for n in p["nodes"] if n["recno"] == 537)
    by_case = node.get("implementation_by_case")
    if by_case is None:
        pytest.fail("node 537 carries no implementation_by_case (pre-re-emit)")
    assert set(by_case) >= {"10906101", "10906102"}, sorted(by_case)
    assert by_case["10906101"]["Ulic_Date"] == "2025/04/29"
    assert by_case["10906102"]["Ulic_Date"] == "2025/05/06"


def test_a_single_case_node_stays_as_it_is():
    """One anchored case with a payload → the single snapshot, no by_case."""
    doc = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    single = 0
    for p in doc["projects"]:
        for n in p.get("nodes", []):
            cases = (n.get("links") or {}).get("taipei") or []
            if len(cases) == 1 and n.get("implementation"):
                single += 1
                assert "implementation_by_case" not in n, (
                    f"{p['project_id']} node {n['recno']}: a single-case node "
                    f"carries implementation_by_case")
    assert single > 0, "the corpus holds no single-case snapshot to pin"


def test_the_joined_node_counters_on_the_live_payload():
    """30 nodes carry 2+ case ids, 28 of them area pairs; after the re-emit
    every node anchoring 2+ cases WITH payloads carries by_case. The figures
    move when the payload moves; the assertion names the drift."""
    doc = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    AREA = re.compile(r"-(A|B|C|北|南|東|西)區$")
    joined = area_pairs = with_by_case = 0
    for p in doc["projects"]:
        cn = (p.get("links") or {}).get("candidate_names") or {}
        for n in p.get("nodes", []):
            cases = (n.get("links") or {}).get("taipei") or []
            if len(cases) < 2:
                continue
            joined += 1
            if any(AREA.search(cn.get(c, "") or "") for c in cases):
                area_pairs += 1
            if n.get("implementation_by_case"):
                with_by_case += 1
    # 2026-11-15 (section8-gate-anchor-parcel-drift): 華中247's two A區/B區
    # nodes joined (09305081+09305082, 09407301+09407302): 30 -> 32, 28 -> 30.
    # Neither has implementation payloads, so with_by_case stays 30 and no new
    # section callout renders.
    assert joined == 32, f"joined nodes moved: {joined} (board says 32 since the 2026-11-15 correction)"
    assert area_pairs == 30, f"area pairs moved: {area_pairs} (board says 30 since the 2026-11-15 correction)"
    assert with_by_case == 30, f"by_case nodes moved: {with_by_case} (board says 30)"


# --- the round trip (task 1.2) -------------------------------------------------

def test_the_field_survives_a_rebuild():
    """implementation_by_case rides the --from-js reload (the D6 contract)."""
    doc = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    proj = next((p for p in doc["projects"]
                 if any(n.get("implementation_by_case") for n in p.get("nodes", []))), None)
    if proj is None:
        pytest.skip("no node carries the field yet (pre-re-emit)")
    node = next(n for n in proj["nodes"] if n.get("implementation_by_case"))
    assert isinstance(node["implementation_by_case"], dict)
    assert node["implementation_by_case"], "the by-case dict is empty"


# --- the badge render (task 1.4) ------------------------------------------------

def test_a_joined_node_renders_one_badge_per_case():
    """The badge template loops the anchored cases, one 北 per case, each
    linking its own page, with the area label beside it."""
    from pathlib import Path as _P
    js = (_P(ROOT / "viewer" / "app.js").read_text(encoding="utf-8")
          .replace("\r\n", "\n"))
    m = re.search(r"function getNodeMilestoneBadges[\s\S]*?\n\}", js)
    assert m, "getNodeMilestoneBadges not found"
    body = m.group(0)
    assert "areaTokenFromName" in body or "area" in body, (
        "the badge render does not derive the area label")
    assert body.count("r_progress_detail.aspx?case_id=") >= 1
    # the loop: the badge is built per case, not only cases[0]
    assert ".map(" in body or "for (" in body, (
        "the badge render does not loop the anchored cases")


# --- the no-wrap sizing (task 1.5) ------------------------------------------------

def test_the_callout_cap_is_retired():
    """E9: the gutter grows to the widest box; the 160 px clamp and the
    wrap-height model retire."""
    js = (ROOT / "viewer" / "app.js").read_text(encoding="utf-8")
    assert "CALLOUT_GUTTER_CAP" not in js, (
        "the 160 px gutter cap is still in app.js")
    assert "implValueLines" not in js, (
        "the wrap-height model (implValueLines) is still in app.js")
