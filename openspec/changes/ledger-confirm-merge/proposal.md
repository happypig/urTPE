## Why

The city printed the 2010-03-25 approval of 吉林段四小段676 (編號 1303) as
`…676地號1筆土地…` in both 案名 and 地號, although the unit is
`676地號等18筆` — the city's own case platform names that approval's case
09703184 `變更…676地號等18筆…`, and both families resolve to the same national
page (view/75). The record therefore forms its own family
`中山區-吉林段四小段-676地號等1筆`, and the §6.8 detector has flagged the pair
`片段家族合併候選 …（合併候選，需人工確認）` with no way for a person to answer
it. The user confirmed the merge on 2026-11-05 (`docs/inspection-batchD.md` D5).

The correction ledger is the designed home for such a confirmation, but it
cannot express one today: correcting `land_count` to 18 lifts the pair's score
only from 0.567 to 0.667, below the 0.7 link threshold, and the parcel list of
the 變更 is published nowhere we hold, so writing one would repair absent data
by inference. Separately, `--ledger` defaults to `None`, so a PDF ingest that
omits the flag silently drops every correction — while AGENTS.md documents the
default as `urtpe-gazettes/corrections.jsonl`.

## What Changes

- New ledger entry kind `confirm_merge`: names two records by their
  (normalized land, ISO approval date) keys and makes the merge link that pair
  regardless of the similarity score. It answers a merge-candidate flag; it
  changes no record field and invents no parcels. An entry whose either key
  matches no record is reported unmatched, never fatal, and links nothing.
- `--ledger` defaults to `DEFAULT_LEDGER_PATH`
  (`urtpe-gazettes/corrections.jsonl`, `URTPE_LEDGER` override), so every PDF
  ingest applies the ledger. An absent ledger file still means "no corrections"
  and reports so. **BREAKING** (behaviour): a PDF ingest without `--ledger` now
  applies the live ledger.
- First ledger entries (the ledger's first use): `confirm_merge` 1303 ↔ 1347,
  and `land_count` → 18 on 1303 — the family anchor is 1303 (newest), and
  `slug_for` takes its count, so without it the merged family would be named
  `…676地號等1筆`.
- The confirmed pair's merge-candidate review flag no longer appears (the
  fragment is no longer a separate family).

Not gated on POC findings: the link threshold (0.7) and weights are unchanged;
`confirm_merge` bypasses scoring only for the named pair.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `correction-ledger`: adds the `confirm_merge` entry kind (match on two
  records, report unmatched) and states that the ledger applies by default on
  every PDF ingest.
- `case-merging`: a confirmed pair links regardless of score; the
  merge-candidate requirement names the ledger as the way a person answers the
  flag.

## Impact

- Code: `urtpe/ledger.py` (entry kind, pair lookup), `urtpe/merge.py`
  (forced links before clustering), `urtpe/cli.py` (`--ledger` default; pass
  the confirmed pairs into merge).
- Data: one PDF ingest with the ledger rewrites the tracked `data/` files and
  `viewer/projects.data.js` (expect the ~23 MB diff); 吉林676's two
  `.link_cache` directories collapse to one family — `data/project_aliases.json`
  and the coverage guard must accept the `…等1筆` identity disappearing.
- Live state: the first lines of `urtpe-gazettes/corrections.jsonl` (outside
  the repo, append-only).
- Docs: AGENTS.md "manual-correction ledger is designed but unused" bullet.
