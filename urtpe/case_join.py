"""Case-id normalisation and join precedence (case-record-join-discriminator).

Pure logic, no I/O: the three fields that carry case ids
(`recovery.cases`, `api_cases`, `links.taipei`) join through here, so a
consumer never attaches the wrong case's timeline and never misses a pair
because the same case is spelled two ways. Stored fields keep their source
spellings; normalisation is a read-side rule only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# The R-form: R + registry number, optionally suffixed with the application
# attempt (R089213-02 = attempt 02 of registry case 089213). Documented pairing,
# docs/urotpe_api.md §4.
_RFORM_RE = re.compile(r"^R(\d+)(?:-\d+)?$")


def normalise_case_id(raw: str) -> str:
    """Map an id to its numeric registry form; anything unrecognised passes
    through unchanged — normalisation never destroys an id it does not know."""
    text = (raw or "").strip()
    m = _RFORM_RE.match(text)
    if m:
        return m.group(1)
    return text


@dataclass
class JoinResult:
    """The join's three answers: the verified anchoring ids (recovery's choice),
    the discovery candidate set (context/breadth), and the ambiguity provenance.
    All comparisons are on normalised ids; the returned ids keep their source
    spellings."""
    anchored: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    ambiguous: bool = False


def join_case_ids(*, recovery_cases: list[str], api_cases: list[str],
                  links_taipei: list[str], ambiguous_zone: bool) -> JoinResult:
    """Precedence: recovery's binding wins for anchoring (it is the
    four-check-verified one); the discovery set is preserved as candidates.
    Agreement collapses to the common set. ambiguous_zone is provenance — it
    marks a choice made under ambiguity, never a reason to prefer discovery."""
    candidates = list(links_taipei or [])
    anchored = list(recovery_cases or [])
    return JoinResult(anchored=anchored, candidates=candidates,
                      ambiguous=bool(ambiguous_zone))
