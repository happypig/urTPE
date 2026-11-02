# tasks — match-superseding-case-on-application-dates

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_supersede.py` (domain, D1/D2): the 雅祥 shape (11009142 →
      11510001, 公展 dates differ) and the 吉林 shape (10410012 → 11503012, 召開幹事會
      differs) match and return the differing labels; a different 申請計畫日期 →
      none; no application date → none; the existing name / ambiguous / sparse /
      older-id refusals still hold; the 11211211 and 10806141 shapes return an
      empty difference list. RED: both new shapes return none today.
- [x] 1.2 `tests/test_supersede.py` (adapter): the refresh's `superseded` entry
      carries `differs`. RED.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `find_superseding_case` compares application dates and returns the
      differing labels (D1/D2).
- [x] 2.2 `refresh_project` puts `differs` in the report; the script prints it.
- [x] 2.3 Full suite, smoke, `openspec validate --all`. Result: 842 passed /
      1 skipped; smoke passes; 26 items valid.

## 3. Live acceptance

- [x] 3.1 Backup `data/.link_cache` → `data/.link_cache_backup_20261102_appdates`;
      record the payload counts.
- [x] 3.2 Live refresh: 雅祥227-4 11009142 → 11510001 and 吉林705-3 10410012 →
      11503012 recorded with their differing labels; nothing else newly
      superseded.
- [x] 3.3 Re-emit: records / projects / never-approved unchanged; superseded 2 → 4.
      Results 3.1-3.3: backup `.link_cache_backup_20261102_appdates`; refresh 89
      projects / 0 failures — 吉林705-3 10410012 → 11503012 (differ: 召開幹事會日期,
      權變召開幹事會日期), 雅祥227-4 11009142 → 11510001 (differ: the four 公展
      dates), 虎林38 re-confirmed (differ: none); 0 無 without successor, 0
      ambiguous, nothing else changed. Re-emission exit 0, 1,442 / 693,
      never-approved 3, links.taipei 1997, orphan nodes 596 — all unchanged;
      superseded 2 → 4. Local Chrome check: both read 已由 … 取代.
- [x] 3.4 Chrome (local server, then live after push + `check_deploy.py`): both
      entries read `已由 … 取代`. Result: pushed 767bc81; check_deploy all 4
      FRESH (4th poll); the live page shows all four superseded cases.
- [x] 3.5 Archive with spec sync; §38 in the ops log; board entry.
