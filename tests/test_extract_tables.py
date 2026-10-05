"""Reader tests: table-based extraction across calendars and table defects.

Task group 1 of robust-gazette-ingestion.
"""

from __future__ import annotations

import pytest

from urtpe import extract as E
from urtpe.extract import extract_pdf as extract_all
from tests.gazette_fixtures import ROC_ROWS, VERBATIM_ROWS, write_gazette


def _pdf(tmp_path, name: str, rows=None, **kw) -> str:
    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), rows if rows is not None else ROC_ROWS, **kw)
    return str(path)


def test_roc_publication_yields_one_row_per_recno(tmp_path):
    recs = E.extract_pdf(_pdf(tmp_path, "roc"))
    assert [r["recno"] for r in recs] == ["1", "2", "3", "4", "5"]


def test_columns_are_assigned_to_the_right_cells(tmp_path):
    recs = E.extract_pdf(_pdf(tmp_path, "cols"))
    first = recs[0]
    assert first["date"] == "115/8/27"
    assert first["district"] == "北投區"
    assert first["name"] == ROC_ROWS[0][3]
    assert first["land"] == ROC_ROWS[0][4]
    assert first["implementer"] == ROC_ROWS[0][5]
    assert first["planner"] == ROC_ROWS[0][6]


def test_gregorian_publication_matches_roc_row_for_row(tmp_path):
    roc = E.extract_pdf(_pdf(tmp_path, "roc2"))
    greg = E.extract_pdf(_pdf(tmp_path, "greg", calendar="gregorian"))
    assert len(greg) == len(roc)
    for a, b in zip(roc, greg):
        assert a["district"] == b["district"]
        assert a["name"] == b["name"]
        assert a["land"] == b["land"]
        assert a["recno"] == b["recno"]
    assert greg[0]["date"] == "2026/8/27"


def test_column_shift_changes_no_cell_assignment(tmp_path):
    base = E.extract_pdf(_pdf(tmp_path, "base"))
    shifted = E.extract_pdf(_pdf(tmp_path, "shift", shift=8.0))
    assert base == shifted


def test_mixed_calendars_normalize_per_cell_and_are_reported(tmp_path):
    path = _pdf(tmp_path, "mixed", calendar="mixed")
    recs, meta = E.extract_pdf_with_meta(path)
    assert [r["date"] for r in recs][:2] == ["115/8/27", "2026/8/26"]
    assert meta["calendar"].startswith("mixed")
    from urtpe.extract import to_iso

    assert to_iso("115/8/27")[0] == "2026-08-27"
    assert to_iso("2026/8/26")[0] == "2026-08-26"


def test_unparseable_date_is_flagged_not_silently_zeroed(tmp_path):
    recs = [{"recno": "1", "date": "not-a-date", "district": "中正區",
             "name": "n", "land": "l", "implementer": "i", "planner": "p"}]
    raws = E.to_raw_records(recs)
    assert "核定日期缺漏" in raws[0].parse_error
    assert E.to_iso("not-a-date") == (None, None)


def test_merged_cell_aborts_with_location(tmp_path):
    path = _pdf(tmp_path, "merged", merged_cells=((0, 4),))
    with pytest.raises(E.TableStructureError) as excinfo:
        E.extract_pdf(path)
    rendered = str(excinfo.value)
    assert "merged cell" in rendered
    assert "land" in rendered
    assert "page 1" in rendered


def test_merged_cell_text_is_not_duplicated_forward(tmp_path):
    """The spanning cell's text must not appear in the row below it."""
    path = _pdf(tmp_path, "merged2", merged_cells=((0, 3),))
    with pytest.raises(E.TableStructureError):
        E.extract_pdf(path)


def test_page_without_ruling_lines_aborts_and_reports_page(tmp_path):
    path = _pdf(tmp_path, "borderless", borderless_pages=(0,))
    with pytest.raises(E.TableStructureError) as excinfo:
        E.extract_pdf(path)
    faults = excinfo.value.faults
    assert any(f.kind == "no table on page" and f.page == 1 for f in faults)
    assert "fall back" in str(excinfo.value)


