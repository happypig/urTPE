## Context

See `proposal.md` for the motivation and the measurement. Constraints that shape the
approach:

- `resolve_node_cases` step 2 already builds the stems from every known id and probes
  `<stem><0-9>` with `fetch_taipei_case_header_api`. Its trigger (per unplaced node)
  and its acceptance (案名 and date against a node) are what fail for a sibling.
- Design rule D7 of that resolver: the emission side issues no request. Live probing
  runs only from a driver script.
- The §8 gate (`verify_view_verified_ids`) decides a city name with an inline
  `city_ok` expression. F3 (`91f7088`) put `own_parcels` in every cache, so the walk
  can read the unit's parcels from the cache.
- The F4 probe pass counted interior gaps from `city_case_ids` plus `view_rejected`.
  A rejected id is evidence that the stem is held; it is not an id to probe.

## Goals / Non-Goals

**Goals:** find the same-unit siblings in the interior of a held stem; decide by one
predicate that the §8 gate also calls; never repeat a probe; leave the emission path
request-free.

**Non-Goals:** ids beyond a stem's held minimum and maximum; other stems; the
declared-count condition on the gate and on the held-by-no-project pairs (F7);
changing a single verdict of the §8 gate; drawing a node for a found case (the normal
attach and the orphan branch decide that on the re-emit).

## Decisions

**1. One predicate, `unit_accepts_case_name(own_land_core, case_name, own_parcels,
*, require_equal_count=False)`.** It returns True when the name yields a land core and
either that core equals the unit's core or scores at least the link threshold, or
`_names_an_own_parcel_in_the_own_section` holds. The gate's `city_ok` becomes a call
to it with the default keyword, so the gate's verdicts do not move (the existing gate
tests and a pair-by-pair check over the payload are the proof). The walk calls it with
`require_equal_count=True`: the own-parcel form then also needs the name's declared
count (`等N筆`) to equal the unit's count (the land core's `等N筆`).

*Why a keyword:* F7 decided a single count rule (the name's count, or its `原N筆`,
equals the unit's count at any approval) for the gate and for the admission of
held-by-no-project pairs. That rule needs the unit's earlier counts as required input,
which F7 introduces. Until then the walk must not admit `09012312` (長春559-5, counts
69 against 80, unproven). F7 deletes this keyword and applies its rule to both
callers.

*Alternative:* land-core-only acceptance for the walk. Rejected: it would refuse a
drifted sibling (the 華中247 shape) that D4 = A exists to accept.

**2. The predicate refuses a nameless or parcel-less name.** The gate keeps such a
name (no evidence of a foreign unit). The walk needs evidence *for* the unit, so the
predicate returns False when the name yields no land core. The gate keeps its own
early branch for `not city_lc` before it calls the predicate.

**3. `walk_unit_siblings(disc, own_land_core, own_parcels, *, held_elsewhere=(),
fetch_header=None, fetch_milestones=None, sleep=None, max_requests=None) -> dict`.**
Candidates: group every held id (`city_case_ids`, `view_verified_case_ids`,
`view_rejected`) by `id[:7]`; per stem take the lowest and highest last digit; the
candidates are `stem+d` strictly between them that are not held, not in
`held_elsewhere` and not in `disc.sibling_probed`. Headers come from `fetch_header`.
The adapters default to the live ones, as in `resolve_node_cases`, so the function
issues a request only when a caller runs it. It returns a report `{added, none,
other_unit, errors, skipped_held_elsewhere, requests}` and mutates `disc` in place.

**4. Header, then decision.** A header with no `CASE_NAME` is `none`. A header whose
name fails the predicate is `other_unit`. A header whose name passes joins the cache:
`city_case_ids` (append), `candidate_names`, `case_case_names`, `case_headers`, and
`case_milestones` from `fetch_milestones`. A fetch that raises is an error and is not
recorded.

**5. `DiscoveryResult.sibling_probed: dict[str, str]`**, default `{}`, written to
`result.json` and loaded with `.get`. Values are `none` and `other_unit`. It is
append-only. The gate and the viewer do not read it.

**6. The driver, `scripts/walk_unit_siblings.py`.** It loads the payload and every
cache, builds `held_elsewhere` (every project's `city_case_ids`), and runs the walk for
each payload project with a cache. The dry run (default) prints the candidate ids per
project and issues **no request**. `--apply` takes the single-writer lock, backs up
each `result.json` it changes into `data/.link_cache_backup_<stamp>_siblingwalk`,
sleeps 1 s per request, stops at `--max-requests` (default 80, above the measured 63),
then saves each changed cache. The re-emit is the normal
`python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links`.

**7. The payload effect is measured, not assumed.** The re-emit task counts nodes,
badges and callouts before and after, and re-pins the badge and callout tests. A found
case that no node anchors may become an orphan that the S5 branch refuses (as
華中247's `09305080`). The report states that count.

## Risks / Trade-offs

- [The walk admits a case of another unit by the own-parcel form] → the equal-count
  condition. The three own-parcel accepts in production were all right. F7 widens this
  on purpose.
- [A real sibling is refused because its name has another parcel or count] → it is
  recorded `other_unit` and never retried. The F7 rule or a ledger entry decides it
  later. The walk's report names each such id once.
- [The 7 ids rest on one probe pass] → the dry-run candidate list is compared with the
  F4 list, and a difference is reported.
- [A live run of at most 80 header requests] → 1 s pacing, a cap, a lock and a backup.
  It is the same read-only endpoint F4 used, with 0 errors.
- [`sibling_probed` records an id that the city later changes] → the walk probes only
  the interior of a held stem, and a case id is a filing-day serial that the city does
  not rewrite. Noted, not fixed.

## Migration Plan

1. Land code and tests. Run the dry run and compare it with F4.
2. Run `--apply`. Check the report: 7 added, the others recorded.
3. Re-emit. Re-pin the badge and callout counts. Commit.
4. Roll back by restoring the backed-up `result.json` files and re-emitting. Older code
   ignores `sibling_probed` (loaded with `.get`).
