## 1. The test-first group

Every task in this group must be fully checked before any task in group 2 or
later can be marked complete.

- [ ] 1.1 A test for the section-form rule: two sections match when they
      carry the same 小段 suffix and the same 段 name, with a trailing 段
      optional on either side. `吳興一小段` matches `吳興段一小段`; `河堤五小段`
      matches `河堤段五小段`; `中山段二小段` does not match `吉林段五小段`.
- [ ] 1.2 A test that the land-core comparison reads a core's section at both
      its first 段 and its last, so `河堤段五小段399地號等3筆` reads as the
      section `河堤段五小段` with parcel `399`, and not only as the section
      `河堤段` with parcel `五小段399`.
- [ ] 1.3 A test that the city core's parcel matches the node when it is one
      of the node's own parcels, not only its first: a node declaring
      parcels 163-2 and 247 matches a case declaring 247.
- [ ] 1.4 A test that the node's land core may be built from the 地號 cell's
      section: a node whose 案名 says `河堤五小段` and whose 地號 cell says
      `河堤段五小段` matches the city's `河堤段五小段` case.
- [ ] 1.5 A test that the comparison is a **superset**: every core pair the
      present comparison accepts, the widened one accepts too. The test
      replays the present rule over the same inputs and asserts the widened
      rule's match set contains it.
- [ ] 1.6 A test that the count mismatch still costs the count term exactly
      as before: a node declaring `等1筆` and a case declaring `等12筆` still
      match, at the same score.
- [ ] 1.7 A test for the search's section forms: the search asks for the
      地號 cell's section when the 案名's section returns nothing. The test
      drives the search through a fake transport and asserts both forms were
      asked for, in that order.
- [ ] 1.8 A test for the all-parcel search: a case found under a parcel other
      than the unit's first is offered to the resolver.
- [ ] 1.9 A test for the portal title search as a third id source: when the
      parcel search and the 168 list both return nothing, the portal's
      `?title=` search is asked, and an id it names enters the project's case
      list only after the case's header confirms it.
- [ ] 1.10 A test that an unconfirmed portal id does not enter the case list,
      and is named in the refresh report as unconfirmed.
- [ ] 1.11 A test that the portal's own view id and national milestones are
      recorded when the title search finds the unit.
- [ ] 1.12 A test for the resolver's end-to-end acceptance on the 11 nodes:
      each of the 7 unplaced projects' nodes binds the case id the live
      search found. 10 of the 11 bind on an exact date match. The 11th
      (復興 recno 1081) binds on the header step's existing 10-day drift
      rule: its node's date is 2015-11-04 and the case's approval is
      2015-11-03. Step 4's date gate stays exact (design D6), so this node
      binds through the header step, not through the parcel search.

## 2. The land-core comparison

- [ ] 2.1 Add the section-form comparison: the same 小段 suffix and the same
      段 name, with a trailing 段 optional on either side.
- [ ] 2.2 Read a core's section at both its first 段 and its last, and pair
      every reading of one side with every reading of the other.
- [ ] 2.3 Let the city's parcel score the full weight when it is one of the
      node's own parcels, not only its first.
- [ ] 2.4 Keep the four-part weighted score and the count term's weight, so
      the widened comparison is a superset (design D1, D2).

## 3. The record's two cells

- [ ] 3.1 Carry the 地號 cell's section on the cleansed record, so the
      comparison can offer the cell's core as an alternative to the 案名's.
- [ ] 3.2 Keep the record's `section` field the 案名's section — the merge's
      grouping key does not change (design D3).

## 4. The search

- [ ] 4.1 Add the 地號 cell's section to the forms the parcel search asks
      for, tried after the 案名's form returns nothing.
- [ ] 4.2 Let the all-parcel search find a case under any parcel of the unit
      (design D4).
- [ ] 4.3 Keep the search's three-retry bound and its >= 1 s spacing.

## 5. The portal as a third id source

- [ ] 5.1 Ask the national portal's `?title=` search when the parcel search
      and the 168 list both return nothing (design D5).
- [ ] 5.2 Read the case ids from the page's 相關連結 block.
- [ ] 5.3 Confirm each id with the case's own header before it enters the
      project's case list, and append it — never insert it.
- [ ] 5.4 Record the portal's own view id, its URL and the national
      milestones read from the page.
- [ ] 5.5 Name an unconfirmed id in the refresh report.

## 6. Verification

- [ ] 6.1 The full suite passes: `python -m pytest`.
- [ ] 6.2 The probes re-run and their counts hold: the widened rule matches
      11 of the 11 unplaced nodes, and over the 5,185 node × candidate pairs
      it adds 3 bindings and loses none.
- [ ] 6.3 The 7 projects' caches are refreshed, one writer at a time, with
      no `data/.pipeline.lock` present and the peers notified.
- [ ] 6.4 A re-emit runs: `python -m urtpe.cli --from-js
      viewer/projects.data.js -o data --viewer viewer --links`. The record
      count and the project count do not move.
- [ ] 6.5 `node scripts\viewer_smoke.js` passes after the re-emit.
- [ ] 6.6 The coverage report's 問題一 table is regenerated and names 0
      projects with no case id.