def test_ragged_row_aborts(tmp_path):
    """A row with fewer cells than the header must abort rather than be padded."""
    path = _pdf(tmp_path, "ragged")

    class _Row:
        def __init__(self, cells):
            self.cells = cells

    class _Table:
        rows = [_Row([(0.0, 0.0, 10.0, 10.0)] * 7)]

        def extract(self):
            # One well-formed row, then a row that is short.
            return [["1", "2", "3", "4", "5", "6", "7"],
                    ["2", "3", "4", "5", "6", "7"]]

    class _Found:
        tables = [_Table()]

    class _Page:
        number = 0
        rect = None

        def find_tables(self, strategy=None):
            return _Found()

        def get_drawings(self):
            return []

    faults: list = []
    E._page_records(_Page(), faults)
    assert faults, "a row narrower than the header must be reported"
    assert any(f.kind == "ragged row" for f in faults)


def test_repeated_header_row_is_discarded_and_last_record_survives(tmp_path):
    """The 1151002 defect: row 1 repeats in every page header.

    All five records must still be present, each exactly once, with the final
    record of the last page emitted in full.
    """
    path = _pdf(tmp_path, "repeat", rows_per_page=2, repeat_header_row=True)
    recs, meta = E.extract_pdf_with_meta(path)
    assert [r["recno"] for r in recs] == ["1", "2", "3", "4", "5"]
    assert len({r["recno"] for r in recs}) == 5
    assert recs[-1]["land"] == ROC_ROWS[-1][4]
    assert recs[-1]["implementer"] == ROC_ROWS[-1][5]


def test_wrapped_cells_are_rejoined_without_inventing_whitespace(tmp_path):
    recs = E.extract_pdf(_pdf(tmp_path, "wrap"))
    first = recs[0]
    # The 段小段 token must survive intact: a wrap never splits it.
    assert "振興段四小段" in first["land"]
    assert "振興 段四小段" not in first["land"]
    for rec in recs:
        assert "\n" not in rec["name"]
        assert "\n" not in rec["land"]


def test_sub_parcel_hyphen_is_never_split(tmp_path):
    recs = E.extract_pdf(_pdf(tmp_path, "hyphen"))
    land = " ".join(r["land"] for r in recs)
    assert "168-2" in land
    assert "168 -2" not in land
    assert "764-1" not in land or "764 -1" not in land


def test_baseline_positional_reader_bleeds_across_record_boundaries():
    """The 1150827 defect the new reader eliminates: 40 records whose 地號 cell
    carried the previous record's tail. The signature is a land cell that does not
    begin at its own 臺北市 prefix but carries a previous cell's fragment first."""
    import re

    # Observed spill (1150827 recno 54, positional reader):
    spilled = "號等138筆土地臺北市中正區南海段二小段164-2、164-11、164-15、171地號等6筆土地"
    # A clean cell always starts with its own 臺北市... prefix and contains exactly
    # one 地號等N筆 clause.
    clean = "臺北市中正區南海段二小段164-2、164-11、164-15、171地號等6筆土地"
    assert clean.startswith("臺北市")
    assert len(re.findall(r"地號等\d+筆土地", clean)) == 1
    # The spilled cell starts before its own prefix and closes two cells' worth.
    assert not spilled.startswith("臺北市")
    assert len(re.findall(r"筆土地", spilled)) == 2
    # The new reader cannot produce this shape: it takes the cell from the
    # document's ruling lines rather than from a midpoint between numbers.
    from tests.gazette_fixtures import ROC_ROWS, write_gazette
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        write_gazette(f"{d}/g.pdf", ROC_ROWS)
        for rec in extract_all(f"{d}/g.pdf"):
            assert rec["land"].startswith("臺北市")


def test_known_data_errors_survive_extraction_verbatim(tmp_path):
    recs = E.extract_pdf(_pdf(tmp_path, "verbatim", rows=VERBATIM_ROWS))
    joined = " ".join(r["name"] + r["land"] for r in recs)
    assert "松化區" in joined          # district typo, cleaned later
    assert "計劃" in joined            # 計劃 -> 計畫, cleaned later
    assert "_核定公告" in joined       # suffix kept
    assert recs[0]["district"] == "松化區"


