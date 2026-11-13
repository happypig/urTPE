# AGENTS.md — urTPE

Turns the Taipei City urban-renewal approved-cases gazette (核定案件一覽表) into a
merged, per-project history graph plus a static viewer. Python, pymupdf, no web server.

## Commands (verified on this machine)

```powershell
python -m pytest                      # 1330 tests, ~3min, fully offline
python -m pytest tests/test_merge.py  # one file
python -m pytest tests/test_merge.py::test_name -q
python -m urtpe.cli source.pdf -o data --links
python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links
```

- Use the **system** interpreter (`C:\Python314\python.exe`, pytest 9.0.1, pymupdf 1.28.2).
  `.venv/` exists but contains only pip — activating it leaves you unable to run tests.
- The count in that first line goes stale whenever tests change. Refresh it with
  `python -m pytest --collect-only -q | Select-Object -Last 1`. It reports **1330 collected**
  while a full run reports **1329 passed, 1 skipped** — the skip is deliberate, at
  `tests/test_idempotent_flags.py:117`, because the node payload builder is not exposed and
  the graph test below it covers the behaviour. With no CI, an unnamed skip reads as a
  silently disabled guard.
- **No `pyproject.toml`, no `requirements.txt`, no CI, no lint/typecheck config, no
  pre-commit.** There is nothing to install from or to satisfy; deps are ambient. Don't
  invent a build step or a `make test`.

## Entry point and exit codes

`urtpe/cli.py:main` is the only entrypoint. Exit codes are a contract:

| Code | Meaning | State on disk |
| --- | --- | --- |
| 0 | success | written |
| 2 | reconcile-block: unexplained changes found, `--allow-reconcile-block` not given | archive/index written, **emission not written** |
| 3 | `TableStructureError` — reader refused the document | **nothing written** |
| 4 | `TripwireFailure` (incl. the census gate) — not provably complete | **nothing written** |
| 5 | `LockHeld` — another run owns this output tree | **nothing written** |
| 1 | anything else: "no records parsed", an unhandled exception | **not a contract** — diagnose before retrying |

A non-zero exit is a refusal, not a flake. Don't retry past it, don't pass a flag to get
around it. `--allow-reconcile-block` is marked 危險 and `--no-archive` 不建議 in the
help text for a reason.

## Traps

- **Single-writer lock.** `urtpe/lock.py` writes `.pipeline.lock` into the output dir and
  serialises writers, after the 2026-08-24 incident where four concurrent runs each
  treated a half-populated cache as authoritative and 47 project caches were wiped. One
  run per output tree. Stale after 6h or a dead PID. Before deleting a lock, check the
  PID is actually gone.
- **`data/` is only half-ignored, and the tracked half is huge.** `.gitignore` has
  `data/*`, but `projects.json` (11.7 MB), `raw.tsv`, `clean.tsv`, `merged.tsv` and
  `review_report.txt` are already tracked, so the rule does not apply to them — gitignore
  never affects tracked paths. Any pipeline run rewrites all of them **plus**
  `viewer/projects.data.js` (8.5 MB): expect a ~23 MB diff from a run you only meant to
  use for checking. Stage deliberately.
- **`viewer/projects.data.js` is both input and output.** `--from-js` loads it and the
  CLI rewrites it, so a bad emission round-trips and propagates. Treat it as state, not
  scratch.
