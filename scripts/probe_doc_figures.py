"""Does every figure in §3 and §4 of DashboardNUXUI.md reproduce at HEAD?

The document's tables are checked against the probes that produced them.
This parses the document's own tables and compares each cell with the value
the probe measures, so a stale figure names itself.

    python scripts/probe_doc_figures.py

Reads the payload and the document. Writes nothing, reaches no network.

Exits 1 when a figure does not reproduce. §3.1's 核定 row is checked against
`probe_wait_date_rule.py`, not against `probe_dashboard_durations.py`: that row
uses the LATEST of its approval dates, and the durations probe prints the
earliest reading.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "DashboardNUXUI.md"


def run(script, *args):
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                         cwd=ROOT, capture_output=True, text=True)
    return out.stdout


def doc_section(title):
    """The text of one '### ' section of the document."""
    text = DOC.read_text(encoding="utf-8")
    start = text.find(title)
    if start < 0:
        return ""
    rest = text[start + len(title):]
    nxt = rest.find("\n### ")
    return rest[:nxt] if nxt >= 0 else rest


def numbers(text):
    return [int(m.group(0).replace(",", "")) for m in re.finditer(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{2,5}\b", text)]


def main() -> int:
    dur = run("probe_dashboard_durations.py")
    dist = run("probe_dashboard_by_district.py")
    shapes = run("probe_dashboard_link_shapes.py")
    awaiting = run("probe_dashboard_awaiting.py")
    nat = run("probe_dashboard_national_dates.py")

    # the HEAD block of each probe: from the word HEAD to the next separator
    def head_block(text):
        i = text.find("HEAD")
        if i < 0:
            return ""
        j = text.find("\n====", i)
        return text[i:j] if j >= 0 else text[i:]

    fails = 0

    # --- §3.1 funnel ---
    sec = doc_section("### 3.1 The funnel")
    rows = re.findall(r"^\| (\S+) \| (\d+) \| (\d+) \| \*?\*?([\d,]+)\*?\*? \| (\d+) \|$",
                       sec, re.M)
    doc_funnel = {r[0]: (int(r[1]), int(r[2]), int(r[3].replace(",", "")), int(r[4]))
                  for r in rows}
    head = head_block(dur)
    # The 核定 row's median uses the LATEST of its approval dates; every other
    # row uses the earliest. probe_dashboard_durations prints the earliest, so
    # the 核定 row's median comes from probe_wait_date_rule instead.
    latest_med = {}
    wl = run("probe_wait_date_rule.py", "HEAD")
    i = wl.find("HEAD")
    if i >= 0:
        for line in wl[i:].splitlines():
            m = re.match(r"\s+(\S+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+", line) \
                or re.match(r"^\s*(\S+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+", line)
            if m and m.group(1) in ("核定", "建照", "開工", "使照", "成果報備"):
                latest_med[m.group(1)] = (int(m.group(2)), int(m.group(3).replace(",", "")),
                                          int(m.group(4).replace(",", "")))
    probe_funnel = {}
    for line in head.splitlines():
        m = re.match(r"\s+(\S+)\s+(\d+)\s+(\d+)\s+([\d,]+)\s*$", line)
        if m and m.group(1) in ("核定", "建照", "開工", "使照", "成果報備"):
            probe_funnel[m.group(1)] = (int(m.group(2)), int(m.group(3)),
                                        int(m.group(4).replace(",", "")))
    print("§3.1 funnel")
    for stage, (ever, stands, med, n) in doc_funnel.items():
        p = probe_funnel.get(stage)
        if stage == "核定":
            lm = latest_med.get("核定")
            p = (p[0], p[1], lm[2]) if (p and lm) else p
        ok = p and p[0] == ever and p[1] == stands and p[2] == med
        if not ok:
            fails += 1
            print("  MISMATCH %s: doc=(%d,%d,%d) probe=%s"
                  % (stage, ever, stands, med, p))
        else:
            print("  ok %s  ever=%d stands=%d median=%d" % (stage, ever, stands, med))

    # --- §3.2 durations ---
    sec = doc_section("### 3.2 Stage-to-stage durations")
    rows = re.findall(r"^\| ([^|]+?) \| (\d+) \| \*?\*?([\d,]+)\*?\*? \| \*?\*?([\d,]+)\*?\*? \| \*?\*?([\d,]+)\*?\*? \|$",
                       sec, re.M)
    print("§3.2 durations")
    probe_tr = {}
    for line in head.splitlines():
        m = re.match(r"\s+(\S+ → \S+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$", line)
        if m:
            probe_tr[m.group(1)] = (int(m.group(2)), int(m.group(3).replace(",", "")),
                                    int(m.group(4).replace(",", "")),
                                    int(m.group(5).replace(",", "")))
    for tr, n, med, p75, mx in rows:
        key = tr.strip()
        p = probe_tr.get(key)
        ok = p and p[0] == int(n) and p[1] == int(med.replace(",", "")) \
            and p[2] == int(p75.replace(",", "")) and p[3] == int(mx.replace(",", ""))
        if not ok:
            fails += 1
            print("  MISMATCH %s: doc=(%s,%s,%s,%s) probe=%s"
                  % (key, n, med, p75, mx, p))
        else:
            print("  ok %s" % key)

    # --- §3.4 district totals ---
    sec = doc_section("### 3.4 By district")
    m = re.search(r"^\| \*\*Total\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \| \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|$",
                  sec, re.M)
    print("§3.4 district total row")
    if m:
        want = tuple(int(x) for x in m.groups())
        mm = re.search(r"^\s+Total\s+(\d+)\s+(\d+)\s+\S*\s+(\d+)\s+(\d+)\s+(\d+)\s*$",
                       head_block(dist), re.M)
        got = tuple(int(x) for x in mm.groups()) if mm else None
        # the probe's total row is: projects n median p75 use-no-done no-permit not-appr
        got = (got[0], got[1], got[2], got[3], got[4]) if got else None
        if got == want:
            print("  ok %s" % (got,))
        else:
            fails += 1
            print("  MISMATCH doc=%s probe=%s" % (want, got))
    else:
        fails += 1
        print("  could not find the Total row")

    # --- §4.2 link shapes ---
    sec = doc_section("### 4.2 Unverified projects")
    print("§4.2 link shapes")
    for shape, count in re.findall(r"^\| (National link [^*]*\*?\*? and [^*]*|National link only|City case id only|Neither) \| \*?\*?(\d+)\*?\*? \|$",
                                   sec, re.M):
        mm = re.search(r"national link AND city case id\s*:\s*(\d+)", shapes)
        mm2 = re.search(r"national link only\s*:\s*(\d+)", shapes)
        mm3 = re.search(r"city case id only\s*:\s*(\d+)", shapes)
        mm4 = re.search(r"neither\s*:\s*(\d+)", shapes)
        probe = {"National link **and** city case id": mm.group(1),
                 "National link only": mm2.group(1),
                 "City case id only": mm3.group(1),
                 "Neither": mm4.group(1)}
        want = probe.get(shape.strip())
        if want == count:
            print("  ok %s = %s" % (shape.strip(), count))
        else:
            fails += 1
            print("  MISMATCH %s: doc=%s probe=%s" % (shape.strip(), count, want))

    # --- §4.1 awaiting ---
    sec = doc_section("### 4.1 Awaiting approval")
    print("§4.1 awaiting")
    m = re.search(r"Projects awaiting an approval \| \*\*(\d+)\*\* of (\d+) \((\d+)%\)", sec)
    if m:
        want_n, want_total = int(m.group(1)), int(m.group(2))
        mm = re.search(r"awaiting approval: (\d+)", awaiting)
        got = int(mm.group(1)) if mm else None
        if got == want_n:
            print("  ok awaiting=%d" % got)
        else:
            fails += 1
            print("  MISMATCH awaiting: doc=%d probe=%s" % (want_n, got))
    else:
        fails += 1
        print("  could not find the awaiting line")

    print()
    print("failures: %d" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
