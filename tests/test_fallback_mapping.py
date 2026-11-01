# -*- coding: utf-8 -*-
"""The curated fallback mapping file is tracked, rooted, and defined once.

P2.3 (docs/inspection.md Wave 1 item 3): `data/taipei_case_ids.json` is a
curated, human-verified land-core -> view/case mapping — the same category as
the tracked `data/twur_overrides.json` — yet git did not track it and the path
was CWD-relative, so a clone lost it silently. It is now tracked (`.gitignore`
negation), and both consumers import the single constant defined here, resolved
from the repository root.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import FALLBACK_MAPPING_FILE, load_fallback_mapping  # noqa: E402


def test_the_constant_is_the_only_definition():
    """One definition: urtpe/links.py owns the path; urtpe/cli.py imports it.
    A second hardcoded copy is exactly how a clone-safety fix gets lost."""
    import urtpe.cli as cli

    assert cli.FALLBACK_MAPPING_FILE is FALLBACK_MAPPING_FILE, (
        "urtpe/cli.py must import the constant from urtpe.links, not redefine it")


def test_the_path_is_repo_rooted_not_cwd_relative():
    """A clone in any working directory resolves the same file."""
    assert FALLBACK_MAPPING_FILE.is_absolute()
    assert FALLBACK_MAPPING_FILE == ROOT / "data" / "taipei_case_ids.json"


def test_the_file_exists_and_is_valid_json():
    """The tracked file must parse; a clone depends on it."""
    assert FALLBACK_MAPPING_FILE.exists(), (
        "data/taipei_case_ids.json is tracked configuration; it must exist")
    data = json.loads(FALLBACK_MAPPING_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    for core, entry in data.items():
        assert "view_id" in entry and "case_ids" in entry, core
        assert isinstance(entry["case_ids"], list), core


def test_load_fallback_mapping_round_trips_the_tracked_file():
    loaded = load_fallback_mapping()
    data = json.loads(FALLBACK_MAPPING_FILE.read_text(encoding="utf-8"))
    assert loaded == data, "the loader must read exactly the tracked file"
