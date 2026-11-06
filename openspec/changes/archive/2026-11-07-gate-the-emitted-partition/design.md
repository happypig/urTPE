## Context

The pipeline has two emission paths and one partition gate.

**The PDF path.** `urtpe/cli.py:_ingest_pdf` reads the gazette, cleanses it,
merges it, and gates the result. The gate is `Tripwire.check_partition`, which
compares the cleansed records against the families and refuses a violation
(exit 4) before any artifact is written.

**The rebuild path.** `urtpe/cli.py:_load_projects_from_js` reads a document
that was emitted earlier, rebuilds the families from its nodes, and re-emits.
It is the path every refresh takes since 2026-08: the D6/D7/D8/D9/D13/D15
work, the whole-corpus refresh, every re-emit after a link discovery run.

The two paths share the emitter (`urtpe/graph.py:build_graph_document`) and
the output tree, but only one of them had a partition gate. See `proposal.md`
for why, and `docs/inspection-batchD.md` D18 for the measured numbers.

**The actors.** The pipeline operator (runs an ingest or a re-emit), the
downstream reader (the viewer, and every script that reads the payload), and
the city (whose published rows are the data). The system boundary is the
output tree: `raw.tsv`, `clean.tsv`, `merged.tsv`, `projects.json`,
`review_report.txt`, and `viewer/projects.data.js`.

**The constraint that shapes everything.** The single-writer rule: one run per
output tree. A gate that refuses a run leaves that tree exactly as it was, so
the refusal is cheap. A gate that does not exist is not.

## Goals / Non-Goals

**Goals:**

- Every emission path holds the partition.
- The gate checks the family set the payload actually carries, and the report
  states the count the payload carries.
- The record that went missing is named, so the refusal is actionable.
- The badge and the flag cannot silently disagree.

**Non-Goals:**

- Not a new data model. The payload's shape does not change.
- Not a repair mechanism. A lost record is refused, never reconstructed —
  the same rule the truncated-rows rule follows (absent data is excluded and
  named, never repaired by inference).
- Not a fix to the corruption itself. The gate makes a corrupt payload
  visible; it does not explain how a payload came to be corrupt.
- Not a change to what a "family" is. The merge rules are untouched.

## Decisions

### The rebuild path gates on the document, before the loader rebuilds it

`Tripwire.check_emitted_partition` reads the payload document as it is on
disk. The loader is not the gate's input, because the loader is what loses
the record: it turns nodes into families, so a document missing a node has no
trace of the loss by the time it returns.

**Alternative considered — gate after loading, on the rebuilt families.** This
reuses `check_partition` unchanged. Rejected: the rebuilt families are
exactly what the loss produced, so the gate would check the loss against
itself. It would catch a count disagreement (the loader can no longer produce
the count the document claims) but not a lost node with a rewritten count.

**Alternative considered — gate on `merged.tsv`.** It holds the partition's
materialised form. Rejected: it is written *after* the payload, so a corrupt
rebuild would overwrite the good `merged.tsv` before the gate could read it.

### `clean.tsv` is the reference, and it is optional

A document that lost a record **and** had its own count rewritten is
internally consistent. No internal check can see that loss. The reference is
`clean.tsv` — the file the ingest wrote, holding every cleansed record. The
gate compares the document's records against it.

**Optional, because a fresh output tree has no `clean.tsv`.** A test fixture
or a first run into an empty directory has no reference, and the gate falls
back to the document's internal consistency. The reference is an *additional*
check, never a substitute: a document with a rewritten count is refused in a
tree with a reference and merely reported in a tree without one.

**Alternative considered — compare against the previous `projects.json`.** It
is the file the rebuild is about to overwrite, and it is a derived artefact:
its own record count is the number under suspicion. `clean.tsv` is the
primary artefact, and it is written from the records themselves.

### The gate refuses (exit 4), not warns

