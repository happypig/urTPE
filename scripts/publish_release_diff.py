"""Regenerate the release-diff report, commit it, and publish it.

The PDF cycle (`scripts/run_cycle.py`, scheduled as `urtpe-cycle`) runs this step
last, after a finished ingest. The weekly `urtpe-poll` task that used to run it is
disabled. A person may run it by hand, for example to retry a failed push. This
step makes the pages that describe a new gazette reach the site, so the published
pages are never a version behind the data they describe.

It does **not** ingest. The pipeline's single-writer lock is not needed and
not taken, because nothing under `data/` or `viewer/` is written: the report
is a separate artefact derived from the archive, and the archive is read-only
here. The `gazette-cadence` guarantee — an unattended run never rewrites the
emitted dataset — is preserved.

The commit is **path-limited**. The working tree routinely carries changes from
other sessions (measured 2026-11-06: `urtpe/cli.py`, `urtpe/emission.py` and
`urtpe/tripwire.py` modified by a concurrent session), and a scheduled step
that swept them into a commit would publish work nobody had finished. This
step names the paths it owns on the commit command itself, not only on the
`git add`: a `git commit` without a path limit takes the whole index, and the
index holds whatever another session has staged (measured 2026-11-09).

The step owns four generated pages and no other path: the release-diff report,
the coverage report, the domain model and the ETL page. It publishes them as ONE
set, and only when the report differs from the committed report (ignoring its
generation stamp) or the payload's project or record count differs from the
committed payload's. When neither does, it commits nothing and leaves the other
pages as it found them: a date-only difference may belong to an emission that is
still waiting for review. The other three pages are published as they are in the
working tree, so run `post_ingest_check.py` first (the PDF cycle does). The step
reads the payload's counts and never writes the payload.

A failed push is reported as a failure, not swallowed. The committed report
is then ahead of the served one, which `scripts/check_deploy.py` reports as
stale — visible rather than silent.

    python scripts/publish_release_diff.py [--dry-run]

Exit codes: 0 published (or nothing to publish), 1 the push failed, 2 the
working tree is not in a state to publish from. A retry after a failed push
finds the commit already made, and pushes it.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

REPORT = ROOT / "docs" / "release-diff.html"
# The paths this step owns. Nothing else is ever staged by it.
OWNED_PATHS = ["docs/release-diff.html", "docs/coverage-report.html",
               "docs/domain-model.html", "docs/etl_process.html"]
# The generator's own source. A working-tree change here would change what
# "regenerate" means, so the step stops rather than publishing a report
# produced by an uncommitted generator.
GENERATOR_PATHS = ["scripts/release_diff.py", "scripts/release_diff_report.py",
                   "scripts/coverage_report.py", "scripts/coverage_checks.py",
                   "scripts/sync_domain_model.py", "scripts/sync_etl_process.py",
                   "scripts/doc_measurements.py"]


class PublishError(RuntimeError):
    """The step could not publish."""


def run(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args), cwd=str(cwd or ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace")


def git(*args: str) -> subprocess.CompletedProcess:
    return run("git", *args)


def dirty_paths() -> list[str]:
    """The tracked paths with uncommitted changes."""
    proc = git("status", "--porcelain")
    out = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        # "XY path" — the path starts after the two status columns.
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        out.append(path.strip('"'))
    return out


def check_tree() -> None:
    """Refuse to publish when the tree is not in a state to publish from."""
    dirty = dirty_paths()
    conflicts = [p for p in dirty if p in GENERATOR_PATHS]
    if conflicts:
        raise PublishError(
            "the report's generator has uncommitted changes (%s); "
            "publishing now would produce a report no commit explains. "
            "Commit or stash them first." % ", ".join(conflicts))


def committed_report() -> str:
    """The report as HEAD holds it, or "" when HEAD has none."""
    proc = git("show", "HEAD:" + OWNED_PATHS[0])
    return proc.stdout if proc.returncode == 0 else ""


def regenerate() -> bool:
    """Rebuild the report. Returns whether it differs from the COMMITTED report.

    "Changed" means: differs from what HEAD holds, ignoring the generation
    timestamp, which the report carries in its header and which changes on
    every run. Without the stamp rule the step would commit a new blob every
    week even when no release changed, and the repository's history would fill
    with reports that differ only in a date.

    It used to mean: differs from the copy on disk before this run. That broke
    when something else had already regenerated the report. `post_ingest_check.py`
    does (and so does the PDF cycle, which runs it first): the copy on disk was
    then the new report, the comparison saw only a timestamp, and the step said
    "nothing to publish" while the committed report was a gazette behind
    (measured 2026-11-23). A person who ran the check and then this step by hand
    got the same answer.

    When nothing but the timestamp differs from the committed report, the
    committed copy is put back, so the file on disk stays byte-identical to the
    committed one and the tree stays clean.
    """
    proc = run(sys.executable, str(ROOT / "scripts" / "release_diff_report.py"))
    if proc.returncode != 0:
        raise PublishError(
            "the report generator failed (exit %d):\n%s"
            % (proc.returncode, proc.stderr.strip()[-2000:]))
    after = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    committed = committed_report()
    if committed and _strip_stamp(committed) == _strip_stamp(after):
        if after != committed:
            REPORT.write_text(committed, encoding="utf-8")
        return False
    return True


_STAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00)")


def _generation_stamp(text: str) -> str:
    m = _STAMP_RE.search(text)
    return m.group(1) if m else ""


def _strip_stamp(text: str) -> str:
    return _STAMP_RE.sub("<stamp>", text)


def _payload_path() -> pathlib.Path:
    return ROOT / "viewer" / "projects.data.js"


_COUNTS_RE = re.compile(r'"counts"\s*:\s*\{\s*"projects"\s*:\s*(\d+)\s*,\s*"records"\s*:\s*(\d+)')


def payload_counts(text: str) -> tuple[int, int]:
    """(projects, records) from the head of a payload. Unreadable counts are an error:
    the step never guesses whether the dataset changed."""
    m = _COUNTS_RE.search(text[:8192])
    if not m:
        raise PublishError("the payload carries no readable counts; refusing to guess "
                           "whether the dataset changed")
    return int(m.group(1)), int(m.group(2))


def counts_changed() -> bool:
    """Whether the payload's project or record count differs from the committed payload's.

    A payload absent from both the commit and the working tree gives no trigger. A payload
    present in only one of them is a change. A payload present but unreadable is an error."""
    path = _payload_path()
    work = path.read_text(encoding="utf-8") if path.exists() else None
    proc = git("show", "HEAD:viewer/projects.data.js")
    head = proc.stdout if proc.returncode == 0 else None
    if work is None and head is None:
        return False
    if work is None or head is None:
        return True
    return payload_counts(work) != payload_counts(head)


def stageable_paths() -> list[str]:
    """The owned pages that exist or are tracked. `git add` fails on a path that is neither."""
    tracked = set(git("ls-files", "--", *OWNED_PATHS).stdout.split())
    return [p for p in OWNED_PATHS if (ROOT / p).exists() or p in tracked]


def unpushed_owned() -> bool:
    """Whether a commit that touches an owned page is ahead of `origin/main`. After a failed
    push the commit already exists, so a retry has nothing new to commit but must still push."""
    proc = git("rev-list", "origin/main..HEAD", "--", *OWNED_PATHS)
    return proc.returncode == 0 and bool(proc.stdout.split())


def commit(message: str) -> bool:
    """Commit the owned paths. Returns whether a commit was made.

    The commit is **path-limited**, not merely path-scoped in the `git add`.
    A `git commit` without a path limit takes everything in the index, and the
    index holds whatever another session has staged. Measured 2026-11-09: the
    step's commit carried `other_session_work.py` along with the report.

    Naming the paths on the commit command gives both properties the spec
    asks for: another session's file is neither committed nor discarded, and
    it stays staged for the session that staged it.
    """
    paths = stageable_paths()
    if not paths:
        return False
    proc = git("add", "--", *paths)
    if proc.returncode != 0:
        raise PublishError("git add failed: %s" % proc.stderr.strip())
    staged = git("diff", "--cached", "--name-only", "--", *paths).stdout.split()
    if not staged:
        return False
    proc = git("commit", "-m", message, "--", *paths)
    if proc.returncode != 0:
        raise PublishError("git commit failed: %s" % proc.stderr.strip())
    return True


def push() -> None:
    """Push to the branch Pages publishes from. Raises on failure.

    The exit code alone does not say the push landed. `git push origin main`
    pushes the `main` ref, so on a detached HEAD — where the commit the step
    made lives on HEAD and `main` has not moved — git answers "Everything
    up-to-date" and exits 0 while the remote keeps the old commit. Measured
    2026-11-09: the step printed "published" and exited 0, and the remote
    never moved.

    So the remote is asked afterwards whether it holds the commit. A push
    that did not land is a failure, whatever git said.
    """
    head = git("rev-parse", "HEAD").stdout.strip()
    proc = git("push", "origin", "main")
    if proc.returncode != 0:
        raise PublishError(
            "git push failed: %s\n"
            "The committed report is ahead of the served one; "
            "scripts/check_deploy.py will report it stale until the push lands."
            % (proc.stderr or proc.stdout).strip()[-2000:])
    remote = git("ls-remote", "origin", "refs/heads/main").stdout.split()
    if not remote or remote[0] != head:
        raise PublishError(
            "git push reported success but the remote does not hold the "
            "commit (%s).\n"
            "The committed report is ahead of the served one; "
            "scripts/check_deploy.py will report it stale until the push "
            "lands." % (remote[0] if remote else "no refs/heads/main"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="regenerate and report what would be published, "
                         "without committing or pushing")
    args = ap.parse_args(argv)

    try:
        check_tree()
        changed = regenerate()
        counts = counts_changed()
    except PublishError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 2

    triggered = changed or counts
    if changed:
        print("[INFO] the report changed")
    if counts:
        print("[INFO] the project or record count changed")

    if args.dry_run:
        if not triggered:
            print("[INFO] the report and the counts are unchanged; nothing to publish")
        print("[INFO] dry run: not committing, not pushing")
        return 0

    try:
        made = commit("docs: regenerate the release-diff report and the generated pages") if triggered else False
        if made:
            print("[INFO] committed")
        if made or unpushed_owned():
            if not made:
                print("[INFO] a commit of the pages is ahead of the remote; pushing it")
            push()
            print("[INFO] published")
            return 0
    except PublishError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 1

    print("[INFO] the report and the counts are unchanged; nothing to publish")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
