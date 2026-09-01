"""Curated-exception resolve flow (category 1) — §6.14 of the operations log.

Pure helpers are unit-tested (tests/test_curated_resolve.py); the live runner
probes the Taipei platform raw (guard-drops captured) and the national portal
by title, verifies identity independently of the automated matcher, and attaches
portal-verified cases with `DiscoveryResult(**data)` round-trip validation.

Usage:
    python scripts/curated_resolve.py            # diagnose + resolve all unresolved
    python scripts/curated_resolve.py --pid X    # single project
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from urtpe.cleanse import SECTION_RE
from urtpe.links import (
    DiscoveryResult,
    SEARCH_URL,
    TAIPEI_SEARCH_API,
    TAIPEI_TOP_API,
    VIEW_URL_BASE,
    _post_taipei_api,
    extract_case_ids_from_view,
    fetch_taipei_milestones_api,
    fetch_url,
)

CACHE = Path("data/.link_cache")
DELAY = 1.0
PARCEL_RE = re.compile(r"(\d+(?:-\d+)?)地號")
SECTION_TOKEN_RE = re.compile(r"([\u4e00-\u9fff]{1,6}?(?:新村|整宅|國宅|大樓|市場))")


# ── pure helpers (unit-tested) ────────────────────────────────────────────────

def classify_failure(d: dict) -> str:
    if "timed out" in (d.get("error") or ""):
        return "timeout"
    if d.get("search_rejected"):
        return "guard-dropped"
    if not d.get("city_case_ids"):
        return "blank-search"
    return "cases-attached"


def _pid_parts(pid: str) -> tuple[str, str]:
    """(section, parcel) from a project_id like 萬華區-華中段一小段-247地號等26筆.
    Unparseable-count ids (…-地號等?筆) return an empty parcel."""
    m = re.search("[\u4e00-\u9fa5]{2,4}區-([^-]+)-([^*]*)地號", pid)
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def derive_queries(project: dict, disc: dict) -> list[tuple[str, str]]:
    """Alternate (section, parcel) queries, excluding the original one:
    - parcels enumerated in the 案名 (anchor-parcel drift: 201-2、352 vs 247)
    - section tokens in the 案名 (section drift: 木新路三段 vs 實踐段二小段)"""
    name = re.sub(r"\s+", "", project.get("name", ""))
    pid = project.get("project_id", "")
    pid_section, pid_parcel = _pid_parts(pid)

    parcels: list[str] = []
    for grp in re.findall(r"((?:\d+(?:-\d+)?)(?:、\d+(?:-\d+)?)*)地號", name):
        for tk in grp.split("、"):
            if tk and tk not in parcels:
                parcels.append(tk)
    if not parcels and pid_parcel:
        parcels = [pid_parcel]

    sections: list[str] = []
    if pid_section:
        sections.append(pid_section)
    for m in SECTION_RE.finditer(name):
        s = m.group(1).rsplit("區", 1)[-1]  # drop 案名 prefix up to the last 區
        if s not in sections:
            sections.append(s)

    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for s in sections:
        for pt in parcels:
            pair = (s, pt)
            if pair != (pid_section, pid_parcel) and pair not in seen:
                seen.add(pair)
                out.append(pair)
    return out


def identity_verdict(case_name: str, project_name: str, searched_parcel: str) -> str:
    """'parcel-in-name' (guard would pass) / 'token-match' (shared settlement/
    building proper noun) / 'none' (no identity evidence)."""
    if searched_parcel and searched_parcel in case_name:
        return "parcel-in-name"
    ptoks = set(SECTION_TOKEN_RE.findall(project_name))
    ctoks = set(SECTION_TOKEN_RE.findall(case_name))
    if ptoks & ctoks:
        return "token-match"
    return "none"


def attach_cases(d: dict, cases: list[dict]) -> None:
    """Attach portal-verified cases to a cache dict and resolve. Validates the
    result against DiscoveryResult (§6.10 poison-key hazard guard)."""
    new_ids = []
    for c in cases:
        cid = c["case_id"]
        new_ids.append(cid)
        if c.get("case_name"):
            d.setdefault("candidate_names", {})[cid] = c["case_name"]
        if c.get("milestones"):
            d.setdefault("case_milestones", {})[cid] = c["milestones"]
            ms_t = d.get("taipei_milestones") or {}
            ms_s = d.get("milestones_source") or {}
            for label, date in c["milestones"].items():
                ms_t.setdefault(label, date)
                ms_s.setdefault(label, cid)
            d["taipei_milestones"] = ms_t
            d["milestones_source"] = ms_s
        if c.get("implementation"):
            impl = d.get("implementation") or {}
            payload = dict(c["implementation"])
            payload.setdefault("case_id", cid)
            impl.setdefault(cid, payload)
            d["implementation"] = impl
    d["city_case_ids"] = sorted(set(d.get("city_case_ids") or []) | set(new_ids))
    d["status"] = "resolved"
    d["error"] = ""
    DiscoveryResult(**d)


def ms_source(milestones_source: dict) -> dict:
    return milestones_source


# ── live flow ────────────────────────────────────────────────────────────────

def raw_search(section: str, parcel: str) -> list[dict]:
    mono, _, suno = parcel.partition("-")
    body = _post_taipei_api(TAIPEI_SEARCH_API, {
        "qitem": "qland", "sectstr": section, "monobuf": mono, "sunobuf": suno or "0",
    })
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return []
    out = []
    for r in rows if isinstance(rows, list) else []:
        det = r.get("details", "")
        m = re.search(r"case_id=(\d+)", det)
        if m:
            out.append({"case_id": m.group(1), "case_name": r.get("case_name", ""),
                        "schedule": r.get("schedule", "")})
    return out


def national_title_search(query: str) -> list[str]:
    url = SEARCH_URL + "?" + __import__("urllib.parse", fromlist=["urlencode"]).urlencode(
        {"title": query, "city_id": "2"})
    html = fetch_url(url, None, True)
    time.sleep(1.0)
    return sorted(set(re.findall(r"/zh/urban/rebuild/view/(\d+)", html)))


def main() -> None:
    only = ""
    if "--pid" in sys.argv:
        only = sys.argv[sys.argv.index("--pid") + 1]
    js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
    data = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))
    report = []
    for p in data["projects"]:
        pid = p["project_id"]
        if only and pid != only:
            continue
        safe = re.sub(r"[^\w\-]", "_", pid)
        rf = CACHE / safe / "result.json"
        if not rf.is_file():
            continue
        d = json.loads(rf.read_text(encoding="utf-8"))
        if d.get("status") == "resolved":
            continue
        kind = classify_failure(d)
        print(f"== {pid} [{kind}]")
        if kind == "timeout":
            print("   skip (retry in calm window)")
            continue

        project_js = next(q for q in json.loads(
            Path("viewer/projects.data.js").read_text(encoding="utf-8").strip()
            [len("window.PROJECTS ="):].rstrip().rstrip(";"))["projects"]
            if q["project_id"] == pid)
        queries = derive_queries(project_js, d)
        cases: dict[str, dict] = {}
        for section, parcel in queries:
            hits = raw_search(section, parcel)
            time.sleep(DELAY)
            for h in hits:
                v = identity_verdict(h["case_name"], project_js.get("name", ""), parcel)
                print(f"   probe {section}/{parcel}: {h['case_id']} [{v}] {h['case_name'][:40]}")
                if v in ("parcel-in-name", "token-match"):
                    cases[h["case_id"]] = h

        # twur'd: portal cross-ref identity (the case_ids the page already links)
        if d.get("twur_view_id"):
            try:
                vhtml = fetch_url(f"{VIEW_URL_BASE}{d['twur_view_id']}", None, True) \
                    if not (CACHE / safe / "view.html").is_file() else \
                    (CACHE / safe / "view.html").read_text(encoding="utf-8", errors="replace")
                time.sleep(1.0)
                for cid in extract_case_ids_from_view(vhtml):
                    if cid not in cases:
                        cases[cid] = {"case_id": cid, "case_name": "", "schedule": ""}
                        print(f"   view-page cross-ref: {cid}")
            except Exception as e:
                print(f"   view fetch failed: {e}")

        if not cases:
            print("   → no verified candidates; needs human lookup")
            continue

        payload = []
        for cid, meta in cases.items():
            miles = fetch_taipei_milestones_api(cid)
            time.sleep(DELAY)
            top = json.loads(_post_taipei_api(TAIPEI_TOP_API, {"case_id": cid}))
            time.sleep(DELAY)
            row = top[0] if isinstance(top, list) and top else (top if isinstance(top, dict) else {})
            name = str(row.get("CASE_NAME", "")).strip() or meta.get("case_name", "")
            payload.append({"case_id": cid, "case_name": name, "milestones": miles})
        attach_cases(d, payload)
        rf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   → RESOLVED ({len(payload)} cases)")


if __name__ == "__main__":
    main()
