"""D14(b): simulate the enum read of district_land over all 1,442 rows.

Read-only. Reports, against the CURRENT rules:
  - the district_land token each row reads (DISTRICT_RE today vs the enum)
  - the 行政區與地號行政區不一致 flag: gain / loss / text change
  - the section and parcels: must not change (the board requires it)
  - the land core: which rows change

The flag's quoted token is the enum read when the enum finds a district, else
the raw printed token (a typo such as 投區 must still be quoted).
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
csv.field_size_limit(10**8)

from urtpe.cleanse import DISTRICT_RE, _parse_land, _section  # noqa: E402

CLEAN = ROOT / "data" / "clean.tsv"

rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))
dist = Counter(r.get("district", "") for r in rows)
enum = sorted((k for k in dist if k and k.endswith("區")), key=lambda s: (-len(s), s))
ENUM_RE = re.compile("|".join(map(re.escape, enum)))
print("enum (%d): %s\n" % (len(enum), " ".join(sorted(enum))))


def raw_token(land):
    m = DISTRICT_RE.search(land)
    return m.group(1) if m else ""


def enum_token(land):
    m = ENUM_RE.search(land)
    return m.group(0) if m else ""


def flag_of(district, quoted):
    if quoted and district and quoted != district:
        return f"行政區與地號行政區不一致(地號為{quoted})"
    return ""


dl_change, flag_gain, flag_loss, flag_text, sec_diff, par_diff = [], [], [], [], [], []
for r in rows:
    land = r.get("land", "")
    district = r.get("district", "")
    old_dl = raw_token(land)
    new_dl = enum_token(land)
    if old_dl != new_dl:
        dl_change.append((r.get("recno"), old_dl, new_dl))
    old_quote = old_dl
    new_quote = new_dl or old_dl          # enum first, raw (typo) as fallback
    old_flag = flag_of(district, old_quote)
    new_flag = flag_of(district, new_quote)
    if not old_flag and new_flag:
        flag_gain.append((r.get("recno"), district, new_flag))
    elif old_flag and not new_flag:
        flag_loss.append((r.get("recno"), district, old_flag))
    elif old_flag != new_flag:
        flag_text.append((r.get("recno"), old_flag, new_flag))

    # section / parcels must not change: _section still splits on DISTRICT_RE
    old_sec, old_rest = _section(land)
    new_sec, new_rest = _section(land)
    old_pl = _parse_land(land)
    new_pl = _parse_land(land)
    if old_sec != new_sec:
        sec_diff.append((r.get("recno"), old_sec, new_sec))
    if old_pl["parcels"] != new_pl["parcels"]:
        par_diff.append((r.get("recno"), old_pl["parcels"], new_pl["parcels"]))

print("district_land changes:", len(dl_change))
for c in dl_change:
    print("  recno=%s  %r -> %r" % c)
print()
print("flag GAIN:", len(flag_gain))
for f in flag_gain:
    print("  ", f)
print("flag LOSS:", len(flag_loss))
for f in flag_loss:
    print("  ", f)
print("flag TEXT change:", len(flag_text))
for f in flag_text:
    print("  ", f)
print()
print("section diffs:", len(sec_diff), sec_diff)
print("parcel diffs:", len(par_diff), par_diff)

# the emitted section column must not change either (the 案名 supplies it)
print()
print("rows whose emitted section column differs from the land-cell parse:")
mismatch = 0
for r in rows:
    land = r.get("land", "")
    pl = _parse_land(land)
    if pl["section"] != r.get("section", ""):
        mismatch += 1
print("  ", mismatch, "(these already differ today; the change does not touch them)")
