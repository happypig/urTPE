# -*- coding: utf-8 -*-
"""Task 6.3 (A/B form): the flag-less path is byte-identical to pre-change code.

The committed data/ is stale relative to check-declared-parcel-counts (emitted
2026-10-07; that extraction change landed 2026-10-26), so the committed files
cannot be the baseline. The honest comparison: run the pipeline flag-less from a
worktree at HEAD (this change's work is uncommitted) and from the working tree,
in the same environment (copied archive, same ledger absence), and compare the
emissions to each other.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"D:\project\urTPE")
LIVE_ARCHIVE = Path(r"D:\project\urtpe-gazettes")
SRC_PDF = LIVE_ARCHIVE / "核定案件-2026-10-06.pdf"
PY = r"C:\Python314\python.exe"

tmp = Path(tempfile.mkdtemp(prefix="urtpe-ab-"))

# --- worktree at HEAD (pre-change code) --------------------------------------
subprocess.run(["git", "worktree", "add", str(tmp / "head"), "HEAD", "--detach"],
               cwd=REPO, check=True, capture_output=True)

# --- shared environment: a copied archive, no ledger -------------------------
archive_copy = tmp / "archive"
archive_copy.mkdir()
for name in os.listdir(LIVE_ARCHIVE):
    src = LIVE_ARCHIVE / name
    if src.is_file() and (name.endswith(".pdf") or name.endswith(".jsonl")
                          or name == "poll_state.json"):
        shutil.copyfile(src, archive_copy / name)

env = {**os.environ, "URTPE_LEDGER": str(tmp / "absent-ledger.jsonl")}

outs = {}
for label, cwd in (("head", tmp / "head"), ("work", REPO)):
    out = tmp / f"out-{label}"
    out.mkdir()
    r = subprocess.run([PY, "-m", "urtpe.cli", str(SRC_PDF), "-o", str(out),
                        "--archive-root", str(archive_copy)],
                       cwd=cwd, env=env, capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, f"{label} run failed: {r.stderr[-800:]}"
    outs[label] = out
    print(f"{label}: rc=0")

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]

ok = True
for name in ("raw.tsv", "clean.tsv", "merged.tsv"):
    a, b = sha(outs["head"] / name), sha(outs["work"] / name)
    same = a == b
    ok &= same
    print(f"{name}: head {a}  work {b}  {'IDENTICAL' if same else 'DIFFERS'}")

def norm(p):
    doc = json.loads(Path(p).read_text(encoding="utf-8"))
    doc.pop("generated_at", None)
    doc.pop("source", None)
    return hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()[:16]

a, b = norm(outs["head"] / "projects.json"), norm(outs["work"] / "projects.json")
same = a == b
ok &= same
print(f"projects.json (normalized): head {a}  work {b}  "
      f"{'IDENTICAL' if same else 'DIFFERS'}")
print("VERDICT:", "flag-less path unchanged by this change" if ok else "REGRESSION")

subprocess.run(["git", "worktree", "remove", str(tmp / "head"), "--force"],
               cwd=REPO, capture_output=True)
