# -*- coding: utf-8 -*-
"""--fresh renames the cache to a timestamped backup instead of deleting it
(P2.2). portal_index.json (the only path to the ~110 oldest portal entries),
no_match_ledger.json, and the per-project result.json dirs are durable state —
a destructive refresh must not destroy what it cannot regenerate."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import LinksDiscovery  # noqa: E402


def test_fresh_renames_the_cache_instead_of_deleting(tmp_path):
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    (cache / "portal_index.json").write_text("[]", encoding="utf-8")
    proj = cache / "中正區-甲段一小段-1地號等1筆"
    proj.mkdir()
    (proj / "result.json").write_text("{}", encoding="utf-8")

    d = LinksDiscovery(cache_dir=str(cache))
    d._fresh_backup()  # the extraction of run()'s fresh branch

    assert cache.exists(), "the cache path must exist again (recreated empty)"
    backups = list(tmp_path.glob(".link_cache_backup_*"))
    assert backups, "the old cache must survive as a timestamped backup"
    backup = backups[0]
    assert (backup / "portal_index.json").exists()
    assert (backup / "中正區-甲段一小段-1地號等1筆" / "result.json").exists()


def test_fresh_backup_names_are_timestamped_and_distinct(tmp_path):
    cache = tmp_path / ".link_cache"
    cache.mkdir()
    d = LinksDiscovery(cache_dir=str(cache))
    d._fresh_backup()
    d._fresh_backup()
    backups = sorted(p.name for p in tmp_path.glob(".link_cache_backup_*"))
    assert len(backups) == 2 and backups[0] != backups[1], (
        "two backups must not collide (timestamped names)")
