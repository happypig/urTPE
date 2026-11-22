# -*- coding: utf-8 -*-
"""A3 — a structured result and a failure record for both pollers.

Optimization board, Part I (U3, A3). A coordinator that chains the pollers must read what
happened, not parse prose. Measured 2026-11-22:

* `poll_gazette.py` prints text only. A caller would have to scrape "gazette check: ..."
  lines to learn the gazette id, the SHA-256 and the archived path, and nothing says the
  archived file still matches the index.
* `poll_p168.py` has `--json`, but a failed fetch prints a warning to stderr and returns 1:
  stdout is empty, no log row exists, so "the check failed" and "the check never ran" look
  the same afterwards. The gazette poller already logs its failures; this one did not.
* An exception that `Poller.poll()` does not catch (anything but `PollerError`, or a
  `PollerError` raised after the page fetch) escaped as a traceback with no log row.

Rules this file pins, because the board says A3 changes no acquisition or refusal semantics:
the default text output stays byte-identical; the exit code is 1 for a failed check and
0 for everything else, with or without `--json`; a failed check never replaces the last good
state; and a failed log write never hides the failure it was recording.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.archive import GazetteArchive  # noqa: E402
from urtpe.poller import PollerError, Poller  # noqa: E402

PAGE_URL = "https://uro.gov.taipei/cp.aspx?n=963B15B39CADB94E"
PDF_URL = "https://example.invalid/gazette.pdf"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


poll_gazette = _load("poll_gazette_under_test", "poll_gazette.py")
poll_p168 = _load("poll_p168_under_test", "poll_p168.py")


# --- scripted network for the gazette poller ------------------------------------

def _page(stamp="115-09-29 13:55"):
    return (
        "<html><body><ul>"
        f"<li><i class=\"mark\">資料更新：</i>{stamp}</span></li>"
        "</ul>"
        f'<a href="{PDF_URL}">下載</a>'
        "</body></html>"
    ).encode("utf-8")


class _Net:
    def __init__(self, pages, pdfs):
        self.pages = list(pages)
        self.pdfs = dict(pdfs)

    def fetch_page(self, url):
        item = self.pages.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def fetch_pdf(self, url):
        if url not in self.pdfs:
            raise PollerError("no scripted PDF at %s" % url)
        return self.pdfs[url]


def _gazette_bytes(tmp_path, name="g"):
    from tests.gazette_fixtures import ROC_ROWS, write_gazette

    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), ROC_ROWS)
    return path.read_bytes()


@pytest.fixture
def gz(tmp_path, monkeypatch):
    """`poll_gazette.main` against a temp archive and a scripted network."""
    root = tmp_path / "gazettes"
    holder = {"net": None}

    class ScriptedPoller(Poller):
        def __init__(self, archive, **kw):
            super().__init__(archive, net=holder["net"], **kw)

    monkeypatch.setattr(poll_gazette, "Poller", ScriptedPoller)

    def run(net, *flags, capsys=None):
        holder["net"] = net
        return poll_gazette.main(["--archive-root", str(root), *flags])

    run.root = root
    run.archive = lambda: GazetteArchive(root)
    run.log_rows = lambda: [json.loads(x) for x in
                            (root / "poll_log.jsonl").read_text(encoding="utf-8").splitlines()
                            if x] if (root / "poll_log.jsonl").exists() else []
    return run


def _json_out(capsys):
    return json.loads(capsys.readouterr().out)


# --- poll_gazette: --json ----------------------------------------------------------

def test_json_reports_a_new_gazette_with_its_verified_archived_path(gz, tmp_path, capsys):
    body = _gazette_bytes(tmp_path)
    rc = gz(_Net([_page()], {PDF_URL: body}), "--json")
    out = _json_out(capsys)
    assert rc == 0
    assert out["status"] == "new_gazette"
    assert out["sha256"] == hashlib.sha256(body).hexdigest()
    assert out["gazette_id"]
    assert Path(out["path"]).is_file()
    assert out["verified"] is True
    assert out["ingested"] is False            # acquisition is never ingestion


def test_json_reports_a_reupload_of_a_held_gazette(gz, tmp_path, capsys):
    body = _gazette_bytes(tmp_path)
    gz.archive().record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    rc = gz(_Net([_page()], {PDF_URL: body}), "--json")
    out = _json_out(capsys)
    assert rc == 0
    assert out["status"] == "reuploaded"
    assert out["gazette_id"] == "2026-09-24"
    assert out["verified"] is True


def test_json_says_not_verified_when_the_archived_file_no_longer_matches(gz, tmp_path, capsys):
    body = _gazette_bytes(tmp_path)
    gz(_Net([_page(), _page()], {PDF_URL: body}), "--json")
    first = _json_out(capsys)
    Path(first["path"]).write_bytes(b"altered after archiving")
    rc = gz(_Net([_page()], {}), "--json")      # page unchanged: the poller does not refetch
    out = _json_out(capsys)
    assert rc == 0                              # a mismatch is reported, never a new exit code
    assert out["status"] == "unchanged"
    assert out["verified"] is False
    assert "does not match" in out["verify_error"]


def test_json_leaves_verified_null_when_there_is_no_gazette_to_verify(gz, capsys):
    rc = gz(_Net([_page()], {}), "--json", "--dry-run")
    out = _json_out(capsys)
    assert rc == 0
    assert out["status"] == "would_download"    # every status passes through
    assert out["verified"] is None
    assert out["path"] == ""


def test_json_reports_a_failed_check_and_exits_one(gz, capsys):
    rc = gz(_Net([PollerError("publisher unreachable")], {}), "--json")
    out = _json_out(capsys)
    assert rc == 1
    assert out["status"] == "failed"
    assert out["error"] == "publisher unreachable"
    assert gz.log_rows()[-1]["status"] == "failed"


# --- poll_gazette: the text contract does not move --------------------------------

def test_the_default_text_output_is_unchanged(gz, tmp_path, capsys):
    body = _gazette_bytes(tmp_path)
    gz.archive().record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    rc = gz(_Net([_page()], {PDF_URL: body}))
    digest = hashlib.sha256(body).hexdigest()
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == [
        "gazette check: reuploaded",
        "  publisher 資料更新 : 115-09-29 13:55   (provenance only, not the decision)",
        "  gazette             : 2026-09-24",
        "  sha256              : %s" % digest,
        "  detail              : publisher re-uploaded identical content (gazette 2026-09-24)",
    ]


# --- poll_gazette: an unexpected failure leaves a record ---------------------------

class _Boom(_Net):
    def fetch_page(self, url):
        raise RuntimeError("the network layer fell over")


def test_an_unexpected_exception_is_recorded_and_exits_one(gz, capsys):
    rc = gz(_Boom([], {}))
    assert rc == 1
    rows = gz.log_rows()
    assert rows and rows[-1]["status"] == "failed"
    assert "RuntimeError" in rows[-1]["error"]
    assert "the network layer fell over" in rows[-1]["error"]
    assert "gazette check: failed" in capsys.readouterr().out


def test_an_unexpected_exception_shows_in_json_too(gz, capsys):
    rc = gz(_Boom([], {}), "--json")
    out = _json_out(capsys)
    assert rc == 1
    assert out["status"] == "failed"
    assert "RuntimeError" in out["error"]


def test_a_dry_run_failure_writes_no_log(gz):
    rc = gz(_Boom([], {}), "--dry-run")
    assert rc == 1
    assert gz.log_rows() == []


# --- Poller.record_failure ---------------------------------------------------------

def test_record_failure_writes_one_failed_row(tmp_path):
    archive = GazetteArchive(tmp_path / "gazettes")
    poller = Poller(archive, page_url=PAGE_URL, net=_Net([], {}))
    outcome = poller.record_failure("RuntimeError: x")
    assert outcome.status == "failed" and outcome.detail == "RuntimeError: x"
    rows = Poller.read_records(archive)
    assert len(rows) == 1
    assert rows[0]["status"] == "failed" and rows[0]["error"] == "RuntimeError: x"


def test_record_failure_never_hides_the_failure_behind_a_log_error(tmp_path):
    archive = GazetteArchive(tmp_path / "gazettes")
    poller = Poller(archive, page_url=PAGE_URL, net=_Net([], {}))
    poller.log_path.parent.mkdir(parents=True, exist_ok=True)
    poller.log_path.mkdir()                       # appending to a directory raises OSError
    outcome = poller.record_failure("RuntimeError: x")
    assert outcome.status == "failed"


# --- poll_p168 ----------------------------------------------------------------------

ROWS = [{"case_id": "10101011", "T_name": "甲"}, {"case_id": "10101012", "T_name": "乙"}]


@pytest.fixture
def p168(tmp_path, monkeypatch):
    root = tmp_path / "gazettes"
    root.mkdir()
    state = {"rows": ROWS}
    monkeypatch.setattr(poll_p168, "fetch_taipei_168_list_api", lambda *a, **k: state["rows"])

    def run(*flags):
        return poll_p168.main(["--archive-root", str(root), *flags])

    run.root = root
    run.state = state
    run.log = lambda: [json.loads(x) for x in
                       (root / "p168_log.jsonl").read_text(encoding="utf-8").splitlines() if x] \
        if (root / "p168_log.jsonl").exists() else []
    return run


def test_p168_json_carries_a_status_word(p168, capsys):
    assert p168("--json") == 0
    assert json.loads(capsys.readouterr().out)["status"] == "first_seen"
    assert p168("--json") == 0
    assert json.loads(capsys.readouterr().out)["status"] == "unchanged"
    p168.state["rows"] = ROWS + [{"case_id": "10101013", "T_name": "丙"}]
    assert p168("--json") == 0
    assert json.loads(capsys.readouterr().out)["status"] == "changed"


def test_p168_json_keeps_every_existing_key(p168, capsys):
    p168("--json")
    out = json.loads(capsys.readouterr().out)
    for key in ("rows", "sha256", "previous_sha256", "changed", "first_seen",
                "checked_at", "dry_run", "snapshot"):
        assert key in out, key


def test_p168_failed_fetch_prints_a_failed_object_on_stdout(p168, capsys):
    p168.state["rows"] = []
    rc = p168("--json")
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "failed"
    assert "empty" in out["error"]


def test_p168_failed_fetch_leaves_a_failed_log_row(p168):
    p168.state["rows"] = []
    assert p168() == 1
    rows = p168.log()
    assert len(rows) == 1
    assert rows[0]["status"] == "failed" and rows[0]["error"]


def test_p168_failed_fetch_keeps_the_last_good_state(p168):
    assert p168() == 0
    before = (p168.root / "p168_state.json").read_text(encoding="utf-8")
    p168.state["rows"] = []
    assert p168() == 1
    assert (p168.root / "p168_state.json").read_text(encoding="utf-8") == before


def test_p168_dry_run_failure_writes_no_log(p168):
    p168.state["rows"] = []
    assert p168("--dry-run") == 1
    assert p168.log() == []


def test_p168_text_failure_message_is_unchanged(p168, capsys):
    p168.state["rows"] = []
    assert p168() == 1
    err = capsys.readouterr().err
    assert err.startswith("[WARN] the 168 list came back empty")


def test_p168_a_write_error_is_reported_as_a_failed_check(p168, capsys):
    (p168.root / "p168_snapshots").write_text("a file where the directory should be",
                                              encoding="utf-8")
    rc = p168("--json")
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "failed"
    assert out["error"]


def test_p168_a_failed_log_write_does_not_hide_the_failure(p168, capsys):
    p168.state["rows"] = []
    (p168.root / "p168_log.jsonl").mkdir()       # appending to a directory raises OSError
    rc = p168("--json")
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "failed"
