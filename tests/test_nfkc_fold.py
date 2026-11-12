"""The NFKC fold at the cleansing boundary (nfkc-fold-compat-ideographs).

CJK compatibility ideographs are distinct byte sequences that render as the
same character. The data carries four (measured 2026-11-12, the 680-project
payload): U+F901/F963/FA26 in 6 corpus 案名, U+F9DD in one city case name.
Two readers break on them: the track reader (live — the F9DD sits inside
權利變換) and parse_name_id (latent — 6 rows get no identity).

The six pins follow the E1 test-first group (docs/inspection-batchE.md E1;
docs/DashboardNUXUI.md §11.3). The corpus-only tests exist beside the live
one because the corpus's six characters sit in text no keyword touches —
the live one sits inside a keyword. The difference is WHERE the character
sits, not which character it is (batch D D16a).
"""

from __future__ import annotations

import unicodedata

from urtpe.cleanse import _tracks, cleanse, parse_name_id
from urtpe.models import RawRecord


def _raw(**kw) -> RawRecord:
    base = dict(
        recno=1, date="113/6/30", district="松山區", name="擬訂臺北市松山區X段一小段1地號等10筆土地都市更新事業計畫案",
        land="臺北市松山區X段一小段1、2、3地號等10筆", implementer="甲公司", planner="乙規劃公司",
    )
    base.update(kw)
    return RawRecord(**base)


# The exact strings, copied from the payload / clean.tsv at the 2026-11-12
# census. Do not retype them by hand — a retyped string carries the unified
# form and the test proves nothing (batch D D16: "a character read by eye").

# The one live city case name (11507018): 利 as U+F9DD at index 32 of 38,
# INSIDE 權利變換.
LIVE_11507018 = "變更臺北市大安區復興段三小段3地號等2筆土地都市更新事業計畫及權利變換計畫案"

# The 6 corpus rows (clean.tsv at the census): 北 as U+F963 (臺北市), 都 as
# U+FA26 and 更 as U+F901 (都市更新).
CORPUS_6 = {
    8: "變更臺北市北投區桃源段四小段424-8地號等15筆土地都市更新事業計畫及權利變換計畫案",
    121: "變更臺北市信義區三興段一小段972地號等9筆土地都市更新權利變換計畫案",
    179: "變更臺北市南港區南港段三小段274地號等16筆土地都市更新權利變換計畫案",
    611: "擬訂臺北市信義區三興段一小段972地號等9筆土地都市更新事業計畫及權利變換計畫案",
    613: "變更臺北市南港區南港段三小段274地號等16筆土地都市更新事業計畫及擬訂權利變換計畫案",
    615: "擬訂臺北市北投區桃源段四小段424-8地號等15筆土地都市車新事業計畫及權利變換計畫案",
}


def test_fixtures_carry_the_compatibility_forms():
    """The fixtures are the defect: each string holds at least one
    compatibility ideograph. If a later edit 'fixes' a fixture by retyping
    it, this test fails and names the mistake."""
    assert chr(0xF9DD) in LIVE_11507018
    compat = {0xF901, 0xF963, 0xFA26}
    folded = {recno: any(ch in name for ch in map(chr, compat)) for recno, name in CORPUS_6.items()}
    assert all(folded.values()), f"a fixture lost its compatibility form: {folded}"


# --- pin 1 + 4: the live case reads both tracks, asserted by name ----------

def test_the_live_case_reads_both_tracks_after_folding():
    """11507018's name writes 利 as U+F9DD inside 權利變換. The track reader
    matches keywords as literal substrings, so it must see the FOLDED name."""
    assert chr(0xF9DD) in LIVE_11507018, "the live fixture lost the compatibility form"
    c = cleanse(_raw(recno=11507018, name=LIVE_11507018,
                     land="臺北市大安區復興段三小段3、4地號等2筆"))
    assert c.track == "事業計畫、權利變換", (
        "the compatibility 利 still breaks the track reader; got %r" % c.track)
    # pin 4: asserted by name, not by count — the folded name is what the
    # record carries, and the compatibility form is gone from it.
    assert chr(0xF9DD) not in c.name
    assert "權利變換" in c.name


def test_tracks_on_the_raw_live_name():
    """_tracks itself folds: the live name (untouched by cleanse) derives
    both tracks, because the fold sits inside the reader's input path."""
    assert chr(0xF9DD) in LIVE_11507018
    folded = unicodedata.normalize("NFKC", LIVE_11507018)
    assert _tracks(folded) == ["事業計畫", "權利變換"]


# --- pin 2: the 6 corpus records are unchanged in track --------------------

