## Why

Two gates that were supposed to hold the emitted dataset did not.

**The `--from-js` path had no partition gate at all.** The census check
(`Tripwire.check_partition`) compares domain objects, so it can only run on the
PDF path, where the cleansed records and the families are both in memory. The
`--from-js` path — the re-emit path, used for every refresh since 2026-08 —
had **no** partition check. Measured 2026-11-06: a payload missing one node
loaded as **1,443** members with no complaint, and was written back as a
complete dataset. One corruption shape did not even load: a family whose
anchor node was gone died with a bare `StopIteration` (`urtpe/graph.py:181`),
**exit 1** — a crash, not a refusal. Every gate this project has is built on
the rule that a check which cannot see the failure is not a check; this path
had no check at all.

**The census gate checked the wrong partition.** It ran **before** the
ledger's confirmed merge (D5), so it checked the **pre-ledger** family set:
**683** families, while the payload carried **682**. The gate was one family
short of the truth and still passed, and the tripwire report printed
`projects: 683` — a count the payload did not have. The board's header read
"Open items: none" and "1,444 records / 682 projects"; both were right about
the payload and wrong about the gate that was supposed to hold it.

**The badge and the flag could disagree, and nothing checked.** A node's 北
badge is drawn from its `links.taipei`; the flag `節點未能對應平台案件` names
the same condition in words. The flag is raised and cleared only on the
`--links` path, so a payload could keep a stale flag after its binding, and a
node could bind nothing with no flag — silently unbound, invisible in the
viewer.

The three questions that exposed all of this — are there projects not in the
lists, are there recno in no project, does every recno carry a 北 badge — are
answered in `docs/inspection-batchD.md` D18. This change makes the gates that
hold those answers part of the spec.

## What Changes

- **The `--from-js` path holds the partition.** A new
  `Tripwire.check_emitted_partition` reads the payload document *as it is on
  disk*, before the loader rebuilds it, and refuses the run (exit 4, the
  tripwire contract) when the payload does not carry its own records. It
  checks the document's count against its nodes, each family's member list
  against that family's nodes, and each family's anchor against that family's
  nodes.
- **`clean.tsv` is the independent reference.** A payload that lost a record
  **and** had its count rewritten to match is internally consistent, so no
  internal check can see the loss. The reference is the file the ingest wrote,
  holding every cleansed record. A tree without a `clean.tsv` has no
  reference, and the gate falls back to the payload's internal consistency.
- **The census gate checks the partition that is emitted.** The ledger now
  runs **before** the census gate and before the tripwire report, so both
  speak about the family set the payload actually carries. The reconciler
  already compared against the post-ledger set, so that comparison is
  unchanged and now agrees with the gate.
- **The badge and the flag are checked against each other.** A node with no
  case id and no flag, or a node with a case id and the flag, is **named**.
  The check applies only to a project link discovery reached: a run without
  `--links` binds nothing, and a check that fires on every run is a check
  nobody reads.

Nothing about the emitted dataset changes. `projects.json` and
`viewer/projects.data.js` are byte-identical before and after: the payload
never moved. What changes is that a gate now holds it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `history-graph`: the emitted document's partition requirement gains the
  `--from-js` path and the rule that the census gate checks the partition
  that is emitted.
- `official-link-discovery`: the 北 badge and the unplaced-node flag must
  agree, and a disagreement is reported.

## Impact

- `urtpe/tripwire.py` — `check_emitted_partition`, the payload-document
  partition check.
- `urtpe/cli.py` — the gate on the `--from-js` path; the ledger moved before
  the census gate and the tripwire report; `_reference_recnos`.
- `urtpe/emission.py` — the badge/flag agreement check.
- `tests/test_emission_completeness.py` — the test-writing group (10 tests).
- `scripts/probe_three_coverage_proofs.py` — the proof script that answers
  the three questions (read-only).
- `docs/inspection-batchD.md` — D18, the findings and the measured numbers.

No re-emit is required: the payload does not change.
