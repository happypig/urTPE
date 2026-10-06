## 1. Tests (test-first; no implementation in this section)

- [x] 1.1 `test_the_deploy_target_is_recorded_in_one_place` — `viewer/deploy.json` exists,
      is tracked, and names owner, repo, pages base and a non-empty artifact list.
- [x] 1.2 `test_the_recorded_pages_path_matches_the_remote_repository_name_case` — compare
      the base URL's final path segment against `git remote get-url origin`, **case
      sensitively**. This is the test that fails for `urtPE` vs `urTPE`, and it needs no
      network. Assert the mismatch is reported as such, so a failure names the cause.
- [x] 1.3 `test_the_recorded_base_is_a_pages_url_for_that_repository` — host is
      `github.io`, owner segment matches the remote's owner, scheme is https.
- [x] 1.4 `test_every_listed_artifact_is_tracked_by_git` — a listed path that is untracked
      or absent is reported; the check must not silently pass on a file git does not know.
- [x] 1.5 `test_the_verdict_distinguishes_fresh_stale_and_missing` — pure function over
      (served bytes, HEAD blob bytes): identical → fresh; same length but different bytes →
      stale; absent → missing.
- [x] 1.6 `test_a_404_is_reported_with_the_case_sensitivity_hint` — the reason a 404 is
      reported must name capitalisation, since that was the real cause and a bare status code
      sent the investigation the wrong way.
- [x] 1.7 `test_agents_records_the_canonical_url` — the docs cite the same base the script
      reads, so the two cannot drift.
- [x] 1.8 `test_the_recorded_record_count_matches_the_emitted_payload` — the count stated
      in `openspec/config.yaml` equals `counts.records` in `viewer/projects.data.js`. This
      is the stale 1,422 assertion, made checkable rather than merely noted.
- [x] 1.9 Confirm 1.1–1.8 fail on the current tree before any implementation.

## 2. Implementation

- [x] 2.1 `viewer/deploy.json` — the single recorded deploy target.
- [x] 2.2 `tests/test_deploy_target.py` imports its verdict logic from the script, so the
      tested function is the one that runs.
- [x] 2.3 `scripts/check_deploy.py` — fetch each artifact, SHA-256 against the `HEAD` blob
      read as bytes (never through shell redirection, which rewrites line endings and would
      report a false mismatch), print a per-artifact table, exit non-zero on any problem.
- [x] 2.4 `AGENTS.md` — canonical URL, the check, and the case-sensitivity trap.
- [x] 2.5 `openspec/config.yaml` — 1,422 → 1,423, and the 統計至 date named.

## 3. Verification

- [x] 3.1 `python -m pytest tests/test_deploy_target.py -q` — all pass, offline, no network.
- [x] 3.2 `python -m pytest -q` — 622 existing plus the new tests, one skip unchanged, and
      still fully offline.
- [x] 3.3 `python scripts/check_deploy.py` — reports every artifact fresh and exits 0
      against the live site.
- [x] 3.4 Negative check: point the script at the mis-capitalised URL and confirm it fails
      with the case hint, and that a deliberately altered local blob reads as `stale`.
- [x] 3.5 `openspec validate deployment-verification --strict`, then all specs.
- [x] 3.6 `python scripts/baseline_silent_failures.py` — items unchanged.

## 4. Close out

- [x] 4.1 `openspec archive deployment-verification` and sync the spec delta.
- [x] 4.2 Append the finding to `docs/portal_operations_log.md`, naming the URL and the
      wrong-capitalisation URL explicitly so the citation resolves.