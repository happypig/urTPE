# Optimization board — update automation, gen-1 membership, gen-2 viewer

Collected 2026-11-15 to 2026-11-20. Item identifiers do not change: `U1–U8`, `A1–A7`,
`U-D1–U-D5`, `M1–M4`, `D11`, `O1–O11` and `O-D1–O-D7`.

| Part | Subject | Items | Priority | Origin |
|---|---|---|---|---|
| I | Run the PDF and city-platform update as one deterministic cycle | U1–U8, A1–A7, U-D1–U-D5 | **P1** | exploration 2026-11-19 |
| II | Gen-1 membership: measurements that follow decisions D11 and S3/S5 | M1–M4, D11 | **P2** | moved here from `docs/inspections/inspection-batchF.md` |
| III | Gen-2 viewer: one `project_uid` for applications and approvals | O1–O11, O-D1–O-D7 | **P3** | exploration 2026-11-19, re-measured 2026-11-20; O10 and O11 added 2026-11-21 |

**Why this order.** Part I depends on nothing in Parts II and III. It protects the data
that both of them read. Part II decides how a city case joins a unit. Part III adds a new
source and a new identity layer, and it must reuse the Part II decision. A second
membership rule in Part III would repeat the seven-rule problem that Batch F measured (F1).

**Rules for this board.**

- Every figure names its date and its source. A figure that was not re-measured says so.
- A recommendation is not a decision. An OpenSpec change opens on the user's word, one item
  at a time. `openspec list` reported no active change on 2026-11-19.
- This board changes no code, no payload and no spec. Part II keeps decisions that the user
  already made on 2026-11-15; Part I and Part III hold none.

**State at 2026-11-20.** Payload `data/projects.json` at commit `6b97a83`: 1,448 records,
676 projects, 統計至 2026-11-12, 2,028 Viewer case ids that carry a name. District tables:
3,655 distinct rows, 3,651 distinct `case_id` values (read 2026-11-19).
`P_project168.aspx` snapshot 2026-11-18T12:31:41Z, 468 ids. The district-page measurements
are in `docs/portals/urotpe_district_pages.md`; its scripts reproduce them (§7 there).

---

## Order and dependencies

Execute top to bottom. A row waits for every item in its "Depends on" column.

| Step | Part | Item | Priority | Form | Depends on |
|---:|---|---|---|---|---|
| 1 | I | **A1** — the refresh takes the single-writer lock | **P1** | fix only | — |
| 2 | I | **A2** — offline candidate-only fast path | **P1** | fix only | A1 |
| 3 | I | **A3** — structured poll adapter and failure logs | **P1** | fix only | — |
| 4 | I | **A4** — deterministic PDF-cycle coordinator | **P1** | OpenSpec change | A1–A3, U-D1 |
| 5 | I | **A5** — report ownership and publication mode | **P1** | OpenSpec change | A4, U-D2, U-D3 |
| 6 | II | **D11 = A** — S1's own-parcel form adopts the count rule | **P2** | OpenSpec change (decided; not opened) | the user's word |
| 7 | II | S3/S5 choice and F8 option C | **P2** | one OpenSpec change each | D11, M4 |
| 8 | I | **A6** — independent city-only cadence | **P2** | OpenSpec change | A4, U-D4 |
| 9 | III | **O1** — identity ledger and `project_uid` | **P3** | OpenSpec change | D11, O-D1, O-D2 |
| 10 | III | **O2** — keep `case_id` per application; flag the four conflicts | **P3** | schema field | O1 |
| 11 | III | **O3** — keep meeting-label rows out of project counts | **P3** | filter rule | O1 |
| 12 | III | **O5** — match amendments through `membership_verdict` | **P3** | match rule + manual review | O1, D11, M4 |
| 13 | III | **O6** — separate pending dataset | **P3** | payload shape | O1–O3, O5 |
| 14 | III | **O9** — fit the pending lane into the ETL and the update cycle | **P3** | OpenSpec change | O6, A4–A6, O-D4–O-D6 |
| 15 | III | **O7** — prove on the nine matched units | **P3** | ledger entries, no graph change | O1–O3, O5, O6 |
| 16 | III | **O8** — what the gen-2 Viewer shows | **P3** | design, then a read-only page | O6, O7 |
| 17 | III | **O4** — reuse the Viewer UI components | **P3** | direct fix after the payload exists | O6, O8 |
| 18 | I | **A7** — optional read-only diagnostic agent | **P3** | OpenSpec change | A4–A6, U-D5 |
| 19 | III | **O10** — reconciliation page: release-diff count to Viewer count | **P3** | fix only (the 652 note), then design and a read-only page | fix: —; page: O6, O8 |
| 20 | III | **O11** — marks on patched values, original value on hover | **P3** | OpenSpec change (sidecar, ledger field), then UI | O1, O6, O8, O-D7 |

Four dependencies cross Part boundaries:

1. **O5 depends on D11 and M4.** Matching an application to a unit is a membership
   decision. It must be one more named policy of `membership_verdict`, with its own golden
   table, and not a second predicate.
2. **O6 operates at the pace of A6.** A pending application changes more often than a
   gazette appears. A pending dataset that refreshes only with the PDF cycle is always old.
3. **O1 reads what A1–A5 protect.** The identity layer reads the Viewer payload and the
   city cache. A4 and A5 keep those from being written by two runs at once.
4. **O9 changes Part I.** A pending lane adds an acquisition step, a join step and three
   state layers to the update cycle. Part I stays correct for the approved lane. O9 lists
   the effect on U1–U7.

---

## Decisions to make

| # | Question | Recommendation | Status |
|---|---|---|---|
| U-D1 | May a scheduled coordinator initiate ingestion after hash acquisition? | yes, through an OpenSpec change and all existing gates | **undecided** |
| U-D2 | Does the first coordinator stop before git publication? | **A: generate and stop first** | **undecided** |
| U-D3 | If automatic publication is later approved, who owns `release-diff.html`? | one cycle owner; serialize or supersede the report-only publisher | **undecided** |
| U-D4 | Should city-only refresh have its own cadence? | measure the need separately; do not couple it to PDF ingestion | **undecided** |
| U-D5 | Should a diagnostic agent receive a failure bundle? | only after deterministic logs prove a triage need | **undecided** |
| D11 | Does S1's own-parcel form adopt the count rule? | **A** | **decided 2026-11-15: A.** The change is not opened. |
| S3/S5 | Does S5 adopt the gate rule? | measure first (M4), then decide | **decided 2026-11-15: measure first.** M4 is that measurement. The choice after it is open. |
| F8-C | Remove a cross-listed case from the wrong holder? | wait for D11 and the S3/S5 choice | **decided 2026-11-15: wait** |
| O-D1 | Where does the identity ledger live, and who may append? | a separate append-only file with the correction ledger's rules (keyed on land core and date, never on 編號 or `case_id` alone) | **undecided** |
| O-D2 | What evidence assigns a record to a `project_uid`? | the `membership_verdict` land-core rule, the same district, and manual review for every ambiguous match (O5 measured one) | **undecided** |
| O-D3 | Does any of the four conflicting IDs get a ledger correction? | no. Record the evidence; let the city correct its own ID | **undecided** |
| O-D4 | Do the approved lane and the pending lane fail independently (O9)? | yes. A pending-lane failure stops that lane only. The old pending file stays and is marked stale with its observation time. | **undecided** |
| O-D5 | Where does the pending lane write? | its own output tree with its own lock. It reads `data/projects.json` at one named revision and never writes `data/`. | **undecided** |
| O-D6 | Does the district crawl have its own cadence? | yes. This answers U-D4 for the pending lane. Decide the interval after the change rate is measured. | **undecided** |
| O-D7 | Where does the original value of a patched field live (O11)? | a sidecar keyed by land core and approval date, written at apply time. It does not rewrite `projects.json`. | **undecided** |

