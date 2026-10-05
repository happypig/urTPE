## Why

Six defects were found in the same session, and every one of them shared a shape:
**something was lost or broken and nothing said so.** In each case the pipeline
reported success, every test passed, and the data was already on disk.

The one that reached the user was a viewer regression. A dataset rebuild ran without
`--links`, so link discovery never ran and no portal data was attached:

```
                          before → after
  project.links            10 sub-keys → {} for all 709 projects
    twur                       708 → 0
    milestones_taipei          700 → 0
    orphan_nodes               388 → 0
  node.links                1419/1419 → 0/1422
```

Every project's detail pane then showed only the `index.html` placeholder. The cause
was a single line — `app.js:1011` read `n.links.taipei[0]` with no guard, the only
unguarded read of that field in the file — so one throw inside `renderDetail` blanked
the pane for all 709 projects. The left pane lost its construction-stage chips, the
national-portal badge and the orphan-node counts at the same time.

The suite passed throughout, and the reason is now clear and general:

- `test_e2e` asserts that files exist and counts match, against a **5-row fixture**
  in which every record is its own project
- the viewer's consistency tests check that `published_date` and `counts` agree
  **between two files** — an empty `links` object satisfies all of them
- **there is no browser test at all**; the page is a static `file://` document that no
  automated check ever loads
- `docs/cli_flow_v2.md:83` documents `--links` as "recommended", and the flow diagram
  branches on `{--links?}` optionally — so the default path silently produces a dataset
  that violates two existing capabilities

That last point matters most: this was not an unstated gap. `official-link-discovery`
already says the system "SHALL attach discovered links to projects and to individual
records", and `taipei-implementation-data` already requires per-record implementation
snapshots, project-level emission of implementation and rewards, and that "Viewer
renders implementation and reward cards". **The emitted dataset violated requirements
that already existed and no gate checked conformance.**

The same shape appears in `urtpe/coverage.py`, which has been carried through a
previous change as a parked observation and is now demonstrably live rather than
theoretical. Line 51 computes regressions over `set(before) & set(after)`; line 81
raises only on `d["regressions"]`. Under a total re-key the intersection is empty, so
the guard passes while every cache is orphaned — and `d["lost"]`, which would have
caught it, is recorded and never acted on. That is the identical failure mode to the
2026-08-24 incident in which four concurrent writers wiped 47 caches.

Two smaller items belong here. The viewer header lost its `統計至` label when the
publication date normalised to ISO, leaving `· 2026-08-27` ambiguous between a
publication date and a generation timestamp. And a truncated 地號 cell is currently
always excluded, including the cases where the same unit's complete parcel list is
printed elsewhere in the same corpus and can be verified three independent ways.

## What Changes

- **BREAKING** Report a portal-field loss at emission. A run that drops the
  link-derived fields `official-link-discovery` and `taipei-implementation-data`
  require SHALL say so, naming the fields and the counts, instead of emitting a
  conforming-looking dataset.
- **BREAKING** Require the viewer to degrade, never to blank. A node missing an
  optional field SHALL cost that one badge or card, not the detail pane for every
  project.
- **BREAKING** Amend `pdf-tsv-extraction` to permit a **bounded, audited** repair of a
  publisher-truncated 地號 cell from another approval of the same unit in the corpus,
  where three independent checks agree. It currently forbids this outright.
- Make `coverage.py` able to observe a total re-key, and treat a wholesale identity
  change as the distinct failure it is rather than as `regressions = {}`.
- Decide and record the `--links` policy for a repository rebuild: advisory with a
  guard, or mandatory.
- Restore the `統計至` label to the viewer header alongside the ISO publication date.
- Add a viewer contract test over the emitted dataset, and a headless smoke test that
  exercises the real `init() → renderList() → renderDetail()` path.

### Non-Goals

- Re-deriving portal data the caches no longer hold. Where `.link_cache` has no entry,
  the field stays absent and the viewer degrades; nothing is re-scraped.
- A general browser test suite. The smoke test drives the real render path far enough
  to catch a field-contract break, not to test interaction design.
- Deciding whether the city truncates by date permanently (still parked), and any
  portal sync work (still parked on reconciliation being trusted in production).

## Repair scope, stated precisely

Of the five records excluded from the `1150827` build, exactly one is safely
repairable. A repair is permitted only where all three checks agree:

| 編號 | same 段/小段 | literal prefix | count closes | outcome |
|---|---|---|---|---|
| 1198 | yes | yes | 102 + 8 = **110** = declared | **repair** |
| 1210 | yes | yes | 61 + 1 = **62** ≠ declared **72** | stays excluded |
| 1141, 1204, 1381 | no candidate | — | — | stay excluded |

`1210` is instructive: its candidate lists 62 parcels while *its own* 案名 claims 72, so
neither publication holds the complete list. Repairing it would assert 62 parcels for a
record that should have 72, with no way to know which 10 are missing. The count check
exists precisely to refuse that, and it does.

Both candidates live in `1151002` — the gazette excluded from the dataset for carrying
15 truncated cells of its own. Using it as a repair source is defensible for `1198`
only because three independent checks agree, and the repair is recorded with its
provenance rather than applied silently.

## Impact

**Code**

- `urtpe/cli.py` — report portal-field loss after emission; `--links` policy
- `urtpe/viewer.py` — none required; the emission report belongs at the boundary
- `urtpe/coverage.py` — detect total re-key and act on `lost`
- `urtpe/extract.py` — bounded cross-approval repair of a truncated 地號 cell
- `viewer/app.js` — guard the remaining unguarded field reads; restore the `統計至` label

**Specs**

- `pdf-tsv-extraction` — MODIFIED "Distinguish reader faults from source faults in cell
  content" (permit bounded repair); ADDED requirements for the viewer data contract
- `official-link-discovery` — ADDED requirement: emission reports dropped link data
- `taipei-implementation-data` — ADDED requirement: the viewer degrades rather than blanks
- `gazette-reconciliation` — ADDED requirement: a total re-key is reported as a distinct
  outcome by the coverage guard, not only by reconciliation

**Data**

- `1150827` gains 編號 1198; 4 records remain excluded and reported
- `viewer/projects.data.js` regenerated with portal data attached

**Dependencies**

- None new. `pymupdf`, and `scripts/viewer_smoke.js` uses only Node's `vm` and `fs`.
