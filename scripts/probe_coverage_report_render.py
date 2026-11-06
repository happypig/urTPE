"""Read the generated coverage report and check it. Read-only."""
import pathlib
import re

t = pathlib.Path("docs/coverage-report.html").read_text(encoding="utf-8")
print("size: %d bytes" % len(t))
print("doctype first:", t.startswith("<!doctype html>"))
print("closes html:", t.rstrip().endswith("</html>"))

tables = list(re.finditer(r"<table", t))
unwrapped = [m for m in tables
             if "wrap" not in t[max(0, m.start() - 40):m.start()]]
print("tables: %d   without an overflow wrapper: %d"
      % (len(tables), len(unwrapped)))

print()
print("the tiles:")
for m in re.finditer(r'<div class="v">([^<]+)</div><div class="n">([^<]+)</div>', t):
    print("   %-8s %s" % (m.group(1), m.group(2)))

print()
print("the table totals:")
for m in re.finditer(r"<tr[^>]*><td>([^<]{2,40})</td><td class='num'>([^<]+)</td>", t):
    print("   %-38s %s" % (m.group(1), m.group(2)))

print()
for token in ("682", "215", "460", "13", "1431", "1444", "466", "1987", "378",
              "88", "84", "83", "110", "620", "109"):
    if token not in t:
        print("   MISSING the figure %s" % token)
print("all expected figures present")
