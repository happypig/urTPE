"""Verify an emission, apply bounded existing repairs, then update reports.

    python scripts/post_ingest_check.py [--check-only] [--root PATH]

No git command is run. The pipeline's exit codes remain refusals, never
transient failures to retry past.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.doc_measurements import DocSyncError, load_payload


class CheckFailure(RuntimeError):
    """A local check or a bounded repair failed."""


def _recnos(path: Path, column: str) -> list[int]:
    with path.open(encoding="utf-8", newline="") as fh:
        values = []
        for row in csv.DictReader(fh, delimiter="\t"):
            value = str(row.get(column) or "").strip()
            if not value.isdigit():
                raise CheckFailure(f"{path.name}: non-numeric {column}: {value!r}")
            values.append(int(value))
        return values


def emission_faults(root: Path | str) -> list[str]:
    """Check all five layers, including identity, not just record totals."""
    root = Path(root)
    faults: list[str] = []
    paths = [root / "data" / name for name in
             ("raw.tsv", "clean.tsv", "merged.tsv", "projects.json", "review_report.txt")]
    paths.append(root / "viewer" / "projects.data.js")
    for path in paths:
        if not path.is_file():
            faults.append(f"missing required file: {path}")
    if faults:
        return faults
    try:
        layers = {"raw.tsv": _recnos(root / "data" / "raw.tsv", "編號"),
                  "clean.tsv": _recnos(root / "data" / "clean.tsv", "recno"),
                  "merged.tsv": _recnos(root / "data" / "merged.tsv", "recno")}
        doc = load_payload(root / "data" / "projects.json")
        viewer = load_payload(root / "viewer" / "projects.data.js")
    except (OSError, ValueError, KeyError, CheckFailure, DocSyncError) as exc:
        return [f"cannot read projects.json or its companion layers: {exc}"]
    layers["graph nodes"] = [n["recno"] for p in doc["projects"] for n in p.get("nodes") or []]
    for name, recnos in layers.items():
        dupes = sorted(k for k, v in Counter(recnos).items() if v > 1)
        if dupes:
            faults.append(f"{name}: duplicate recnos {dupes[:20]}")
    base = set(layers["raw.tsv"])
    for name, recnos in layers.items():
        other = set(recnos)
        if other != base:
            faults.append(f"{name}: recnos differ; missing {sorted(base - other)[:20]}, "
                          f"extra {sorted(other - base)[:20]}")
    if doc != viewer:
        faults.append("viewer projects.data.js differs from data/projects.json")
    projects = doc.get("projects") or []
    ids = [p.get("project_id") for p in projects]
    if len(set(ids)) != len(ids):
        faults.append("duplicate project_id in graph payload")
    counts = doc.get("counts") or {}
    if counts.get("records") != len(layers["graph nodes"]) or counts.get("projects") != len(projects):
        faults.append("graph counts disagree with its projects and nodes")
    for project in projects:
        recnos = {n.get("recno") for n in project.get("nodes") or []}
        if project.get("anchor_recno") not in recnos:
            faults.append(f"{project.get('project_id')}: anchor is not a node")
        for edge in project.get("edges") or []:
            if edge.get("from") not in recnos or edge.get("to") not in recnos:
                faults.append(f"{project.get('project_id')}: edge points outside its nodes")
    for recno in truncation_exclusions(root):
        faults.append(f"truncated: {recno}")
    return faults


def truncation_exclusions(root: Path | str) -> list[int]:
    """Read named residuals, not an assumed contiguous recno range."""
    report = (Path(root) / "data" / "review_report.txt").read_text(encoding="utf-8")
    lines = report.splitlines()
    exclusions: set[int] = set()
    for line in lines:
        if "publisher truncated" in line and "編號" in line:
            tail = line.split("編號", 1)[1]
            exclusions.update(int(v) for v in re.findall(r"\d+", tail))
    for index, line in enumerate(lines):
        match = re.match(r"INCOMPLETE:\s*(\d+)", line.strip())
        if match and int(match.group(1)) == 0:
            break
        if match:
            for item in lines[index + 1:]:
                recno = re.match(r"\s*編號\s+(\d+):", item)
                if recno:
                    exclusions.add(int(recno.group(1)))
            break
    return sorted(exclusions)


def archived_pdf_for(root: Path | str, archive_root: Path | str | None = None) -> Path:
    from urtpe.archive import DEFAULT_ARCHIVE_ROOT, GazetteArchive
    archive = GazetteArchive(archive_root or DEFAULT_ARCHIVE_ROOT)
    doc = load_payload(Path(root) / "viewer" / "projects.data.js")
    gazette_id = str(doc.get("published_date") or "")
    path = archive.path_for(gazette_id)
    archive.assert_matches_entry(path, gazette_id)
    return path


def latest_p168_snapshot(archive_root: Path | str) -> dict:
    """Use the poller's state and its content hash, never the newest mtime."""
    archive_root = Path(archive_root)
    try:
        state = json.loads((archive_root / "p168_state.json").read_text(encoding="utf-8"))
        digest = state["sha256"]
        checked_at = state["checked_at"]
        path = archive_root / "p168_snapshots" / f"p168-{digest[:16]}.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError) as exc:
        raise CheckFailure(f"cannot read the archived 168 snapshot: {exc}") from exc
    canonical = json.dumps(sorted(rows, key=lambda r: str(r.get("case_id") or "")),
                           ensure_ascii=False, sort_keys=True)
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != digest:
        raise CheckFailure(f"168 snapshot hash mismatch: {path.name}")
    if not rows or not all(row.get("case_id") for row in rows):
        raise CheckFailure("168 snapshot is empty or lacks case ids")
    return {"rows": rows, "sha256": digest, "checked_at": checked_at,
            "source": str(path)}


