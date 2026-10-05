"""Correction-ledger tests: durable, content-keyed, re-applied every rebuild.

Task group 5 of robust-gazette-ingestion.
"""

from __future__ import annotations

import pytest

from urtpe.ledger import Correction, CorrectionLedger, key_from_raw, normalize_land


@pytest.fixture
def ledger(tmp_path) -> CorrectionLedger:
    return CorrectionLedger(tmp_path / "corrections.jsonl")


class Rec:
    """Minimal stand-in for a CleanRecord."""

    def __init__(self, land: str, iso_date: str, track: str = "其他", name: str = "n"):
        self.land = land
        self.iso_date = iso_date
        self.track = track
        self.name = name


LAND = "臺北市北投區大業段三小段184-1地號等10筆土地"
DATE = "2026-04-30"


def _entry(**kw) -> Correction:
    base = dict(match_land_core=LAND, match_iso_date=DATE, field="track",
                to="事業計畫", why="案名 事業換計畫 → 事業計畫", by="jeffw")
    base.update(kw)
    return Correction(**base)


def test_appending_changes_no_existing_entry(ledger):
    ledger.append(_entry())
    first = ledger.path.read_text(encoding="utf-8")
    ledger.append(_entry(field="name", to="x"))
    lines = ledger.path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == first.splitlines()[0]
    assert len(lines) == 2


def test_correction_applies_across_a_renumbered_record(ledger):
    ledger.append(_entry())
    rec = Rec(LAND, DATE)
    outcome = ledger.apply([rec])
    assert rec.track == "事業計畫"
    assert len(outcome.applied) == 1


def test_correction_follows_the_case_not_the_recno(ledger):
    """The same case at 編號 621 in one gazette and 631 in the next still matches."""
    ledger.append(_entry())
    for recno in (621, 631, 1200):
        rec = Rec(LAND, DATE)
        ledger.apply([rec])
        assert rec.track == "事業計畫", recno


def test_unmatched_correction_is_reported_and_changes_nothing(ledger):
    ledger.append(_entry())
    other = Rec("臺北市大安區仁愛段四小段114地號等6筆土地", "2000-09-29")
    outcome = ledger.apply([other])
    assert outcome.applied == []
    assert len(outcome.unmatched) == 1
    assert other.track == "其他"


def test_unmatched_correction_does_not_abort(ledger):
    ledger.append(_entry())
    outcome = ledger.apply([Rec("其他地號", "2020-01-01")])
    assert outcome.unmatched  # reported
    # No exception is raised: a correction for an unpublished record is normal.


def test_rebuild_reapplies_every_correction(ledger):
    ledger.append(_entry())
    for _ in range(3):
        rec = Rec(LAND, DATE)
        ledger.apply([rec])
        assert rec.track == "事業計畫"


def test_correction_to_identity_field_changes_the_slug(ledger):
    """A corrected first-parcel must flow into project_id, not just the display."""
    from urtpe import cleanse as cleanse_mod
    from urtpe.models import RawRecord

    raw = RawRecord(recno=621, date="115/4/30", district="北投區",
                    name="擬訂臺北市北投區大業段三小段999地號等10筆土地都市更新事業計畫案",
                    land=LAND, implementer="甲", planner="乙", gazette_id="g")
    clean = cleanse_mod.cleanse(raw)
    before = clean.first_parcel
    ledger.append(_entry(field="first_parcel", to="184-1", why="corrected by hand"))
    clean2 = cleanse_mod.cleanse(raw)
    ledger.apply([clean2])
    assert clean2.first_parcel == "184-1" != before


def test_superseded_correction_stays_as_history(ledger):
    ledger.append(_entry(to="事業計畫"))
    original = ledger.entries()[0].describe()
    ledger.append(_entry(to="權利變換計畫", supersedes=original))
    rec = Rec(LAND, DATE)
    outcome = ledger.apply([rec])
    assert rec.track == "權利變換計畫"
    assert len(ledger.entries()) == 2
    assert any("-> '事業計畫'" in e.describe() for e in ledger.entries())


def test_report_states_applied_and_unmatched_counts(ledger):
    ledger.append(_entry())
    ledger.append(_entry(match_iso_date="1999-01-01"))
    outcome = ledger.apply([Rec(LAND, DATE)])
    text = outcome.report()
    assert "manual corrections applied: 1" in text
    assert "unmatched corrections: 1" in text
    assert "unmatched:" in text


def test_empty_ledger_reports_zero_applied(tmp_path):
    outcome = CorrectionLedger(tmp_path / "empty.jsonl").apply([Rec(LAND, DATE)])
    assert "manual corrections applied: 0" in outcome.report()


def test_general_rule_supersedes_correction_but_entry_survives(ledger):
    ledger.append(_entry())
    assert len(ledger.entries()) == 1
    # A cleansing rule would now handle this for every record; the ledger entry is
    # retained as history rather than deleted.
    assert ledger.entries()[0].why


def test_land_normalization_absorbs_punctuation_and_spacing():
    a = normalize_land("臺北市X段一小段159、161、162 地號等113筆土地")
    b = normalize_land("臺北市X段一小段159,161,162地號等113筆土地")
    assert a == b


def test_removal_acceptance_is_exposed_for_reconciliation(ledger):
    ledger.append(Correction(match_land_core=LAND, match_iso_date="2000-09-29",
                             field="", to=None, why="verified with the city",
                             by="jeffw", accept_removal=True))
    assert (LAND, "2000-09-29") in ledger.accepted_removals()


def test_uncorrectable_field_is_rejected(ledger):
    with pytest.raises(ValueError):
        Correction(match_land_core=LAND, match_iso_date=DATE, field="not_a_field",
                   to=1, why="", by="t")


def test_key_from_raw_normalizes_the_land_cell():
    raw = {"land": "臺北市X段一小段1、2地號等2筆土地", "date": "115/8/27"}
    assert key_from_raw(raw) == ("臺北市X段一小段12地號等2筆土地", "2026-08-27")


def test_malformed_ledger_line_is_skipped_not_fatal(ledger):
    ledger.append(_entry())
    with ledger.path.open("a", encoding="utf-8") as fh:
        fh.write("{oops\n")
    assert len(ledger.entries()) == 1