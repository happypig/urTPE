## Context

The extractor matches `{district}{section}{first_parcel}地號等{count}筆` with a
single regex. Three real city shapes break it (C4, measured over the 726
caches): the 、-list, the `(原NNN)` suffixes, and stray spaces. Compatibility
characters (U+F963 北 after 臺) break the 臺北市 split (Appendix A).

## Goals / Non-Goals

**Goals:**
- Extract a land core from every name a human reads as parseable.
- Name every name that still yields no land core in the run report.
- No API call: the re-emit restores the 8 cases from the caches.

**Non-Goals:**
- The 號-without-地號 shape (`401號等10筆`, 3 anchor names) is NOT learned: it
  is an anchor name, not an orphan name, and inventing a 地號 prefix would
  repair by inference. It stays reported.
- The parcel-less rule (崇仁新村) is unchanged, by design.

## Decisions

### 1. NFKC first, then normalise, then match

`unicodedata.normalize("NFKC", name)` recovers U+F963→北. Then strip spaces
inside the land-fragment span and learn the two structural shapes.

### 2. The 、-list keeps its first parcel

`長安段三小段709、711地號等2筆` extracts as
`長安段三小段709地號等2筆`: the land core keys on the first parcel
(AGENTS.md: identity is the land core `{district}{section}{first_parcel}`),
and the full list stays in the case name for the viewer.

### 3. `(原NNN)` is stripped from the parcel and the count

`105(原90)地號等13筆(原24筆)` extracts as `中南段105地號等13筆` — the same
shape the gazette cleanser already treats (等N筆(原M筆) closing-phrase
variants are stripped chunk-wise).

### 4. Reporting lives at the gate, not the extractor

The extractor stays pure (returns ""). The orphan gate names every
unparseable orphan case_name in its report; an anchored case with an
unparseable name is not reported (its binding does not need the land core).
