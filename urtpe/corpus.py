"""Build a candidate corpus for bounded completion of truncated 地號 cells.

A truncated cell can only be completed from another approval of the same unit printed
elsewhere in the corpus. Scanning the archive for those candidates costs a full read per
gazette, so the result is cached outside the working tree and keyed on the member set —
a rebuild should not re-read every archive to notice one cell needs completing.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Iterable, Sequence

from urtpe.extract import RECNO_RE, _clean_cell, _section_token, parcel_token_count

CACHE_VERSION = 2


def _flat(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()


def scan_gazette(path: Path, gazette_id: str) -> list[dict]:
    """Every data row's land cell, as a completion candidate."""
    import pymupdf

    out: list[dict] = []
    doc = pymupdf.open(str(path))
    try:
        for page in doc:
            for table in page.find_tables(strategy="lines").tables:
                for row in table.extract():
                    if len(row) < 5:
                        continue
                    recno = _flat(row[0])
                    if not RECNO_RE.match(recno):
                        continue
                    land = _clean_cell(row[4])
                    if not land:
                        continue
                    m = re.match(r"^臺北市([^區]{1,4}區)", land)
                    out.append({
                        "gazette_id": gazette_id,
                        "recno": recno,
                        "land": land,
                        "district": m.group(1) if m else "",
                        "section": _section_token(land),
                        "parcel_count": parcel_token_count(land),
                    })
    finally:
        doc.close()
    return out


def _key(members: Sequence[tuple[str, Path]]) -> str:
    raw = "|".join(f"{gid}:{p.stat().st_size}" for gid, p in sorted(members))
    return hashlib.sha256(f"v{CACHE_VERSION}|{raw}".encode("utf-8")).hexdigest()[:16]


def build_corpus(members: Iterable[tuple[str, Path]], *, exclude: str = "",
                 cache_dir: Path | None = None,
                 ) -> list[dict]:
    """Candidates from every archived gazette except the one being read.

    ``members`` yields (gazette_id, path). Cached under ``cache_dir`` when given; the
    cache is keyed on the member set, so a changed archive is rescanned.
    """
    selected = [(gid, Path(p)) for gid, p in members
                if gid != exclude and Path(p).exists()]
    if not selected:
        return []

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = cache_dir / f"corpus-{_key(selected)}.json"
        if cache.exists():
            try:
                payload = json.loads(cache.read_text(encoding="utf-8"))
                if payload.get("version") == CACHE_VERSION:
                    return payload["candidates"]
            except (OSError, ValueError, KeyError):
                pass  # a corrupt cache is a miss, not a failure

    candidates: list[dict] = []
    for gid, path in selected:
        candidates.extend(scan_gazette(path, gid))

    if cache_dir is not None:
        try:
            cache.write_text(json.dumps(
                {"version": CACHE_VERSION, "candidates": candidates},
                ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass  # caching is an optimisation, never a precondition
    return candidates
