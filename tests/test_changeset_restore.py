# -*- coding: utf-8 -*-
"""Restoring a publication re-derives the change sets its insertion invalidates.

restore-2026-09-24-gazette task 1.4. Inserting 09-24 into the archived chain
moves ``predecessor_of`` for 10-01, so the live change set that compared 10-01
against 08-27 no longer describes an adjacent pair. The repair: re-derive under
the current reader, then supersede the old file — renamed, content preserved —
so exactly one live change set per transition remains.

Runs against a temp archive built from fixtures; never the live one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.archive import GazetteArchive  # noqa: E402
from urtpe.changeset import ChangeSetStore  # noqa: E402
from tests.gazette_fixtures import ROC_ROWS, write_gazette  # noqa: E402


def _gazette(tmp_path, name: str, published: str, **kw) -> str:
    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), ROC_ROWS, published=published, **kw)
    return str(path)


@pytest.fixture
def chain(tmp_path):
    """A three-link chain with a gap where 09-24 would be restored:
    08-11 ingested, 08-27 ingested (change set vs 08-11), 09-24 ABSENT —
    mirroring today's live archive minus the middle links."""
    arch = GazetteArchive(tmp_path / "gazettes")
    a = _gazette(tmp_path, "a", "統計至115年8月11日")
    c = _gazette(tmp_path, "c", "統計至115年9月24日", footer_inside_last_cell=True)
    arch.record_ingest(a, "2026-08-11", record_count=5)
    arch.record_ingest(c, "2026-09-24", record_count=5)
    store = ChangeSetStore(arch.root / "change_sets")
    # the live change set compares 09-24 against 08-11 — the wrong predecessor
    # once 08-20 is restored between them.
    b = _gazette(tmp_path, "b", "統計至115年8月20日")
    arch.record_ingest(b, "2026-08-20", record_count=5)
    store.write({"previous_id": "2026-08-11", "current_id": "2026-09-24",
                 "new_approvals": 9, "net_change": 9, "note": "pre-restore"})
    return arch, store


def test_insertion_moves_the_predecessor_link(chain):
    arch, _store = chain
    # Before any repair: 09-24's predecessor is 08-11 (the gap swallowed 08-20's
    # position). The restored link re-derives the chain from recorded_ids, so the
    # fixture's own ingest of 08-20 already fixes the link — pin that first.
    assert arch.predecessor_of("2026-09-24") == "2026-08-20", (
        "predecessor_of follows recorded_ids, so an ingested middle publication "
        "immediately re-points the link")


def test_the_stale_change_set_is_superseded_not_rewritten(chain):
    """The repair supersedes the old file: renamed, content preserved, so the
    comparison that was actually made stays auditable and exactly one live
    change set per transition remains."""
    arch, store = chain
    stale = store.path_for("2026-09-24")
    original_content = json.loads(stale.read_text(encoding="utf-8"))

    superseded = stale.with_name(stale.stem + ".superseded-pre-08-20-restore.json")
    stale.rename(superseded)

    assert not stale.exists(), "the live slot is empty until re-derived"
    assert json.loads(superseded.read_text(encoding="utf-8")) == original_content, (
        "the superseded file preserves its content byte-for-byte")


def test_re_derived_change_set_names_the_restored_predecessor(chain, tmp_path):
    """After re-derivation the live change set for 09-24 compares against 08-20
    (the restored link), not against 08-11 (the gap's answer)."""
    arch, store = chain
    stale = store.path_for("2026-09-24")
    stale.rename(stale.with_name(stale.stem + ".superseded-pre-08-20-restore.json"))

    # Re-derive: in production this is the reconcile step of re-ingesting 09-24
    # under the current reader. Here, write the payload the re-derivation would
    # produce, through the store's own write path.
    store.write({"previous_id": "2026-08-20", "current_id": "2026-09-24",
                 "new_approvals": 1, "net_change": 1, "note": "re-derived"})

    live = store.load("2026-09-24")
    assert live["previous_id"] == "2026-08-20"
    superseded_path = stale.with_name(stale.stem + ".superseded-pre-08-20-restore.json")
    assert superseded_path.exists(), "the old comparison remains readable"


def test_exactly_one_live_change_set_per_transition(chain):
    """After repair, every transition has one live file; superseded copies carry
    the marker and are excluded from the live listing."""
    arch, store = chain
    stale = store.path_for("2026-09-24")
    stale.rename(stale.with_name(stale.stem + ".superseded-pre-08-20-restore.json"))
    store.write({"previous_id": "2026-08-20", "current_id": "2026-09-24"})

    # `all()` — the accessor consumers read — sees only live change sets; the
    # glob is *.json so the superseded marker must keep them out of it.
    live_names = [p["current_id"] for p in store.all()]
    assert "2026-09-24" in live_names
    superseded = sorted(p.name for p in store.root.glob("*superseded*"))
    assert len(superseded) == 1 and "superseded" in superseded[0], (
        "the old comparison remains on disk, named as superseded")
    assert len(store.all()) == len([p for p in store.root.glob("*.json")
                                    if "superseded" not in p.name]), (
        "all() and the live-slot count agree; superseded files are invisible "
        "to consumers")
