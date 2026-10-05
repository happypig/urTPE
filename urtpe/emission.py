"""Report the portal-derived data an emission failed to attach.

`official-link-discovery` and `taipei-implementation-data` both state that link and
implementation data SHALL be attached to an emitted dataset. Neither statement was
checked, so a rebuild without `--links` produced a dataset violating both and reported
success — the viewer then served 709 projects with an empty link set and no milestone
data, and presented the absence as "no data" rather than "no link data".

This module is the missing check. It reads a project list and reports what is absent,
naming the fields, both counts, and the run step that attaches them.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

# Fields `official-link-discovery` requires on a project. Absence of all of them
# together means link discovery did not run, which is different from a project that
# genuinely has no portal record.
LINK_FIELDS = ("twur", "taipei", "milestones_national", "milestones_taipei")

# The step that attaches them, named so the cause is readable from the output alone.
LINK_STEP = "link discovery (the --links run step)"


def _links(project: dict[str, Any]) -> dict[str, Any]:
    value = project.get("links")
    return value if isinstance(value, dict) else {}


def _has_link_data(project: dict[str, Any]) -> bool:
    links = _links(project)
    return any(links.get(f) for f in LINK_FIELDS)


def _has_record_link_data(project: dict[str, Any]) -> bool:
    for node in project.get("nodes") or ():
        links = node.get("links")
        if isinstance(links, dict) and links.get("taipei"):
            return True
    return False


def emission_faults(projects: Sequence[dict[str, Any]]) -> list[str]:
    """Report link- and implementation-derived data wholly absent from an emission.

    Returns a list of human-readable faults; empty means the run attached the data.
    Only *wholesale* absence is a fault. Partial coverage is the expected state — the
    portals do not cover every project — so a dataset in which some projects carry link
    data is conforming, and 7 of 709 without is not a defect.
    """
    faults: list[str] = []
    total = len(projects)
    if not total:
        return ["emission contained no projects"]

    # --- link data ---------------------------------------------------------
    with_links = [p for p in projects if _has_link_data(p)]
    if not with_links:
        faults.append(
            f"no link data on any of {total} projects: none of "
            f"{', '.join(LINK_FIELDS)} is present on any project. This run did not "
            f"execute {LINK_STEP}, so the emitted viewer data cannot render milestone "
            f"cards, portal badges or execution-stage labels. Re-run with --links")

    # --- implementation and reward data ------------------------------------
    with_impl = [p for p in projects
                 if "implementation" in p
                 or any("implementation" in n for n in p.get("nodes") or ())]
    if not with_impl:
        faults.append(
            f"no implementation data on any of {total} projects or their records. "
            f"The implementation and reward cards cannot render. This run did not "
            f"execute {LINK_STEP}")

    return faults


def emission_partial(projects: Sequence[dict[str, Any]]) -> list[str]:
    """Report coverage that is partial, so a regression against a prior run is visible.

    Informational, not a fault. The portals do not cover every project, so these counts
    are expected to be less than the project total on a healthy emission.
    """
    notes: list[str] = []
    total = len(projects)
    if not total:
        return []

    with_links = [p for p in projects if _has_link_data(p)]
    if with_links and len(with_links) < total:
        notes.append(
            f"link data covers {len(with_links)} of {total} projects; "
            f"{total - len(with_links)} have no portal record")

    with_record = [p for p in projects if _has_record_link_data(p)]
    if with_record and len(with_record) < len(with_links):
        notes.append(
            f"record-level links cover {len(with_record)} of {len(with_links)} "
            f"projects that carry project-level links")

    with_impl = [p for p in projects if "implementation" in p]
    if with_impl and len(with_impl) < total:
        notes.append(
            f"implementation data covers {len(with_impl)} of {total} projects")

    with_rewards = [p for p in projects if "rewards" in p]
    if with_rewards and len(with_rewards) < total:
        notes.append(
            f"reward data covers {len(with_rewards)} of {total} projects")

    return notes