---

## Part I — Run the PDF and city-platform update as one deterministic cycle (U1–U8)

This section follows the gen-2 source exploration. It concerns the current approved-record
pipeline. It does not depend on gen-2 and does not put district-page applications into the
approved graph.

**Source and state.** The measured payload at `6b97a83` holds 1,448 records and 676
projects, 統計至 2026-11-12. A targeted refresh selected 101 projects and updated 8 approval
dates, changed 14 statuses, added 6 cases and reported 0 failures. A later dry run selected
94 projects. The rebuild preserved all 1,448 records and 676 project ids. The full suite
reported 1,494 passed, 1 skipped, 4 xfailed. All 12 deployed artifacts matched the commit.

**Current boundary.** The scheduled `urtpe-poll` task runs both pollers and
`publish_release_diff.py`. It does not ingest a PDF or update the Viewer. The full manual
runbook is `docs/pipeline/etl_process.md` §11. `openspec list --json` reported no active change on
2026-11-19. This section records recommendations, not new decisions.

### U1 — one deterministic cycle, not polling inside ingestion

**The gap.** `poll_gazette.py` detects a new PDF by content hash. Normal `--links` discovery
returns an existing cache without re-querying the city (`urtpe/links.py:618`). The refresh
changes the cache, not the Viewer payload. Three successful commands can therefore leave
three different layers current at different times.

**Proposed full cycle:**

1. Run `python scripts/poll_gazette.py`.
2. Run `python scripts/poll_p168.py`.
3. Detect a newly archived PDF by content hash and archive entry, not by timestamp or mtime.
4. Ingest the archived PDF with `python -m urtpe.cli <archived.pdf> -o data --viewer viewer
   --links --recover-truncated`.
5. Run `python scripts/refresh_awaiting_caches.py` after a successful ingest when its
   offline selector finds candidates.
6. Rebuild with `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer
   viewer --links`.
7. Run `python scripts/post_ingest_check.py`.
8. Run `python -m pytest` and `node scripts/viewer_smoke.js`.
9. Review the result, commit only the owned paths and push `main` only if publication was
   approved for that cycle.
10. Verify the remote commit and run `python scripts/check_deploy.py` after the Pages build.

The cycle coordinator calls the existing commands. It does not move scheduling into
`urtpe.cli`, the pollers, or `post_ingest_check.py`. A 168-list change alone does not trigger
PDF ingestion. The separate city-only cadence remains undecided (U7).

**Form: OpenSpec change.** `openspec/specs/gazette-cadence/spec.md` currently requires an
unattended check never to initiate ingestion. The coordinator may initiate a later gated
act, but the specification must say when that act is authorized and what evidence gates it.
This is not a scheduler-only fix.

### U2 — acquisition, cache state, emission and publication stay separate

| Layer | Owner of the write | What success proves | What it does not prove |
|---|---|---|---|
| Archive | poller | the hash-identified PDF or 168 snapshot is held | the PDF was ingested |
| City cache | targeted refresh | selected city replies were merged and reported | the Viewer contains the result |
| Emission | CLI ingest/rebuild | the graph and payload were written | the city reply was current or the case join was correct |
| Reports | `post_ingest_check.py` | checks passed and dependent artifacts regenerated | anything was committed or deployed |
| Deployment | explicit publication step | `origin/main` holds the commit and served bytes match it | unresolved source semantics were reviewed |

The selected refresh population is evidence-limited. It includes a payload project with an
anchor search key when a cached case has an application date but no approval date. Terminal,
superseded and `無` cases do not qualify. The 101 selections were not a count of stale caches,
changed projects, or every project that might hold an undiscovered case. See
`scripts/refresh_awaiting_caches.py:39` and `urtpe/links.py:2354`.

A completely missing case cannot itself trigger this selector. The 木柵623 project qualified
through existing pending cases; the refresh then found `10804122`. Gen-1 discovery coverage
is not closed by running this refresh every week.

**Form: fix only** to document these boundaries or add a machine-readable refresh candidate
count to an existing report. **Form: OpenSpec change** to widen discovery, change case
membership or claim citywide freshness.

### U3 — make the small safety gaps executable before scheduling

| Gap | Current evidence | Required boundary | Form |
|---|---|---|---|
| Structured gazette result | `poll_gazette.py` prints text; `poll_p168.py` has `--json` | preserve the poller contract; read the archive index for gazette id, SHA-256 and verified path | **fix only** adapter/tests |
| Refresh lock | `refresh_awaiting_caches.py` warns about concurrent writers but takes no lock | acquire `SingleWriterLock` over the `data` tree, as `scripts/refresh_second_id_source.py:96` does; report `LockHeld` and write nothing | **fix only** existing safety contract |
| Candidate-only refresh | `select_candidates()` is offline; 96 cases still awaiting does not mean 96 defects | select first; skip network and cache writes when no candidates exist | **fix only** if kept inside existing command semantics |
| Processed hash | the archive records acquisition, not successful full-cycle publication | an idempotency record names the PDF hash and reached stage; it does not replace archive history | **OpenSpec change** with U1 |

The coordinator must not parse a recno, current payload counts, or `new_gazette` text as
proof that an archived PDF is ready for ingestion. It must use the archived path and verify
its content against the archive entry. A previously processed hash must not be ingested again
merely because a later run started.

The processed-cycle state is operational state, not domain identity. It must not use recno
or `project_id` as the PDF key. A failed cycle remains resumable, but no retry may cross a
CLI refusal. Recovery starts with diagnosis of the recorded failed stage.

### U4 — failure stops the cycle before publication

**Required behavior:**

