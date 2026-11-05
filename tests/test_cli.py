"""CLI helper tests: projects.data.js round-trip preserves emitted state."""

from __future__ import annotations

import json

from urtpe.cli import _load_projects_from_js


def _write_js(tmp_path, doc):
    path = tmp_path / "projects.data.js"
    path.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";", encoding="utf-8")
    return str(path)


def test_load_from_js_restores_implementation_state(tmp_path):
    node = {
        "recno": 991,
        "date": "2026-08-11",
        "stage": "核定",
        "track": "事業計畫",
        "case_name": "擬訂中山區中山段一小段254地號等13筆都市更新事業計畫案",
        "district": "中山區",
        "implementation": {"Exe_Way": "權利變換", "case_id": "09811141"},
        "links": {"taipei": ["09811141"]},
    }
    doc = {
        "schema_version": 2,
        "generated_at": "t",
        "source": "s",
        "published_date": "",
        "projects": [
            {
                "project_id": "中山區-中山段一小段-254地號等13筆",
                "anchor_recno": 991,
                "nodes": [node],
                "links": {},
                "implementation": {"Exe_Way": "權利變換", "case_id": "09811141"},
                "rewards": {"F0": "8,982.01", "case_id": "09811141"},
            }
        ],
    }
    path = _write_js(tmp_path, doc)
    projects, meta = _load_projects_from_js(path)

    assert meta["generated_at"] == "t"
    project = projects[0]
    assert project.implementation == {"Exe_Way": "權利變換", "case_id": "09811141"}
    assert project.rewards["F0"] == "8,982.01"
    rec = next(r for r in project.members if r.recno == 991)
    assert rec.implementation == {"Exe_Way": "權利變換", "case_id": "09811141"}


def test_load_from_js_aliases_orphan_milestones_key(tmp_path):
    """D1 (inspection-batchD): an old payload's orphan `milestones_national`
    (Taipei ashx data under a false name) loads as `milestones_taipei_case`;
    a project-level `milestones_national` is NOT aliased (it IS national)."""
    orphan_node = {
        "recno": "v09907221",
        "virtual": True,
        "case_id": "09907221",
        "date": "",
        "stage": "擬訂",
        "track": "事業計畫",
        "case_name": "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案",
        "links": {"taipei": ["09907221"], "milestones_national": {"核定日期": "2019/01/31"}},
    }
    doc = {
        "schema_version": 2,
        "generated_at": "t",
        "source": "s",
        "published_date": "",
        "projects": [
            {
                "project_id": "文山區-木柵段三小段-623地號等39筆",
                "anchor_recno": 1,
                "nodes": [orphan_node],
                "links": {"milestones_national": {"使用核發日期": "109.10.25"}},
            }
        ],
    }
    path = _write_js(tmp_path, doc)
    projects, _ = _load_projects_from_js(path)
    rec = projects[0].members[0]
    assert rec.links.get("milestones_taipei_case") == {"核定日期": "2019/01/31"}
    assert "milestones_national" not in rec.links


# --------------------------------------------------------------------------
# --ledger default (D5, ledger-confirm-merge): a PDF ingest without the flag
# applies the default ledger; conftest points URTPE_LEDGER at a session temp
# file, so the default the parser sees is the session path.
# --------------------------------------------------------------------------

def test_parser_ledger_default_is_the_default_ledger_path():
    """parse_args without --ledger yields ledger == str(DEFAULT_LEDGER_PATH).

    conftest sets URTPE_LEDGER into the session temp dir before urtpe.ledger is
    imported, so the resolved default is the session path, not the live ledger.
    """
    from urtpe import cli, ledger as ledger_mod

    parser = cli._build_parser()
    args = parser.parse_args([])
    assert args.ledger == str(ledger_mod.DEFAULT_LEDGER_PATH)


def test_ingest_without_ledger_file_reports_zero_applied(tmp_path):
    """A PDF ingest with no ledger file completes and reports 0 applied."""
    from tests.gazette_fixtures import ROC_ROWS, write_gazette
    from urtpe import cli

    pdf = tmp_path / "g.pdf"
    write_gazette(str(pdf), ROC_ROWS, published="統計至115年8月11日")
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([str(pdf), "-o", str(out)]) == 0
    report = (out / "review_report.txt").read_text(encoding="utf-8")
    assert "manual corrections applied: 0" in report


def test_ingest_applies_a_default_ledger_entry(tmp_path):
    """The default-ledger path is wired: an entry in the session ledger applies
    to an ingest run that names no --ledger option."""
    from tests.gazette_fixtures import ROC_ROWS, write_gazette
    from urtpe import cli, ledger as ledger_mod

    # Full contiguity: the tripwire refuses gaps between 編號 1..5.
    rows = [tuple([str(i + 1), r[1], *r[2:]]) for i, r in enumerate(ROC_ROWS)]
    row = rows[4]  # 中正區 永昌段三小段159地號等113筆
    land = "臺北市中正區永昌段三小段159、161、162地號等113筆土地"
    # The ledger now applies on EVERY PDF ingest (D5), so the session ledger is
    # live state for every later test in this run: append the probe entry and
    # restore the file afterwards, or the byte-identity acceptance test
    # ingests this correction and fails.
    ledger_path = ledger_mod.CorrectionLedger().path
    saved = ledger_path.read_bytes() if ledger_path.exists() else None
    try:
        ledger_mod.CorrectionLedger().append(ledger_mod.Correction(
            match_land_core=ledger_mod.normalize_land(land),
            match_iso_date="2026-08-11", field="implementer", to="乙公司",
            why="test: the default path applies the ledger", by="test"))
        pdf = tmp_path / "g.pdf"
        write_gazette(str(pdf), rows, published="統計至115年8月11日")
        out = tmp_path / "out"
        out.mkdir()
        assert cli.main([str(pdf), "-o", str(out)]) == 0
        report = (out / "review_report.txt").read_text(encoding="utf-8")
        assert "manual corrections applied: 1" in report
    finally:
        if saved is None:
            ledger_path.unlink(missing_ok=True)
        else:
            ledger_path.write_bytes(saved)
