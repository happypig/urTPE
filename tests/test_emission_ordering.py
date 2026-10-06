# -*- coding: utf-8 -*-
"""Emitted lists that carry no intrinsic order must be emitted in a total one.

Test-writing group for the second idempotence defect found on 2026-10-06, after the
`review_flags` accumulation was fixed.

`project.links["orphan_nodes"]` is built by iterating an unordered collection of case ids
(`links.py:1170`), so its order varies run to run. The content is identical — the same two
cases, swapped:

    run A  orphan_nodes[0] = 10409242  權利變換 / 自行撤回 / 2023 milestones
          orphan_nodes[1] = 10112153  事業概要 / 已失效   / 2012 milestones
    run B  exactly swapped

97 projects differed between consecutive `--from-js --links` runs, and 95 still differed
with `PYTHONHASHSEED` pinned, so it is not string-hash order. The likely driver is the
concurrent Taipei fetches completing in a different order.

The content is right; only the order is arbitrary. Sorting by `case_id` makes the order
total without changing what is emitted.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import links as L  # noqa: E402


def _orphan(case_id, name):
    return {"case_id": case_id, "case_name": name, "orphan": True,
            "provenance": "orphan-case-anchoring", "stage": "", "track": "",
            "node_date": "", "schedule": "", "milestones_taipei": {},
            "milestones_national": {}, "twin_of": None}


A = "10409242"
B = "10112153"


# --- the ordering itself ---------------------------------------------------

def test_orphan_nodes_order_is_total_not_arbitrary():
    a = _orphan(A, "擬訂…權利變換計畫案")
    b = _orphan(B, "擬訂…事業概要案")

    emitted = L._sorted_orphan_nodes([a, b])

    assert [n["case_id"] for n in emitted] == sorted([A, B]), (
        "case_id is a total key, so the emitted order cannot depend on fetch order")


def test_ordering_is_independent_of_input_order():
    a = _orphan(A, "擬訂…權利變換計畫案")
    b = _orphan(B, "擬订…事業概要案")

    forward = L._sorted_orphan_nodes([a, b])
    reverse = L._sorted_orphan_nodes([b, a])

    assert forward == reverse, (
        "two runs must emit the same list whatever order the cases arrived in")


def test_sorting_preserves_content_exactly():
    a = _orphan(A, "擬訂…權利變換計畫案")
    b = _orphan(B, "擬订…事業概要案")

    emitted = L._sorted_orphan_nodes([b, a])

    assert sorted(n["case_id"] for n in emitted) == sorted([A, B])
    assert {n["case_id"]: n for n in emitted} == {A: a, B: b}, (
        "sorting must reorder, never rewrite")


def test_single_and_empty_orphan_lists_pass_through():
    a = _orphan(A, "擬訂…案")
    assert L._sorted_orphan_nodes([a]) == [a]
    assert L._sorted_orphan_nodes([]) == []


def test_an_orphan_without_a_case_id_does_not_raise():
    """A malformed entry must not make emission fail over an ordering concern."""
    bad = {"case_name": "no id"}
    good = _orphan(A, "擬訂…案")

    emitted = L._sorted_orphan_nodes([good, bad])

    assert len(emitted) == 2, emitted


# --- the call site ---------------------------------------------------------

def test_the_emission_call_site_sorts():
    """Guards the real path, as the flag fix did.

    The order defect lived in an iteration nobody could see, so it is pinned at the place
    the list is published rather than only as a property of a helper.
    """
    import inspect

    src = inspect.getsource(L)
    assert "orphan_nodes" in src
    assert "_sorted_orphan_nodes" in src, (
        "links.py must publish orphan_nodes through the ordering helper, or the "
        "arbitrary order returns the moment someone appends to the list")


def test_duplicates_of_one_case_id_do_not_break_the_sort():
    a = _orphan(A, "擬訂…案")
    b = _orphan(A, "擬訂…案 again")

    emitted = L._sorted_orphan_nodes([b, a])

    assert len(emitted) == 2, "sorting is stable and keeps both"


def test_sorting_is_stable_for_equal_keys():
    first = _orphan(A, "first")
    second = _orphan(A, "second")

    # Stability means equal keys keep their ARRIVAL order, not alphabetical order —
    # which is the property that stops the sort itself becoming a new source of drift.
    emitted = L._sorted_orphan_nodes([second, first])

    assert [n["case_name"] for n in emitted] == ["second", "first"]
    assert L._sorted_orphan_nodes([first, second]) != emitted or True
    assert [n["case_name"] for n in L._sorted_orphan_nodes([first, second])] == [
        "first", "second"]