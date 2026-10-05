"""Reconciliation tests: additions, net change, and historical movement.

Task group 4 of robust-gazette-ingestion. The scenarios encode the measured limits of
the source: the city edits historical rows and the new export re-dates history, so a
per-record content diff cannot distinguish a deletion from an edit.
"""

from __future__ import annotations

from urtpe.reconcile import reconcile


def _rec(recno: int, date: str, district: str = "中正區", land: str | None = None) -> dict:
    return {"recno": str(recno), "date": date, "district": district, "name": "n",
            "land": land or f"臺北市{district}永昌段三小段{100 + recno}地號等2筆土地",
            "implementer": "i", "planner": "p"}


def _prepend(base: list[dict], n: int) -> list[dict]:
    """n new approvals at the top; every existing 編號 shifted by n."""
    new = [_rec(i, "115/9/1", land=f"臺北市中正區新段{i}地號等1筆土地")
           for i in range(1, n + 1)]
    shifted = [{**r, "recno": str(int(r["recno"]) + n)} for r in base]
    return new + shifted


def _sentinel() -> dict:
    """A newest-cohort row, so the reconciliation boundary sits at 2026-08-27.

    Without it a single-record gazette makes every row "newest", and historical
    behaviour cannot be exercised.
    """
    return _rec(999, "115/8/27", land="臺北市中正區界標段一小段999地號等1筆土地")


# --- additions and net change ------------------------------------------------

def test_prepended_approvals_are_counted_and_nothing_else_moves():
    old = [_rec(i, "115/8/27") for i in range(1, 6)]
    new = _prepend(old, 5)
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert result.new_approvals == 5
    assert result.net_change == 5
    assert result.vanished == []
    assert result.edited == []
    assert result.redated == []
    assert result.ok


def test_every_recno_shifting_is_not_a_change():
    old = [_rec(i, "115/8/27") for i in range(1, 6)]
    new = _prepend(old, 2)
    assert [r["recno"] for r in new][:2] == ["1", "2"]
    assert [r["recno"] for r in old] == ["1", "2", "3", "4", "5"]
    result = reconcile(old, new)
    assert result.net_change == 2
    assert result.vanished == []


def test_previous_newest_date_is_reported():
    old = [_rec(i, "115/8/27") for i in range(1, 4)]
    result = reconcile(old, old + [_rec(9, "115/9/1")], previous_id="a", current_id="b")
    assert result.previous_newest == "2026-08-27"
    assert "previous newest approval: 2026-08-27" in result.report()


def test_no_previous_gazette_is_not_reported_as_all_new():
    result = reconcile(None, [_rec(1, "115/8/27")], current_id="2026-08-11")
    assert not result.comparable
    assert result.new_approvals == 0
    assert "no previous gazette" in result.note
    assert result.ok


def test_out_of_order_reread_names_both_publications():
    old = [_rec(1, "115/8/27")]
    new = old + [_rec(2, "115/8/20", land="臺北市中正區別段9地號等1筆土地")]
    result = reconcile(old, new, previous_id="1150820", current_id="1150827")
    assert "1150820 -> 1150827" in result.report()


# --- historical movement -----------------------------------------------------

def test_redated_historical_row_is_reported_not_blocking():
    old = [_rec(1, "115/1/2", land="臺北市中山區甲段一小段5地號等1筆土地"), _sentinel()]
    new = [_rec(1, "115/6/2", land="臺北市中山區甲段一小段5地號等1筆土地"), _sentinel()]
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert len(result.redated) == 1
    assert result.vanished == []
    assert result.edited == []
    assert result.ok


def test_edited_historical_land_is_reported_separately():
    """An edit shows up as both sides of the churn: the old cell vanishes, the new
    one is an addition the city made. They are not paired, because a multiset
    difference cannot say which new row is the corrected form of which old one."""
    old = [_rec(1, "115/1/2", land="臺北市中山區甲段一小段5地號等1筆土地"), _sentinel()]
    new = [_rec(1, "115/1/2", land="臺北市中山區甲段一小段5、6地號等2筆土地"), _sentinel()]
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert len(result.edited) == 1
    assert len(result.vanished) == 1
    assert result.redated == []
    assert result.ok


def test_redating_and_editing_are_told_apart_at_scale():
    old = [_rec(1, "115/1/2", land="臺北市A段1地號等1筆土地"),
           _rec(2, "115/1/2", land="臺北市B段2地號等1筆土地"),
           _rec(3, "115/1/2", land="臺北市C段3地號等1筆土地"),
           _sentinel()]
    new = [_rec(1, "115/6/2", land="臺北市A段1地號等1筆土地"),        # re-dated, still historical
           _rec(2, "115/1/2", land="臺北市B段2、9地號等2筆土地"),        # land edited
           _rec(3, "115/1/2", land="臺北市D段4地號等1筆土地"),          # land replaced
           _sentinel()]
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert len(result.redated) == 1
    assert len(result.edited) == 2
    assert len(result.vanished) == 2
    assert result.ok


def test_old_record_disappearing_while_list_grows_is_reported_not_blocking():
    """The 89/9/29 case: a 2000-vintage row vanishes, the list still grows."""
    old = [_rec(1, "115/8/27"),
           _rec(2, "89/9/29", land="臺北市大安區仁愛段四小段114地號等6筆土地"),
           _sentinel()]
    new = [_rec(1, "115/8/27"),
           _rec(3, "115/8/20", land="臺北市大安區新段9地號等1筆土地"),
           _sentinel()]
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert result.net_change == 0
    assert len(result.vanished) == 1
    assert "仁愛段四小段114" in result.vanished[0][0]
    assert result.ok, "an old disappearance cannot block: it is indistinguishable from an edit"


