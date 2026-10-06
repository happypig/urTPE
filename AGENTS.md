# AGENTS.md — urTPE

Turns the Taipei City urban-renewal approved-cases gazette (核定案件一覽表) into a
merged, per-project history graph plus a static viewer. Python, pymupdf, no web server.

## Commands (verified on this machine)

```powershell
python -m pytest                      # 597 tests (1 skipped), ~75s, fully offline
python -m pytest tests/test_merge.py  # one file
python -m pytest tests/test_merge.py::test_name -q
python -m urtpe.cli source.pdf -o data --links
python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links
```

- Use the **system** interpreter (`C:\Python314\python.exe`, pytest 9.0.1, pymupdf 1.28.2).
  `.venv/` exists but contains only pip — activating it leaves you unable to run tests.
- **No `pyproject.toml`, no `requirements.txt`, no CI, no lint/typecheck config, no
  pre-commit.** There is nothing to install from or to satisfy; deps are ambient. Don't
  invent a build step or a `make test`.

## Entry point and exit codes

`urtpe/cli.py:main` is the only entrypoint. Exit codes are a contract:

| Code | Meaning | State on disk |
| --- | --- | --- |
| 0 | success | written |
| 3 | `TableStructureError` — reader refused the document | **nothing written** |
| 4 | `TripwireFailure` — not provably complete | **nothing written** |
| 5 | `LockHeld` — another run owns this output tree | **nothing written** |

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
  the publisher's fault, the text is absent from the PDF. Do not "fix" (b).
- **Never repair absent data by inference.** Truncated records are excluded and named,
  and the exclusion count is reported, so a short gazette never reads as a faithful copy.
- **Calendars:** ROC (115/8/27) until the 1151002 gazette, Gregorian after. Both accepted
  per cell, normalised to ISO. `published_date` comes from the document's 統計至 line.
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
- `viewer/` — a static `file://` site. No dev server, and **no browser test exists**, so
  nothing automatically checks the page renders.
- `scripts/` — 45 files. Undated ones (`poll_gazette.py`, `fetch_remaining_national_portal.py`,
  `build_project_aliases.py`, `stranded_report.py`) are durable tools; dated ones
  (`*_2026MMDD`) and `probe_*.py` are one-shot archaeology.
- `data/`, `data_test/` — generated output; gitignored except the six tracked files above.
- `openspec/` — 21 specs, spec-driven workflow. **`openspec/config.yaml` holds the
  authoritative project context** (calendars, identity rules, the 編號 warning) plus
  per-artifact rules and the test-first gate. Read it before proposing a change.
  `openspec/changes/` holds only `archive/` right now — no change is in flight.
  `gazette-cadence` is the newest spec (2026-10-06).

## Docs — which one answers your question

- `docs/facts_2_portals.md` — portal reference: endpoints, field maps, open issues, priorities.
- `docs/portal_operations_log.md` — append-only dated record; **new sessions append at the
  bottom**, and it is what keeps citations like "§6.7" or "§18 rule 1" resolving.
- `docs/cli_flow_v2.md` — current CLI/link-discovery flow. It grew by accretion and its
  line numbers are cited from outside (`openspec/changes/archive/2026-10-05-no-silent-data-loss/proposal.md`
  pins line 83, and `scripts/baseline_silent_failures.py` asserts that row still reads
  "recommended"). **Append; do not insert above it.**
- `docs/domain_model.md` — entity/mermaid model. `docs/cli_flow.archive.md` — dead, archived.
- `docs/gazette-churn.md`, `docs/stranded-cache-dirs.md` — generated; do not hand-edit.
- `docs/sync_architecture.md` — the PDF-heartbeat + two-portals sync design; was the design
  `gazette-ingest-cadence` was cut from.
- `docs/temp.*` — ignored paste pad, deliberately untracked.

## Conventions

- Commit prefixes in use: `feat:`, `fix:`, `docs:`, `chore:`, `openspec:` (archiving a
  change is `openspec: archive <name> and sync its four spec deltas`).
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