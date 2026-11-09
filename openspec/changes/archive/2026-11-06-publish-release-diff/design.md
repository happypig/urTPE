## Context

The release-diff report was built on 2026-11-06 as a read-only tool:
`scripts/release_diff.py` holds the pure logic, `scripts/release_diff_report.py`
reads every archived PDF and renders `docs/release-diff.html`. It is not
published, nothing links to it, and it is regenerated only by hand.

**How the site is published.** GitHub Pages serves this repository from `main`
(the `viewer/deploy.json` record names `published_from: {branch: main, path: /}`).
There is no CI. A page is published by committing it and pushing. `scripts/check_deploy.py`
compares each artifact's served bytes against its `HEAD` blob and reports
fresh / stale / missing — so a published page that is not in the artifact list
is simply never checked, and a page that is in the list but was not pushed
reads as current until the check runs.

**What the viewer loads.** `viewer/index.html` loads exactly four files:
`app.css`, `app.js`, `projects.data.js`, and itself. The `?v=` cache-bust on
the two scripts is derived from the dataset by `urtpe/viewer.py`, so it cannot
drift from the payload. `tests/test_viewer_contract.py` and
`tests/test_viewer_degrades.py` pin the shape: one version token across the
assets, and no hardcoded 統計至 label in the HTML.

**The publisher's addressing.** Measured 2026-11-06 against the live gazette
page (`https://uro.gov.taipei/cp.aspx?n=963B15B39CADB94E`):

| Fact | Measurement |
|---|---|
| PDF links on the page | exactly 1 |
| Past-publication list on the page | none (no 歷次/往期/歷史 listing) |
| The live link's document | sha256 `2afa1ba6…` = the 2026-10-28 gazette |
| A known old link (2026-10-15) | still 200, sha256 `9b80a6bc…` = the 2026-10-15 gazette |
| A fabricated UUID path | 404 |
| The gazette page's own captures (Wayback) | one PDF link each, repointed over time |

So the live URL is a pointer to "whatever is newest", and a version-specific
URL is a durable pointer to "this document" — but only to someone who recorded
it. Exactly one version-specific URL survives in this repository
(`docs/urotpe_api_vs_pdf.md` names the 2026-10-15 one), because the poller
records the digest and the publisher's 資料更新 stamp but never the URL it
fetched from.

**The archive index.** `urtpe/archive.py` writes one append-only JSONL entry
per ingest with these fields: `gazette_id`, `published_date`, `ingested_at`,
`record_count`, `project_count`, `reader_version`, `filename`, `calendar`,
`source_path`, `sha256`, `event`, `acquisition`, `publisher_stamp`,
`date_order_violations`, `dated_records`, `supersedes`, `restored_from`. There
is no publisher URL. The index is append-only and entries are never rewritten,
so a field added today leaves every existing entry without it.

**The scheduled task.** `urtpe-poll` runs weekly, Monday 06:30, with two
actions: `scripts/poll_gazette.py` and `scripts/poll_p168.py`. It runs as the
logged-in user, in `InteractiveToken` mode (not `S4U`), so a network-available
session is needed for a push. `MultipleInstances: IgnoreNew`,
`ExecutionTimeLimit: PT72H`.

**What the report already measures.** The report re-reads every archived PDF
under the current reader, merges it, and pairs the releases by member content.
Its numbers are reconstructible from its own rows: `previous + born − dead ==
current` holds for all seven transitions. The identity rule is the 案名's land
core, because the 地號 cell is not stable across publications (three units
differ by one character between the 08-27 and 09-24 releases).

## Goals / Non-Goals

**Goals:**

- The release-diff report is reachable from the site a reader visits, and
  reachable from the report back.
- Every release links to the document the city published for it, or says in
  words that no link is known.
- A new gazette makes the report regenerate itself, unattended.
- The published report is covered by the existing deploy check, so "stale" is
  detectable rather than silent.

