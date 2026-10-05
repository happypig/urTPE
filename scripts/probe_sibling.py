"""Can a truncated land cell be repaired from a sibling record for the same unit?

For every truncated 地號 cell, look for another record in the same gazette with the
same (行政區, 段, 小段) whose land cell is complete, and compare parcel sets.
"""
import collections
import re
import sys

sys.path.insert(0, ".")

from urtpe.extract import extract_pdf  # noqa: E402

sys.path.insert(0, "scripts")
from build_project_aliases import parcels_of, section_of  # noqa: E402

BAD = re.compile(r"[、，,]\s*$|\d+-\s*$")
TERM = re.compile(r"地\s*號\s*(?:等)?\s*(?:共)?\s*\d+\s*筆\s*土\s*地\s*$")

PDFS = [
    ("2026-08-11", "source.pdf"),
    ("2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"),
    ("2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"),
]

for gid, path in PDFS:
    rs = extract_pdf(path)
    for r in rs:
        r["_sec"] = section_of(r["land"])
        r["_parcels"] = parcels_of(r["land"])
        r["_flat"] = re.sub(r"\s+", " ", (r["land"] or "").replace("\n", "")).strip()
        r["_trunc"] = bool(BAD.search(r["_flat"]))
        r["_term"] = bool(TERM.search(r["_flat"]))

    trunc = [r for r in rs if r["_trunc"]]
    print("=" * 92)
    print("%s : %d records, %d truncated" % (gid, len(rs), len(trunc)))
    print("=" * 92)
    bysec = collections.defaultdict(list)
    for r in rs:
        bysec[(r["district"], r["_sec"])].append(r)

    repairable = same = differ = none = unsafe = 0
    for r in trunc:
        sibs = [s for s in bysec[(r["district"], r["_sec"])]
                if not s["_trunc"] and s["_flat"] and TERM.search(s["_flat"])]
        if not sibs:
            none += 1
            print("  編號 %-6s %s %-22s NO complete sibling" % (r["recno"], r["district"], r["_sec"]))
            continue
        best = max(sibs, key=lambda s: len(set(r["_parcels"]) & set(s["_parcels"])))
        inter = len(set(r["_parcels"]) & set(best["_parcels"]))
        union = len(set(r["_parcels"]) | set(best["_parcels"]))
        j = inter / union if union else 0.0
        # can the truncated cell's own text be a strict prefix of the sibling's?
        prefix = best["_flat"].startswith(r["_flat"][:40]) if r["_flat"] else False
        if j >= 0.999:
            same += 1
            repairable += 1
            verdict = "IDENTICAL parcel set"
        elif prefix:
            differ += 1
            repairable += 1
            verdict = "truncated text is a prefix of sibling (J=%.2f, sibling has %d more)" % (
                j, len(best["_parcels"]) - len(r["_parcels"]))
        else:
            differ += 1
            unsafe += 1
            verdict = "DIFFERENT parcel set (J=%.2f) -- unsafe to borrow" % j
        print("  編號 %-6s %s %-22s truncated=%2d筆  sibling 編號 %-6s %2d筆  %s"
              % (r["recno"], r["district"], r["_sec"], len(r["_parcels"]),
                 best["recno"], len(best["_parcels"]), verdict))
    print("  -> repairable %d/%d  (identical %d, prefix %d, unsafe %d, no sibling %d)"
          % (repairable, len(trunc), same, unsafe, differ - unsafe, none))