- **Live state lives outside the repo** at `D:\project\urtpe-gazettes\` (gazette archive +
  `index.jsonl` + `corrections.jsonl` + `poll_state.json` + `poll_log.jsonl` +
  `change_sets/`), shared by every process that imports `urtpe`.
  Override with `URTPE_ARCHIVE_ROOT` / `URTPE_LEDGER` (or `--archive-root` / `--ledger`).
  `tests/conftest.py` repoints both into a session temp dir precisely because fixture PDFs
  carry a real gazette's 統計至 date and would otherwise overwrite real archive members.
  `change_sets/` is keyed by *publication*, not by run: a re-ingestion overwrites one
  publication's conclusion instead of accumulating competing records.
- **`data/.link_cache/` is the durable middle layer**, not a cache you may clear: per-project
  `result.json`, `view.html`, `portal_index.json` (only the ~110 newest entries — the crawl
  is WAF-capped, so older identities are reachable *only* via this dir), and
  `no_match_ledger.json` (14-day TTL). The CLI and the sweep scripts both write into it;
  whoever runs second must respect the single-writer rule. Five `data/.link_cache_backup_*`
  directories (plus one `.link_cache_wip_*`) exist as a result of past incidents — do not
  delete them casually.
- **The manual-correction ledger applies on every PDF ingest.** `--ledger`
  (default `urtpe-gazettes/corrections.jsonl`, `URTPE_LEDGER` override,
  `urtpe/ledger.py`, the `correction-ledger` spec) holds its first entries
  since 2026-11-05 (`confirm_merge` + `land_count` for 吉林676, D5). An
  ingest without the flag still applies it; an explicit empty string opts
  out. `--from-js` keeps families as emitted and never re-merges.
- **`data/project_aliases.json` is tracked configuration, not derived data.** It migrates
  `.link_cache` directories across `project_id` churn and refuses ambiguous pairs;
  regenerate with `scripts/build_project_aliases.py`.

## Domain invariants

Violating any of these corrupts output silently rather than raising.

- **編號 is a coordinate, not an identity.** The list is newest-first, the city prepends
  new approvals and edits/ re-dates historical rows, so the shift is not even affine.
  Never key anything durable on it.
- **`project_id` is not stable either** — it is the slug of the latest approval's land
  core and churns (~11% of multi-record families have moved). Within one gazette use
  `recno`; across both portals use the land core
  `{district}{section}{first_parcel}地號等{count}筆`.
- **A 地號 cell fails in two unrelated ways; the distinction decides the response.**
  (a) The city sometimes prints the page number *inside* the last row's 地號 cell — that
  is the reader's fault, stripped only when the digits equal that page. (b) The city
  truncates long cells at the printed row height and never draws the remainder — that is
  the publisher's fault, the text is absent from the PDF. Do not "fix" (b). A cell is
  publisher-truncated iff its text ends in a tail pattern (`、，,` / digit / sub-parcel
  hyphen, the measured `…578、579-` of 編號 1005) **or** it lost its closing phrase while
  showing fewer parcels than its own 案名 declares; a cell whose closing phrase is present
  is never count-checked (48 rows per Gregorian gazette disagree with their 案名 and are
  complete as published). The counter does not strip spaces before tokenising —
  `163 164` is two parcels, `573 -6` one — and closing-phrase variants
  (`地號等22土地`, `地號等2筆(原17筆)土地`, chained `…土地)等 4 筆土地`) are stripped
  chunk-wise so their digits never count as parcels (check-declared-parcel-counts,
  2026-10-26; census in `openspec/changes/check-declared-parcel-counts/poc_findings.md`).
- **Never repair absent data by inference.** Truncated records are excluded and named,
  and the exclusion count is reported, so a short gazette never reads as a faithful copy.
- **Calendars:** ROC (115/8/27) through the 2026-08-27 gazette; Gregorian from the
  2026-09-24 gazette onward. (The boundary was once mislabelled 1151002 because the
  09-24 document was quarantined on release and missing from the archive; it was
  restored by `restore-2026-09-24-gazette` on 2026-10-31.) Both accepted per cell,
  normalised to ISO. `published_date` comes from the document's 統計至 line.
- **~70% of records are repeat stage approvals of the same unit.** Identity is found by
  similarity (`LINK_THRESHOLD = 0.7`, flag band 0.5–0.7), never by equality — parcel
  coverage changes (`13筆(原11筆)`) and renumbering (`689地號(原726地號)`) break exact keys.
- **Manual corrections go in the append-only ledger**, keyed on land core + approval date
  (never 編號), applied after cleansing and before merge. Dated one-off scripts that patch
  emitted output are obsolete by construction.
- **Gazette detection is by content hash, never by timestamp.** The city re-uploads a
  byte-identical PDF and only advances its mtime (measured 2026-10-05: page advertised
  資料更新 115-09-29 while the newest gazette held is 2026-09-24). A `Last-Modified` poller
  would report a new gazette every week for one already held. Hash, reusing the archive's
  existing SHA-256 rather than adding a second digest.
- **Acquisition is separate from ingestion.** `urtpe/poller.py` never ingests and never
  touches the emitted dataset; the single-writer lock serialises writers without deciding
  which writer is correct. Don't wire polling into ingestion.
- **The publisher serves one PDF link at a time and repoints it on every publication**, so
  the live link names "whatever is newest", not any particular gazette. A *version-specific*
  URL (`…/relfile/18558/10496/<uuid>.pdf`) names one document and stays a durable address
  for it — measured 2026-11-06: the URL that served the 2026-10-15 gazette still serves the
  2026-10-15 document, a different digest from the current one, while a fabricated path
  answers 404. The archive index therefore records `publisher_url` per entry, and a URL is
  accepted only when the document it serves hashes to a digest the archive already holds.
  A release with no recorded URL says so; it never borrows the live link, which serves a
  different gazette.

## Gates — understand before bypassing

- `urtpe/tripwire.py` — completeness gate (編號 contiguity, unparsed dates, pages that
  yielded no table). Deliberately evaluates **before** any artifact is written, because a
  check that runs after the damage is not a check.
- `urtpe/coverage.py` — coverage regression guard over the per-project caches. Raises on a
  flag dropping *and* on a total re-key: when every `project_id` changes, the before/after
  intersection is empty, so a naive diff reports success while all 709 caches are orphaned.
  That is the 2026-08-24 shape.
- If you believe a gate is wrong, fix its blind spot explicitly and add the test — don't
  reach for a bypass flag.

## Layout

- `urtpe/` — the pipeline. `links.py` (64 KB, both portal adapters) is the largest and
  most failure-prone surface; `extract.py` owns the ruled-table reader; `cli.py` wires it.
  `poller.py` / `changeset.py` / `ordering.py` handle gazette cadence and are deliberately
  decoupled from the emitted dataset. Keep pure cleansing/merge/scoring logic separate
  from I/O adapters.
- `viewer/` — a static `file://` site. No dev server. The render path is
  exercised by `node scriptsiewer_smoke.js` (a Node DOM-stub harness;
  runs by hand — it reaches no network and is not a pytest case, so
  nothing *automatically* checks it). It is also published to GitHub Pages at
  **`https://happypig.github.io/urTPE`** — the canonical address is recorded once in
  `viewer/deploy.json`, and that path is **case-sensitive**: `/urtPE/` is a different site
  that serves GitHub's "Page not found" document, which a browser will keep rendering over
  from cache, so a stale page reads as a working one. This cost a real investigation on
  2026-10-06. `tests/test_deploy_target.py` checks the capitalisation offline, by reading
  `deploy.json` and `git remote get-url origin` and comparing them;
  `python scripts\check_deploy.py` fetches each artifact and compares it byte-for-byte
  against the `HEAD` blob, reporting **fresh / stale / missing** separately. It reaches the
  network, so it is a command and not a pytest case.
