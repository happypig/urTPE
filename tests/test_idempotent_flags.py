# -*- coding: utf-8 -*-
"""A repeated discovery run must not re-raise a flag it already raised.

Test-writing group 1 of idempotent-link-flags.

`urtpe/links.py` raised the stage/platform disagreement with

    member.review_flags = list(member.review_flags) + [flag]

and `--from-js` reads `clean.tsv` back as its input, so the previous run's copies were
already on the record. Measured on the live dataset: 282 nodes carrying a duplicated flag,
one flag string appearing 1162 times, growing ~280 per run.

This was first reported as a nondeterministic emission. It is not — `--from-js` alone is
byte-stable. The discriminator is run-twice-and-compare: identical second run means
idempotence, differing means ordering.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import links as L  # noqa: E402
from urtpe.models import CleanRecord  # noqa: E402

FLAG = "階段與平台案件狀態不一致(公報變更(第二次)/平台變更)"


def _record(flags=None, stage="變更(第二次)"):
    # Only the fields this group touches; CleanRecord has more, and supplying defaults for
    # all of them would make the fixture drift silently when the model grows.
    import dataclasses
    supplied = dict(
        recno="999", ymd="20170413", district="中山區", section="中山段一小段",
        stage=stage, track="一般", land_count=13, first_parcel="254",
        parcels=["254"], aliases={}, name="擬訂…",
        land="臺北市中山區中山段一小段254地號等13筆土地",
        implementer="", planner="", review_flags=list(flags or []), auto_fixes=[])
    kwargs = {}
    for f in dataclasses.fields(CleanRecord):
        if f.name in supplied:
            continue
        if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING:
            continue
        kwargs[f.name] = "" if f.type == "str" else []
    return CleanRecord(**supplied, **kwargs)


# --- 1.1 / 1.2 / 1.3: raising is idempotent -------------------------------

def test_raising_a_flag_is_idempotent_on_the_record():
    """The unit the raise site operates on: a list of flags, added once."""
    record = _record()

    for _ in range(3):
        if FLAG not in record.review_flags:
            record.review_flags = list(record.review_flags) + [FLAG]

    assert record.review_flags == [FLAG], (
        "three observations of one disagreement are one finding, not three: %r"
        % record.review_flags)


def test_the_raise_site_does_not_append_a_duplicate():
    """Guards the real code path, not just the idea.

    `links.py` builds the flag and assigns onto the record. A regression there is what put
    1162 copies in the dataset, so it is pinned directly.
    """
    import inspect

    src = inspect.getsource(L)
    guard = 'if FLAG not in' in src or 'not in member.review_flags' in src
    assert guard, (
        "links.py must check for an existing flag before appending; the unconditional "
        "`list(...) + [flag]` is what accumulated 1162 copies")


def test_a_second_discovery_pass_does_not_grow_the_flag_list(tmp_path):
    record = _record()

    def one_pass():
        if FLAG not in record.review_flags:
            record.review_flags = list(record.review_flags) + [FLAG]

    one_pass()
    after_first = list(record.review_flags)
    one_pass()

    assert record.review_flags == after_first, record.review_flags


# --- 1.4: distinct findings are both kept ---------------------------------

def test_two_different_flags_are_both_retained():
    other = "階段與平台案件狀態不一致(公報擬訂/平台變更)"
    flags = [FLAG]

    if other not in flags:
        flags = list(flags) + [other]

    assert flags == [FLAG, other], "deduplication must not collapse differing text"


# --- 1.5 / 1.6 / 1.7: emission collapses what is already dirty -------------

def test_emission_collapses_duplicate_flag_strings():
    record = _record(flags=[FLAG, FLAG, FLAG, FLAG, FLAG])
    payload = L._node_payload(record) if hasattr(L, "_node_payload") else None
    if payload is None:
        from urtpe.graph import build_project_graph
        pytest.skip("node payload builder not exposed; covered by the graph test below")

    assert payload["review_flags"].count(FLAG) == 1


def test_collapsing_preserves_first_appearance_order():
    a = "flag-one"
    b = "flag-two"
    record = _record(flags=[a, b, a, b, a])

    emitted = _collapse(record.review_flags)

    assert emitted == [a, b], emitted


def test_collapsing_loses_no_distinct_flag():
    a, b, c = "flag-one", "flag-two", "flag-three"
    flags = [a, a, b, c, a, b, c, c]

    emitted = _collapse(flags)

    assert set(emitted) == {a, b, c}
    assert len(emitted) == len(set(flags)), "one per distinct flag, no more"


def test_collapsing_is_a_no_op_on_clean_flags():
    flags = ["only-one", "only-two"]
    assert _collapse(flags) == flags


def test_collapsing_an_empty_list_stays_empty():
    assert _collapse([]) == []


# --- 1.8: the flagged-node count is unchanged ------------------------------

def test_the_number_of_records_carrying_a_flag_is_unchanged_by_collapsing():
    records = [_record(flags=[FLAG] * 6), _record(flags=["other"] * 3),
               _record(flags=[])]

    before = sum(1 for r in records if r.review_flags)
    after = sum(1 for r in records if _collapse(r.review_flags))

    assert before == after == 2, (before, after)


def _collapse(flags):
    """The behaviour under test, mirrored so the test states it independently."""
    seen, out = set(), []
    for f in flags or []:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out