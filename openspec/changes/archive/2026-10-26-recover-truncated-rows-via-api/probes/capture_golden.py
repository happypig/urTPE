# -*- coding: utf-8 -*-
"""Capture the PRE-CHANGE unflagged baseline for the recovery acceptance test.

One-shot (2026-10-26, before any implementation of recover-truncated-rows-via-api).
Builds the acceptance gazette (tests/fixtures_recovery.build_fixture_pdf), runs
urtpe.cli.main WITHOUT the recovery flag into a temp tree with an isolated archive,
and copies the four emitted artifacts into tests/fixtures/recovery/golden_unflagged/.

The acceptance test compares the post-change unflagged output against these bytes:
the change must not alter the flag-less path at all (task 2.9 / 6.3). Note
projects.json embeds generated_at and the source path, so the test normalizes those
two keys before comparing; raw.tsv / clean.tsv / merged.tsv / review_report.txt
compare byte-for-byte.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"D:\project\urTPE")

REPO = Path(r"D:\project\urTPE")
GOLDEN = REPO / "tests" / "fixtures" / "recovery" / "golden_unflagged"

tmp = Path(tempfile.mkdtemp(prefix="urtpe-golden-"))
os.environ["URTPE_ARCHIVE_ROOT"] = str(tmp / "archive")
os.environ["URTPE_LEDGER"] = str(tmp / "corrections.jsonl")

from tests.fixtures_recovery import build_fixture_pdf  # noqa: E402

pdf = build_fixture_pdf(str(tmp / "fixture_gazette.pdf"))
out = tmp / "out"
out.mkdir()

from urtpe import cli  # noqa: E402

rc = cli.main([pdf, "-o", str(out)])
print(f"cli.main -> {rc}")
assert rc == 0, "the pre-change run on the fixture gazette must succeed"

GOLDEN.mkdir(parents=True, exist_ok=True)
for name in ("raw.tsv", "clean.tsv", "merged.tsv", "projects.json", "review_report.txt"):
    shutil.copyfile(out / name, GOLDEN / name)
    print(f"golden: {name} ({(GOLDEN / name).stat().st_size} bytes)")
print(f"fixture pdf kept at {tmp / 'fixture_gazette.pdf'} for reference")
