"""Baseline the six silent failures in no-silent-data-loss, task 0.1.

Run before any fix, so each failure is shown to have been caught rather than merely
asserted gone afterwards. Re-run after implementing; every line should then report a
caught or non-failing state.

    python scripts/baseline_silent_failures.py
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

DATA = ROOT / "viewer" / "projects.data.js"
APP = ROOT / "viewer" / "app.js"
INDEX = ROOT / "viewer" / "index.html"
GAZETTE = pathlib.Path(r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf")


def load_doc() -> dict:
    if not DATA.exists():
        print("  projects.data.js not emitted; run a pipeline first")
        return {}
    text = DATA.read_text(encoding="utf-8")
    return json.loads(text[len("window.PROJECTS = "):].rstrip().rstrip(";"))


def line(label: str, value, note: str = "") -> None:
    print(f"  {label:<52} {value}{('  — ' + note) if note else ''}")


print("=" * 96)
print("BASELINE — no-silent-data-loss (task 0.1)")
print("=" * 96)

# --- 1. emission dropped portal-derived fields -------------------------------
doc = load_doc()
projects = doc.get("projects", [])
nodes = [n for p in projects for n in p["nodes"]]

empty_links = [p for p in projects if not (p.get("links") or {})]
no_node_links = [n for n in nodes if "links" not in n]
no_impl_node = [n for n in nodes if "implementation" not in n]
no_impl_proj = [p for p in projects if "implementation" not in p]

print("\n[1] emission of link-derived fields")
line("projects in dataset", len(projects))
line("projects with an EMPTY link set", len(empty_links))
line("approvals carrying no link", len(no_node_links), f"of {len(nodes)}")
line("approvals with no implementation snapshot", len(no_impl_node), f"of {len(nodes)}")
line("projects with no implementation object", len(no_impl_proj))
line("=> emitted dataset is conforming?", "no" if empty_links else "yes")

# --- 2. viewer blanked the pane ---------------------------------------------
print("\n[2] viewer render path")
app = APP.read_text(encoding="utf-8")
m = re.search(r"function renderDetail\b", app)
start = m.start() if m else 0
nxt = re.search(r"^function \w+", app[start + 10:], re.M)
body = app[start:start + 10 + (nxt.start() if nxt else 20000)]
unguarded = [mm.group(0) for mm in re.finditer(r"\bn\.links\.", body)]
line("unguarded n.links reads in the detail path", len(unguarded))
line("=> can one record blank the pane?", "yes" if unguarded else "no")
line("approvals lacking that field", len(no_node_links))

# --- 3. viewer header label --------------------------------------------------
print("\n[3] viewer header label")
html = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
line("header renders 統計至?", "統計至" in app)
line("header template", "` · ${published_date}`" if "` · ${window.PROJECTS.published_date" in app else "?")
line("=> date distinguishable from a generation stamp?", "no" if "統計至" not in app else "yes")

# --- 4. coverage guard cannot see a total re-key -----------------------------
print("\n[4] coverage guard vs a total re-key")
src = (ROOT / "urtpe" / "coverage.py").read_text(encoding="utf-8")
intersect_only = "set(before) & set(after)" in src
raises_on_rekey = bool(re.search(r'if d\[.total_rekey.\]', src))
reports_rekey = bool(re.search(r'"total_rekey"\s*:', src))
line("regressions computed over the intersection", "yes" if intersect_only else "no")
line("diff reports a total_rekey outcome", "yes" if reports_rekey else "no")
line("guard acts on a total re-key", "yes" if raises_on_rekey else "no")
line("=> can a total re-key pass the guard?",
     "yes" if intersect_only and not raises_on_rekey else "no")

# --- 5. --links stays advisory (D5) -----------------------------------------
print("\n[5] --links policy")
flow = ROOT / "docs" / "cli_flow_v2.md"
recmd = ""
if flow.exists():
    for ln in flow.read_text(encoding="utf-8").split("\n"):
        if "`--links`" in ln:
            recmd = ln.strip()
            break
line("cli_flow_v2.md describes --links as",
     "recommended" if "recommended" in recmd else "required" if recmd else "not documented")
try:
    from urtpe.emission import emission_faults, emission_partial
    import json as _json
    _doc = load_doc()
    _faults = emission_faults(_doc.get("projects", [])) if _doc else []
    _notes = emission_partial(_doc.get("projects", [])) if _doc else []
    line("emission fault when no link data is present", "reported" if _faults else "silent")
    line("partial coverage reported as a count", "yes" if _notes else "no")
except Exception as exc:  # the check not existing is itself the finding
    line("emission check present", f"NO — {exc}")
line("=> default path covered by a check?",
     "yes" if _faults == [] and _notes else "no",
     "advisory by design (D5); the guard is what covers it")

# --- 6. completable truncated cells excluded --------------------------------
print("\n[6] publisher-truncated cells")
if GAZETTE.exists():
    from urtpe.archive import GazetteArchive
    from urtpe import corpus as corpus_mod
    from urtpe.extract import extract_pdf_with_faults, gazette_id_for

    # the completion corpus matters here: without it the reader cannot complete 編號
    # 1198, so the baseline must exercise the same path the pipeline does
    corpus = []
    try:
        arch = GazetteArchive()
        root = pathlib.Path(arch.root)
        seen, members = set(), []
        for e in arch.entries():
            fp = root / e.filename
            if e.filename in seen or not fp.exists():
                continue
            seen.add(e.filename)
            members.append((e.published_date or e.gazette_id, fp))
        corpus = corpus_mod.build_corpus(
            members, exclude=str(gazette_id_for(str(GAZETTE))),
            cache_dir=ROOT / ".corpus_cache")
    except Exception as exc:
        line("completion corpus", f"unavailable ({exc})")

    recs, faults = extract_pdf_with_faults(str(GAZETTE), corpus=corpus)
    line("records emitted", len(recs))
    line("records excluded as source-truncated", len(faults),
         ", ".join(f.recno for f in faults))
    line("records completed from another approval",
         sum(1 for r in recs if str(r.get("recno")) == "1198"),
         "(編號 1198; 1210 prefix-matches and is refused on the count)")
else:
    line("gazette not found", str(GAZETTE))

print()
print("=" * 96)
print("Expected end state: items 1, 2, 3 and 4 read 'no' for their '=>' line (each")
print("failure is now caught), and item 5 reads 'yes' because --links stays advisory")
print("by design (D5) with the emission check covering the default path.")
print("=" * 96)