- `docs/release-diff.html` — why the project count differs between PDF releases. Generated
  by `scripts/release_diff_report.py` (pure logic in `scripts/release_diff.py`), published
  from `main`, and reached from the viewer through the 關於 page (`viewer/about.html`),
  which links the report and the coverage report (`docs/coverage-report.html`); the
  report links back to the about page. All links are relative, so the chain works from
  `file://` too. The report
  re-reads every archived PDF under the *current* reader, so its numbers describe what the
  gazettes yield today, not what each yielded when it was published. Its family identity is
  the **案名's land core**, not the 地號 cell: the cell differs by one character between
  some releases, and keying on it counted three units as both dead and born.
- `scripts/publish_release_diff.py` — the third action of the `urtpe-poll` task, after the two
  pollers. It regenerates the report, commits it, and pushes to `main`, which is the branch
  Pages publishes from. It never ingests and writes nothing under `data/` or `viewer/`.
  Two hazards are closed, both measured 2026-11-09:
  - **The commit is path-limited, not merely path-scoped in the `git add`.** A `git commit`
    without a path limit takes the whole index, and the index holds whatever another
    session has staged. The step names its owned paths on the commit command, so another
    session's file is neither committed nor discarded, and stays staged for them.
  - **The push is verified against the remote.** `git push origin main` pushes the `main`
    ref; on a detached HEAD the commit the step made lives on `HEAD`, git answers
    "Everything up-to-date" and exits 0, and the remote never moves. The step asks the
    remote afterwards whether it holds the commit, and reports a failure when it does not.
  A failed push is reported, and the committed report is then ahead of the served one —
  which `check_deploy.py` reports as stale.
- `scripts/` — 172 files, of which 115 are `probe_*.py`. Undated ones (`poll_gazette.py`,
  `fetch_remaining_national_portal.py`, `build_project_aliases.py`, `stranded_report.py`)
  are durable tools; dated ones (`*_2026MMDD`) and `probe_*.py` are one-shot archaeology.