**Non-Goals:**

- Recovering publisher URLs for the releases already held. Their URLs were
  never recorded and cannot be reconstructed from what we hold. The Wayback
  Machine has captures of 14 older publisher PDFs, none of which is a release
  we hold, and its captures of the gazette *page* stop in 2019.
- Changing how a gazette is ingested. Ingestion stays an explicit, separate
  act. The publication step publishes a report derived from what was already
  ingested; it never ingests.
- A CI workflow. There is no CI in this repository, and the scheduled task
  already runs on the machine that holds the archive.

## Decisions

### D1 — The report is published as `docs/release-diff.html`, and joins the artifact list

GitHub Pages serves the whole repository from `main`, so a page under `docs/`
is published without any build step. Verified live:
`https://happypig.github.io/urTPE/docs/domain-model.html` returns 200.

The alternative — copying the report into `viewer/` — would put a
regenerated artefact inside the directory the viewer's own consistency tests
inspect, and would make the report's `?v=` cache-bust interact with the
dataset's. `docs/` keeps it out of that machinery, next to
`docs/domain-model.html`, which is already a self-contained static page.

It joins `viewer/deploy.json`'s `artifacts` so `check_deploy.py` compares it.
`tests/test_deploy_target.py` requires every listed artifact to be tracked by
git, so the report must be committed before it is listed.

**Cost:** GitHub Pages caches for `max-age=600` (measured), so a freshly
pushed report can serve stale for up to ten minutes. The report's own header
carries its generation timestamp, so a reader can tell.

### D2 — The link between the viewer and the report is relative

