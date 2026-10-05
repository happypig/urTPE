"""Would repairing 1198/1210 from 1151002 be sound?

Three conditions, each of which must hold:
  (a) same unit      - same 行政區 + 段/小段
  (b) prefix         - the truncated cell's text is a literal prefix of the candidate's
  (c) count closes   - repaired parcel count equals the 案名's declared count

Also records which gazette the candidate comes from, since 1151002 is excluded from
the dataset for carrying 15 of its own truncated cells.
"""
import re
import sys

import pymupdf

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

from build_project_aliases import jaccard, parcels_of, section_of  # noqa: E402
from urtpe.extract import TRUNCATED_TAIL_RE  # noqa: E402

G = {
    "1150827": r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf",
    "1151002": r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf",
}
RECNO = re.compile(r"^\d{1,4}$")


def flat(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()


def rows(path):
    doc = pymupdf.open(path)
    out = []
    try:
        for page in doc:
            for t in page.find_tables(strategy="lines").tables:
                for row in t.extract():
                    if len(row) < 7 or not RECNO.match(flat(row[0])):
                        continue
                    land = flat(row[4])
                    out.append({
                        "recno": flat(row[0]), "date": flat(row[1]),
                        "district": flat(row[2]), "name": flat(row[3]),
                        "land": land, "sec": section_of(land),
                        "parcels": parcels_of(land),
                        "trunc": bool(TRUNCATED_TAIL_RE.search(land)),
                    })
    finally:
        doc.close()
    seen, keep = set(), []
    for r in out:
        if r["recno"] not in seen:
            seen.add(r["recno"])
            keep.append(r)
    return keep


corpora = {k: rows(v) for k, v in G.items()}
src = {r["recno"]: r for r in corpora["1150827"]}

TARGETS = {"1198": None, "1210": None}
print("=" * 96)
print("Candidate repair for the two repairable exclusions in 1150827")
print("=" * 96)
for recno in TARGETS:
    t = src[recno]
    claim = re.search(r"等\s*(?:共)?\s*(\d+)\s*筆", t["name"])
    declared = int(claim.group(1)) if claim else None
    print("\n編號 %s  %s  %s  %s" % (recno, t["date"], t["district"], t["sec"]))
    print("   案名        : %s" % t["name"][:74])
    print("   truncated at: %r" % t["land"][-40:])
    print("   parcels read: %-4d   案名 declares: %s" % (len(t["parcels"]), declared))

    cands = []
    for gid, rs in corpora.items():
        for s in rs:
            if s["trunc"] or s["district"] != t["district"] or s["sec"] != t["sec"]:
                continue
            if gid == "1150827" and s["recno"] == recno:
                continue
            if s["land"].startswith(t["land"][:34]):
                cands.append((gid, s))
    if not cands:
        print("   -> no prefix-verified candidate in any gazette")
        continue
    cands.sort(key=lambda gs: -len(gs[1]["parcels"]))
    for gid, s in cands[:2]:
        j = jaccard(t["parcels"], s["parcels"])
        merged = len(t["parcels"]) + len(set(s["parcels"]) - set(t["parcels"]))
        print("   candidate %s 編號 %-6s  %d parcels  J=%.3f"
              % (gid, s["recno"], len(s["parcels"]), j))
        print("      (a) same 段/小段 : yes")
        print("      (b) literal prefix: yes")
        print("      (c) count closes : repaired=%d declared=%s -> %s"
              % (merged, declared, "YES" if declared == merged else "NO"))
        if declared != merged:
            print("      !! borrowing asserts %d parcels for a record whose 案名 declares %d"
                  % (merged, declared))
            print("         the discrepancy is unexplained; the candidate may be a")
            print("         different parcel set that merely shares a prefix")
        print("      candidate 案名: %s" % s["name"][:74])
