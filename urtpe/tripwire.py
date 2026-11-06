"""Completeness tripwire for gazette ingestion.

Refuses to emit a dataset it cannot prove is complete. The reader already raises
``TableStructureError`` for structural faults; this module covers the faults that
only show up *across* records — a gap in 編號, an unparsed date, a page that yielded
no table — and, critically, evaluates everything before any artifact is written.

That ordering is the whole point. ``urtpe.coverage`` diffs only
``set(before) & set(after)``, so when every ``project_id`` changes the intersection
is empty, ``regressions`` is empty, and the guard passes while all 709 caches are
orphaned. A check that runs after the damage, or that cannot see the failure, is
not a check.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Tripwire:
    """Structural completeness gate.

    Thresholds are parameters rather than constants: they are calibrated against the
    gazettes measured so far and may need adjustment when the city publishes again.
    """

    # A defective export repeats one data row in the page header of every page after
    # the first. The reader discards those as duplicate 編號, so a small non-zero
    # count is expected and healthy; a large one means something else is wrong.
    max_duplicate_recnos: int = 400
    # 編� runs 1..N with no gaps in every gazette measured (1422 / 1427 / 1436).
    require_contiguous_recnos: bool = True

    # 編號 absent because the publisher truncated that record's cell; set by check().
    excluded_recnos: list[int] = field(default_factory=list)

    def check(self, records: list[dict], *, pages: int = 0, tables_found: int = 0,
              duplicate_recnos: int = 0,
              excluded_recnos: set[int] | None = None) -> list[str]:
        """Return every fault found; an empty list means the extraction is complete.

        ``excluded_recnos`` are the 編號 the reader deliberately dropped because the
        publisher truncated their cell (see :class:`urtpe.extract.CellFault`). They
        are absent from ``records`` on purpose, so they must not be reported as
        missing; any *other* gap still means a page or record went unread.
        """
        faults: list[str] = []
        excluded = {int(v) for v in (excluded_recnos or ())}
        self.excluded_recnos = []
        if not records:
            return ["no records extracted"]

        recnos = []
        for rec in records:
            try:
                recnos.append(int(rec["recno"]))
            except (KeyError, TypeError, ValueError):
                faults.append(f"record with a non-integer 編號: {rec.get('recno')!r}")
        if not recnos:
            return faults or ["no integer 編號 present"]

        unique = sorted(set(recnos))
        if self.require_contiguous_recnos:
            expected = set(range(1, max(unique) + 1))
            missing = sorted(expected - set(unique))
            unexplained = sorted(set(missing) - excluded)
            if unexplained:
                preview = ", ".join(str(v) for v in unexplained[:20])
                more = f" (+{len(unexplained) - 20} more)" if len(unexplained) > 20 else ""
                faults.append(
                    f"編號 not contiguous: {len(unexplained)} missing "
                    f"(expected 1..{max(unique)}): {preview}{more}")
            extra = sorted(set(unique) - expected)
            if extra:
                faults.append(f"編號 above the maximum: {extra[:10]}")
            # A gap that is entirely explained is still a shortfall in the gazette,
            # so it is surfaced as a note the caller reports rather than a pass.
            accounted = sorted(set(missing) & excluded)
            if accounted:
                self.excluded_recnos = accounted

        bad_dates = [r["recno"] for r in records
                     if not _parses(r.get("date", ""))]
        if bad_dates:
            faults.append(
                f"{len(bad_dates)} record(s) with an unparsed 核定日期: "
                f"{', '.join(str(v) for v in bad_dates[:20])}")

        if pages and tables_found != pages:
            faults.append(
                f"pages yielding a table: {tables_found} of {pages}; "
                "a page with no table would silently drop its records")

        if duplicate_recnos > self.max_duplicate_recnos:
            faults.append(
                f"duplicate 編號 count {duplicate_recnos} exceeds tolerance "
                f"{self.max_duplicate_recnos}")

        return faults

    def check_emitted_partition(self, doc: dict,
                                reference_recnos: set[int] | None = None) -> list[str]:
        """The same partition check, over an emitted payload document.

        :meth:`check_partition` compares domain objects, so it can only run on
        the PDF path where the cleansed records and the families are both in
        memory. The ``--from-js`` path reads a payload that was emitted
        earlier and re-emits it, and it had no partition check at all: a
        payload missing one node loaded as 1,443 members and was written back
        as a complete dataset (measured 2026-11-06).

        The check reads the document's own ``counts`` as the expected total,
        because that is the number the payload claims. A payload whose nodes
        do not sum to its own count is corrupt, and the check names the
        missing recnos.

        ``reference_recnos`` is the independent reference: the recnos of
        ``clean.tsv``, the file the ingest wrote. A payload that lost a record
        AND had its count rewritten to match is internally consistent, so no
        internal check can see the loss — only a reference outside the payload
        can.
        """
        faults: list[str] = []
        projects = doc.get("projects") or []
        if not projects:
            return ["the payload holds no projects"]

        owner: dict[int, str] = {}
        for project in projects:
            for node in project.get("nodes") or ():
                recno = node.get("recno")
                if recno is None:
                    faults.append(
                        "a node in %s carries no 編號" % project.get("project_id", "?"))
                    continue
                recno = int(recno)
                if recno in owner:
                    faults.append(
                        "record %d appears in two families: %s and %s"
                        % (recno, owner[recno], project.get("project_id", "?")))
                else:
                    owner[recno] = project.get("project_id", "?")

        counts = doc.get("counts") or {}
        claimed = counts.get("records")
        present = len(owner)
        if claimed is not None and int(claimed) != present:
            faults.append(
                "the payload claims %d records but its nodes hold %d" % (claimed, present))

        claimed_projects = counts.get("projects")
        if claimed_projects is not None and int(claimed_projects) != len(projects):
            faults.append(
                "the payload claims %d projects but holds %d"
                % (claimed_projects, len(projects)))

        # A family that claims members its nodes do not carry is a second way
        # to lose a record: the node list is what the viewer reads, but the
        # member list is what the partition count is built from.
        for project in projects:
            members = project.get("member_recnos")
            nodes = {int(n["recno"]) for n in (project.get("nodes") or ())
                     if n.get("recno") is not None}
            if members is not None:
                missing = sorted(set(int(m) for m in members) - nodes)
                if missing:
                    faults.append(
                        "family %s lists %d member(s) its nodes do not carry: %s"
                        % (project.get("project_id", "?"), len(missing),
                           ", ".join(str(v) for v in missing[:10])))
            # The anchor is the family's own identity: the emitter resolves it
            # to build the node, so a family whose anchor is missing cannot be
            # emitted at all. Without this the run died with a bare
            # StopIteration (exit 1) — a crash, not a refusal.
            anchor = project.get("anchor_recno")
            if anchor is not None and int(anchor) not in nodes:
                faults.append(
                    "family %s anchors on record %s, which its nodes do not carry"
                    % (project.get("project_id", "?"), anchor))

        # The independent reference. A record clean.tsv holds and the payload
        # does not was lost between the ingest and this payload.
        if reference_recnos is not None:
            lost = sorted(reference_recnos - set(owner))
            if lost:
                preview = ", ".join(str(v) for v in lost[:20])
                more = f" (+{len(lost) - 20} more)" if len(lost) > 20 else ""
                faults.append(
                    "the payload holds %d of the %d records clean.tsv holds; "
                    "%d are missing: %s%s"
                    % (len(set(owner) & reference_recnos), len(reference_recnos),
                       len(lost), preview, more))
            extra = sorted(set(owner) - reference_recnos)
            if extra:
                faults.append(
                    "the payload holds %d record(s) clean.tsv does not: %s"
                    % (len(extra), ", ".join(str(v) for v in extra[:10])))

        return faults

    def check_partition(self, clean: list, projects: list,
                        *, emitted_records: int | None = None) -> list[str]:
        """The merge census: the partition must be total, disjoint, and agree with
        the emitted count. Returns the same faults-list shape as :meth:`check`;
        pure — domain objects in, strings out, no I/O.

        A partition violation is data corruption, not absence, so the caller wires
        it under the same exit-4 contract as the extraction faults. The audited
        property (dataset-completeness audit, Appendix A): every cleansed record
        belongs to exactly one project family, and the family members sum to the
        cleansed record count.
        """
        faults: list[str] = []
        owner: dict[int, str] = {}
        for project in projects:
            for member in project.members:
                if member.recno in owner:
                    faults.append(
                        f"record {member.recno} appears in two families: "
                        f"{owner[member.recno]} and {project.project_id}")
                else:
                    owner[member.recno] = project.project_id

        clean_recnos = {r.recno for r in clean}
        lost = sorted(clean_recnos - set(owner))
        if lost:
            preview = ", ".join(str(v) for v in lost[:20])
            more = f" (+{len(lost) - 20} more)" if len(lost) > 20 else ""
            faults.append(
                f"merge partition not total: {len(lost)} cleansed record(s) in no "
                f"family: {preview}{more}")

        extra = sorted(set(owner) - clean_recnos)
        if extra:
            faults.append(
                f"merge partition holds records that cleansing does not: "
                f"{extra[:10]}")

        members_total = sum(len(p.members) for p in projects)
        if members_total != len(clean):
            faults.append(
                f"family members sum to {members_total}, but cleanse produced "
                f"{len(clean)} records")

        if emitted_records is not None and emitted_records != len(clean):
            faults.append(
                f"the document reports {emitted_records} records but cleanse "
                f"produced {len(clean)}")

        return faults


def _parses(date_str: str) -> bool:
    from urtpe.extract import to_iso

    return to_iso(date_str)[0] is not None


@dataclass
class TripwireResult:
    """Outcome of the gate, including what was observed for the run report."""

    ok: bool
    faults: list[str] = field(default_factory=list)
    calendar: str = "unknown"
    record_count: int = 0
    project_count: int = 0
    duplicate_recnos: int = 0
    # 編號 dropped because the publisher truncated their cell. Carried into the run
    # report so a gazette missing records is never presented as a faithful copy.
    excluded_recnos: list[int] = field(default_factory=list)

    def report(self) -> str:
        head = "tripwire: PASS" if self.ok else f"tripwire: FAIL ({len(self.faults)} fault(s))"
        lines = [
            head,
            f"  records: {self.record_count}  projects: {self.project_count}",
            f"  calendar: {self.calendar}  duplicate 編號: {self.duplicate_recnos}",
        ]
        if self.excluded_recnos:
            shown = ", ".join(str(v) for v in self.excluded_recnos[:20])
            more = (f" (+{len(self.excluded_recnos) - 20} more)"
                    if len(self.excluded_recnos) > 20 else "")
            lines.append(
                f"  INCOMPLETE: {len(self.excluded_recnos)} record(s) excluded because the "
                f"publisher truncated their 地號 cell — this gazette is NOT a faithful "
                f"copy: {shown}{more}")
        lines += [f"  - {f}" for f in self.faults]
        return "\n".join(lines)


class TripwireFailure(RuntimeError):
    """The extraction was not provably complete; nothing was written."""

    def __init__(self, result: TripwireResult):
        self.result = result
        super().__init__(result.report())