def refresh_p168_input(archive_root: Path | str, data_dir: Path | str) -> dict:
    selected = latest_p168_snapshot(archive_root)
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "p168_all.json").write_text(
        json.dumps(selected["rows"], ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {k: v for k, v in selected.items() if k != "rows"}
    (data_dir / "p168_all.meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return selected


def run_command(cmd: list[str], root: Path = ROOT) -> subprocess.CompletedProcess:
    print("+ " + " ".join(str(v) for v in cmd), flush=True)
    proc = subprocess.run(cmd, cwd=root, text=True, encoding="utf-8", errors="replace",
                          capture_output=True)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
    if proc.returncode:
        raise CheckFailure(f"command refused with exit {proc.returncode}: {' '.join(cmd)}")
    return proc


#: Tests that compare a fact GENERATED from the payload with the payload. `generate_reports`
#: writes that fact later in the same run, so the check before generation cannot require it: the
#: 2026-11-25 cycle stopped here, exit 1, because `openspec/config.yaml` still said 1,448
#: approvals while the new payload held 1,450 — a sentence this command was about to rewrite.
#: The check after generation, and `--check-only`, run every test, so a generation that left a
#: fact stale still fails. A test asserts each name exists (a5-cycle-emission-publication, D9).
GENERATED_FACT_TESTS = (
    "tests/test_deploy_target.py::test_the_recorded_record_count_matches_the_emitted_payload",
)


def run_local_checks(root: Path, runner=run_command, generated_facts: bool = True) -> list[str]:
    """Standing checks are failures by exit code AND by their success marker.

    `generated_facts=False` leaves out the tests in `GENERATED_FACT_TESTS`; it is for the checks
    that run BEFORE `generate_reports` and for nothing else."""
    left_out = [] if generated_facts else ["--deselect=" + node for node in GENERATED_FACT_TESTS]
    checks = [
        ([sys.executable, "-m", "pytest", "tests/test_deploy_target.py",
          "tests/test_viewer_consistency.py", "tests/test_about_page.py", "-q", *left_out],
         "passed"),
        (["node", "scripts/viewer_smoke.js"], "all checks passed"),
        ([sys.executable, "scripts/baseline_silent_failures.py"], "Expected end state"),
        ([sys.executable, "scripts/probe_three_coverage_proofs.py"],
         "the flag and the badge agree exactly"),
    ]
    for cmd, marker in checks:
        proc = runner(cmd, root=root)
        if marker not in proc.stdout:
            raise CheckFailure(f"check did not report its success marker: {' '.join(cmd)}")
    return []


def generate_reports(root: Path, runner=run_command) -> None:
    from urtpe.archive import DEFAULT_ARCHIVE_ROOT
    refresh_p168_input(DEFAULT_ARCHIVE_ROOT, root / "data")
    for script in ("sync_etl_process.py", "sync_domain_model.py",
                   "release_diff_report.py", "coverage_report.py"):
        runner([sys.executable, "scripts/" + script], root=root)


def run(argv=None, *, validator=None, command_runner=run_command) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if validator is None:
        def validator(path, generated_facts=True):
            return emission_faults(path) + run_local_checks(path, command_runner, generated_facts)
    takes_flag = "generated_facts" in inspect.signature(validator).parameters

    def validate(path, generated_facts=True):
        """A validator injected by a test may take only the root; the real one takes the flag
        too. Decided by its signature: a `TypeError` raised INSIDE a validator must not be
        mistaken for a missing parameter."""
        if takes_flag:
            return validator(path, generated_facts=generated_facts)
        return validator(path)

    try:
        # Before generation the generated-fact tests are left out (see GENERATED_FACT_TESTS);
        # `--check-only` generates nothing, so it runs every test.
        initial = validate(root, generated_facts=bool(args.check_only))
        if args.check_only:
            for script in ("sync_etl_process.py", "sync_domain_model.py"):
                command_runner([sys.executable, "scripts/" + script, "--check"], root=root)
            if initial:
                raise CheckFailure("; ".join(initial))
            print("[OK] all local post-ingest checks passed; no writes performed")
            return 0
        if initial:
            truncations = [v for v in initial if v.startswith("truncated: ")]
            if len(truncations) == len(initial):
                pdf = archived_pdf_for(root)
                command_runner([sys.executable, "-m", "urtpe.cli", str(pdf),
                                "-o", "data", "--viewer", "viewer", "--links",
                                "--recover-truncated"], root=root)
            elif all(v.startswith("viewer ") for v in initial):
                command_runner([sys.executable, "-m", "urtpe.cli", "--from-js",
                                "viewer/projects.data.js", "-o", "data", "--viewer",
                                "viewer", "--links"], root=root)
            else:
                raise CheckFailure("; ".join(initial))
        final = validate(root, generated_facts=False)
        if final:
            raise CheckFailure("post-repair checks failed: " + "; ".join(final))
        generate_reports(root, command_runner)
        # Generation itself updates the configured count and documentation.
        # Prove the final bytes, not merely the pre-generation state: EVERY test runs here,
        # the generated-fact ones included, so a generation that left a fact stale fails.
        final = validate(root, generated_facts=True)
        if final:
            raise CheckFailure("post-generation checks failed: " + "; ".join(final))
        print("[OK] verified; documentation and dependent reports updated. No commit or push performed.")
        return 0
    except (CheckFailure, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