- Stop immediately on a failed check or command refusal.
- Never use `--allow-reconcile-block` or `--no-archive` to pass a refusal.
- Keep the single-writer lock around cache mutation.
- Publish no output from a failed cycle.
- Leave the previously deployed Viewer untouched after a pre-commit failure.
- Record the PDF hash, command, exit code, failed stage and observation time.
- Do not call an unchanged payload proof that no city case changed.
- Do not treat `post_ingest_check.py` as proof that a case-id binding is semantically right.

A push failure differs from a generation failure. It can leave a local commit ahead of
`origin/main`. The coordinator must report that state rather than discard the commit or
claim deployment. `check_deploy.py` distinguishes fresh, stale and missing served artifacts.
A failed deployment check must not trigger a new ingest or a payload rewrite.

**Not measured:** whether a Pages build can remain green while one or more served artifacts
still lag. `check_deploy.py` currently returns 1 for that state. A bounded deployment wait
needs its own exit contract; it must not turn a failed ingest into a retryable condition.

**Form: OpenSpec change** for cycle states and unattended retry policy. **Fix only** for
structured logs and preservation of the existing refusal behavior.

### U5 — publication needs an explicit mode and one report owner

| Option | Behavior | Consequence |
|---|---|---|
| **A — generate and stop** | run acquisition through verification; write no git commit or push | safest first automation; an operator reviews and publishes |
| **B — publish after all gates pass** | path-limited commit, verified push, Pages build and `check_deploy.py` | removes manual work; requires an explicit standing publication decision |
| C — agent chooses repairs and publishes | model judgment can change the cycle | **rejected**; non-deterministic and outside the bounded repair contract |

`publish_release_diff.py` regenerates, commits and pushes only `docs/release-diff.html`.
`post_ingest_check.py` also regenerates that report. Running both publishers in one cycle
can produce two commits with different timestamps and two Pages builds for unrelated payload
states. Path-limited commits protect unrelated work; they do not merge concurrent commits to
the same report.

A full-cycle run must therefore have one publication owner. The scheduled report-only path
must not commit the same report concurrently. A report-only run outside a full cycle keeps
its existing narrow scope. The solution must state whether the full cycle suppresses,
serializes or supersedes the report-only action. A simple flag that silently disables the
third scheduled action is not enough.

A path-limited commit includes only the cycle's declared paths. It must also protect against
concurrent payload writers and same-path report changes. The commit must contain a coherent
checked state, not files assembled from two different runs. A later successful push does not
repair an earlier failed payload check.

**Form: OpenSpec change** for automatic commit/push and shared report ownership.
**Recommendation: A first; B only after an explicit user decision and failure drills.** No
automatic commit, push or deployment is authorized by this board.

### U6 — validation must cover the cycle, not only its commands

The current commands already supply most gates. The coordinator must preserve their order
and add cycle-level proofs:

1. An unchanged PDF performs no ingest and creates no payload commit.
2. A newly archived, hash-verified PDF reaches ingest exactly once.
3. A refresh with no candidates performs no network calls or cache writes.
4. A `LockHeld` result stops before any cache write.
5. CLI exit 2, 3, 4 or 5 stops without bypass flags or publication.
6. A failed refresh does not get hidden by a later successful rebuild.
7. A rebuild preserves the recno partition and the payload's project ids.
8. Generated reports describe the same payload revision that the Viewer carries.
9. The commit excludes unrelated staged and modified paths.
10. A push or deployment failure is reported separately from an ingest failure.
11. Rerunning a completed PDF cycle does not ingest the same PDF again.
12. A new PDF after a failed cycle cannot make the failed stage look successful.

Test doubles simulate network, CLI refusals, locks and git results. The offline suite must
stay offline. One read-only live smoke run can exercise a temporary archive and output tree.
It must not mutate the real cache, repository or deployed site.

**Form: OpenSpec change** with U1 and U5; test-first tasks precede implementation.

### U7 — a city-platform change can need a different trigger

The PDF cadence and city-platform cadence are independent. A pending case can gain approval
before the next PDF publication. The 2026-11-19 refresh selected 101 projects and found
changes that ordinary cached discovery would not fetch.

A city-only scheduled refresh could run more often than PDF ingestion. It would still need
the candidate selector, single-writer lock, rebuild, checks and publication policy. It must
not re-read or rewrite the four PDF-derived layers as though a new gazette had arrived. The
last rebuild left `raw.tsv`, `clean.tsv`, `merged.tsv` and `review_report.txt` unchanged.

**Options:**

| Option | Trigger | Limit |
|---|---|---|
| **A** | full refresh/rebuild only after successful PDF ingest | simple; pending city approvals wait for the next PDF |
| **B** | PDF cycle plus a less frequent city-only cycle | fresher statuses; needs its own state, cadence and publication decision |
| C | full city discovery for every project on every poll | broad and costly; changes cache semantics and is not justified by this measurement |

**Form: OpenSpec change** for a city-only cadence. **Recommendation: decide it separately
from the PDF coordinator.** The 168-list poller remains an archived programme snapshot; its
change hash is not a complete pending-case change detector.

### U8 — optional agent expansion belongs after deterministic failure logs

**The question:** should an agent participate in periodic ingestion?

**Recommendation: no agent in the normal path.** Poll, ingest, refresh, rebuild, verify and
publish have fixed commands and success conditions. An agent must not decide whether a
refusal is safe to bypass, infer missing data, edit the cache or emitted payload directly,
or publish its own repair.

An optional diagnostic agent can start only after the deterministic coordinator stops. It
can classify the failed stage, compare the archived PDF, cache, payload and saved city reply,
and propose an existing bounded repair or a code change. It must identify records by land
core and approval date, not recno alone.

| Agent permission | Recommendation |
|---|---|
| Read saved logs and source evidence | allowed in a future diagnostic mode |
| Classify a failure and draft an incident report | allowed; not verification |
| Propose an existing bounded repair | allowed; deterministic checks still decide the result |
| Edit production cache or emitted payload | forbidden |
| Add a case id, date or parcel by inference | forbidden |
| Select `--allow-reconcile-block` or `--no-archive` | forbidden |
| Commit, push or publish autonomously | forbidden |
| Replace the coordinator's control flow | forbidden |

Useful triggers are a changed PDF table structure, a repeated case-name mismatch, or a
missing case outside the refresh selector's evidence. A routine pending approval needs no
model judgment.

**Form: fix only** to preserve structured failure bundles for manual diagnosis.
**Form: OpenSpec change** for any agent invocation, tool permissions or repair handoff.
Add this only if failure triage becomes frequent; it is not a prerequisite for U1–U6.

### Automation items A1–A7

