# -*- coding: utf-8 -*-
"""Check whether a new gazette exists, and report what was seen.

Acquisition only. This never ingests: an unattended run that could ingest is one that
could overwrite a good dataset with a bad one, and the single-writer lock serialises
writers without deciding which writer is correct (design D4).

Change detection is by content hash. The publisher re-uploads the same PDF and advances
its timestamp — measured 2026-10-05: page 資料更新 115-09-29 while the newest gazette held
is 2026-09-24, served PDF byte-identical to the archived copy — so a poller keyed on
Last-Modified would report a new gazette every week for one already held.

Weekly by default, to match observed publication cadence. The interval is a staleness
choice, not a correctness one: nothing about detection changes with it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.archive import GazetteArchive  # noqa: E402
from urtpe.poller import CADENCE_DAYS, PAGE_URL, Poller  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--archive-root", default=None,
                        help="archive directory (default: the configured archive root)")
    parser.add_argument("--page-url", default=PAGE_URL,
                        help="the gazette page to check")
    parser.add_argument("--dry-run", action="store_true",
                        help="report whether the page changed without downloading the PDF "
                             "or writing anything")
    parser.add_argument("--cadence-days", type=int, default=CADENCE_DAYS,
                        help="expected interval between checks, for reporting a missed one "
                             "(default: %(default)s)")
    args = parser.parse_args(argv)

    archive = GazetteArchive(args.archive_root) if args.archive_root else GazetteArchive()
    poller = Poller(archive, page_url=args.page_url, cadence_days=args.cadence_days,
                    dry_run=args.dry_run)

    outcome = poller.poll()

    print("gazette check: %s" % outcome.status)
    if outcome.publisher_stamp:
        print("  publisher 資料更新 : %s   (provenance only, not the decision)"
              % outcome.publisher_stamp)
    if outcome.gazette_id:
        print("  gazette             : %s" % outcome.gazette_id)
    if outcome.sha256:
        print("  sha256              : %s" % outcome.sha256)
    if outcome.detail:
        print("  detail              : %s" % outcome.detail)

    if outcome.status == "new_gazette" and not args.dry_run:
        print("\n  archived only. Ingesting is a separate, explicit act:")
        print("    python -m urtpe.cli \"%s\""
              % str(archive.path_of(outcome.gazette_id)))

    records = Poller.read_records(archive)
    if not args.dry_run and len(records) > 1:
        gap = Poller.max_gap_days(records, cadence_days=args.cadence_days)
        if gap is not None and gap > args.cadence_days * 1.5:
            print("\n  WARNING: last check was %.1f days ago, cadence is %d days — "
                  "a publication may have been missed" % (gap, args.cadence_days))

    return 1 if outcome.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())