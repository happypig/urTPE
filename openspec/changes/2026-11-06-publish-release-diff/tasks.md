## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [x] 1.1 `tests/test_release_diff.py` — the report's back link points at the viewer: the committed `docs/release-diff.html` carries a relative link whose target is `../viewer/index.html`
- [x] 1.2 `tests/test_release_diff_publish.py` — the viewer's header link points at the report: `viewer/index.html` carries a relative link whose target is `../docs/release-diff.html`
- [x] 1.3 `tests/test_release_diff.py` — the newest release's row links to the publisher PDF, and carries the publisher's 資料更新 stamp
- [x] 1.4 `tests/test_release_diff_publish.py` — a release with no recorded publisher URL shows no link: its row carries no publisher URL, and the report states that the URL is unknown rather than linking to the newest document
- [x] 1.5 `tests/test_release_diff.py` — a release with a recorded publisher URL links to that URL, not to the live one
- [x] 1.6 `tests/test_release_diff_publish.py` — the report is self-contained: it carries no external script, stylesheet, font or image request
- [x] 1.7 `tests/test_release_diff.py` + `tests/test_release_diff_publish.py` — the report's link column distinguishes "the live URL, newest release" from "the version-specific URL, older release", so a reader can tell which is which
- [x] 1.8 `tests/test_release_diff.py` — the poll outcome carries the publisher URL it fetched from, and the archive index entry records it
- [x] 1.9 `tests/test_release_diff.py` — an archive index entry without the field is still readable: a pre-existing entry parses, and the report treats that release as having no URL rather than failing
- [x] 1.10 `tests/test_release_diff_publish.py` — the publication step stages only the paths it owns: a dirty working tree with an unrelated modification is left untouched by the step's commit
- [x] 1.11 `tests/test_release_diff_publish.py` — the publication step does not ingest: it writes no file under `data/` and no file under `viewer/`
- [x] 1.12 `tests/test_release_diff.py` — the publication step reports a failed push rather than reporting success
- [x] 1.13 `tests/test_release_diff_publish.py` — the deploy record lists the report as an artifact, so the existing deploy check compares it

## 2. Domain and adapter implementation

- [x] 2.1 `urtpe/poller.py` — `PollOutcome` gains `publisher_url`; the poller records the href it downloaded from on both the `new_gazette` and `reuploaded` paths
- [x] 2.2 `urtpe/archive.py` — `IndexEntry` gains `publisher_url`; `record_ingest` and `record_ingest_bytes` pass it through; an entry written without it still parses (the field defaults to empty)
- [x] 2.3 `scripts/release_diff_report.py` — each release reads its `publisher_url` from the archive index (newest `first_ingest`/`restored` entry for that publication)
- [x] 2.4 `scripts/release_diff_report.py` — the 各版公報 table's link column: the newest release links to the live publisher PDF with the 資料更新 stamp; an older release links to its recorded URL; a release with neither shows that no link is known
- [x] 2.5 `scripts/release_diff_report.py` — the report's header carries a back link to `../viewer/index.html`
- [x] 2.6 `scripts/release_diff.py` — the publisher-URL matching is pure logic with its own tests: which release a URL belongs to, and how a URL that is not the live one is labelled

## 3. Viewer and deploy wiring

- [x] 3.1 `viewer/index.html` — the header carries a `歷次公報差異` link to `../docs/release-diff.html`, present before any data loads
- [x] 3.2 `viewer/app.css` — the header link is styled to sit with the title and not be mistaken for a filter control
- [x] 3.3 `viewer/deploy.json` — `docs/release-diff.html` joins the `artifacts` list, so `scripts/check_deploy.py` compares its served bytes against the committed blob

## 4. The publication step

- [x] 4.1 `scripts/publish_release_diff.py` — regenerate `docs/release-diff.html` from the archive; write nothing else
- [x] 4.2 `scripts/publish_release_diff.py` — stage only `docs/release-diff.html` (and the viewer payload when it changed); never `git add -A`; never touch a path another session modified
- [x] 4.3 `scripts/publish_release_diff.py` — commit with a message naming the release that triggered the regeneration, and push to `origin main`
- [x] 4.4 `scripts/publish_release_diff.py` — report the outcome: what was regenerated, whether anything was committed, whether the push succeeded; exit non-zero on a failed push
- [x] 4.5 `scripts/publish_release_diff.py` — refuse to run when the working tree carries an uncommitted change to the report's own generator, and say so
- [x] 4.6 The `urtpe-poll` Windows task gains a third action running the publication step, after the two pollers

## 5. Verification

- [x] 5.1 The full suite passes (`python -m pytest`) — **1137 passed, 1 skipped** (the deliberate skip at `tests/test_idempotent_flags.py`)
- [x] 5.2 `python scripts/release_diff_report.py` regenerates the report and the committed copy is byte-identical, so a re-run does not churn the file — the publication step compares with the generation timestamp masked out, and restores the committed timestamp when nothing else moved
- [x] 5.3 The report's links are checked by opening both pages: the viewer's header link reaches the report, and the report's back link reaches the viewer — verified in Chrome against a local server (2026-11-06): the header link resolves to `../docs/release-diff.html`, the back link to `../viewer/index.html`, 8 release rows render, and the report makes **no external request**
- [x] 5.4 `python scripts/check_deploy.py` is run against the published site once the push lands — **all 5 artifacts fresh** (2026-11-06): `viewer/index.html`, `viewer/app.js`, `viewer/app.css`, `viewer/projects.data.js`, `docs/release-diff.html`
- [x] 5.5 `python scripts/baseline_silent_failures.py` still passes
- [x] 5.6 `AGENTS.md` records the new scheduled action, the new artifact, and the `publisher_url` field in the archive index

## 6. Recorded outside the repository

- [x] 6.1 The archive index gains a `publisher_url` field on two entries: 2026-10-15 (sha `9b80a6bc…`, stamp `115-10-21 08:34`) and 2026-10-28 (sha `2afa1ba6…`, stamp `115-11-03 13:47`), each accepted only after the document the URL served hashed to the digest the archive already held
- [x] 6.2 `scripts/record_publisher_urls.py` recovers and records the remaining releases' URLs — the Wayback Machine's index of the publisher's PDF path holds 14 captures, none of which is a release we hold, so the six older releases carry no URL and the report says so
