# -*- coding: utf-8 -*-
"""The reconciliation comparison, kept after the terminal that printed it.

`reconcile()` returns a result the CLI prints and then discards. That is enough to gate a
run and not enough to audit one: the parked portal cascade was gated on "reconciliation is
trusted in production and has produced a reliable change set across at least two
consecutive ingestions", which is not a judgement anyone can make about output that only
ever existed on one screen.

Two properties of the stored form matter more than the storage itself:

- **It is keyed by publication, not by run.** A re-ingestion overwrites one publication's
  conclusion rather than accumulating competing records, and a re-read is stored under its
  own `event` so it cannot silently rewrite what the original ingestion concluded against a
  predecessor that no longer applies.
- **Authoritative signals are separated from unresolvable movement.** This data cannot
  distinguish a deletion from an edit or a re-dating — they are the same observation — so
  filing them beside new-approval counts would assert more than the comparison can support.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

# What the published data actually supports: additions and net change are assertions.
AUTHORITATIVE = ("new_approvals", "net_change", "previous_total", "current_total")
# Movement is reported, never treated as removal.
UNRESOLVABLE = ("redated", "edited", "vanished", "withdrawn_recent")


def change_set_payload(result, *, event: str = "first_ingest",
                       recorded_at: str = "") -> dict:
    """The structured form of one comparison, beside the human report it came from."""
    row = asdict(result)
    payload = {
        "previous_id": row.get("previous_id") or "",
        "current_id": row.get("current_id") or "",
        "comparable": bool(row.get("comparable")),
        "note": row.get("note", ""),
        # `net_change` is a property on the result, so it is absent from asdict; computing
        # it here keeps the stored record free of a null that reads as a missing count.
        "authoritative": {k: (result.net_change if k == "net_change" else row.get(k))
                           for k in AUTHORITATIVE},
        "unresolvable": {k: len(row.get(k) or []) for k in UNRESOLVABLE},
        "calendar_previous": row.get("calendar_previous", ""),
        "calendar_current": row.get("calendar_current", ""),
        "total_rekey": bool(row.get("total_rekey")),
        "moved_project_ids": len(row.get("moved_project_ids") or []),
        "blocking": list(row.get("blocking") or []),
        "event": event,
        "recorded_at": recorded_at,
    }
    # Kept at the top level as well, so a consumer reading counts does not have to know
    # which half of the record they are in.
    payload.update({k: row.get(k) for k in AUTHORITATIVE})
    payload["net_change"] = result.net_change
    payload["gained_project_ids"] = []
    return payload


def gained_project_ids(payload: dict | None) -> list[str]:
    """Projects that gained an approval in this publication.

    Read only when ``comparable`` is true. An incomparable record carries an empty list
    because nothing was measured, which is not the same finding as nothing gained.
    """
    if not payload or not payload.get("comparable"):
        return []
    return list(payload.get("gained_project_ids") or [])


class ChangeSetStore:
    """One file per publication, outside the working tree alongside the archive."""

    def __init__(self, root: Path | str | None = None):
        if root is None:
            from urtpe.archive import GazetteArchive
            root = Path(GazetteArchive().root) / "change_sets"
        self.root = Path(root)

    def path_for(self, gazette_id: str) -> Path:
        return self.root / f"{gazette_id}.json"

    def load(self, gazette_id: str) -> dict | None:
        path = self.path_for(gazette_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def all(self) -> list[dict]:
        if not self.root.exists():
            return []
        out = []
        for path in sorted(self.root.glob("*.json")):
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except ValueError:
                continue
        return out

    def write(self, payload: dict) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(payload.get("current_id") or "unknown")
        tmp = path.with_suffix(".json.part")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return path

    def append_event(self, payload: dict) -> Path:
        """Record a re-read without disturbing the original ingestion's conclusion.

        The first ingestion owns the file's top level: it is the comparison that ingestion
        actually made. A re-read is appended under ``events`` with the predecessor it used,
        so a later publication cannot silently rewrite what an earlier run concluded.
        """
        path = self.path_for(payload.get("current_id") or "unknown")
        if not path.exists():
            return self.write({**payload, "events": [payload]})

        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return self.write({**payload, "events": [payload]})

        events = current.get("events") or []
        current["events"] = events + [{k: v for k, v in payload.items() if k != "events"}]
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.part")
        tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return path


def write_change_set(store: ChangeSetStore, result, *, event: str = "first_ingest",
                     gained: list[str] | None = None,
                     recorded_at: str = "") -> Path:
    """Persist one comparison's outcome.

    ``gained`` is supplied by the caller because the set of projects that gained a node is
    a product of the merge that runs after reconciliation, not of the comparison itself.
    """
    payload = change_set_payload(result, event=event, recorded_at=recorded_at)
    # When the merge has not run yet, fall back to what the comparison itself saw: the land
    # labels of approvals newer than the predecessor. Both are "projects that gained"; one
    # is measured before merge, the other after, and the caller supplies the latter when
    # it is available.
    payload["gained_project_ids"] = list(
        gained if gained is not None else (result.new_approval_labels or []))
    if event == "reread":
        return store.append_event(payload)
    return store.write(payload)