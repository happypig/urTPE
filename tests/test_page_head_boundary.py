# -*- coding: utf-8 -*-
"""The ROC→Gregorian boundary on a page-head publication — pinned, not inferred.

The 2026-09-24 gazette (quarantined on release as "abnormal SN", restored by
restore-2026-09-24-gazette) is the first Gregorian-dated document the archive
held, and it exhibits the 1151002 running-page-head defect: 編號 1 restated as an
exact copy of page 1's real row atop every later page. Two properties must hold
for any reader that claims to accept it:

1. The head is dropped **because its 編號 duplicates a record already read**
   (content-dedup, first occurrence wins) — never because it sits at row 0.
   The v2 reader's positional skip is the standing counter-example: on the
   opposite head shape (1151006, where the band row appears nowhere else) it
   deleted one real approval per page, 230 of 1,439 records.
2. The calendar boundary does not perturb the read: dates on both sides of the
   boundary parse to ISO, and contiguity holds so the tripwire passes.

Fixture-level, so it runs offline and fast. The real-file acceptance shape is
pinned separately (task 1.2, test_quarantined_2026_09_24_acceptance).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.extract import extract_pdf_with_meta  # noqa: E402
from urtpe.tripwire import Tripwire  # noqa: E402
from tests.gazette_fixtures import ROC_ROWS, write_gazette  # noqa: E402


def _boundary_rows(n_roc: int, n_gregorian: int) -> list[tuple]:
    """A lineage that crosses the calendar boundary: the older records carry
    ROC dates (as every held gazette up to 08-27 does), the newest record is
    Gregorian-dated (as 09-24 already is). Rows otherwise reuse the fixture
    corpus, recno renumbered 1..N newest-first."""
    rows = []
    recno = 1
    for i in range(n_gregorian):
        src = ROC_ROWS[i % len(ROC_ROWS)]
        rows.append((recno, "2026/9/24", *src[2:]))
        recno += 1
    for i in range(n_roc):
        src = ROC_ROWS[(n_gregorian + i) % len(ROC_ROWS)]
        rows.append((recno, src[1], *src[2:]))
        recno += 1
    return rows


def test_page_head_publication_across_the_calendar_boundary_reads_completely(tmp_path):
    """The 09-24 shape: running head on every later page, Gregorian newest row,
    ROC historical rows. Every 編號 exactly once, every date parses, tripwire
    PASS."""
    rows = _boundary_rows(n_roc=7, n_gregorian=3)
    path = write_gazette(str(tmp_path / "boundary.pdf"), rows,
                         rows_per_page=2, repeat_header_row=True,
                         calendar="mixed")
    recs, meta = extract_pdf_with_meta(path)

    recnos = [int(r["recno"]) for r in recs]
    assert len(recnos) == len(rows), (
        f"expected {len(rows)} records, got {len(recnos)} "
        f"(a head copy leaked through, or a real record was dropped)")
    assert sorted(recnos) == list(range(1, len(rows) + 1)), (
        "編號 must be contiguous 1..N after the head dedup")
    assert len(recnos) == len(set(recnos)), "no 編號 may appear twice"

    # Every date parses to ISO regardless of which calendar its cell printed.
    from urtpe.extract import to_iso
    bad = [r["recno"] for r in recs if to_iso(r["date"])[0] is None]
    assert not bad, f"unparsed dates at 編號 {bad}: the boundary broke the read"

    # And the tripwire — the gate the real ingestion runs — accepts it.
    faults = Tripwire().check(recs, pages=5, tables_found=5)
    assert faults == [], faults


def test_a_unique_head_row_is_a_record_not_furniture(tmp_path):
    """The negative guard: content decides, never position.

    With repeat_header_row the band carries a *copy* of a record that also
    appears as data, so dropping it loses nothing. The 1151006 shape is the
    opposite — the band row exists nowhere else — and a reader that skips
    grid row 0 by position deletes a real approval per page. The head-dedup
    must therefore key on 編號 content, and this test pins it: when the
    repeated row is made unique (a 編號 no data row carries), the reader must
    emit it.
    """
    # Page 1: the real 編號 1..N. Pages 2+: the band repeats row 0's content —
    # but we give that content a 編號 no data row has, emulating the shape
    # where the band row is a record in its own right. write_gazette has no
    # knob for that, so build the opposite shape directly:
    # no_header_band_after_first puts a *real* record at grid row 0 of every
    # later page — the exact shape the v2 reader destroyed.
    rows = _boundary_rows(n_roc=3, n_gregorian=2)
    path = write_gazette(str(tmp_path / "straight.pdf"), rows,
                         rows_per_page=2, no_header_band_after_first=True,
                         calendar="mixed")
    recs, _meta = extract_pdf_with_meta(path)

    recnos = sorted(int(r["recno"]) for r in recs)
    assert recnos == list(range(1, len(rows) + 1)), (
        "a reader that skips grid row 0 by position deletes real records on "
        "the 1151006 shape; every 編號 must survive")


QUARANTINE_PATH = (Path(r"D:\project\urtpe-gazettes")
                   / "skipped since abnormal SN" / "核定案件-2026-10-02.pdf")


@pytest.mark.skipif(not QUARANTINE_PATH.exists(),
                    reason="the quarantined 09-24 candidate is not on this machine")
def test_quarantined_2026_09_24_acceptance():
    """The real file, through the real reader, read-only.

    Pins the acceptance shape restore-2026-09-24-gazette commits to: the file
    the poller recorded as gazette 2026-09-24 reads as a complete publication
    under the current reader — 1,681 raw rows collapse to 1,436 distinct, 編號
    contiguous 1..1436, Gregorian 統計至, 22 publisher-truncated rows named,
    zero duplicates after the reader's dedup. This is the pre-condition the
    restoration (tasks group 4) relies on; if it fails, the restoration must
    not run.
    """
    recs, meta = extract_pdf_with_meta(str(QUARANTINE_PATH))

    assert meta.get("published_date") == "2026-09-24", meta.get("published_date")
    assert meta.get("calendar") == "gregorian", meta.get("calendar")

    # The reader excludes publisher-truncated rows and names them; printed
    # records = emitted + excluded. 1,414 + 22 = 1,436.
    recnos = sorted(int(r["recno"]) for r in recs)
    excluded = {int(v) for v in (meta.get("excluded_recnos") or "").split(",")
                if v.strip().isdigit()}
    assert len(excluded) == 22, (
        f"expected 22 named publisher truncations, got {len(excluded)}")
    assert len(recnos) + len(excluded) == 1436, (
        f"printed records: {len(recnos)} emitted + {len(excluded)} excluded")
    assert not (set(recnos) & excluded), "an excluded 編號 must not also be emitted"

    # Contiguity 1..1436 over emitted ∪ excluded — the tripwire's own view.
    assert set(recnos) | excluded == set(range(1, 1437)), (
        "編號 1..1436 must be fully accounted for: emitted plus named exclusions")