def test_the_six_corpus_records_keep_their_tracks():
    """The corpus's six sit in text no keyword touches (臺北市 / 都市更新).
    Folding must not change a single track. Their expected tracks, measured
    on clean.tsv at the census:

    8, 615: 事業計畫、權利變換 (combined names)
    121, 179: 權利變換 (plan-change-only names)
    611: 事業計畫、權利變換
    613: 事業計畫、權利變換 (combined, two ordinals)
    """
    expected = {
        8: "事業計畫、權利變換",
        121: "權利變換",
        179: "權利變換",
        611: "事業計畫、權利變換",
        613: "事業計畫、權利變換",
        615: "事業計畫、權利變換",
    }
    for recno, name in CORPUS_6.items():
        c = cleanse(_raw(recno=recno, name=name,
                         land="臺北市松山區X段一小段1地號等10筆"))
        assert c.track == expected[recno], (
            f"recno {recno}: track moved under the fold: {c.track!r}")


# --- pin 3: the project count does not move --------------------------------

# Each pair's own land (the folded identity's district/section/parcels), so
# the merge clusters by the unit's real core and not by a placeholder.
PAIR_LAND = {
    8: "臺北市北投區桃源段四小段424-8、425地號等15筆",
    615: "臺北市北投區桃源段四小段424-8、425地號等15筆",
    121: "臺北市信義區三興段一小段972地號等9筆",
    611: "臺北市信義區三興段一小段972地號等9筆",
    179: "臺北市南港區南港段三小段274地號等16筆",
    613: "臺北市南港區南港段三小段274地號等16筆",
}


def test_the_fold_does_not_move_the_family_count():
    """The fold changes what the merge's scoring compares, so it can join or
    split a family. The 3 affected projects' records must cluster the same
    way with and without the fold."""
    from urtpe.merge import merge

    pairs = [(8, 615), (121, 611), (179, 613)]
    raws = []
    for a, b in pairs:
        for recno in (a, b):
            raws.append(_raw(recno=recno, name=CORPUS_6[recno],
                             land=PAIR_LAND[recno]))
    # Cleanse normally (with the fold in place)…
    with_fold = [cleanse(r) for r in raws]
    families_with = merge(with_fold)
    fam_of = {}
    for i, fam in enumerate(families_with):
        for m in fam.members:
            fam_of[m.recno] = i
    for a, b in pairs:
        assert fam_of[a] == fam_of[b], (
            f"recnos {a} and {b} split into different families under the fold")
    assert len(families_with) == 3


# --- pin 5: the 6 records parse to their identity after folding ------------

def test_the_six_records_parse_to_their_identity():
    """parse_name_id returned ('', '', '', None) on all 6 before the fold.
    After it, the identity is exact for each of the 3 projects."""
    expected = {
        8: ("北投區", "桃源段四小段", "424-8", 15),
        615: ("北投區", "桃源段四小段", "424-8", 15),
        121: ("信義區", "三興段一小段", "972", 9),
        611: ("信義區", "三興段一小段", "972", 9),
        179: ("南港區", "南港段三小段", "274", 16),
        613: ("南港區", "南港段三小段", "274", 16),
    }
    for recno, want in expected.items():
        name = CORPUS_6[recno]
        folded = unicodedata.normalize("NFKC", name)
        got = parse_name_id(folded)
        assert got == want, f"recno {recno}: {got!r} != {want!r}"


def test_parse_name_id_fails_without_the_fold():
    """The defect is real: the compatibility forms defeat the regex today.
    (Guards the guard — if this passes, the fixtures were retyped.)"""
    for recno, name in CORPUS_6.items():
        assert parse_name_id(name) == ("", "", "", None), (
            f"recno {recno}: the raw form parses; the fixture is not the defect")


# --- pin 6: the 3 projects' portal links do not move -----------------------

def test_the_three_projects_view_ids_are_untouched():
    """The 3 projects' portal links came from the cached view pages
    (view/793 北投, view/791 信義, view/253 南港) — they are already right,
    and a change at the cleansing boundary must not disturb them. The
    fold never touches links; this pin holds the invariant at the payload."""
    import json
    from pathlib import Path

    payload = Path(__file__).resolve().parents[1] / "data" / "projects.json"
    doc = json.loads(payload.read_text(encoding="utf-8"))
    want = {
        "北投區-桃源段四小段-424-8地號等15筆": "view/793",
        "信義區-三興段一小段-972地號等9筆": "view/791",
        "南港區-南港段三小段-274地號等16筆": "view/253",
    }
    by_id = {p["project_id"]: p for p in doc["projects"]}
    for pid, view in want.items():
        p = by_id.get(pid)
        assert p is not None, f"{pid} is not in the payload"
        twur = (p.get("links") or {}).get("twur") or ""
        assert view in twur, f"{pid}: twur is {twur!r}, expected {view}"
