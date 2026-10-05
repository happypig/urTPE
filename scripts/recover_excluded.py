"""Can any excluded (publisher-truncated) record be completed from another gazette?

For each record the reader excluded from 1150827, search all four archived
gazettes for a complete copy of the same unit. A copy is only usable if it is the
same approval (same 核定日期) in the same 段/小段 and carries the same parcel list
continued past the cut — which the text itself proves when the truncated cell is a
literal prefix of the candidate.
"""
import re
import sys

import pymupdf

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

from build_project_aliases import jaccard, parcels_of, section_of  # noqa: E402
from urtpe.extract import TRUNCATED_TAIL_RE  # noqa: E402

PDFS = [
    ("1150822", "2026-08-11", "source.pdf"),
    ("1150820", "2026-08-20", r"D:\project\urtpe-gazettes\核定案件-2026-08-20.pdf"),
    ("1150827", "2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"),
    ("1151002", "2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"),
]
RECNO_RE = re.compile(r"^\d{1,4}$")
TERM_RE = re.compile(r"地\s*號\s*(?:等)?\s*(?:共)?\s*\d+\s*筆\s*土\s*地\s*\)?\s*$")
EXCLUDED_0827 = ["868", "909", "1141", "1198", "1204", "1210", "1381"]


def flat(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", "")).strip()


def all_rows(path):
    """Every data row in the gazette, including cells the reader would exclude."""
    doc = pymupdf.open(path)
    out = []
    try:
        for page in doc:
            for t in page.find_tables(strategy="lines").tables:
                grid = t.extract()
                for row in grid:
                    if len(row) < 7:
                        continue
                    recno = flat(row[0])
                    if not RECNO_RE.match(recno):
                        continue
                    land = flat(row[4])
                    out.append({
                        "recno": recno,
                        "date": flat(row[1]),
                        "district": flat(row[2]),
                        "name": flat(row[3]),
                        "land": land,
                        "sec": section_of(land),
                        "parcels": parcels_of(land),
                        "trunc": bool(TRUNCATED_TAIL_RE.search(land)),
                        "complete": bool(TERM_RE.search(land)),
                    })
    finally:
        doc.close()
    seen, dedup = set(), []
    for r in out:
        if r["recno"] in seen:
            continue
        seen.add(r["recno"])
        dedup.append(r)
    return dedup


gazettes = {gid: all_rows(p) for gid, _, p in PDFS}
print("rows read: " + ", ".join("%s=%d" % (g, len(v)) for g, v in gazettes.items()))
print()

target = {r["recno"]: r for r in gazettes["1150827"] if r["recno"] in EXCLUDED_0827}

print("=" * 100)
print("The 7 records excluded from 1150827")
print("=" * 100)
for recno in EXCLUDED_0827:
    r = target.get(recno)
    if not r:
        continue
    claim = re.search(r"等\s*(?:共)?\s*(\d+)\s*筆", r["name"])
    print("\n編號 %-5s %s  %s  %s" % (recno, r["date"], r["district"], r["sec"]))
    print("   案名        : %s" % r["name"][:78])
    print("   cell ends   : %r" % r["land"][-34:])
    print("   parcels read: %-4d   案名 declares: %s"
          % (len(r["parcels"]), claim.group(1) if claim else "?"))

    cands = []
    for gid, rows in gazettes.items():
        for s in rows:
            if s["trunc"] or not s["complete"]:
                continue
            if s["district"] != r["district"] or s["sec"] != r["sec"]:
                continue
            cands.append((gid, s))
    if not cands:
        print("   -> NO complete record of this 段/小段 in any archived gazette")
        continue

    scored = []
    for gid, s in cands:
        j = jaccard(r["parcels"], s["parcels"])
        prefix = s["land"].startswith(r["land"][:34])
        same_date = s["date"] == r["date"]
        scored.append((prefix, same_date, j, gid, s))
    scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

    prefix, same_date, j, gid, s = scored[0]
    verdict = []
    if prefix:
        verdict.append("truncated text is a literal PREFIX of this copy")
    if same_date:
        verdict.append("same 核定日期 (same approval)")
    elif s["date"] != r["date"]:
        verdict.append("different 核定日期 (%s) — a different approval" % s["date"])
    print("   -> best candidate: %s 編號 %s  J=%.2f  parcels %d"
          % (gid, s["recno"], j, len(s["parcels"])))
    print("      %s" % ("; ".join(verdict) or "no stronger link"))
    if prefix:
        extra = sorted(set(s["parcels"]) - set(r["parcels"]))
        print("      recovered %d additional parcel(s): %s%s"
              % (len(extra), ", ".join(extra[:10]), " ..." if len(extra) > 10 else ""))
        print("      案名 copy    : %s" % s["name"][:78])