# Tasks: refresh-whole-corpus

## 1. Tests (test-first — all checked before any implementation task)

- [ ] 1.1 Unit test: the checkpoint round-trips (write, read, skip-finished)
      — `tests/test_refresh_whole_corpus.py::TestCheckpoint`
- [ ] 1.2 Unit test: the slice splitter (sorted payload keys → ~100-project
      slices; a re-run with a checkpoint starts after the last finished
      project) — `TestSlices`
- [ ] 1.3 Unit test: the national-page change signal (資料更新日期 parsed from
      the cached page; a later live date marks the project moved; a same or
      absent date does not) — `TestPageSignal`
- [ ] 1.4 Unit test: the finished-case skip (已完工 / 完成成果備查 / a 使照
      核發日期 present skips the header fetch; a moved project overrides) —
      `TestFinishedCaseSkip`
- [ ] 1.5 Unit test: the report counts fetched / skipped-unchanged / failed
      per source and names each failure — `TestReport`
- [ ] 1.6 Unit test: the driver calls the standing `refresh_project` and the
      resolver for unplaced nodes (adapters injected, offline) —
      `TestDriverCalls`

## 2. Implementation

- [ ] 2.1 `scripts/refresh_whole_corpus.py`: the slice splitter, the
      checkpoint, the change-detection signals, the report — adapters
      injected so the unit tests run offline
- [ ] 2.2 Wire the coverage guard around each slice and the single-writer
      lock per slice (the standing helpers)

## 3. Verification

- [ ] 3.1 `python -m pytest` full suite green
- [ ] 3.2 Dry-run: the slice plan over the 682 payload projects (7 slices)
      prints without fetching
- [ ] 3.3 Live run: the slices execute (about 2,000–2,500 requests); the
      checkpoint survives an interrupted slice; the report names every skip
- [ ] 3.4 One emission after the last slice; smoke + baseline pass; the
      B1/B5/B6/C2 measurements re-checked against the board
- [ ] 3.5 `openspec validate --all` green; archive the change and sync the
      delta
