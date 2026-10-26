# -*- coding: utf-8 -*-
"""Task 6.3: flag-less re-execution is byte-identical to the committed emission.

Runs the pipeline WITHOUT the recovery flag on the gazette the shipped data/
was emitted from (核定案件-2026-10-02.pdf, 統計至 2026-10-01), into a temp tree,
against a COPY of the live archive (so the single-writer state and the change
sets stay untouched), and hash-compares raw.tsv / clean.tsv / merged.tsv plus
projects.json with its wall-clock fields normalized.
"""
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"D:\project\urTPE")

REPO = Path(r"D:\project\urTPE")
LIVE_ARCHIVE = Path(r"D:\project\urtpe-gazettes")
SRC_PDF = LIVE_ARCHIVE / "核定案件-2026-10-06.pdf"  # 統計至 2026-10-01 = gazette_id 2026-10-01

tmp = Path(tempfile.mkdtemp(prefix="urtpe-flagless-"))
archive_copy = tmp / "archive"
archive_copy.mkdir()
for name in os.listdir(LIVE_ARCHIVE):
    src = LIVE_ARCHIVE / name
    if src.is_file() and (name.endswith(".pdf") or name.endswith(".jsonl") or name == "poll_state.json"):
        shutil.copyfile(src, archive_copy / name)

out = tmp / "out"
out.mkdir()

# the committed emission includes the manual corrections; a fresh ledger would
# drop exactly those records and the hash compare would lie
os.environ["URTPE_LEDGER"] = str(archive_copy / "corrections.jsonl")

from urtpe import cli  # noqa: E402

rc = cli.main([str(SRC_PDF), "-o", str(out), "--archive-root", str(archive_copy)])
print(f"cli.main -> {rc}")
assert rc == 0


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


for name in ("raw.tsv", "clean.tsv", "merged.tsv"):
    mine, theirs = sha(out / name), sha(REPO / "data" / name)
    print(f"{name}: run {mine}  committed {theirs}  {'IDENTICAL' if mine == theirs else 'DIFFERS'}")

import json  # noqa: E402

def norm(p):
    doc = json.loads(Path(p).read_text(encoding="utf-8"))
    doc.pop("generated_at", None)
    doc.pop("source", None)
    return hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()[:16]

mine, theirs = norm(out / "projects.json"), norm(REPO / "data" / "projects.json")
print(f"projects.json (normalized): run {mine}  committed {theirs}  "
      f"{'IDENTICAL' if mine == theirs else 'DIFFERS'}")