| Step | Item | Priority | Form | Depends on | Notes |
|---|---|---|---|---|---|
| A1 | U3 — refresh takes the single-writer lock over `data` | **P1** | **fix only** | — | existing safety contract; test `LockHeld` before the first write |
| A2 | U3 — offline candidate-only fast path | **P1** | **fix only** | A1 | no candidates means no network and no rebuild |
| A3 | U3/U4 — structured poll adapter and failure logs | **P1** | **fix only** | — | no change to acquisition or refusal semantics |
| A4 | U1/U3/U4/U6 — deterministic PDF-cycle coordinator | **P1** | **OpenSpec change** | A1–A3 | amend `gazette-cadence`; hash idempotency and failure drills required |
| A5 | U5 — report ownership and publication mode | **P1** | **OpenSpec change** | A4; explicit user decision for automatic publication | start with generate-and-stop; one writer for `release-diff.html` |
| A6 | U7 — independent city-only cadence | **P2** | **OpenSpec change** | A4; separate cadence decision | not triggered by a 168 hash alone |
| A7 | U8 — optional read-only diagnostic agent | **P3** | **OpenSpec change** | A4–A6 and measured triage need | never in the normal ingest or publication path |

A1–A3 can land independently without opening a periodic ingest change. They do not authorize
A4. A4 without A5 can generate and verify but cannot publish. A5 decides who may commit and
push. A6 and A7 are separate expansions, not hidden parts of the PDF-cycle implementation.

### Automation decisions

U-D1 to U-D5 are in the "Decisions to make" table at the top of this board. All five are
undecided.

**If Part III goes ahead.** The district tables add a second lane to this cycle. See O9. Part I
stays correct for the approved lane and is not rewritten.

---

## Part II — Gen-1 membership: measurements after decisions D11 and S3/S5 (M1–M4)

These measurements concern the gen-1 membership rules, not the district-page source.
They moved here from `docs/inspections/inspection-batchF.md` without content changes. Their D11,
S3/S5 and F8 decisions belong to the Batch F membership work. They are not gen-2
implementation decisions.

