"""Record the publisher URL and 資料更新 stamp for the releases we hold.

The archive's index now carries a `publisher_url`, and the poller fills it for
every publication it fetches from now on. The publications already held were
archived before the field existed, so their URLs were never written down.

This script recovers what can be recovered, and records it **only** when the
document the URL serves hashes to the digest the archive already holds for
that release. A URL that serves a different document is refused: a link to
the wrong gazette looks correct, and the report would publish it.

Sources tried, in order:

1. The publisher URLs the archive's own poll log implies — the poller fetched
   from one, and the stamp it recorded is the 資料更新 timestamp for the
   document that URL served.
2. The URL the repository's history names (docs/urotpe_api_vs_pdf.md).
3. The Wayback Machine's index of the publisher's PDF path.

    python scripts/record_publisher_urls.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.archive import GazetteArchive  # noqa: E402

UA = {"User-Agent": "urtpe-release-diff"}
PDF_PREFIX = "www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/*"

# The URL the repository's own history names, and the release it serves.
KNOWN_URLS = [
    ("2026-10-15",
     "https://www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/"
     "1d9657b0-55a3-4bbb-8846-f28eeb1a5a85.pdf"),
]


def get(url: str) -> bytes:
    with urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=180) as resp:
        return resp.read()


def candidate_urls() -> list[str]:
    urls = [u for _, u in KNOWN_URLS]
    try:
        api = ("https://web.archive.org/cdx/search/cdx?url=" + PDF_PREFIX +
               "&output=json&fl=original&collapse=urlkey")
        rows = json.loads(get(api).decode("utf-8", "replace"))
        for row in rows[1:]:
            if ".pdf" in row[0].lower():
                urls.append(row[0])
    except Exception as exc:  # noqa: BLE001
        print("[INFO] the Wayback index was unreachable: %s" % exc)
    return list(dict.fromkeys(urls))


def stamp_for(gazette_id: str, archive_root: pathlib.Path) -> str:
    """The publisher's 資料更新 stamp for a publication, from the poll log."""
    path = archive_root / "poll_log.jsonl"
    if not path.exists():
        return ""
    stamp = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("gazette_id") == gazette_id and row.get("publisher_stamp"):
            stamp = row["publisher_stamp"]
    return stamp


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--archive-root", default=str(
        pathlib.Path(r"D:\project\urtpe-gazettes")))
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be recorded, without recording it")
    args = ap.parse_args(argv)

    archive_root = pathlib.Path(args.archive_root)
    archive = GazetteArchive(archive_root)

    held: dict[str, str] = {}
    for entry in archive.entries():
        if entry.sha256:
            held.setdefault(entry.sha256, entry.gazette_id)

    recorded = 0
    for url in candidate_urls():
        try:
            body = get(url)
        except Exception as exc:  # noqa: BLE001
            print("[INFO] %s unreachable: %s" % (url.rsplit("/", 1)[-1][:40], exc))
            continue
        digest = hashlib.sha256(body).hexdigest()
        gazette = held.get(digest)
        if not gazette:
            print("[INFO] %s serves a document this archive does not hold; skipped"
                  % url.rsplit("/", 1)[-1][:40])
            continue
        stamp = stamp_for(gazette, archive_root)
        if args.dry_run:
            print("[DRY] would record %s -> %s (資料更新 %s)"
                  % (gazette, url.rsplit("/", 1)[-1][:40], stamp or "—"))
            continue
        entry = archive.record_publisher_url(gazette, url, digest,
                                             publisher_stamp=stamp)
        print("[INFO] recorded %s -> %s (資料更新 %s)"
              % (gazette, entry.publisher_url.rsplit("/", 1)[-1][:40], stamp or "—"))
        recorded += 1

    print("[INFO] %d URL(s) recorded" % recorded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
