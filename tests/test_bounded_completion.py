"""Bounded completion of a publisher-truncated 地號 cell.

Test-writing group 4 of no-silent-data-loss.

The previous change forbade completion outright, on the evidence that borrowing is unsafe
for 17 of 21 truncated records. That evidence stands, so completion here requires three
conjunctive checks rather than a similarity threshold. Two of them — same unit and
literal prefix — can be satisfied by a parcel set that merely *starts* the same way. The
third, the count, is what distinguishes "the same list continued" from "a different list".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from urtpe.extract import complete_truncated_cell  # noqa: E402

SEC = "甲段一小段"


def _cell(parcels, section=SEC, district="中正區", terminator=True):
    body = "、".join(parcels)
    tail = f"地號等{len(parcels)}筆土地" if terminator else ""
    return f"臺北市{district}{section} {body} {tail}".strip(), len(parcels)


def _candidate(gazette_id, recno, parcels, section=SEC, district="中正區",
               terminator=True):
    text, n = _cell(parcels, section, district, terminator)
    return {"gazette_id": gazette_id, "recno": recno, "land": text,
            "district": district, "section": section, "parcel_count": n}


# --- task 4.1 all three checks hold -----------------------------------------

def test_completes_when_same_unit_prefix_and_count_all_hold():
    truncated, read = _cell(["1", "2", "3"], terminator=False)
    candidate = _candidate("1151002", "1194", ["1", "2", "3", "4", "5"])
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等5筆土地都市更新事業計畫案",
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is True
    assert list(result.parcels) == ["1", "2", "3", "4", "5"]
    assert result.source_gazette == "1151002" and result.source_recno == "1194"


def test_a_candidate_that_adds_nothing_is_not_a_completion():
    truncated, _ = _cell(["1", "2", "3"], terminator=False)
    candidate = _candidate("1151002", "1194", ["1", "2", "3"])
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等3筆土地",
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is False, (
        "nothing was added; that is the closing-phrase case, not a repair")


# --- task 4.2 the count check refuses ----------------------------------------

def test_refuses_when_the_count_does_not_close():
    truncated, _ = _cell(["1", "2", "3"], terminator=False)
    candidate = _candidate("1151002", "1206", ["1", "2", "3", "4"])
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等9筆土地",  # declares 9
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is False
    assert "count" in (result.reason or "").lower(), (
        "the refusal must say the count did not close: %r" % result.reason)


def test_refuses_when_the_count_closes_but_a_second_candidate_does_not():
    """The best candidate is chosen on the checks, not on parcel overlap."""
    truncated, _ = _cell(["1", "2"], terminator=False)
    good = _candidate("1151002", "10", ["1", "2", "3"])
    poor = _candidate("1151002", "11", ["1", "2", "3", "4", "5", "6"])
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等3筆土地",
        candidates=[poor, good], source_gazette="1150827")
    assert result.completed is True
    assert result.source_recno == "10", (
        "the candidate that closes the count wins, not the larger parcel set")


# --- task 4.3 never across a section boundary --------------------------------

def test_never_completes_across_a_section_boundary():
    truncated, _ = _cell(["1", "2", "3"], terminator=False)
    other = _candidate("1151002", "1194", ["1", "2", "3", "4", "5"],
                       section="乙段二小段")
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等5筆土地",
        candidates=[other], source_gazette="1150827")
    assert result.completed is False
    assert "段" in (result.reason or ""), (
        "the refusal must name the section mismatch: %r" % result.reason)


def test_never_completes_across_a_district():
    truncated, _ = _cell(["1", "2", "3"], terminator=False)
    other = _candidate("1151002", "1194", ["1", "2", "3", "4", "5"],
                       district="大安區")
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等5筆土地",
        candidates=[other], source_gazette="1150827")
    assert result.completed is False


def test_spacing_differences_between_publications_are_not_a_content_difference():
    """The publisher's spacing varies between publications for the same list.

    1150827 writes `332 、333` where 1151002 writes `332、333`. Comparing raw text
    refuses a genuine continuation on that alone — which is how 編號 1198 was wrongly
    reported as unrepairable during this change. Spacing is presentation; parcel
    identity is checked separately.
    """
    truncated = "臺北市萬華區漢中段二小段328 、328 -1、332 、333 、334 、"
    # same parcels, tighter spacing, plus the continuation
    candidate = {
        "gazette_id": "1151002", "recno": "1194",
        "land": "臺北市萬華區漢中段二小段328、328-1、332、333、334、335 地號等6筆土地",
        "district": "萬華區", "section": "區漢中段二小段", "parcel_count": 6,
    }
    result = complete_truncated_cell(
        land=truncated,
        name="擬訂臺北市萬華區漢中段二小段328地號等6筆土地都市更新事業計畫案",
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is True, (
        "spacing alone must not refuse a continuation: %s" % result.reason)
    assert result.parcel_count == 6


def test_a_candidate_missing_an_already_read_parcel_is_refused():
    """Containment is a separate check from the prefix.

    A candidate can share a prefix and still omit a parcel the truncated cell
    already showed, which would mean it is a different list.
    """
    truncated = "臺北市萬華區漢中段二小段328、329 、330 、"
    candidate = {
        "gazette_id": "1151002", "recno": "1",
        # 328, 330, 331 — 329 was read but is absent here
        "land": "臺北市萬華區漢中段二小段328、330 、331 地號等3筆土地",
        "district": "萬華區", "section": "區漢中段二小段", "parcel_count": 3,
    }
    result = complete_truncated_cell(
        land=truncated,
        name="擬訂臺北市萬華區漢中段二小段328地號等3筆土地都市更新事業計畫案",
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is False, (
        "a candidate missing a parcel the truncated cell already showed is a "
        "different list and must be refused")
    """甲段一小段 must not match 甲段二小段 by string containment."""
    truncated, _ = _cell(["1", "2", "3"], section="甲段一小段", terminator=False)
    other = _candidate("1151002", "1", ["1", "2", "3", "4"], section="甲段二小段")
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等4筆土地",
        candidates=[other], source_gazette="1150827")
    assert result.completed is False


# --- task 4.4 provenance ----------------------------------------------------

def test_a_completion_names_its_source_gazette_and_recno():
    truncated, _ = _cell(["1", "2"], terminator=False)
    candidate = _candidate("1151002", "1194", ["1", "2", "3"])
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等3筆土地",
        candidates=[candidate], source_gazette="1150827")
    assert result.source_gazette == "1151002"
    assert result.source_recno == "1194"
    assert result.audit_entry(), "a completion must be auditable from the result alone"


def test_a_refusal_carries_a_reason():
    truncated, _ = _cell(["1", "2"], terminator=False)
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等9筆土地",
        candidates=[], source_gazette="1150827")
    assert not result.completed
    assert result.reason, "a refusal must say why"


# --- task 4.5 the 1210 case, pinned -----------------------------------------

def test_the_1210_case_is_refused():
    """雙連段一小段197等72筆: prefix match at J=0.984, and the count still fails.

    1150827 truncates at 61 parcels; the only prefix-sharing candidate (1151002 編號
    1206) terminates at 62; the 案名 declares 72. Neither publication holds the list, so
    completing it would assert 62 parcels for a record that should have 72 — the exact
    silent corruption this change exists to remove.

    Pinned as a named case so the count check cannot be relaxed to "close enough".
    """
    truncated = ("臺北市大同區雙連段一小段 197、198、199、219 -91 、 219-92 、219 -93 、"
                 "219 -94 、")
    candidate = {
        "gazette_id": "1151002", "recno": "1206",
        "land": ("臺北市大同區雙連段一小段 197、198、199、219 -91 、 219-92 、219 -93 、"
                 "219 -94 、219-95、238-1 地號等72筆土地"),
        "district": "大同區", "section": "區雙連段一小段", "parcel_count": 62,
    }
    result = complete_truncated_cell(
        land=truncated,
        name="擬訂臺北市大同區雙連段一小段197地號等72筆土地都市更新事業計畫及權利變換計畫案",
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is False, (
        "1210 must stay excluded: the candidate closes at 62 while the 案名 declares 72")
    assert "count" in (result.reason or "").lower()


def test_the_1198_case_is_repaired():
    """漢中段二小段328等110筆: the count closes exactly, so this one is repaired.

    1150827 truncates at 102; 1151002 編號 1194 supplies 110, which is what the 案名
    declares. Three independent checks agree, so the record is emitted with an audit
    entry naming its source.
    """
    truncated = ("臺北市萬華區漢中段二小段 328、328-1、433 、434 、435 、436 、438 、"
                 " 439 、440 、441 、442 、")
    candidate = {
        "gazette_id": "1151002", "recno": "1194",
        "land": ("臺北市萬華區漢中段二小段 328、328-1、433 、434 、435 、436 、438 、"
                 " 439 、440 、441 、442 、443、444、445、446、447、448、449、450 地號等110筆土地"),
        "district": "萬華區", "section": "區漢中段二小段", "parcel_count": 110,
    }
    result = complete_truncated_cell(
        land=truncated,
        name="擬訂臺北市萬華區漢中段二小段328地號等110筆土地都市更新事業計畫及權利變換計畫案",
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is True
    assert result.parcel_count == 110
    assert result.source_recno == "1194"


# --- task 4.6 the closing-phrase case is untouched ---------------------------

def test_a_complete_list_missing_its_closing_phrase_is_not_repaired():
    """Already whole; a completion must not be attempted or reported."""
    truncated = "臺北市中正區甲段一小段 1、2、3"
    candidate = _candidate("1151002", "9", ["1", "2", "3"])
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等3筆土地",
        candidates=[candidate], source_gazette="1150827")
    assert result.completed is False
    assert "closing" in (result.reason or "").lower() or "whole" in (result.reason or "").lower(), (
        "the reason must distinguish 'already whole' from 'not repairable': %r"
        % result.reason)


def test_no_candidates_yields_a_refusal_not_an_error():
    truncated, _ = _cell(["1", "2", "3"], terminator=False)
    result = complete_truncated_cell(
        land=truncated, name="擬訂臺北市中正區甲段一小段1地號等5筆土地",
        candidates=[], source_gazette="1150827")
    assert not result.completed and result.reason
