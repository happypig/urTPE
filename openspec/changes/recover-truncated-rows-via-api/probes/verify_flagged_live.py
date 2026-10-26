# -*- coding: utf-8 -*-
"""Task 6.2: flagged live run on the current gazette into a temp tree.

Runs the pipeline WITH --recover-truncated on 核定案件-2026-10-23.pdf (統計至
2026-10-15, held but not yet ingested — the shipped data/ still reflects
1151006) against the real APIs, into a temp output tree with a copied archive
(live state untouched). Prints the recovery audit and the acceptance numbers.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(r"D:\project\urTPE")
LIVE_ARCHIVE = Path(r"D:\project\urtpe-gazettes")
SRC_PDF = LIVE_ARCHIVE / "核定案件-2026-10-23.pdf"
PY = r"C:\Python314\python.exe"

tmp = Path(tempfile.mkdtemp(prefix="urtpe-flagged-"))
archive_copy = tmp / "archive"
archive_copy.mkdir()
for name in os.listdir(LIVE_ARCHIVE):
    src = LIVE_ARCHIVE / name
    if src.is_file() and (name.endswith(".pdf") or name.endswith(".jsonl")
                          or name == "poll_state.json"):
        shutil.copyfile(src, archive_copy / name)

out = tmp / "out"
out.mkdir()

env = {**os.environ, "URTPE_LEDGER": str(tmp / "absent-ledger.jsonl")}
r = subprocess_run = None
import subprocess

r = subprocess.run([PY, "-m", "urtpe.cli", str(SRC_PDF), "-o", str(out),
                    "--archive-root", str(archive_copy), "--recover-truncated"],
                   cwd=REPO, env=env, capture_output=True, text=True, timeout=1800)
tail = [line for line in (r.stdout or "").splitlines()
        if ("recovery" in line or "RECOVERED" in line or "INCOMPLETE" in line
            or "tripwire" in line or "records:" in line or "Projects:" in line
            or "raw.tsv" in line or "merged.tsv" in line or "編號" in line)]
print("\n".join(tail))
print(f"rc={r.returncode}")
if r.returncode != 0:
    print(r.stderr[-1500:])

report = (out / "review_report.txt")
if report.exists():
    text = report.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(("RECOVERED", "INCOMPLETE")):
            print(line)
doc = json.loads((out / "projects.json").read_text(encoding="utf-8"))
recovered_nodes = sum(1 for p in doc["projects"] for n in p["nodes"] if n.get("recovery"))
print(f"emitted records: {doc['counts']['records']}  projects: {doc['counts']['projects']}"
      f"  nodes with provenance: {recovered_nodes}")
print(f"output tree: {out}")
