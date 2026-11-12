# Proposal: dashboard-spec

## Why

The policy dashboard (`viewer/dashboard.html`, `dashboard.js`, `dashboard.css`)
shipped on 2026-11-11 in commit `94cd3e8` and closed its publishing contracts on
2026-11-12 in `ee389c2`, with no openspec change behind it. It was ported by hand
from the Claude Desktop artifact "Taipei urban renewal: process duration"
(`https://claude.ai/artifact/DMpCPHZGqougawwmvMxz2H`), whose 14-column derivation
was rebuilt in the repo and matched byte-for-byte on all 682 rows on 2026-11-09.
So the shipped page carries the artifact's rules, but nothing in `openspec/specs/`
states them: no `policy-dashboard` capability exists, and the only spec that names
the dashboard is `viewer-related-links`, for its header links and palette.

Three actors are exposed by that gap:

- **The policy reader** arriving from the PUMA 都更政策 / 住宅政策 pages reads a
  stage, an idle flag and a median whose definitions live only in the page's
  own 定義與限制 block and in `viewer/dashboard.js`. Nothing outside the code
  says that 已完工 means "a use-permit date is recorded" or that idle years run
  to the gazette's 統計至 date, not to today.
- **The maintainer** of the next viewer change has nine tests in
  `tests/test_viewer_dashboard.py` that pin the deploy record, the cache-bust,
  the version agreement and the two links — and none that pin a derivation
  rule. A change to the stage order (say, a start date outranking a completion
  date) passes today's suite and today's specs.
- **The artifact**, which is the only record of provenance, is a design
  reference and not a source: its page calls the artifact runtime and renders
  nothing when copied, and its data is a CSV snapshot that goes stale at every
  gazette. No file under `docs/`, `scripts/` or `openspec/` names it.

The measured corpus moves at every gazette (682 → 681 → 680 projects across
2026-11-06 → 2026-11-12), so every figure on the page moves with it. A rule that
is not written down is re-derived, differently, by the next session.

## What Changes

- **A new capability, `policy-dashboard`**, whose delta spec states what the
  shipped page does today, read from `viewer/dashboard.js` and measured against
  the 2026-10-28 payload (680 projects / 1,444 records): the page reads the
  viewer's payload and computes every figure in the browser; each project is
  placed in one of four stages by its furthest recorded construction milestone;
  idle time runs from the last recorded progress to `published_date` with 3- and
  5-year flags; dates are read under either calendar and implausible dates are
  treated as absent; review time runs from the earliest application to the
  first approval, total time to completion, with medians over present values;
  approvals are counted by year and split 擬訂 / 變更; households, public land
  and public-benefit area are read from the implementation record; every figure
  is available for 全市 and for one district; the two tables name the projects
  behind the figures and link to their history graphs; the view is linkable and
  bilingual through the URL hash.
- **The derivation rules gain tests** over fixture payloads, driven through a
  node harness after `scripts/viewer_smoke.js`, one per scenario — the shape
  `docs/DashboardNUXUI.md` §13.1 already names as the better one for the
  dashboard. The nine existing publishing-contract tests stay as they are.
- **The provenance is recorded** once, in the notes' revision record, so the
  artifact's address survives the session that knew it.
- **No behavior change.** The code is the reference implementation; where it
  reads a field the current payload never carries (two of its six construction
  date sources, see design.md D2), the spec states the source list as the code
  has it and the design records the measured gap for a follow-up change.

## Capabilities

### New Capabilities
- `policy-dashboard`: the published policy dashboard page — its data source
  and freshness contract, the stage / idle / duration / land derivation rules
  it applies to every project, the per-district scope, the two tables, and the
  linkable bilingual view.

### Modified Capabilities
<!-- none -->
- (none) — the dashboard's header links and the 關於 chip are already required
  by `viewer-related-links`; the derived cache-bust by `pdf-tsv-extraction`;
  the deploy record by `deployment-verification` ("Every published page is
  covered by the artifact list"). The new capability cites those contracts for
  its own page and adds no requirement to them, so the archive is ADDED-only
  and the scenario-count guard has nothing to drop.

## Impact

- `openspec/specs/policy-dashboard/spec.md` — created by the archive from the
  delta, with its `## Purpose`.
- `scripts/dashboard_smoke.js` (new) and `tests/test_dashboard_rules.py` (new):
  the test-first group. `tests/test_viewer_dashboard.py` is untouched.
- `docs/DashboardNUXUI.md` §14 — one revision entry naming the artifact and
  this change.
- No change to `viewer/`, `urtpe/`, `data/` or the published site. The
  suite count in `AGENTS.md` moves by the number of new tests.
