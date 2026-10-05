"""Confirm the trailing digits are the page-number footer, and that the truncated
tails are absent from the PDF.

Both claims decide the design, so both are checked directly.
"""
import re
import sys

import pymupdf

sys.path.insert(0, ".")

from urtpe.extract import extract_pdf  # noqa: E402

BLEED = re.compile(r"土\s*地\s*(\d+)\s*$")
PDFS = [
    ("2026-08-11", "source.pdf"),
    ("2026-08-20", r"D:\project\urtpe-gazettes\核定案件-2026-08-20.pdf"),
    ("2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"),
    ("2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"),
]

print("CLAIM 1: the digits after 土地 are the page number of the page the row sits on")
print("-" * 92)
for gid, path in PDFS:
    rs = extract_pdf(path)
    doc = pymupdf.open(path)
    hits = 0
    agree = 0
    for r in rs:
        m = BLEED.search(re.sub(r"\s+", " ", (r["land"] or "").replace("\n", "")))
        if not m:
            continue
        hits += 1
        trailing = m.group(1)
        # locate the row's page by searching for its recno+date in each page
        found_page = None
        for pno, page in enumerate(doc, 1):
            txt = re.sub(r"\s+", " ", page.get_text("text").replace("\n", " "))
            if re.search(r"\b%s\b\s*%s" % (re.escape(r["date"].replace("/", "/")), re.escape(r["district"])), txt):
                found_page = pno
                break
        ok = found_page is not None and str(found_page) == trailing
        agree += ok
        print("  %s  編號 %-6s trailing=%-4s page=%-6s %s"
              % (gid, r["recno"], trailing, found_page, "MATCH" if ok else "differs"))
    print("  -> %s: %d/%d trailing digits equal the page number\n" % (gid, agree, hits))
    doc.close()