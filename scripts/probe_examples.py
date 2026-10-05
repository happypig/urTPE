"""Print the three worked examples verbatim, for the Defect 2 decision."""
import re
import sys

import pymupdf

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

from build_project_aliases import jaccard, parcels_of  # noqa: E402
from urtpe.extract import extract_pdf  # noqa: E402

BAD = re.compile(r"[、，,]\s*$|\d+-\s*$")
TERM = re.compile(r"地\s*號\s*(?:等)?\s*(?:共)?\s*\d+\s*筆\s*土\s*地\s*$")
G9 = r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"
G8 = r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"


def flat(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", "")).strip()


def load(path):
    out = []
    for r in extract_pdf(path):
        r["_flat"] = flat(r["land"])
        r["_parcels"] = parcels_of(r["land"])
        r["_trunc"] = bool(BAD.search(r["_flat"]))
        r["_term"] = bool(TERM.search(r["_flat"]))
        out.append(r)
    return out


r9 = load(G9)
r8 = load(G8)
by9 = {str(r["recno"]): r for r in r9}
by8 = {str(r["recno"]): r for r in r8}

print("#" * 94)
print("EXAMPLE 1 — 雙園段二小段 505: looks recoverable, borrowing still unsafe")
print("#" * 94)
for rec in ("924", "999", "1105"):
    r = by9[rec]
    print("\n 09-24 編號 %-5s %s  %s" % (rec, "TRUNCATED" if r["_trunc"] else "complete",
                                        "%d parcels parsed" % len(r["_parcels"])))
    print("   %s" % (r["_flat"][-70:] if r["_trunc"] else r["_flat"][-70:]))
print("\n   編號 924 parcels  : %d   e.g. %s .. %s"
      % (len(by9["924"]["_parcels"]), sorted(by9["924"]["_parcels"])[:4],
         sorted(by9["924"]["_parcels"])[-4:]))
print("   編號 1105 parcels : %d   e.g. %s .. %s"
      % (len(by9["1105"]["_parcels"]), sorted(by9["1105"]["_parcels"])[:4],
         sorted(by9["1105"]["_parcels"])[-4:]))
j = jaccard(by9["924"]["_parcels"], by9["1105"]["_parcels"])
print("   J=%.3f   only in 1105: %s" % (j, sorted(set(by9["1105"]["_parcels"]) - set(by9["924"]["_parcels"]))[:8]))
print("   案名 924  : %s" % by9["924"]["name"][:70])
print("   案名 1105 : %s" % by9["1105"]["name"][:70])
print("   -> same unit, but the complete sibling carries parcels the truncated cell")
print("      may or may not have had; borrowing asserts an approval's parcel set from")
print("      a DIFFERENT approval.")

print("\n" + "#" * 94)
print("EXAMPLE 2 — 虎林段四小段 38: the text is simply not in the file")
print("#" * 94)
doc = pymupdf.open(G9)
for pno in (11, 95):
    page = doc[pno - 1]
    for t in page.find_tables(strategy="lines"):
        data = t.extract()
        if not data or len(data[0]) < 5:
            continue
        for ri, row in enumerate(data):
            if len(row) < 5:
                continue
            c = flat(row[4])
            if "虎林段四小段" not in c:
                continue
            if not BAD.search(c):
                continue
            rect = t.rows[ri].cells[4]
            words = [w for w in page.get_text("words")
                     if w[0] >= rect[0] - 6 and w[2] <= rect[2] + 6]
            inband = [w for w in words if rect[1] - 2 <= w[1] <= rect[3] + 2]
            below = [w for w in words if w[1] > rect[3] + 2]
            print("\n page %-4d row %-3d cell band y %.1f-%.1f" % (pno, ri, rect[1], rect[3]))
            print("   last text line inside the band (y=%.1f): %r" % (inband[-1][1], inband[-1][4]))
            print("   words below the band in the same column: %d" % len(below))
            for w in below[:3]:
                print("      y=%7.1f %r" % (w[1], w[4]))
            break
        break
doc.close()
r61 = by9["61"]
print("\n 09-24 編號 61  案名: %s" % r61["name"][:72])
print("   parsed parcels: %d  ending %s" % (len(r61["_parcels"]), sorted(r61["_parcels"])[-3:]))
sib = by9["361"]
print("   same 段/小段 sibling 編號 361: %d parcels, J=%.2f, ends %s"
      % (len(sib["_parcels"]), jaccard(r61["_parcels"], sib["_parcels"]),
         sorted(sib["_parcels"])[-3:]))
print("   案名 361: %s" % sib["name"][:72])
print("   -> J=0.00: the only same-section sibling is a DIFFERENT project.")
print("      There is no complete copy of this list anywhere in the gazette.")

print("\n" + "#" * 94)
print("EXAMPLE 3 — 南港段一小段 710-3: padding the window imports the next unit")
print("#" * 94)
doc = pymupdf.open(G8)
page = doc[160]
for t in page.find_tables(strategy="lines"):
    data = t.extract()
    if not data or len(data[0]) < 5:
        continue
    for ri, row in enumerate(data):
        if len(row) < 5:
            continue
        c = flat(row[4])
        if not (BAD.search(c) and "南港段一小段" in c.replace(" ", "")):
            continue
        rect = t.rows[ri].cells[4]
        print("\n 08-27 page 161 row %d, cell band y %.1f-%.1f" % (ri, rect[1], rect[3]))
        print("   clipped tail: %r" % c[-46:])
        for pad in (0, 6, 14, 24):
            clip = pymupdf.Rect(rect[0] - 1, rect[1] - 1, rect[2] + 1, rect[3] + pad)
            got = re.sub(r"\s+", " ", page.get_text("text", clip=clip).replace("\n", "")).strip()
            print("   pad %-3d len %-4d tail %r" % (pad, len(got), got[-52:]))
        if ri + 1 < len(data):
            print("\n   next row land cell (a DIFFERENT unit):")
            print("     %s" % flat(data[ri + 1][4])[:74])
        break
    else:
        continue
    break
doc.close()
print("   -> at pad 14 the window crosses the row rule and returns the next")
print("      unit's text (華中段一小段). Widening the window cannot recover the")
print("      tail; it only manufactures cross-record contamination.")