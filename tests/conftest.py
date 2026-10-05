# -*- coding: utf-8 -*-
"""Test-session isolation for state that lives outside the working tree.

The gazette archive and the correction ledger default to a sibling of the repository,
so they are shared by every process that imports urtpe — including the test suite.
Fixture PDFs can carry a real publication's 統計至 date (the sample fixtures use
115年8月11日, which is a genuine gazette date), so an unisolated test run writes a
20 KB test PDF over a real archive member and appends its record count to the live
index.

Pointing both at a temporary directory for the whole session makes that impossible
rather than merely discouraged, without needing every test to remember a flag.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_SESSION_ROOT = Path(tempfile.mkdtemp(prefix="urtpe-test-state-"))


def pytest_configure(config):
    os.environ.setdefault("URTPE_ARCHIVE_ROOT", str(_SESSION_ROOT / "gazettes"))
    os.environ.setdefault("URTPE_LEDGER", str(_SESSION_ROOT / "corrections.jsonl"))


@pytest.fixture(scope="session", autouse=True)
def _isolate_external_state():
    """Fail loudly if any test wrote outside the temporary state directory."""
    from urtpe.archive import GazetteArchive
    from urtpe.ledger import CorrectionLedger

    archive_root = Path(GazetteArchive().root)
    ledger_path = Path(CorrectionLedger().path)
    repo_root = Path(__file__).resolve().parents[1]
    for path, label in ((archive_root, "archive"), (ledger_path, "ledger")):
        assert repo_root not in path.parents, f"{label} escaped the session temp dir: {path}"
        assert not path.exists() or _SESSION_ROOT in path.parents or path.parent == _SESSION_ROOT, (
            f"{label} wrote outside the session temp dir: {path}")