"""Release diff: what changed in the project count between two PDF releases.

Pure domain logic for the release-diff report. No file I/O, no PDF reading, no
emission — the adapters live in ``scripts/release_diff_report.py``.

The report answers one question: **why does the total number of projects differ
between two PDF releases?** Two counts move for different reasons and the report
keeps them apart:

- **records** move because the city published new approvals, re-dated or edited
  old ones, or because the reader dropped rows it could not trust.
- **projects** move because the records changed *and* the similarity merge
  clustered them differently. A new approval landing inside an existing family
  adds a record and no project. This is the common case: ~70% of records are
  repeat stage approvals of the same unit.

Identity across releases is matched on **member content**, never on the slug.
The slug is the land core of the newest approval and it churns (~11% of
multi-record families have moved at least once), so keying on it would report
every rename as a death and every birth as a loss. But the 地號 cell is not
stable either — the publisher re-prints it, sometimes a character short — so
the member identity is the **案名's own land core** (district, 段/小段, first
parcel, declared count) with the 地號 cell as the fallback for a 案名 that
carries no parseable core. See :meth:`ReleaseRecord.matches`.

The record-level signals come from :func:`urtpe.reconcile.reconcile`, which
already separates the authoritative (new approvals, net change) from the
unresolvable (re-dated, edited, vanished). This module does not re-derive them.

The report also links each release to the document the city published for it.
That link is a publisher address, not a domain fact, but deciding *which* link
a release may carry is a rule with a failure mode — a link to the wrong
gazette looks correct — so it lives here with the rest of the logic
(:func:`publisher_link_for`).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from urtpe.cleanse import parse_name_id
from urtpe.ledger import normalize_land


def _name_core(name: str) -> str:
    """The 案名's land core: district, 段/小段, first parcel, declared count.

    Empty when the 案名 carries no parseable core, so the caller can fall
    back to the 地號 cell.
    """
    district, section, parcel, count = parse_name_id(name or "")
    if not (district and section and parcel):
        return ""
    return "|".join([district, section, parcel,
                     "" if count is None else str(count)])


@dataclass(frozen=True)
class ReleaseRecord:
    """One approval as a release holds it."""

    recno: int
    iso_date: str
    land: str
    name: str
    district: str

    def content_key(self) -> tuple[str, str]:
        """The record's identity: approval date plus a stable land core.

        The 地號 cell alone is not stable. Measured 2026-11-06 across the
        2026-08-27 and 2026-09-24 releases: three units carry a 地號 cell that
        differs by a trailing character or a prefix bleed between the two
        publications (``…地號等6筆土`` against ``…地號等6筆土地``, and a cell
        carrying the previous row's tail in front of its own list). Keying on
        the cell text made those units read as one family dying and another
        born — a family counted twice in opposite directions.

        So the key has two parts, and a record matches on **either**:

        1. the 案名's own land core — district, 段/小段, first parcel, declared
           count — which the publisher prints consistently, and which is the
           identity the cleansing layer already trusts
           (:func:`urtpe.cleanse.parse_name_id`);
        2. the normalized 地號 cell, which is exact when the publisher printed
           it the same way both times.

        The date is part of the key, so two approvals of the same unit at
        different dates stay two records.
        """
        core = parse_name_id(self.name)
        if core and core[0] and core[1] and core[2]:
            name_core = "|".join([core[0], core[1], core[2],
                                  "" if core[3] is None else str(core[3])])
        else:
            name_core = ""
        return (self.iso_date, name_core or normalize_land(self.land))

    def matches(self, other: "ReleaseRecord") -> bool:
        """Whether two records across releases are the same approval.

        True when their approval dates agree and either their 案名 cores or
        their normalized 地號 cells agree. The date must agree: without it two
        stage approvals of one unit would match each other.
        """
        if self.iso_date != other.iso_date:
            return False
        a_core = _name_core(self.name)
        b_core = _name_core(other.name)
        if a_core and b_core:
            return a_core == b_core
        return normalize_land(self.land) == normalize_land(other.land)


@dataclass(frozen=True)
class ReleaseFamily:
    """One merged project family in a release."""

    project_id: str
    members: tuple[ReleaseRecord, ...] = ()

    def member_keys(self) -> Counter:
        return Counter(m.content_key() for m in self.members)


def family_content_keys(family: ReleaseFamily) -> Counter:
    """A family's content identity: the multiset of its members' keys.

    A multiset, not a set: two families whose members carry the same keys but
    in different multiplicity are different families, and a set would make them
    equal.
    """
    return family.member_keys()


@dataclass
class FamilyChange:
    """One family's movement between two releases."""

    previous: ReleaseFamily | None
    current: ReleaseFamily | None
    added: tuple[ReleaseRecord, ...] = ()
    removed: tuple[ReleaseRecord, ...] = ()


@dataclass
class ReleaseDiff:
    """The whole comparison between two releases."""

    previous_id: str
    current_id: str

    previous_records: int = 0
    current_records: int = 0
    previous_projects: int = 0
    current_projects: int = 0

    # Families that exist in both releases.
    matched: list[tuple[ReleaseFamily, ReleaseFamily]] = field(default_factory=list)
    # A family whose members all left, or that the merge split away.
    dead: list[ReleaseFamily] = field(default_factory=list)
    # A family whose members were all new.
    born: list[ReleaseFamily] = field(default_factory=list)
    # A family that kept its identity and gained members.
    grew: list[FamilyChange] = field(default_factory=list)
    # A family that kept its identity and lost members.
    shrank: list[FamilyChange] = field(default_factory=list)
    # A family that kept its members and only changed its slug.
    renamed: int = 0

    # The record-level signals, as `urtpe.reconcile` reported them.
    new_approvals: int = 0
    redated: int = 0
    edited: int = 0
    vanished: int = 0
    recovered: int = 0
    withdrawn_recent: int = 0
    calendar_previous: str = ""
    calendar_current: str = ""
    blocking: list[str] = field(default_factory=list)

    @property
    def net_projects(self) -> int:
        return self.current_projects - self.previous_projects

    @property
    def net_records(self) -> int:
        return self.current_records - self.previous_records


def match_families(
    previous: list[ReleaseFamily],
    current: list[ReleaseFamily],
) -> tuple[list[tuple[ReleaseFamily, ReleaseFamily]], list[ReleaseFamily], list[ReleaseFamily]]:
    """Pair each release's families by member content.

    Returns ``(matched, born, lost)``. A family is matched when it shares at
    least one member with a family in the other release; the pairing is greedy
    over the strongest overlap, so a family that absorbed another family's
    members matches the one it absorbed from.

    A family that shares nothing is either born (present only in ``current``)
    or lost (present only in ``previous``). Neither is a claim about the city's
    data: it is a statement about which families the reader could pair up.

    A family must not be both born and lost. Measured 2026-11-06: three units
    had a 地號 cell that differs by one character between the 08-27 and 09-24
    releases, and matching on the cell text alone put the same unit in both
    lists — inflating the movement in both directions at once. The member
    comparison therefore falls back to the 案名's land core (see
    :meth:`ReleaseRecord.matches`).
    """
    # Score every candidate pair by how many members they share.
    scores: Counter = Counter()
    for pi, prev_fam in enumerate(previous):
        for ci, cur_fam in enumerate(current):
            shared = sum(
                1 for pm in prev_fam.members
                for cm in cur_fam.members
                if pm.matches(cm))
            if shared:
                scores[(pi, ci)] = shared

    matched_pairs: list[tuple[ReleaseFamily, ReleaseFamily]] = []
    used_prev: set[int] = set()
    used_cur: set[int] = set()
    # Strongest overlap first, so the best pair wins when one family could
    # match several others.
    for (pi, ci), _score in scores.most_common():
        if pi in used_prev or ci in used_cur:
            continue
        used_prev.add(pi)
        used_cur.add(ci)
        matched_pairs.append((previous[pi], current[ci]))

    # A slug on both sides that did not pair is a matching failure, not two
    # separate families. ``project_id`` is the land core of the newest
    # approval, and the merge makes it unique within one release, so the same
    # slug on both sides names the same unit. Pairing them is using the
    # domain's own identity, not guessing.
    prev_by_slug: dict[str, list[int]] = {}
    for i, fam in enumerate(previous):
        prev_by_slug.setdefault(fam.project_id, []).append(i)
    for ci, cur_fam in enumerate(current):
        if ci in used_cur:
            continue
        for pi in prev_by_slug.get(cur_fam.project_id, ()):
            if pi in used_prev:
                continue
            used_prev.add(pi)
            used_cur.add(ci)
            matched_pairs.append((previous[pi], cur_fam))
            break

    born = [fam for i, fam in enumerate(current) if i not in used_cur]
    lost = [fam for i, fam in enumerate(previous) if i not in used_prev]
    return matched_pairs, born, lost


@dataclass(frozen=True)
class PublisherLink:
    """How one release links to the document the city published for it.

    Two kinds, and the difference matters:

    - ``live`` — the publisher's current PDF link. The city serves one link at
      a time and repoints it on every publication, so it names "whatever is
      newest". Correct only for the newest release.
    - ``versioned`` — the URL that served *this* release when it was fetched.
      A version-specific URL stays a durable address for that document
      (measured 2026-11-06: the 2026-10-15 URL still serves the 2026-10-15
      document, a different digest from the current one; a fabricated path
      answers 404).

    A release with neither carries no link. Giving it the live URL would send
    a reader to a different gazette while the link looked correct, so the
    report says the URL is unknown instead.
    """

    url: str = ""
    kind: str = ""          # "live" | "versioned" | ""
    publisher_stamp: str = ""
    label: str = ""

    @property
    def known(self) -> bool:
        return bool(self.url)


def publisher_link_for(
    published_date: str,
    *,
    recorded_url: str = "",
    live_url: str = "",
    publisher_stamp: str = "",
    live_stamp: str = "",
    newest_published_date: str = "",
) -> PublisherLink:
    """The link one release may carry.

    ``recorded_url`` is the version-specific URL the archive index holds for
    this release. ``live_url`` is the publisher's current PDF link, which
    serves the newest document and no other.

    The newest release may carry the live URL, because the live URL serves
    exactly that document. An older release may carry only its own recorded
    URL: the live URL would serve a different document, and the link would
    look correct while being wrong.

    The stamp beside a link dates the **document that link serves**. A
    version-specific link carries the stamp recorded with that URL; the live
    link carries the publisher's current stamp. A release never inherits
    another release's date.
    """
    if recorded_url:
        return PublisherLink(url=recorded_url, kind="versioned",
                             publisher_stamp=publisher_stamp,
                             label="該版原始檔")
    if live_url and published_date and published_date == newest_published_date:
        return PublisherLink(url=live_url, kind="live",
                             publisher_stamp=live_stamp,
                             label="出版方最新檔")
    return PublisherLink(kind="", publisher_stamp=publisher_stamp,
                         label="未記錄")


def diff_releases(
    previous_id: str,
    current_id: str,
    previous: list[ReleaseFamily],
    current: list[ReleaseFamily],
    *,
    reconciliation=None,
) -> ReleaseDiff:
    """Compare two releases at the record and the project level.

    ``reconciliation`` is an optional :class:`urtpe.reconcile.ReconcileResult`
    for the same pair. Its record-level signals are copied in as they stand:
    this module does not re-derive what the reconciler already measured, and it
    does not upgrade an unresolvable signal into an authoritative one.
    """
    diff = ReleaseDiff(previous_id=previous_id, current_id=current_id)
    diff.previous_projects = len(previous)
    diff.current_projects = len(current)
    diff.previous_records = sum(len(f.members) for f in previous)
    diff.current_records = sum(len(f.members) for f in current)

    matched, born, lost = match_families(previous, current)
    diff.matched = matched
    diff.born = born
    diff.dead = lost

    for prev_fam, cur_fam in matched:
        # A member is "added" when no member of the previous family matches it.
        # The comparison uses the same rule the pairing used, so a 地號 cell
        # that changed by one character does not read as a member leaving.
        added = tuple(m for m in cur_fam.members
                      if not any(m.matches(pm) for pm in prev_fam.members))
        removed = tuple(m for m in prev_fam.members
                        if not any(m.matches(cm) for cm in cur_fam.members))
        if added or removed:
            change = FamilyChange(previous=prev_fam, current=cur_fam,
                                  added=added, removed=removed)
            if added and removed:
                # Members moved between the two families. It is neither a pure
                # growth nor a pure shrink, so it is reported in both lists and
                # the reader sees the exchange.
                diff.grew.append(change)
                diff.shrank.append(change)
            elif added:
                diff.grew.append(change)
            else:
                diff.shrank.append(change)
        elif prev_fam.project_id != cur_fam.project_id:
            diff.renamed += 1

    if reconciliation is not None:
        diff.new_approvals = reconciliation.new_approvals
        diff.redated = len(reconciliation.redated)
        diff.edited = len(reconciliation.edited)
        diff.vanished = len(reconciliation.vanished)
        diff.recovered = len(reconciliation.recovered)
        diff.withdrawn_recent = len(reconciliation.withdrawn_recent)
        diff.calendar_previous = reconciliation.calendar_previous
        diff.calendar_current = reconciliation.calendar_current
        diff.blocking = list(reconciliation.blocking)
    return diff
