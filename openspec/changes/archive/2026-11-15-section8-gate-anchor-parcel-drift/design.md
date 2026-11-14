## Context

See `proposal.md` for the motivation and the measured population.

The §8 gate is `verify_view_verified_ids` (`urtpe/links.py`). It receives the
cache's own land core, the ids, the city names and the labels. It returns kept,
rejected, not-confirmed and label-error ids. The refresh calls it once per run,
after the view page's ids are absorbed. A rejected id leaves `view_verified_case_ids`
and `city_case_ids`, loses its milestones, and is recorded in `view_rejected`.

The parcel search has its own admission rule, `_case_name_carries_parcel`. It
keeps a case when the case name carries the searched parcel **or any of the
unit's own parcels** (`own_parcels`). That rule exists because the city indexes
a case under whichever parcel it lists first (臨沂412, 復興3).

Three facts shape the design:

1. **The gate has no parcel list.** It gets a land core, which holds one parcel.
   `refresh_project` has the parcel list only when a caller passes `search_key`.
   Measured: six scripts call it. Two pass no key (`verify_view_verified_ids.py`,
   `refresh_rederive_pass.py`). Three pass a three-part key with no parcel list
   (`refresh_awaiting_caches.py`, `refresh_whole_corpus.py` through the same
   loader, `refresh_second_id_source.py`). Only
   `refresh_unplaced_by_cell_section.py` passes the five-part key with the
   parcels. A gate that reads the key alone would
   accept an id on one run and reject it on the next. That is a silent
   regression, not a fix.
2. **A recorded rejection is final today** (S3a). The absorb skips ids in
   `view_rejected`, and the merge step does not re-add them. A corrected gate
   would change nothing for the three affected ids without a re-decision step.
3. **The cache is a plain dataclass dump** (`asdict` / `DiscoveryResult(**data)`).
   A new field with a default needs no migration. The payload is built field by
   field, so a cache-only field does not reach `--from-js`.

## Goals / Non-Goals

**Goals:**

- A view-named case of the unit's own parcels is kept, whichever parcel its
  案名 starts at.
- The gate gives the same answer on every call path.
- The three affected ids return to their projects in one refresh and one
  re-emit.

**Non-Goals:**

- No change to `LINK_THRESHOLD`, to the shape A / shape B reasons, or to the
  offer step.
- No repair of 市府220-2's cache land core (a wrong district, 中正區). The change
  names it. A repair is a separate change.
- No change to the payload schema or to the viewer.
- No attempt to find view-named ids that no cache ever recorded.

## Decisions

### D1. Accept on section plus an own parcel, using the search's own predicate

The gate keeps an id whose land core does not match when both hold:

1. the section text of the city name's land core equals the section text of the
   cache's land core. Section text is the part before the first digit
   (`萬華區華中段一小段`), so district and 段/小段 are both compared;
2. `_case_name_carries_parcel(city_name, own_first_parcel, own_parcels)` is true.

Condition 2 is the predicate the search already trusts, so the two routes now
agree. Condition 1 is the new part. The search gets it for free from its query
(it asks the city for one section). The gate has no query, so it must test it.
Without condition 1, a foreign case that shares a parcel number would pass.

**Alternatives rejected:**

- *Lower the threshold below 0.45.* The measured foreign id 09608220 sits in
  犁和段一小段, the same section as its project, and names parcel `165`. Any
  threshold that admits 0.45 for 華中247 needs a parcel test to refuse it.
  The parcel test is the real discriminator; the threshold is not.
- *Score the name's land core against every own parcel's land core.* It needs
  26 to 55 similarity calls per id and gives the same answer as the token test.
- *Accept on section alone.* It admits 09608220. The measurement refuses it.

### D2. The cache stores `own_parcels`

`DiscoveryResult` gains `own_parcels: list[str]` (default empty). It is written
in three places:

- discovery, from the anchor record's parcel list, beside `land_core`;
- `refresh_project`, when `search_key` carries a parcel list (it overwrites);
- a one-time backfill (task 4) for the caches that hold view ids.

A `--fresh` discovery carries it forward like `case_headers` (B3). The gate reads
the key's parcel list first and falls back to the cache's `own_parcels`. An empty
list means "no evidence": the land-core rule alone decides, as today. So a cache
nobody backfilled behaves exactly as before.

**Alternative rejected:** pass the key in every caller. Five callers, three key
shapes, and the failure is silent. The cache is the one place every caller
already reaches.

### D3. Re-decide recorded rejections before the absorb

A new step runs first in the view part of `refresh_project`. For each id in
`view_rejected` with a held city name, it runs the gate rule. When the rule keeps
the id, the step removes the record. The absorb then adds the id to
`view_verified_case_ids` and `city_case_ids` and fetches its milestones, and the
merge-never-replace step no longer skips it. An id the rule still rejects keeps
its record and is not fetched, as S3a requires (09511211 and the others).

The step is idempotent. A second run finds nothing to lift.

### D4. The section check stays strict; 市府220-2 is named, not fixed

The 市府220-2 cache records land core `中正區市府段二小段220-2地號等54筆`. The
project and the city name both say 大同區. The district differs, so condition 1
fails and 09609301 stays rejected. This is conservative. Loosening the check to
ignore the district would make the gate depend on a cache field that is known to
be wrong. The change records the id and the cause in the board and leaves the
repair to its own change.

### D5. What the re-emit moves

The re-emit reads the caches. The three ids affect the payload as follows:

- 華中247: 09305081 anchors on the node of 2014-04-25 (with 09305082) and
  09407302 on the node of 2015-10-02 (with 09407301). Each node then holds two
  cases. Whether the E7 per-case callout shows `[A區]` and `[B區]` depends on
  the cases having implementation payloads; the absorb fetches milestones only.
  The change does not promise the callout. The re-emit measures it, and the
  board records the result.
- The two nodes gain the 國 badge if they did not have it: the badge rule reads
  `view_verified_case_ids`.
- `tests/test_national_badge.py` counters move and are re-pinned from the new
  payload. The count is measured, not predicted.

## Risks / Trade-offs

- **A same-section foreign case that names one of the unit's parcels.** Two
  units cannot both own one parcel in one section, so the case is the unit's own.
  The measured population has 0 such ids (the 7 foreign ids all fail condition 1
  or 2). The 54-parcel and 25-parcel units give the token test the widest
  surface; the tests pin a `220` versus `2201` boundary.
- **The mono form of the predicate.** `220` matches `220地號` as a declared
  parcel. It cannot match `2201` (the token pattern forbids a digit before and
  after). Pinned.
- **Population is the recorded rejections only.** A view-named id that no cache
  recorded (a cache older than the gate) is not seen. The task list includes a
  re-count after the refresh, and the board names the limit.
- **Network cost.** The refresh of the two affected caches made 26 city
  requests (13 milestone, 11 header, 2 view page) and no search request, because
  the run passes no search key. The design first estimated two; the refresh also
  reads headers and the milestones of cases it already held. The city answered
  all 26. The correction runs under the single-writer lock with a delay between
  projects.
- **Backfill writes cache files.** Only caches holding view ids are touched, and
  their `result.json` files are copied to a dated backup first (AGENTS: the cache
  is the durable middle layer).