def test_published_date_is_read_from_each_document(tmp_path):
    a = _pdf(tmp_path, "pa", published="統計至115年8月11日")
    b = _pdf(tmp_path, "pb", published="統計至115年9月24日")
    assert E.find_published_date(a) == "2026-08-11"
    assert E.find_published_date(b) == "2026-09-24"
    _, meta_a = E.extract_pdf_with_meta(a)
    _, meta_b = E.extract_pdf_with_meta(b)
    assert meta_a["published_date"] != meta_b["published_date"]
    assert meta_a["gazette_id"] == "2026-08-11"


def test_gazette_id_is_attached_to_every_row(tmp_path):
    recs = E.extract_pdf(_pdf(tmp_path, "gid"))
    assert {r["gazette_id"] for r in recs} == {"2026-08-11"}
    raws = E.to_raw_records(recs)
    assert all(r.gazette_id == "2026-08-11" for r in raws)


# ---------------------------------------------------------------------------
# Task group 0: baseline tests pinning the failure this change exists to prevent.
# These are the regressions the positional reader could not survive.
# ---------------------------------------------------------------------------

def test_baseline_positional_reader_fails_on_gregorian_publication(tmp_path):
    """The 1151002 failure mode: ROC-only date matching loses every date.

    The positional reader's date band is strict ROC, so a Gregorian publication
    yields unparseable dates. This is the baseline the new reader is measured against.
    """
    greg = E.to_iso("2026/9/24")
    assert greg == ("2026-09-24", (2026, 9, 24))
    # The old rule could not do this: its regex allowed at most 3 year digits.
    import re

    assert re.fullmatch(r"(\d{1,3})/(\d{1,2})/(\d{1,2})", "2026/9/24") is None


def test_baseline_column_shift_is_invisible_to_the_new_reader(tmp_path):
    """An 8pt shift broke the old bands at exactly x=185; the new reader is unaffected."""
    base = E.extract_pdf(_pdf(tmp_path, "b0"))
    for shift in (4.0, 8.0, 12.0):
        shifted = E.extract_pdf(_pdf(tmp_path, f"b{shift}", shift=shift))
        assert shifted == base


def test_baseline_repeated_header_row_would_have_became_245_phantoms(tmp_path):
    """The old reader anchored records on standalone numbers, so each repeated
    header row became its own record and truncated the page's last real record."""
    path = _pdf(tmp_path, "phantom", rows_per_page=2, repeat_header_row=True)
    recs = E.extract_pdf(path)
    assert len(recs) == len(ROC_ROWS)
    assert len({r["recno"] for r in recs}) == len(ROC_ROWS)

# --- 1.13 page furniture absorbed into a cell (Defect 1, reader fault) --------

def test_page_number_inside_the_last_land_cell_is_not_emitted_as_cell_text(tmp_path):
    """The city's layout prints the page number inside the last row's 地號 cell.

    A reader that trusts the cell rectangle absorbs it, leaving a land cell that
    ends in a bare integer. Confirmed in the real gazettes 11 of 11 times: the
    trailing digits always equal the page the row sits on.
    """
    recs = E.extract_pdf(_pdf(tmp_path, "footer", footer_inside_last_cell=True))
    assert recs[-1]["land"] == ROC_ROWS[-1][4]
    assert not recs[-1]["land"].rstrip()[-1].isdigit()


def test_page_number_below_the_table_leaves_every_land_cell_intact(tmp_path):
    """The control: with the footer outside the table, nothing changes."""
    recs = E.extract_pdf(_pdf(tmp_path, "nofooter"))
    assert [r["land"] for r in recs] == [r[4] for r in ROC_ROWS]


# --- 1.14 publisher truncation (Defect 2, source fault) ----------------------

def test_source_truncated_land_cell_is_reported_with_its_location(tmp_path):
    """The publisher stops drawing the parcel list at the printed row height.

    The missing text is not in the PDF at all, so the record cannot be repaired.
    It must be reported as a source fault naming page, row and column.
    """
    _recs, faults = E.extract_pdf_with_faults(_pdf(tmp_path, "clipped", longest_land_row=2))
    assert [f.kind for f in faults] == ["source_truncated_land_cell"]
    fault = faults[0]
    assert fault.recno == "3"
    assert fault.column == "地號"
    assert fault.page is not None and fault.row is not None


