## Why

The coverage report (`docs/coverage-report.html`, 問題一) names 7 projects that
carry no city case id at all: their 11 nodes carry the flag
節點未能對應平台案件 and render no 北 badge. A live search of the city's own
endpoints finds a case id for every one of the 11 nodes. The pipeline binds
only 3 of them, because the resolver's tier-3 name rule cannot read a unit
whose gazette text and the city's index name it differently.

Three actors are involved. The city publishes the 核定案件一覽表 as a PDF, and
its two indexes — the 審議服務平台 (gis.uro.taipei) and the 國土署入口網
(twur.nlma.gov.tw) — carry the same units under their own spellings. The
gazette's 案名 column and its 地號 column sometimes disagree about which
段小段 the unit is in, and the city indexes the 地號 column's spelling. The
resolver joins a node to a case by comparing the two names, so a disagreement
leaves the node unbound and the unit invisible to a reader.

## What Changes

- The land-core comparison used by the tier-3 name rule gains a **section
  form** rule: two sections match when they name the same 小段 and the same
  段, with a trailing 段 optional on either side. The gazette prints
  吳興一小段 where the city prints 吳興段一小段.
- The land-core comparison gains a **parcel set** rule: the city's declared
  parcel scores the full weight when it equals the node's first parcel or is
  one of the node's own parcels. The 吳興街二期 unit's first parcel is
  163-2; the city declares 247.
- The land-core comparison reads a core's section at **both** its first 段 and
  its last, so 河堤段五小段 reads as a section name rather than as section
  河堤段 with parcel 五小段399.
- A node's land core may be built from the **地號 cell's** section as well as
  the 案名's. The gazette's 案名 says 河堤五小段 and its 地號 cell says
  河堤段五小段; the city indexes the cell's.
- The parcel search asks for the section the **city indexes**, not only the
  one the 案名 prints: the search retries the 地號 cell's section when the
  案名's returns nothing.
- The parcel search accepts a case found under **any parcel of the unit**,
  not only its first. The city indexes 臨沂412 under 414 and 復興3 under 7.
- The national portal's **title search** becomes a third id source for a unit
  the parcel search does not index at all (懷生928), confirmed by the case's
  own header before the id enters the project's case list.

The comparison stays a **superset** of the pipeline's own: measured over the
5,185 node × candidate pairs the pipeline compares today, it adds 3 bindings
and loses none. The 3 additions are cases the gazette's own 地號 cell names
correctly and its 案名 does not.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `taipei-case-discovery`: the parcel search must retry the 地號 cell's
  section and accept a case indexed under another parcel of the same unit.
- `official-link-discovery`: the land-core comparison must accept a section
  form and a parcel-set match, and must offer the 地號 cell's core as an
  alternative to the 案名's.

## Impact

- `urtpe/links.py` — `_parse_landcore`, `compute_landcore_similarity`,
  `_tier3_names_match`, `_search_taipei_raw`, `resolve_node_cases`.
- `urtpe/cleanse.py` — the record must carry the 地號 cell's section, which
  it already parses but discards in favour of the 案名's.
- `data/.link_cache/` — a refresh writes the newly found ids. The 7 projects'
  caches gain their case ids; the other 682 are unchanged.
- The emitted payload: 7 projects gain a 北 badge on 11 nodes. The record
  count and the project count do not move.