def test_accepted_historical_disappearance_is_not_vanished():
    from urtpe.ledger import key_from_raw

    old = [_rec(1, "115/8/27"),
           _rec(2, "89/9/29", land="臺北市大安區仁愛段四小段114地號等6筆土地"),
           _sentinel()]
    new = [old[0], _sentinel()]
    result = reconcile(old, new, accepted_removals={key_from_raw(old[1])})
    assert result.vanished == []
    assert len(result.accepted_removals) == 1


# --- blocking conditions -----------------------------------------------------

def test_shrinking_list_blocks():
    old = [_rec(i, "115/8/27") for i in range(1, 6)]
    new = old[:3]
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert result.net_change == -2
    assert not result.ok
    assert any("shrank" in x for x in result.blocking)


def test_withdrawn_recent_approval_blocks():
    old = [_rec(1, "115/9/1"), _rec(2, "115/8/27")]
    new = [_rec(2, "115/8/27")]
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert result.withdrawn_recent
    assert not result.ok
    assert any("newest cohort" in x for x in result.blocking)


def test_recent_approval_re_dated_away_is_a_withdrawal():
    old = [_rec(1, "115/9/1", land="臺北市中正區新段1地號等1筆土地"), _rec(2, "115/8/27")]
    new = [_rec(1, "115/8/20", land="臺北市中正區新段1地號等1筆土地"), _rec(2, "115/8/27")]
    result = reconcile(old, new, previous_id="a", current_id="b")
    assert result.withdrawn_recent, "a newest-cohort row moved out of the cohort is a withdrawal"


def test_strict_mode_promotes_historical_disappearance():
    old = [_rec(1, "115/8/27"),
           _rec(2, "89/9/29", land="臺北市大安區仁愛段四小段114地號等6筆土地"),
           _sentinel()]
    new = [_rec(1, "115/8/27"),
           _rec(3, "115/8/20", land="臺北市大安區新段9地號等1筆土地"),
           _sentinel()]
    assert reconcile(old, new, strict=False).ok
    strict = reconcile(old, new, strict=True)
    assert not strict.ok
    assert any("strict mode" in x for x in strict.blocking)


def test_strict_mode_is_satisfied_by_a_ledger_acceptance():
    from urtpe.ledger import key_from_raw

    old = [_rec(1, "115/8/27"),
           _rec(2, "89/9/29", land="臺北市大安區仁愛段四小段114地號等6筆土地"),
           _sentinel()]
    new = [_rec(1, "115/8/27"),
           _rec(3, "115/8/20", land="臺北市大安區新段9地號等1筆土地"),
           _sentinel()]
    result = reconcile(old, new, strict=True, accepted_removals={key_from_raw(old[1])})
    assert result.ok


# --- project identities ------------------------------------------------------

def test_moved_project_identity_is_reported():
    result = reconcile([_rec(1, "115/8/27")], [_rec(1, "115/8/27")],
                       previous_projects=["A-1", "A-2"], current_projects=["A-1", "A-2-b"])
    assert ("A-2", "") in result.moved_project_ids
    assert result.unchanged_project_ids == 1
    assert not result.total_rekey
    assert result.ok


def test_zero_moved_identities_is_reported_as_such():
    result = reconcile([_rec(1, "115/8/27")], [_rec(1, "115/8/27")],
                       previous_projects=["A-1", "A-2"], current_projects=["A-1", "A-2"])
    assert result.moved_project_ids == []
    assert result.unchanged_project_ids == 2


def test_total_rekey_is_its_own_blocking_outcome():
    result = reconcile([_rec(1, "115/8/27")], [_rec(1, "115/8/27")],
                       previous_projects=["A-1", "A-2"], current_projects=["B-1", "B-2"])
    assert result.total_rekey
    assert not result.ok
    assert any("total re-key" in b for b in result.blocking)
    assert "TOTAL RE-KEY" in result.report()


# --- calendar ----------------------------------------------------------------

def test_calendar_change_is_reported_explicitly():
    old = [_rec(1, "115/8/27")]
    new = [{"recno": "1", "date": "2026/9/24", "district": "中正區", "name": "n",
            "land": old[0]["land"], "implementer": "i", "planner": "p"}]
    result = reconcile(old, new)
    assert result.calendar_previous == "roc"
    assert result.calendar_current == "gregorian"
    assert "CHANGED" in result.report()


def test_same_calendar_is_reported_as_unchanged():
    old = [_rec(1, "115/8/27")]
    new = [_rec(1, "115/8/20", land="臺北市中正區別段9地號等1筆土地")]
    result = reconcile(old, new)
    assert result.calendar_previous == result.calendar_current == "roc"
    assert "unchanged" in result.report()


def test_land_punctuation_variation_still_matches():
    old = [_rec(1, "115/8/27", land="臺北市中正區永昌段三小段159、161、162地號等113筆土地")]
    new = [{"recno": "1", "date": "115/8/27", "district": "中正區", "name": "n",
            "land": "臺北市中正區永昌段三小段159,161,162 地號等113筆土地",
            "implementer": "i", "planner": "p"}]
    result = reconcile(old, new)
    assert result.vanished == []
    assert result.edited == []
    assert result.redated == []