"""Verify the cell-content fixes against the real gazettes.

Before:  page-number bleed on 4/3/4 records in 1150822/1150820/1150827, and
         source truncation on 3/3/3/21 records in 1150822/1150820/1150827/1151002.
After:   no bleed survives, and every truncated record is excluded and reported.
"""
import re
import sys

sys.path.insert(0, ".")

from urtpe.extract import extract_pdf_with_faults  # noqa: E402

BLEED = re.compile(r"土\s*地\s*\d+\s*$")
TAIL_BAD = re.compile(r"[、，,]\s*$|\d\s*$")

PDFS = [
    ("1150822", "2026-08-11", "source.pdf"),
    ("1150820", "2026-08-20", r"D:\project\urtpe-gazettes\核定案件-2026-08-20.pdf"),
    ("1150827", "2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"),
    ("1151002", "2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"),
]

print("%-9s %-12s %8s %9s %8s %9s" % ("gazette", "published", "emitted", "excluded", "bleed", "bad tail"))
print("-" * 62)
for gid, pub, path in PDFS:
    recs, faults = extract_pdf_with_faults(path)
    bleed = sum(1 for r in recs if BLEED.search(re.sub(r"\s+", " ", r["land"] or "")))
    bad = sum(1 for r in recs if TAIL_BAD.search(re.sub(r"\s+", " ", r["land"] or "").strip()))
    print("%-9s %-12s %8d %9d %8d %9d"
          % (gid, pub, len(recs), len(faults), bleed, bad))

print()
print("excluded records, with location:")
for gid, pub, path in PDFS:
    recs, faults = extract_pdf_with_faults(path)
    if not faults:
        continue
    print("\n  %s (%s) — %d excluded" % (gid, pub, len(faults)))
    for f in faults:
        print("    %s" % f)

print()
print("emitted 編號 contiguity check (a gap means an exclusion, not a lost page):")
for gid, pub, path in PDFS:
    recs, faults = extract_pdf_with_faults(path)
    nums = sorted(int(r["recno"]) for r in recs)
    gaps = [n for n in range(1, max(nums) + 1) if n not in set(nums)]
    print("  %-9s max=%-5d emitted=%-5d gaps=%s"
          % (gid, max(nums), len(nums), gaps if gaps else "none"))