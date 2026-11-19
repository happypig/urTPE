"""Pure measurements and marked-region rendering for documentation sync.

Only elements carrying data-doc-field are mutable. Historical prose elsewhere
in a document is never selected by a number or a date.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_MEASUREMENT_KEYS = (
    "projects_rendered", "dated_approvals_rendered", "inverted_pairs",
    "inverted_projects", "construction_events", "no_provenance",
    "source_case_missing", "unique_anchors", "ambiguous_markers",
    "ambiguous_resolvable", "ambiguous_unresolved", "national_occupancy_units",
    "occupancy_same_day",
)


class DocSyncError(RuntimeError):
    """A measurement or destination is not safe to update."""


def load_payload(path: Path | str) -> dict:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".js":
        match = re.fullmatch(r"\s*window\.PROJECTS\s*=\s*(\{.*\})\s*;?\s*", text, re.S)
        if not match:
            raise DocSyncError(f"invalid viewer payload: {path}")
        text = match.group(1)
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise DocSyncError(f"invalid payload {path}: {exc}") from exc
    if not isinstance(doc.get("projects"), list):
        raise DocSyncError(f"payload has no projects list: {path}")
    return doc


def measure_etl(doc: dict, root: Path) -> dict:
    from urtpe.ledger import CorrectionLedger

    projects = doc.get("projects") or []
    nodes = [n for p in projects for n in (p.get("nodes") or [])]
    dates = sorted(str(n.get("date") or "") for n in nodes if n.get("date"))
    multi = [p for p in projects if len(p.get("nodes") or []) > 1]
    repeat = sum(len(p.get("nodes") or []) - 1 for p in multi)
    flagged = sum(bool(n.get("review_flags")) for n in nodes)
    flagged_projects = sum(any(n.get("review_flags") for n in p.get("nodes") or [])
                           for p in projects)
    report = root / "data" / "review_report.txt"
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    applied = re.search(r"^manual corrections applied:\s*(\d+)", text, re.M)
    # A --from-js rebuild keeps recovered nodes but has no fresh PDF ledger
    # outcome. Read the live append-only ledger in that case, not zero.
    corrections = int(applied.group(1)) if applied else len(CorrectionLedger().entries())
    cache = root / "data" / ".link_cache"
    cache_dirs = sum(p.is_dir() for p in cache.iterdir()) if cache.is_dir() else 0
    links = root / "urtpe" / "links.py"
    return {
        "published_date": doc.get("published_date") or "",
        "generated_at": doc.get("generated_at") or "",
        "projects": len(projects), "records": len(nodes),
        "date_first": dates[0] if dates else "", "date_last": dates[-1] if dates else "",
        "flagged_nodes": flagged, "flagged_projects": flagged_projects,
        "corrections": corrections,
        "recovered": sum(bool(n.get("recovery")) for n in nodes),
        "repeat_records": repeat,
        "repeat_percent": round(100 * repeat / len(nodes)) if nodes else 0,
        "count_disagreements": count_disagreements(nodes),
        "cache_dirs": cache_dirs,
        "links_lines": len(links.read_text(encoding="utf-8").splitlines()) if links.exists() else 0,
        "measurement_date": dt.date.today().isoformat(),
    }


def count_disagreements(nodes: list[dict]) -> int:
    """All complete published cells whose visible count differs from the 案名."""
    from urtpe.extract import (closing_phrase_present, declared_parcel_count,
                               parcel_token_count)
    count = 0
    for node in nodes:
        land = node.get("land") or ""
        declared = declared_parcel_count(node.get("name_raw") or "")
        if (declared is not None and closing_phrase_present(land)
                and parcel_token_count(land) != declared):
            count += 1
    return count


def replace_fields(source: str, fields: dict[str, str]) -> tuple[str, list[str]]:
    """Replace one element's inner HTML for each field, with no HTML dependency."""
    names = re.findall(r'\bdata-doc-field="([A-Za-z0-9_-]+)"', source)
    counts = {name: names.count(name) for name in set(names)}
    for name in fields:
        if counts.get(name, 0) == 0:
            raise DocSyncError(f"missing documentation marker: {name}")
        if counts[name] > 1:
            raise DocSyncError(f"duplicate documentation marker: {name}")
    changed = []
    for name, value in fields.items():
        pattern = re.compile(
            r'(<(?P<tag>[A-Za-z][A-Za-z0-9]*)\b[^>]*\bdata-doc-field="'
            + re.escape(name) + r'"[^>]*>)(?P<body>.*?)(?P<close></(?P=tag)>)', re.S)
        match = pattern.search(source)
        if not match:
            raise DocSyncError(f"unreadable documentation marker: {name}")
        if match.group("body") != value:
            source = source[:match.start("body")] + value + source[match.end("body"):]
            changed.append(name)
    return source, sorted(changed)


def write_or_check(path: Path | str, fields: dict[str, str], check: bool = False) -> list[str]:
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    rendered, changed = replace_fields(source, fields)
    if check:
        for name in changed:
            print(f"STALE {path.name}: {name}", file=sys.stderr)
    elif changed:
        path.write_text(rendered, encoding="utf-8")
    return changed


def parse_node_measurements(text: str) -> dict[str, int]:
    try:
        values = json.loads(text)
    except ValueError as exc:
        raise DocSyncError("the viewer measurement did not return JSON") from exc
    if not isinstance(values, dict):
        raise DocSyncError("the viewer measurement is not an object")
    missing = [key for key in NODE_MEASUREMENT_KEYS if key not in values]
    if missing:
        raise DocSyncError("viewer measurement missing: " + ", ".join(missing))
    for key in NODE_MEASUREMENT_KEYS:
        if not isinstance(values[key], int) or isinstance(values[key], bool) or values[key] < 0:
            raise DocSyncError(f"viewer measurement {key} is not a non-negative integer")
    return values


def measure_viewer(root: Path = ROOT) -> dict[str, int]:
    proc = subprocess.run(
        ["node", str(root / "scripts" / "probe_tab1_numbers.js"), "--json"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise DocSyncError("viewer measurement failed: " + (proc.stderr or proc.stdout)[-1600:])
    return parse_node_measurements(proc.stdout)


def sync_config_text(source: str, doc: dict) -> str:
    m = measure_etl(doc, ROOT)
    pattern = re.compile(
        r"(?P<a>list \(臺北市都市更新核定案件一覽表, )[\d,]+ approvals as emitted from the \d{4}-\d{2}-\d{2}\n"
        r"(?P<indent>\s*)gazette, dated \d{4}-\d{2}-\d{2}–\d{4}-\d{2}-\d{2},\n"
        r"(?P=indent)統計至 \d{4}-\d{2}-\d{2}")
    replacement = (rf"\g<a>{m['records']:,} approvals as emitted from the {m['published_date']}" + "\n"
                   + rf"\g<indent>gazette, dated {m['date_first']}–{m['date_last']}," + "\n"
                   + rf"\g<indent>統計至 {m['published_date']}")
    result, n = pattern.subn(replacement, source, count=1)
    if n != 1:
        raise DocSyncError("the current-dataset sentence in openspec/config.yaml is missing")
    return result


def sync_config(doc: dict, root: Path = ROOT) -> bool:
    path = root / "openspec" / "config.yaml"
    before = path.read_text(encoding="utf-8")
    after = sync_config_text(before, doc)
    if after != before:
        path.write_text(after, encoding="utf-8")
        return True
    return False
