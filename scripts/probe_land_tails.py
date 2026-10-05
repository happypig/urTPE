"""Probe the terminal form of 地號 cells across the known gazettes.

Establishes what a well-formed land cell ends with, so a validity rule can be
written against observed data rather than assumption.
"""
import collections
import re
import sys

sys.path.insert(0, ".")

from urtpe.extract import extract_pdf  # noqa: E402

PDFS = [
    ("2026-08-11", "source.pdf"),
    ("2026-08-20", r"D:\project\urtpe-gazettes\核定案件-2026-08-20.pdf"),
    ("2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"),
    ("2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"),
]

# candidate terminal forms, most specific first
TAIL = re.compile(r"(地號等\s*\d+\s*筆\s*土地)\s*(\d*)\s*$")
TAIL_NOCOUNT = re.compile(r"(地號)\s*(\d*)\s*筆\s*土地\s*(\d*)\s*$")

for gid, path in PDFS:
    rs = extract_pdf(path)
    stats = collections.Counter()
    tails = collections.Counter()
    examples = collections.defaultdict(list)
    for r in rs:
        cell = (r["land"] or "").replace("\n", "")
        flat = re.sub(r"\s+", " ", cell).strip()
        m = TAIL.search(flat)
        if m:
            stats["ends 地號等N筆土地"] += 1
            if m.group(2):
                stats["  ...with trailing digits"] += 1
                tails[m.group(2)] += 1
                if len(examples["trailing"]) < 4:
                    examples["trailing"].append((r["recno"], flat[-30:]))
        elif TAIL_NOCOUNT.search(flat):
            stats["ends 地號N筆土地"] += 1
            if TAIL_NOCOUNT.search(flat).group(3):
                stats["  ...with trailing digits"] += 1
                if len(examples["trailing"]) < 4:
                    examples["trailing"].append((r["recno"], flat[-30:]))
        elif flat.endswith("土地"):
            stats["ends 土地 (other shape)"] += 1
            if len(examples["other"]) < 4:
                examples["other"].append((r["recno"], flat[-40:]))
        elif flat.endswith("、") or flat.endswith("，") or flat.endswith(","):
            stats["ENDS WITH A COMMA  <-- clipped"] += 1
            if len(examples["comma"]) < 6:
                examples["comma"].append((r["recno"], flat[-40:]))
        elif re.search(r"\d+-\s*$", flat):
            stats["ENDS MID SUB-PARCEL  <-- clipped"] += 1
            if len(examples["dash"]) < 6:
                examples["dash"].append((r["recno"], flat[-40:]))
        else:
            stats["unrecognised tail"] += 1
            if len(examples["other"]) < 8:
                examples["other"].append((r["recno"], flat[-40:]))

    print("=" * 88)
    print("%s   %d records" % (gid, len(rs)))
    print("=" * 88)
    for k in sorted(stats):
        print("   %-34s %d" % (k, stats[k]))
    for kind in ("trailing", "comma", "dash", "other"):
        if examples[kind]:
            print("   -- %s --" % kind)
            for recno, t in examples[kind]:
                print("      編號 %-6s ...%s" % (recno, t))
    print()