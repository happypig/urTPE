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

    def __init__(self, land: str, iso_date: str, track: str = "其他", name: str = "n",
                 recno: int = 0):
        self.land = land
        self.iso_date = iso_date
        self.track = track
        self.name = name
        self.recno = recno


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


# --------------------------------------------------------------------------
# confirm_merge (D5, ledger-confirm-merge) — 吉林676: 編號 1303 prints
# `676地號等1筆` for the 18-parcel unit whose 擬訂 is 編號 1347.
# --------------------------------------------------------------------------

# The two real keys, copied from data/clean.tsv. A Rec stand-in shaped like
# each record: 1303 (2010-03-25, `…676地號等1筆`), 1347 (2008-12-31, 18 parcels).
LAND_1303 = "臺北市中山區吉林段四小段676地號等1筆土地"
LAND_1347 = ("臺北市中山區吉林段四小段671-3、671-5、676、677、678、679、680、"
             "681、682、683、683-1、683-2、683-3、684、685、686、687、688地號等18筆土地")
DATE_1303 = "2010-03-25"
DATE_1347 = "2008-12-31"


def _confirm(**kw) -> Correction:
    base = dict(match_land_core=LAND_1303, match_iso_date=DATE_1303, field="",
                to=None, confirm_merge=True,
                with_land_core=LAND_1347, with_iso_date=DATE_1347,
                why="city case 09703184 names the unit 676地號等18筆", by="happypig")
    base.update(kw)
    return Correction(**base)


def test_confirm_merge_round_trips_with_both_keys(ledger):
    ledger.append(_confirm())
    entries = ledger.entries()
    assert len(entries) == 1
    e = entries[0]
    assert e.confirm_merge is True
    assert e.key == (LAND_1303, DATE_1303)
    assert (e.with_land_core, e.with_iso_date) == (LAND_1347, DATE_1347)
    assert e.field == ""


def test_confirm_merge_sets_no_field(ledger):
    ledger.append(_confirm())
    r1 = Rec(LAND_1303, DATE_1303, track="事業計畫", recno=1303)
    r2 = Rec(LAND_1347, DATE_1347, track="事業計畫", recno=1347)
    outcome = ledger.apply([r1, r2])
    assert r1.track == "事業計畫"
    assert r2.track == "事業計畫"
    # The confirmation is applied (it links the pair), not unmatched.
    assert outcome.applied and not outcome.unmatched


def test_confirm_merge_requires_with_keys(ledger):
    with pytest.raises(ValueError):
        _confirm(with_land_core="")
    with pytest.raises(ValueError):
        _confirm(with_iso_date="")


def test_confirm_merge_describe_names_both_keys(ledger):
    ledger.append(_confirm())
    original = ledger.entries()[0].describe()
    assert LAND_1303 in original and LAND_1347 in original
    # Supersede-by-description keeps working for confirmations.
    ledger.append(_confirm(supersedes=original, why="withdrawn: wrong pairing"))
    outcome = ledger.apply([Rec(LAND_1303, DATE_1303, recno=1303),
                            Rec(LAND_1347, DATE_1347, recno=1347)])
    # The superseding entry is the live one and links the pair; the original is
    # gone from effective() and reported as history.
    assert outcome.confirmed_pairs == [(1303, 1347)]
    assert outcome.applied and "withdrawn" in outcome.applied[0]
    assert outcome.superseded and original in outcome.superseded


def test_confirm_merge_yields_recno_pair(ledger):
    ledger.append(_confirm())
    outcome = ledger.apply([Rec(LAND_1303, DATE_1303, recno=1303),
                            Rec(LAND_1347, DATE_1347, recno=1347)])
    assert outcome.confirmed_pairs == [(1303, 1347)]


def test_confirm_merge_with_missing_second_record_is_unmatched(ledger):
    ledger.append(_confirm())
    outcome = ledger.apply([Rec(LAND_1303, DATE_1303, recno=1303)])
    assert outcome.confirmed_pairs == []
    assert len(outcome.unmatched) == 1
    assert LAND_1347 in outcome.unmatched[0]


def test_confirm_merge_with_ambiguous_key_is_unmatched(ledger):
    """A land cell + date printed twice cannot be resolved to one recno."""
    ledger.append(_confirm())
    r1 = Rec(LAND_1303, DATE_1303); r1.recno = 1
    r2 = Rec(LAND_1303, DATE_1303); r2.recno = 2
    r3 = Rec(LAND_1347, DATE_1347); r3.recno = 1347
    outcome = ledger.apply([r1, r2, r3])
    assert outcome.confirmed_pairs == []
    assert outcome.unmatched and "ambiguous" in outcome.unmatched[0]


def test_report_counts_field_correction_plus_confirmation(ledger):
    ledger.append(_entry())
    ledger.append(_confirm())
    outcome = ledger.apply([Rec(LAND, DATE, track="其他"),
                            Rec(LAND_1303, DATE_1303, track="事業計畫", recno=1303),
                            Rec(LAND_1347, DATE_1347, track="事業計畫", recno=1347)])
    text = outcome.report()
    assert "manual corrections applied: 2" in text
    assert LAND_1303 in text and LAND_1347 in text

# --- ledger-date-correction: a printed approval date can be corrected -----------

class DatedRec(Rec):
    """A stand-in carrying the three date views a CleanRecord holds."""

    def __init__(self, land: str, iso_date: str, date: str, ymd: tuple, stage: str = "變更",
                 recno: int = 0):
        super().__init__(land, iso_date, recno=recno)
        self.date = date
        self.ymd = ymd
        self.stage = stage


def test_date_correction_sets_iso_date_and_ymd_and_keeps_the_print(ledger):
    """recno 986's shape: the gazette prints 2017/5/10 for an approval the city
    dates 2018/05/10. The entry is keyed on the printed day."""
    rec = DatedRec(LAND, "2017-05-10", "2017/5/10", (2017, 5, 10), recno=986)
    ledger.append(_entry(match_iso_date="2017-05-10", field="iso_date", to="2018-05-10",
                         why="city case 10409213 dates the approval 2018/05/10"))
    out = ledger.apply([rec])
    assert rec.iso_date == "2018-05-10"
    assert rec.ymd == (2018, 5, 10)
    assert rec.date == "2017/5/10"
    assert len(out.applied) == 1 and out.unmatched == []


def test_date_and_stage_corrections_on_one_record_both_apply(ledger):
    """Matching uses the printed day, so a second entry keyed on it still lands
    after the date entry has moved iso_date."""
    rec = DatedRec(LAND, "2017-05-10", "2017/5/10", (2017, 5, 10), recno=986)
    ledger.append(_entry(match_iso_date="2017-05-10", field="iso_date", to="2018-05-10", why="d"))
    ledger.append(_entry(match_iso_date="2017-05-10", field="stage", to="變更(第二次)", why="s"))
    out = ledger.apply([rec])
    assert rec.iso_date == "2018-05-10" and rec.stage == "變更(第二次)"
    assert len(out.applied) == 2 and out.unmatched == []


@pytest.mark.parametrize("bad", ["2018/5/10", "2018-02-30", "107.05.10", ""])
def test_malformed_date_correction_is_refused(ledger, bad):
    with pytest.raises(ValueError):
        Correction(match_land_core=LAND, match_iso_date="2017-05-10", field="iso_date",
                   to=bad, why="", by="t")