`viewer/index.html` links to `../docs/release-diff.html`; the report links
back to `../viewer/index.html`. Both are relative, so the pair works from
`file://` (the viewer's normal mode), from the published site, and from a
clone. An absolute `https://happypig.github.io/...` URL would break the
`file://` case, which is the way most readers open the viewer.

The viewer link lives in the header, next to the title, so it is present
before any data loads — a reader who lands on a broken payload can still reach
the report.

### D3 — A release links to its own publisher URL, or says it has none

The 各版公報 table's newest row links to the live publisher PDF with the
publisher's 資料更新 stamp beside it, because the live URL serves exactly that
document (verified by hash). Older rows link to the version-specific URL that
served that release, when the archive index records one.

A release whose URL is unknown shows `—` in the link column, not a link to
the live PDF. The live PDF is the *newest* document; linking a 2026-08-11 row
to it would send a reader to the wrong gazette, and the link would look
correct. From this change forward, every release acquires a URL when the
poller next sees the city publish it.

The report's own footer states the rule, so a reader knows why a row has no
link.

### D4 — The poller records the publisher URL; the archive index carries it

`PollOutcome` gains `publisher_url`, and `IndexEntry` gains
`publisher_url`. The poller already knows the URL — it extracts the href and
downloads from it — and simply does not keep it.

The URL is recorded on the `new_gazette` path, where the document is archived
by hash and the URL is the address that served it. A `reuploaded` outcome
records the URL too: the city repointing its link without changing the
document is exactly the event that would otherwise lose the association
between a URL and a release.

The index is append-only, so existing entries carry no URL. The report reads
the newest `first_ingest`/`restored` entry per release, which is the same rule
it already uses for the record and project counts.

**Alternative rejected:** writing the URL to a separate map file. The index is
already the archive's provenance record and it is already read by the report;
a second file would be a second source of truth with no owner.

### D5 — The publication step regenerates, commits and pushes; it never ingests

`scripts/publish_release_diff.py` does three things, in order:

1. Regenerate `docs/release-diff.html` from the archive (read-only over the
   PDFs; it writes one HTML file).
2. Commit, if the report changed, with a message naming the release that
   triggered it.
3. Push to `origin main`, which is the branch GitHub Pages publishes from.

It does **not** ingest. The pipeline's single-writer lock is not needed
because nothing under `data/` or `viewer/` is written — the report is a
separate artefact derived from the archive, and the archive is read-only here.
This keeps the `gazette-cadence` guarantee intact: an unattended run never
rewrites the emitted dataset.

**The commit must not sweep up unrelated work.** The working tree carries
changes from other sessions (measured 2026-11-06: `urtpe/cli.py`,
`urtpe/emission.py`, `urtpe/tripwire.py` modified by a concurrent session).
The publication step stages **only** the paths it owns
(`docs/release-diff.html` and, when it changed, the viewer payload) and
commits with an explicit path list. It never uses `git add -A`.

**If the tree is dirty in a way that affects the report**, the step reports it
and stops rather than committing a half-finished change. The report is
derived from the archive, not from the working tree, so a dirty tree does not
change the report's numbers — but a dirty `scripts/release_diff*.py` would
change what "regenerate" means, and that is worth stopping for.

**The push can fail.** A network outage, or a concurrent push, makes the push
fail. The step reports it and exits non-zero; the scheduled task records that
result. The next week's run publishes then. A failed publish leaves the
committed report ahead of the served one, which `check_deploy.py` reports as
stale — visible, not silent.

### D6 — The scheduled task gains the publication as a third action

The `urtpe-poll` task already runs `poll_gazette.py` and `poll_p168.py` as
separate actions. A third action runs the publication step. Actions run in
order, so the report is regenerated after the gazette is polled.

The task's `ExecutionTimeLimit` is PT72H and `MultipleInstances` is
`IgnoreNew`, so a slow run cannot overlap the next one.

**The task runs in `InteractiveToken` mode.** A push needs the user's
credentials, which live in the Windows credential manager (`credential.helper =
manager`) and in `gh`'s keyring. A task running as `S4U` or as SYSTEM would
have neither and the push would fail. The task therefore only runs when the
user is logged in — which is how it already runs.

**Order matters.** The publication step runs *after* the poller, so a new
gazette is in the archive before the report is regenerated. But the poller
never ingests, so the report describes a release the dataset does not yet
contain. The report already states this: the 各版公報 table has a 匯入 column
saying whether a release became the dataset's source, and the payload-gap note
names the difference between the report's numbers and the viewer's.

### D7 — The report's back link and the viewer link are part of the report's contract

Both links are asserted by a test that reads the committed HTML, so a
regeneration that drops one fails the suite rather than shipping a report
with a dead end.

## Risks / Trade-offs

- **The push publishes whatever is on `main`.** If another session has
  committed something to `main` that is not ready, the publication step's push
  publishes it too. This is inherent to publishing from a branch with no CI.
  Mitigated by the path-scoped commit, but not by the push itself: the push
  carries whatever `main` holds. Accepted, because the alternative — a
  separate `gh-pages` branch — needs a build step this repository does not
  have.

- **Two pushes race.** The publication step and a person pushing at the same
  time: one fails. The step reports it and the next run publishes. The report
  is not lost — it is committed locally either way.

- **The report takes about a minute to regenerate.** Eight PDFs, each read
  under the current reader. The corpus cache in `.corpus_cache/` makes it
  much faster when warm. The task's time limit is ample.

- **A concurrent session's in-flight change to `scripts/release_diff*.py`
  would change the report's meaning.** The publication step reads the
  committed version? No — it runs the working tree's version. This is
  accepted: the step reports the commit it made, so a changed report is
  visible in the history, and the report's own header carries its generation
  timestamp.

- **The live PDF link breaks when the city republishes.** The newest row's
  link is the live URL, which always serves the newest document — so it stays
  correct for the newest row and becomes wrong only if the city republishes
  without a new gazette (a re-upload, which the poller detects as
  `reuploaded` and does not treat as new). The stamp beside the link dates it.

- **Pages' ten-minute cache.** A pushed report can serve stale for up to ten
  minutes. The generation timestamp in the header is the reader's check.
