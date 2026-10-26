# -*- coding: utf-8 -*-
"""Task 6.2 row-by-row review: flagged vs flag-less diff on the same gazette,
and why the two R-form recoveries stayed partial."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(r"D:\project\urTPE")
LIVE_ARCHIVE = Path(r"D:\project\urtpe-gazettes")
SRC_PDF = LIVE_ARCHIVE / "核定案件-2026-10-23.pdf"
PY = r"C:\Python314\python.exe"

tmp = Path(tempfile.mkdtemp(prefix="urtpe-review-"))
archive_copy = tmp / "archive"
archive_copy.mkdir()
for name in os.listdir(LIVE_ARCHIVE):
    src = LIVE_ARCHIVE / name
    if src.is_file() and (name.endswith(".pdf") or name.endswith(".jsonl")
                          or name == "poll_state.json"):
        shutil.copyfile(src, archive_copy / name)

env = {**os.environ, "URTPE_LEDGER": str(tmp / "absent-ledger.jsonl")}
outs = {}
for label, flag in (("flagless", []), ("flagged", ["--recover-truncated"])):
    out = tmp / f"out-{label}"
    out.mkdir()
    r = subprocess.run([PY, "-m", "urtpe.cli", str(SRC_PDF), "-o", str(out),
                        "--archive-root", str(archive_copy), *flag],
                       cwd=REPO, env=env, capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, f"{label}: {r.stderr[-500:]}"
    outs[label] = out
    print(f"{label}: rc=0")

def rows(path):
    lines = Path(path).read_text(encoding="utf-8").strip().split("\n")
    header = lines[0].split("\t")
    out = {}
    for line in lines[1:]:
        cells = line.split("\t")
        rec = dict(zip(header, cells))
        out[int(rec["recno"])] = rec
    return out

less, more = rows(outs["flagless"] / "merged.tsv"), rows(outs["flagged"] / "merged.tsv")
added = sorted(set(more) - set(less))
removed = sorted(set(less) - set(more))
changed = sorted(n for n in set(more) & set(less) if less[n] != more[n])
print(f"added recnos: {added}")
print(f"removed recnos: {removed}")
print(f"changed recnos: {changed}")
for n in added:
    rec = more[n]
    print(f"  + {n} {rec['date']} {rec['name'][:44]} | land_count={rec['land_count']}"
          f" | flags={rec['review_flags']!r}")
for n in changed:
    diffs = [k for k in less[n] if less[n][k] != more[n][k]]
    print(f"  ~ {n}: fields {diffs}")

# why did the two R-form recoveries stay partial?
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
B = "https://zonegeo.udd.gov.taipei/geoserver/Taipei/wfs?" + urllib.parse.urlencode({
    "service": "WFS", "request": "GetFeature", "version": "1.1.0",
    "outputFormat": "json", "srsName": "EPSG:4326",
    "typename": "Taipei:uro-redevelop-ALL-5"})
for cid in ("R089213-02", "R089213", "R091007-02", "R091007"):
    req = urllib.request.Request(B + "&" + urllib.parse.urlencode(
        {"cql_filter": f"ID='{cid}'"}), headers=UA)
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
        print(f"boundary {cid}: {len(d.get('features', []))} feature(s)")
    except Exception as e:
        print(f"boundary {cid}: ERR {e}")