def test_source_truncated_record_is_excluded_from_the_emitted_rows(tmp_path):
    """A record with an unknown parcel tail must not reach the dataset, and its
    loss must not be silent."""
    recs, faults = E.extract_pdf_with_faults(_pdf(tmp_path, "clipped2", longest_land_row=2))
    assert len(faults) == 1
    assert [r["recno"] for r in recs] == ["1", "2", "4", "5"]


def test_gazette_with_no_truncation_emits_every_record_and_no_faults(tmp_path):
    recs, faults = E.extract_pdf_with_faults(_pdf(tmp_path, "clean"))
    assert faults == []
    assert [r["recno"] for r in recs] == ["1", "2", "3", "4", "5"]


# --- 1.15 published terminal wording is not a fault (1.16 fixture support) ---

BENIGN_LAND = [
    "臺北市中正區甲段一小段 1、2、3 地號等共 3筆土地",
    "臺北市大安區乙段二小段 5、6 地號等 2 筆土地)",
    "臺北市松山區丙段三小段 9、10 地號等 2 筆土 地",
    "臺北市信義區丁段四小段 11、12 地號等2筆",
]


def test_published_terminal_variations_are_not_faults(tmp_path):
    """`地號等共 N筆土地`, a trailing paren, 土地 split across a line, and a bare
    `地號等N筆` all carry a complete parcel list and must extract normally."""
    rows = [
        (i + 1, "115/8/%02d" % (27 - i), "中正區",
         "擬訂臺北市中正區甲段一小段%d地號等3筆土地都市更新事業計畫案" % (i + 1),
         BENIGN_LAND[i], "甲公司", "乙顧問")
        for i in range(len(BENIGN_LAND))
    ]
    recs, faults = E.extract_pdf_with_faults(
        _pdf(tmp_path, "benign", rows=rows, paginate=False)
    )
    assert faults == []
    assert [r["recno"] for r in recs] == ["1", "2", "3", "4"]
    for rec, land in zip(recs, BENIGN_LAND):
        flat = rec["land"].replace(" ", "")
        assert flat == land.replace(" ", "")


# --- 1.17 only the closing phrase was cut (count self-check) -----------------

def test_land_cell_missing_only_its_closing_phrase_is_kept(tmp_path):
    """The publisher sometimes cuts `地號等N筆土地` while drawing every parcel.

    The row's own 案名 still declares N parcels and the cell still shows N, so the
    list is provably whole. Measured on 1150827 編號 868 and 909, where the reader
    was discarding two sound records for want of a closing phrase.
    """
    rows = [
        (1, "115/8/27", "萬華區",
         "擬訂臺北市萬華區測試段一小段100地號等4筆土地都市更新事業計畫案",
         "臺北市萬華區測試段一小段 100、101、102、103 地號等4筆土地",
         "甲公司", "乙顧問"),
        (2, "115/8/26", "大安區",
         "擬訂臺北市大安區測試段二小段200地號等2筆土地都市更新事業計畫案",
         "臺北市大安區測試段二小段 200、201 地號等2筆土地",
         "丙公司", "丁顧問"),
    ]
    recs, faults = E.extract_pdf_with_faults(
        _pdf(tmp_path, "noterm", rows=rows, paginate=False, land_without_terminator=1)
    )
    assert faults == []
    assert [r["recno"] for r in recs] == ["1", "2"]
    assert "地號等" not in recs[1]["land"]
    assert E.parcel_token_count(recs[1]["land"]) == 2


def test_land_cell_short_of_its_declared_count_is_still_excluded(tmp_path):
    """The count self-check must not admit a cell that really is missing parcels."""
    recs, faults = E.extract_pdf_with_faults(
        _pdf(tmp_path, "short", longest_land_row=2)
    )
    assert [f.kind for f in faults] == ["source_truncated_land_cell"]
    assert "3" not in {r["recno"] for r in recs}


def test_parcel_token_count_ignores_the_section_prefix(tmp_path):
    """Section numbers must not be mistaken for parcels, or every count self-check
    would pass and nothing would ever be excluded."""
    assert E.parcel_token_count("臺北市萬華區漢中段二小段328、329、330 地號等3筆土地") == 3
    assert E.parcel_token_count("臺北市萬華區漢中段二小段328、329、330") == 3
    assert E.declared_parcel_count("擬訂臺北市萬華區漢中段二小段328地號等3筆土地都市更新事業計畫案") == 3
    assert E.declared_parcel_count("無筆數資訊") is None