**Decided 2026-11-15: D11 = A** (S1's own-parcel form adopts the count rule). The change
opens on the user's word (not yet opened). Also decided the same day: **S3/S5 —
measure first** (below); **F8 option C waits** for D11 and S3/S5; the three read-only
measurements below were ordered.

### Measurements M1–M4 ordered with those decisions (2026-11-15, all read-only)

**M1. The other 46 held-by-no-project pairs (33 projects).** Every one of the 46 names
starts at a different parcel than its unit's and carries a different count; none is the
unit's own parcel with the unit's count. Pattern: a same-section neighbour (`正義段三小段-418等10`
vs `419等9`, 3 cases; `大安段一小段-421等16` vs `427等17`; `臨沂363等28` vs `403等25`), or a
far larger or smaller unit (`永昌段四小段-46-4等117` vs `48等133` and `48等160`, 3 cases;
`虎林38等138` vs `376等48`). A name's parcel can sit inside a unit that later grew, so a
predecessor is possible (the 華興8 shape), but nothing in a name tells which. The hand
sample **does not support admitting them as a group**; D2's "leave them out" stands.
Each one would need its view page (or a user's look) to judge.

**M2. Ids beyond a stem's held min and max (F4's lower bound).** The population is **not
small**: 8,975 ids over all 10 digits of each held stem (7,932 distinct, 674 projects), or
**1,937** (1,903 distinct, 665 projects) for only the id just below the lowest and just
above the highest digit. The "about 60 requests" in the question was wrong. A pilot of
**40 adjacent ids** (the first 40 by project name, **not a random sample**) found: 37 name
no case, 3 name a case in another district, **0 accepted**. The full adjacent probe is
about 32 minutes at one request a second; it was **not run**.

**M3. The 4 nameless orphans have one cause.** The orphan branch reads the case name from
`search_rejected`, then `candidate_names`, never `case_case_names` or the header. All 4
have a name in `case_case_names`: `11412011` (南港玉成段二小段-166, its own unit's B區),
`09210151` (文山萬隆段二小段-463, its own unit's A區, view-verified), and `10203261` /
`10203262` under **玉成段二小段-253-1**, which are the `166地號等12筆` cases (held and badged
by project 166; listed under 253-1 too, F8's "not established" pair, now established as the
stem-rule cross-listing). A name fallback would draw nodes for `11412011` and `09210151`
(2 new nodes) and give `10203261/2` under 253-1 the "未達相似度門檻" flag instead of a silent
empty orphan (2 new flags). Not applied.

**M4. S5 adopting the gate rule (the dry run you chose).** Over the 529 named,
not-view-verified orphans on the payload: S5 accepts 505, both refuse 12, and **S5 refuses
but the gate accepts 12**. Those 12 are exactly: the 7 F7-admitted cases, 華中247's
`09305080`, 吳興163-2's 3 cases (`09102222`, `10103231`, `11510019`) and 臨沂412's `10010221`.
So the effect would be 12 orphan flags cleared and **12 orphan nodes drawn** (24 flags
become 12); nothing else moves. Caveats: the dry run uses the cache's land core, not the
anchor record's built core; it covers S5 only, not S3 (the offer step); a node's
"ghost" status is a viewer judgement, since each name carries a stage and a track.

---

## Part III — Gen-2 viewer: one `project_uid` for applications and approvals (O1–O9)

Eleven items. O1–O7 explore whether the current Viewer interface can be reused for a
generation-2 Viewer that holds district-page applications and gazette approvals under one
stable `project_uid`. O8 and O9 were added on 2026-11-20 from the design discussion. O10 and
O11 were added on 2026-11-21 at the user's request. They are proposals, and each one says
what was measured. Priority P3: it adds a source and an identity layer, and it waits for
Part II. Everything below was measured offline unless it says it made requests. The
2026-11-20 re-measurements read three live case headers (3 requests, read-only).

### O1 — one `project_uid` for applications and approval records

**The question.** Can one Viewer show an application from the district pages and an
approval from the gazette as entries of the same project history?

**Measurement.** No repository code assigns a stable unit id across the two sources. The
Viewer keys on `project_id` (the slug of the latest approval's land core), and every node
carries `recno`. District-page rows carry neither. They carry `case_id`, `case_name`,
`district`, `place`, `implementer` and a status.

The Viewer holds three ids that the district tables do not: `11510011`, `11510014` and
`11510015`. They are not extra projects. They are the 松山 cases' own ids (O2).

| Identifier | Meaning | Stable? | Safe as a durable key? |
|---|---|---|---|
| `project_uid` | Stable id of one renewal unit | yes, if assigned by evidence | **yes** |
| `project_id` | Slug of the latest approval's land core | churns (~11% of families moved) | no |
| `case_id` | Taipei portal lookup key per application | four printed ids conflict (O2) | no |
| `recno` | Gazette row coordinate within one PDF | not assigned to district rows | no |

**Proposed form.** Each pending application and each approval record points to one
`project_uid`. One unit can hold several applications. A later `project_id` change never
moves the UID. The assignment lives in an append-only ledger, so a wrong match can be split
or merged later.

**Recommendation: build gen-2 on a new identity layer.** Do not reuse `project_id` or
`case_id` as the durable unit key.

### O2 — `case_id` is an application key, not a project key

**The question.** Can the Viewer's `links.taipei` set stay as it is under one `project_uid`?

**Measurement.** Four ids print two cases each on the district pages. The live header of
the printed id names only one of the two. For three of the four, the other id is known.
The Viewer holds `11510011`, `11510014` and `11510015` on the 松山 projects. On 2026-11-20
their live headers named the same 松山 cases whose rows the district tables print under
`11509011`, `11509014` and `11509015`. The case header answers under a different id than
the one the district table prints. This board does not say why.

| Printed `case_id` | Row A | Row B | Header of the printed id names | The id of Row B |
|---|---|---|---|---|
| `11509011` | 大同區 大同段一小段393地號等19筆 (品陽建設) | 松山區 敦化段二小段449-12地號28筆(原25筆) (金朋建設) | Row A | `11510011`; header application date 2026/08/31 |
| `11509014` | 大同區 圓環段一小段184地號等30筆 (柏合投資) | 松山區 寶清段二小段353-2地號等21筆 (A基地) (北碁建設) | Row A | `11510014`; header application date 2026/10/08 |
| `11509015` | 中正區 臨沂段一小段357地號等16筆 (璞永建設) | 松山區 寶清段二小段353-2地號等21筆 (B基地) (北碁建設) | Row A | `11510015`; header application date 2026/10/08 |
| `11510016` | 信義區 信義段二小段133地號等12筆 (友座建設) | 大安區 仁愛段五小段480地號等2筆(原1筆) (合作金庫資產管理) | Row B (大安) | not established for the 信義 row |

The headers of `11510014` and `11510015` carry the same case name, with no A基地 or B基地
suffix, so the headers do not tell the two apart. The pairing comes from the Viewer's
`candidate_names`: `11510014` is named `…(A基地及道路用地)` and `11510015` is named
`…(B基地)`. The district rows carry `(A基地)` and `(B基地)`. For `11510015` the names are
exactly equal. For `11510014` they differ by the suffix `及道路用地`. The Viewer holds both
ids on one project, `松山區-寶清段二小段-353-2地號等21筆`.

**Proposed form.** Each application keeps its own `application_id` and `case_id`.
`case_id` links to `r_progress_detail.aspx?case_id=<id>` for status. `project_uid` groups
applications by unit evidence, not by `case_id`. The four conflicts stay flagged. The
evidence above supports the three 11510xxx ids; this board corrects no id by inference.

**Recommendation: treat `case_id` as one application's portal key.** One project can hold
several `case_id` values. Do not group pending applications by `case_id` alone.

### O3 — meeting-label records cannot join projects

**The question.** Do the three `審議會` rows count as pending cases?

**Measurement.** All three sit in 大安區. Their headers repeat the label. They are not case
names, and no land core parses from them.

| `case_id` | 案名 | District status | Header status | Note |
|---|---|---|---|---|
| `11011301` | `516次審議會` | 事業計畫階段─業經幹事會審查 | same | no applicant, location or date |
| `11011021` | `511次審議會` | 事業計畫階段─業申請審議會審議 | same | same |
| `11010261` | `第522次審議會` | 事業計畫階段─業申請審議會審議 | same | same |

**Proposed form.** Keep them out of project counts. Keep them as labelled rows if gen-2
ever lists district rows verbatim.

**Recommendation: exclude meeting-label records from pending-project counts.** They need
separate review before any identity assignment.

### O4 — the Viewer graph assumes `recno`; district pages have none

**The question.** Can `viewer/app.js` render district rows without changes?

**Measurement.** `viewer/index.html` and `viewer/app.js` read `project_id`, `anchor_recno`,
`member_recnos`, `nodes[].recno`, `published_date`, `implementation`, `rewards`, `edges` and
`links.taipei`. The pipeline fills every node's `recno` and every project's `anchor_recno`.
`viewer/app.js:147` checks `(node.links || {}).taipei` for badge membership. Line 935 uses
`p.member_recnos.length`. Line 1359 prints `共 ${p.member_recnos.length} 筆`. District rows
carry none of `recno`, `anchor_recno`, `member_recnos`, a gazette date, an approval stage or
an edge history.

**Proposed form.** Gen-2 can reuse the list layout and the graph drawing code. Its payload
differs:

- `application_id` instead of `recno` per row
- `application_date` instead of the gazette approval date
- a pending-review stage vocabulary instead of the gazette stage
- `links.taipei` still works as a `case_id` set for the detail link
- no `member_recnos`; use `member_applications`, or leave it absent
- no edges until an amendment links to a base application by unit evidence

**Recommendation: gen-2 needs its own payload and its own field handling.** Reuse the UI
components, not the schema. This step comes after O6 and O8.

### O5 — attach amendments to units by land core, through `membership_verdict`

**The question.** Can an amendment join an existing unit under one `project_uid`?

**Measurement (2026-11-20, offline dry run).** The existing `gate` policy of
`membership_verdict` (`urtpe/links.py:1582`) ran over the 497 active-review rows of the
district screen. Each of the 676 projects supplied one `Unit`: the land core from its
project id, the parcels and counts from its nodes. Only units of the same district were
tried.

| Rows | Result |
|---|---|
| 485 new (擬訂) applications | 484 match no unit. 1 matches one unit by the own-parcel rule: `11510012` → `信義區-雅祥段一小段-6地號等21筆`. The counts are equal (21). It is not judged. |
| 9 amendments (變更) | 8 match exactly one unit. 1 matches two: `11511010` matches `內湖區-文德段二小段-232地號等4筆` by land core and `…-231-3地號等4筆` by the own-parcel rule (equal count 4). |
| 3 meeting labels | no land core parses |

By district, section and first parcel, each of the nine amendments names a unit that the
Viewer already holds. Three of the nine (`11509011`, `11509014`, `11509015`) are the 松山
rows of O2. The Viewer holds them under `11510011`, `11510014` and `11510015`. The district
screen counted them as absent for two reasons. The printed id differs. The probe also
compared names against node case names only, and it did not read `candidate_names`.

**Recomputed 2026-11-20** on the saved distinct rows and the current payload, with the
candidate names read. The active-review rows fall from 497 to **493**, and those outside the
168 list from 421 to **417**. The new applications stay at 485. The amendments fall from
nine to **five**. Four are held in the Viewer under another id and drop out: `11508005`
(`10806012`), `11509011` (`11510011`), `11509015` (`11510015`) and `11505026`
(`11510009`). `11509014` stays because its name differs by a suffix. So O5's population is
five amendments that the Viewer lacks and four that it already holds under another id.
The table above ran on the older screen, so its first row and third row are unchanged.
Also, 387 of the 485 new applications sit in a section where the Viewer holds a
unit, on other parcels. Those are separate units, not amendments.

Two limits. The unit's land core came from the project id, not from the cache. The
own-parcel rule is the one whose width Batch F measured (F7, M-series below): it can admit
a neighbour. The ambiguous row `11511010` shows it.

**Proposed form.** Add one named policy to `membership_verdict` for "application to unit".
Add a golden table over the nine amendments and the one new application. Pair an
amendment with its base unit by:

1. the land-core rule of the `gate` policy,
2. the same district and section,
3. a shared implementer where the district row carries one,
4. manual review for every ambiguous match and for the conflicting ids.

Do not use `case_id` equality. A基地 and B基地 stay separate applications inside one unit's
pending history.

**Recommendation: match by land-core evidence, through the one membership function.** Wait
for D11 and M4: if S5 moves onto the gate rule, this policy moves with it.

### O6 — a separate pending dataset is the safe first shape

**The question.** Should pending applications merge into the approved-project graph?

**Measurement.** The approved graph has strict invariants. Every node has `recno`. Every
project has `anchor_recno`. Stages are gazette-approval stages. The tripwire and coverage
guards run over the emitted caches. A row with no `recno` in that graph corrupts it
silently rather than raising.

**Proposed form.** A separate dataset, for example `projects.pending.json` (name to be
decided), keyed by `project_uid`, holding:

- one entry per pending unit,
- one entry per application: `application_id`, `case_id`, status, district, applicant,
  location, application date,
- links to an approved Viewer project only where evidence supports it,
- flags for conflicting ids, missing headers and meeting-label names,
- the observation time, so the age of a status is visible.

The Viewer can render both datasets from one shell page. They remain two payloads with two
contracts. Acquisition stays separate from ingestion (`gazette-cadence`): the poller of
district pages must not write the emitted dataset.

**Recommendation: keep a separate pending dataset.** Merge only after the identity ledger
and the membership rule have run on known approvals. Refresh it at the pace of A6.

### O7 — gen-2 proof population: the nine matched units

**The question.** Which units prove the UID design without guessing?

**Measurement (2026-11-20).** The nine amendments of O5 name nine applications on eight
units, plus one conflicting id on a ninth unit. Each unit exists in the Viewer.

| Viewer project | Application | Note |
|---|---|---|
| `北投區-大業段三小段-184-1地號等10筆` | amendment `11509024` | application date 2026/09/22 |
| `南港區-玉成段二小段-253-1地號等16筆` | amendment `10405044` | header status moved on to 業經幹事會審查 |
| `內湖區-文德段二小段-232地號等4筆` | amendment `11511010` | **ambiguous** under the own-parcel rule (O5) |
| `內湖區-東湖段一小段-14-2地號等1筆` | amendment `11508005` | no applicant on the district table |
| `大同區-雙連段三小段-98地號等25筆` | amendment `11511007` | `等25筆(原23筆)` |
| `松山區-寶清段二小段-353-2地號等21筆` | amendments `11509014` (A) and `11509015` (B) | held as `11510014` and `11510015`; one unit, two applications |
| `松山區-敦化段二小段-449-12地號等28筆` | amendment `11509011` | held as `11510011` |
| `大安區-仁愛段一小段-92地號等11筆` | amendment `11505026` | no header row on the live check |
| `大安區-仁愛段五小段-480地號等2筆` | conflict row `11510016` | the 大安 row; the 信義 row has no Viewer unit |

These units cover the amendment shapes and the one conflict whose second id is not
established. The other three conflict rows (大同 393, 大同 圓環184, 中正 臨沂357) and the
信義 row have no Viewer unit. They are new applications.

**Recommendation: prove gen-2 on these nine units first.** Add units only by user decision
after each match is checked.

### O8 — what the gen-2 Viewer shows

**The question.** What does a reader see once one unit holds both pending applications and
approvals?

**Measured 2026-11-20.** The district table gives each application one of many statuses. The
mix over the 3,655 rows is far wider than "pending":

| Status in the district table | Rows |
|---|---:|
| 業經本府核定 / 業經本府核准 | 726 / 236 |
| 事業概要業已失效 | 498 |
| 實施者自行撤回 / 申請人自行撤回 | 364 / 75 |
| 執行階段 (completed, finished, under construction) | 295 / 259 / 194 |
| 業經本府駁回 | 236 |
| 業已提出申請審查 | 178 |
| 無 | 120 |
| 業已辦理公開展覽 | 102 |
| 業經幹事會審查 | 85 |
| 業申請幹事會審查 | 45 |

The 168 list holds 468 of the 3,651 district ids (12.8%). So an application can end
approved, withdrawn, rejected or expired. A gen-2 page must show all of these. It must not
call every district row "pending".

**Proposed form (not measured).** One timeline per unit. Each application is one entry.
Each approval is one entry. An entry carries its source: the district table, the live
header, or the gazette. The reader sees:

- a filter for pending only, approved only, or both;
- a filter for the review stage (the eleven phrases of the screen) and for the closed
  outcomes;
- the district, applicant and location;
- a link to `r_progress_detail.aspx?case_id=<id>`;
- a flag on a conflicting id, a missing header or a status that the district table and the
  header disagree on (82 of 495 active rows on 2026-11-19).

A district status and a gazette approval stay on separate lines. A pending application must
never read as an approval. The district table and the header are two observations. Store
both with their times, and do not pick one as the single current status.

**Limits.** An application can end withdrawn or rejected and never reach a gazette.
Several applications can run in one unit at the same time (O5: A基地 and B基地). A wrong
`project_uid` needs a split entry in the ledger, so the ledger must support split and merge.

**Recommendation: design the page from the status mix, then build a read-only page on the
pending dataset.** Do this after O6 and O7.

### O9 — fit the pending lane into the ETL and the update cycle

**The question.** If the district tables join gen-2, what changes in the full ETL and in the
Part I cycle?

**Proposed form.** Gen-2 adds a second lane. It does not change the first.

```text
Lane A (approved, unchanged)  poll_gazette → archive → ingest → refresh → rebuild → payload
Lane B (pending, new)         district crawl → snapshot → parse + dedup → header check
Join   (new, after rebuild)   identity ledger + membership policy → pending dataset
Publish                       post_ingest_check → one commit → push → check_deploy
```

Lane B follows the existing rule that acquisition never ingests. The crawl saves a
snapshot, as the 168 poller does. A separate step builds the pending dataset. The approved
graph, `projects.json` and the four PDF-derived layers do not change.

**Effect on Part I.**

| Item | Effect |
|---|---|
| U1 | The cycle gains a second acquisition step (the district snapshot) and a join step after the rebuild. A new gazette hash or a new district hash can start a cycle. |
| U2 | Three new layers: the district snapshot (owner: the crawler), the pending dataset (owner: the join step) and the identity ledger (owner: a person appends). |
| U3 | The processed-state record names both hashes and the payload revision the join step read. The crawl needs a completeness gate: all 12 districts fetched, no rejected rows, and a row-count check against the last snapshot. On failure it writes nothing. |
| U4 | A Lane B failure stops Lane B. Lane A may still publish. The old pending file stays and is marked stale (O-D4). |
| U5 | The pending dataset joins the commit's owned paths. The commit records which payload revision the join step read. |
| U6 | New proofs: an unchanged district hash causes no rebuild; Lane B writes nothing under `data/`; the pending file names its payload revision. |
| U7 | The district hash is a better trigger for a city-only cycle than the 168 hash, which covers 12.8% of district ids. Option B then means a district-hash cycle that runs Lane B and the join only, with no PDF layers. |
| U8 | No change. An ambiguous match goes to a person through the ledger. |

**The identity ledger follows the correction ledger.** `correction-ledger` entries are
append-only, keyed on land core and approval date, never on 編號, and a mistake is
corrected by a superseding entry. The 14 entries on file carry `match_land_core`,
`match_iso_date`, `field`, `to`, `why`, `by`, `at`, `supersedes` and the two merge
flags. An identity entry needs different fields (a `project_uid`, the evidence and a
split or merge action). Decide that in O-D1.

**The full ETL from scratch** gains Lane B: crawl, parse, dedup, screen, header check,
match, ledger, emit. `docs/pipeline/etl_process.md` §11 needs a matching section. It stays
untouched until a change opens.

**Measured 2026-11-20:** a re-run of the crawl gave the same counts as 2026-11-19: 3,655
rows, 3,651 ids, 497 active-review rows. I compared counts only, not row content.
**Not measured:** how often the district tables change, and how long a full header pass
takes. O-D6 waits for the first.

**Recommendation: build the pending lane as its own lane, with its own tree and lock.**
Open it as one OpenSpec change after O6, because it extends `gazette-cadence`.

### O10 — a reconciliation page: from the release-diff count to the Viewer count

**The question.** The release-diff report and the Viewer give two counts for the same
gazette. Which steps lie between them, and how does a reader see each step?

**Measured 2026-11-21** (payload at `6b97a83`, report of 2026-11-20 02:06 +08:00):

| Step | Projects | Records | Owner |
|---|---:|---:|---|
| `docs/release-diff.html` reads the 2026-11-12 PDF | 674 | 1,444 | `scripts/release_diff_report.py` |
| The reader refuses 4 truncated rows (編號 194, 1011, 1137, 1212) | — | — | already inside the report as "excluded" |
| Ingest completes those 4 rows from the city API (`recovery` nodes) | +2 | +4 | `--recover-truncated` |
| The Viewer payload | 676 | 1,448 | `data/projects.json` |

The four recovery nodes carry the same four 編號 that the report excludes. Two of them
make a project that has no other record (`中正區-永昌段四小段-46-4地號等117筆`,
`南港區-南港段一小段-720地號等105筆`). The other two join a family that the PDF already
holds (萬華 雙園段二小段-505, 文山 萬隆段二小段-623). So +4 records and +2 projects.

The 14 ledger entries do not move either count. The report applies the same ledger to every
release, so both sides hold it.

**A defect in the report, found while reading the step above.** The gap note on
`docs/release-diff.html` says "652 個家族是復原列自行成立的". The right number is 2. The
code (`scripts/release_diff_report.py:656-668`) builds the PDF-side key from the 案名's land
core (`content_key()`) and the payload-side key from the normalized 地號 cell. The two keys
have different shapes, so 652 of 676 projects find no match. The note then lists them as
"created by recovery". The page names 652 families under a total that moves by 2. I read the
code and the printed note. I did not re-run `_render_payload_note` with a corrected key.

**Proposed form.** A page in the gen-2 Viewer, "數字從哪裡來", that walks the chain above for
the current payload. Each row names its step, its owner, the count in, the delta, the count
out, and the rows that make the delta (編號, land core, approval date). It reads the
payload and the archive. It holds no copy of the numbers.

It extends to the pending lane (O9) with a second chain: district rows (3,655) → distinct
`case_id` (3,651) → active-review rows → rows outside the 168 list → pending units. The
page shows each step with the same layout.

**How the page mitigates the gap.**

1. **Name the delta.** A reader who sees 674 and 676 finds the two projects and the four
   rows that explain them.
2. **Refuse a chain that does not sum.** `post_ingest_check.py` (or the page build) checks
   that read count + recovered rows = the Viewer's record count, and read count +
   recovery-only projects = its project count. A mismatch stops the page. It does not print
   an estimate.
3. **Fix the report first.** Use one key shape on both sides of the comparison. Add a test
   that the "created by recovery" count equals the project delta.
4. **Show what the report cannot see.** The report reads PDFs only. The page says so and
   points at the stages after the PDF: recovery, targeted refresh, ledger.

**Form.** Step 3 is **fix only** and independent of gen-2: it can land now. Steps 1, 2 and
the pending chain are a design, then a read-only page, after O6 and O8.

**Not measured:** whether the chain still sums for the older releases. The report re-reads
them under today's reader, so recovery rows there are not tied to a payload.

**Recommendation: fix the 652 note first. Then add the chain as the first page of gen-2.**

### O11 — marks on patched values, with the original value on hover

**The question.** The Viewer shows a value that a patch changed. How does a reader tell, and
see what the city printed?

**Measured 2026-11-21 on the 1,448 nodes of the payload at `6b97a83`:**

| Patch | Where it is today | Count | Original value in the payload? |
|---|---|---:|---|
| API completion of a truncated row (`recovery`) | node field `recovery` | 4 nodes | no. The node holds the completed 地號 cell. The printed fragment is not kept. |
| Cleanse fix (`auto_fixes`) | node field `auto_fixes` | 13 nodes | partly. `name_raw` keeps the printed 案名. It differs from `case_name` on 37 nodes, more than the 13 fixes. |
| Manual correction (`corrections.jsonl`) | outside the repository | 14 entries | no. An entry holds `to` and `why`, not the old value. |
| Review flag (`review_flags`) | node field | 322 nodes | not a patch. A flag names a doubt and changes no value. |

So a hover with the original value needs data that the payload does not carry. `auto_fixes`
holds a reason only, as text (for example "案名補事業(都市更新計畫案簡寫)", 10 nodes). The
ledger records the new value and its reason, not the value that the PDF printed.

**Proposed form.**

- One mark per patched value, in three kinds that look different: 復原 (API), 自動修正
  (cleanse) and 人工修正 (ledger). A fourth mark, 待查, is for a review flag. A flag must not
  look like a patch.
- On hover or focus: the original value, the new value, the reason, the source and the date.
- A touch screen has no hover. The mark must also open on tap, and a `title` attribute alone
  is not enough.
- The mark goes on the field it changed (案名, 地號, stage, date), not on the whole node.

**Where the original value lives (O-D7).** A sidecar file, keyed by land core and approval
date (never 編號), built at emission from the three sources. It does not rewrite
`projects.json`. A node field is the alternative. It changes the gen-1 payload shape, so it
needs an OpenSpec change under `history-graph`.

**Limits.** The ledger has no "old value" field, so an entry written before this change has
no original on record. The emitter can read the PDF value at apply time for new entries. For
the 14 old entries, a person must supply it, or the hover says "not recorded". It must not
infer it. A patch that the cross-release completion makes in the release-diff report is not
a payload patch. Whether the payload carries the same completion was not measured.

**Form.** An OpenSpec change for the sidecar and for the ledger's new field. The mark and
the hover are a UI step after O6 and O8.

**Recommendation: record the original value at apply time, in a sidecar keyed by land core
and date. Then draw the marks from it.**

---

## Appendix — method

- **Viewer payload:** read `data/projects.json`; counted projects, nodes, `recno`,
  `anchor_recno`, `member_recnos`, `implementation`, `rewards`, `edges`, `links`. Named
  case ids: 2,022 before commit `6b97a83`, 2,028 after.
- **District rows and the Venn counts:** reproduce with the three scripts in
  `docs/portals/urotpe_district_pages.md` §7. They write under `data_test/district_probe/`.
- **Amendments and meeting labels:** `special-records.json` was written by hand from the
  header evidence. No script makes it.
- **Header evidence:** `district_header_summary.json` (594 candidates, 495 successful active
  rows, 4 failures). On 2026-11-20 three more read-only requests read `11510011`,
  `11510014` and `11510015`.
- **Membership dry run (O5):** ad hoc, not kept. One `Unit` per project from
  `expected_land_core_of_project_id`, the anchor node's parcels and the counts of all nodes;
  `membership_verdict(name, unit, "gate")` over the active rows, same district only.
- **Viewer graph fields:** `viewer/app.js` lines 147, 935 and 1359 and `viewer/index.html`.
- **O8 status mix:** counted `status` over the 3,655 distinct district rows on 2026-11-20
  (the rows of 2026-11-19; the re-run gave identical counts). The 12.8% is 468 of 3,651
  ids. The existing ledger was read from `urtpe-gazettes/corrections.jsonl` (14 entries).
- **O10 and O11 (2026-11-21):** read `docs/release-diff.html` (text), `scripts/release_diff_report.py:616-708`
  and `scripts/release_diff.py:69`. Counted `recovery`, `auto_fixes`, `review_flags` and
  `name_raw != case_name` over the 1,448 nodes of `viewer/projects.data.js`; counted projects
  made only of `recovery` nodes; read the 14 entries of `corrections.jsonl`. Ad hoc, not kept.
  No request, no ingest.
- **Part I:** read the scripts and specs it names. It cites `scripts/refresh_awaiting_caches.py:39`,
  `urtpe/links.py:618` and `:2354`, `openspec/specs/gazette-cadence/spec.md` and
  `docs/pipeline/etl_process.md` §11. The 2026-11-19 refresh figures (101 and 94 projects,
  8 dates, 14 statuses, 6 cases) come from the session that ran it. Their run output is not
  kept, and this board did not re-measure them. The 101 selections, the 94 later candidates
  and the 96 still-awaiting cases are different populations and are not interchangeable.
  The scheduled-task description comes from the runbook. This board did not inspect or
  change the Windows task.
- **Part I automation options:** work was classified against the existing acquisition-only
  specification, the single-writer contract, the bounded repairs, path-limited publication
  and the byte-for-byte deploy check. No automatic commit, push, scheduling or agent
  invocation was performed.
- **Part II:** the method of M1–M4 is the Batch F appendix
  (`docs/inspections/inspection-batchF.md`, "Appendix — method"). The scripts were ad hoc.

No pipeline run, ingest or deployment happened for this board. No file under `urtpe/` or
`viewer/` changed.

## Corrections made when this board was reorganized (2026-11-20)

| Earlier text | Correction |
|---|---|
| O1: the three Viewer-only ids sit "in the 松山 conflict cluster" | They are the 松山 cases' own ids, read live. See O2. |
| Order table: step labels did not match the section ids (O4 for the pending payload, O6 for the proof population, O7 for UI reuse) | The table names each item by its own section id. |
| O4: `viewer/app.js` line 146 | Line 147. |
| O5: nine amendments are "outside the Viewer" | Each of the nine names a unit the Viewer holds. Recomputed with `candidate_names`: five amendments are absent from the Viewer; four are held under another id (`10806012`, `11510011`, `11510015`, `11510009`). The 497 active rows become 493. |
| O7: seven units, "cover the four conflicts" | Nine units. They cover the amendments and one conflict. |
| Source line: 1,444 records, 675 projects, 2026-10-28 | 1,448 records, 676 projects, 2026-11-12. |
| Probe outputs "live in the session scratchpad" | Three scripts reproduce them. |
| Items O8 and O9 | New on 2026-11-20. Proposals from the design discussion. The status mix, the 12.8% and the ledger shape were measured; the page design and the lane layout were not. |
| Items O10 and O11 | New on 2026-11-21, at the user's request. The two chains and the patch counts were measured; the page design, the sidecar and the hover were not. The report's "652" note is a defect found while measuring O10. |
| Part I: `docs/etl_process.md`, `urtpe/links.py:617`, `SingleWriterLock("data")` | `docs/pipeline/etl_process.md`; `urtpe/links.py:618`; a lock over the `data` output tree, as `scripts/refresh_second_id_source.py:96` takes it. |

## Provenance

Parts I and II were written by another session (transcript `1db9b1d5…`, 2026-11-20) and kept
uncommitted in this file. A `git checkout` run in this session discarded them. They were
rebuilt from the diff that this session had printed before the revert.

**Checked 2026-11-20.** The rebuilt text was compared line by line with the text of that
session's own `Edit` calls on the file, read from its transcript. Part I differs in 0
lines. Part II differs in 1 line, which is a trailing `## Order` heading that belongs to the
next section. The edits this session made on purpose are the new part titles, the `docs/`
path updates, `urtpe/links.py:617` corrected to `:618`, the labels `M1–M4`, the move of the
five automation decisions into one table, and the corrections table above.

That session also edited the top of the file and the appendix (edits 4113 to 4118). Those
edits are carried in the reorganized header, the Rules for this board and the appendix. The
appendix lines about the different refresh populations and the Windows task were first
dropped in the rewrite and are restored.