- `data/`, `data_test/` — generated output; gitignored except the six tracked files above.
- `openspec/` — 26 specs, spec-driven workflow. **`openspec/config.yaml` holds the
  authoritative project context** (calendars, identity rules, the 編號 warning) plus
  per-artifact rules and the test-first gate. Read it before proposing a change.
  `openspec/changes/` holds `archive/` plus the in-flight changes. Run `openspec list`
  before proposing one — another session may already have opened it.
  `docs-pages` (2026-11-12) is the newest spec.

## Docs — which one answers your question

- `docs/facts_2_portals.md` — portal reference: endpoints, field maps, open issues, priorities.
- `docs/portal_operations_log.md` — append-only dated record; **new sessions append at the
  bottom**, and it is what keeps citations like "§6.7" or "§18 rule 1" resolving.
- `docs/cli_flow_v2.md` — current CLI/link-discovery flow. It grew by accretion and its
  line numbers are cited from outside (`openspec/changes/archive/2026-10-05-no-silent-data-loss/proposal.md`
  pins line 83, and `scripts/baseline_silent_failures.py` asserts that row still reads
  "recommended"). **Append; do not insert above it.**
- `docs/domain_model.md` — entity/mermaid model, in two blocks: the record→graph path, and
  the gazette cadence layer (archive, ledger, poller, change sets).
  `docs/domain-model.html` — its self-contained bilingual rendering (no CDN, opens from
  `file://`). `docs/cli_flow.archive.md` — dead, archived.
- `docs/gazette-churn.md`, `docs/stranded-cache-dirs.md` — generated; do not hand-edit.
- `docs/dataset_completeness_audit.md` — the 2026-10-26 post-`recover-truncated-rows-via-api`
  audit: per-gazette record→project binding, the 718→709→694 viewer-count history, and
  record churn between consecutive publications (only 1151002 churns). Generated scripts
  were ad-hoc; the method is reproduced in its Appendix A.
- `docs/sync_architecture.md` — the PDF-heartbeat + two-portals sync design; was the design
  `gazette-ingest-cadence` was cut from.
- `docs/viewer-UX.md` — viewer improvement backlog, one numbered entry (`viewer-UX §N`)
  per proposal with problem, design, trade-offs and spec impact. Append; do not renumber.
  An entry is a candidate — open an openspec change before implementing it.
- `docs/temp.*` — ignored paste pad, deliberately untracked.

## Conventions

- Commit prefixes in use: `feat:`, `fix:`, `docs:`, `chore:`, `openspec:` (archiving a
  change is `openspec: archive <name> and sync its four spec deltas`).
- **A MODIFIED requirement must carry every scenario of the requirement it replaces**,
  and the archive **aborts** if one is missing: it exits 1, names the missing scenario
  by name, and changes no file. But the guard is narrower than it looks. Verified in
  the installed openspec (`dist/core/specs-apply.js:285` → `findMissingCurrentScenarios`,
  2026-11-09): it compares scenario **names only**, is multiplicity-aware, and **masks
  fenced code-block lines** before counting — a fence opens on 3+ backticks **or 3+
  tildes**, closing on the same character at the same length or longer
  (`dist/core/parsers/code-fence.js`). So the **prose is unprotected**, and so is a
  fenced `#### Scenario:` and any other `####` heading — a delta that drops those archives
  cleanly and the archive reports nothing. The delta must carry the live body too,
  verbatim or extended. The archive rewrites the shared `openspec/specs/` tree, so copy
  `openspec/` to a temp dir and run it there first: it reports what it applied
  (`+ 4, ~ 2, - 0`), and the synced specs can be compared against that copy before the
  real run. `scripts/probe_spec_unprotected.py <commit> <spec-path>` finds the content
  the guard does not protect. `node scripts/probe_fence_mask_diff.js` diffs the Python
  probes' fence mask against the installed `buildCodeFenceMask` itself — run it after
  touching either probe, rather than re-deriving the rule from the JS.
- Test-first is enforced by openspec: every test-writing task must be checked before any
  implementation task, or the change declares `> POC: <reason>` as the first non-heading
  line of `tasks.md`.
- Comments and docstrings here explain *why* and cite the incident or the spec section
  that forced the choice. Match that; generic comments are noise in this codebase.

## Verification

```powershell
python scripts\baseline_silent_failures.py   # standing silent-failure findings
```

Item 5 of that script asserts `docs/cli_flow_v2.md` still describes `--links` as
"recommended" — `--links` is advisory **by design** (D5); the coverage guard is what
covers the default path. Changing that wording is a behaviour change, not a docs fix.