The tripwire contract: exit 4 means "not provably complete", and **nothing is
written**. A lost record is data corruption, not absence — the same reasoning
the existing census gate uses, and the reason `--links` (exit 0, a warning)
and the census gate (exit 4, a refusal) are different contracts.

**Alternative considered — warn and emit.** Rejected: the emission would then
be a complete-looking dataset that lost a record, which is the exact shape
that went unnoticed since 2026-08. A warning that every re-emit prints is a
warning nobody reads.

### The anchor check belongs in the gate, not in the emitter

A family whose anchor node is missing cannot be emitted at all: the emitter
resolves the anchor to build the node. Before the gate, that was a bare
`StopIteration` (`urtpe/graph.py:181`) — **exit 1**, a crash with no message.
The gate names the family and its missing anchor and refuses with exit 4.

### The ledger runs before the census gate and before the tripwire report

The ledger's `confirm_merge` entry unions two records into one family, so the
post-correction family count is one lower than the uncorrected count. The
census gate used to run first, so it checked the uncorrected set (683
families) while the payload carried the corrected set (682) — and the
tripwire report printed 683.

**The reconciler already compared against the post-ledger set.** It read
`[p.project_id for p in projects]` after the ledger block, so the identity
comparison was already about the emitted set. Moving the ledger earlier
makes the gate agree with the reconciler; it does not change the reconciler.

**Alternative considered — run the census gate twice, before and after the
ledger.** Rejected: the first gate checks a set that is never emitted, so it
proves nothing about the payload. The gate's purpose is to describe the
emission.

### The badge/flag check is scoped to a project discovery reached

A record's badge comes from `links.taipei`; the flag `節點未能對應平台案件`
says the same in words. They must agree.

But a project whose own link set is empty was **not reached by discovery** —
the portals have no record for it, which the coverage report already names as
a count. Its records carry no badge for that reason, and there is nothing to
disagree with. A run with no discovery at all binds nothing everywhere; the
wholesale-absence report already covers it, and a badge/flag fault on every
record would fire on every run.

**Alternative considered — check every record.** Rejected: it makes the check
fire on every run without `--links`, and a check that always fires is a check
nobody reads. This is the same reasoning the existing emission-fault check
uses for wholesale absence versus partial coverage.

### The check stays a warning

`emission_faults` is a warning by design (D5): `--links` is advisory, and the
coverage guard is what covers the default path. The badge/flag disagreement
joins that contract — it is reported, named, and does not refuse the run. A
stale flag is a finding to read; a lost record is corruption to refuse.

## Risks / Trade-offs

**A gate refuses a good run** → The gate's own conditions are the payload's
stated counts and its own node lists. A payload that satisfies them is
accepted; the test group pins a complete payload as accepted. A false
refusal would surface on the first re-emit after the change, and the fault
names the record, so it is diagnosable rather than mysterious.

**`clean.tsv` and the payload disagree for a legitimate reason** → The gate
refuses and names the difference. The only legitimate disagreement is a
payload newer than its `clean.tsv`, which cannot happen: `clean.tsv` is
written by the ingest that writes the payload, and the rebuild path does not
rewrite `clean.tsv`. The reference is used only when the file is present, and
a tree without one is not blocked.

**The gate adds a read of the payload before the loader reads it again** → The
document is 13 MB; it is read twice instead of once, on a path that already
takes minutes. The cost is a second parse of a JSON file, against a run that
does 682 projects of link discovery. Negligible.

**The badge/flag check's scope rule is subtle** → "A project discovery
reached" is not a phrase the code can evaluate directly; the implementation
uses the project's own link set as the proxy. The rule is stated in the spec
so the behaviour is pinned, and the test group covers all four shapes
(silent, stale, agreeing, unreached).

**The proof script and the gate could drift** → The script
(`scripts/probe_three_coverage_proofs.py`) reads the emitted files and
re-derives the partition independently of the gate's in-memory check. Two
independent derivations of the same property is the point: if they ever
disagree, one of them is wrong and the reader can see which.
