"""Regenerate the release-diff report, commit it, and publish it.

The third action of the `urtpe-poll` scheduled task, after the two pollers.
A new gazette is archived by the poller; this step makes the report that
describes it reach the site, so the published page is never a version behind
the archive it describes.

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

A failed push is reported as a failure, not swallowed. The committed report
is then ahead of the served one, which `scripts/check_deploy.py` reports as
stale — visible rather than silent.

    python scripts/publish_release_diff.py [--dry-run]

Exit codes: 0 published (or nothing to publish), 1 the push failed, 2 the
working tree is not in a state to publish from.
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
OWNED_PATHS = ["docs/release-diff.html"]
# The generator's own source. A working-tree change here would change what
# "regenerate" means, so the step stops rather than publishing a report
# produced by an uncommitted generator.
GENERATOR_PATHS = ["scripts/release_diff.py", "scripts/release_diff_report.py"]


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


def regenerate() -> bool:
    """Rebuild the report. Returns whether the file changed.

    The comparison ignores the generation timestamp, which the report carries
    in its header and which changes on every run. Without that, the step would
    commit a new blob every week even when no release changed, and the
    repository's history would fill with reports that differ only in a date
    — churning the published page for nothing.

    The timestamp is restored afterwards, so the committed report keeps the
    moment it was actually built.
    """
    before = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    before_stamp = _generation_stamp(before)
    proc = run(sys.executable, str(ROOT / "scripts" / "release_diff_report.py"))
    if proc.returncode != 0:
        raise PublishError(
            "the report generator failed (exit %d):\n%s"
            % (proc.returncode, proc.stderr.strip()[-2000:]))
    after = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    if _strip_stamp(before) == _strip_stamp(after):
        # Nothing but the timestamp moved. Put the committed timestamp back so
        # the file on disk stays byte-identical to the committed one.
        if before and after != before:
            REPORT.write_text(before, encoding="utf-8")
        return False
    return True


_STAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00)")


def _generation_stamp(text: str) -> str:
    m = _STAMP_RE.search(text)
    return m.group(1) if m else ""


def _strip_stamp(text: str) -> str:
    return _STAMP_RE.sub("<stamp>", text)


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
    proc = git("add", "--", *OWNED_PATHS)
    if proc.returncode != 0:
        raise PublishError("git add failed: %s" % proc.stderr.strip())
    staged = git("diff", "--cached", "--name-only", "--", *OWNED_PATHS).stdout.split()
    if not staged:
        return False
    proc = git("commit", "-m", message, "--", *OWNED_PATHS)
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
    except PublishError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 2

    if not changed:
        print("[INFO] the report is unchanged; nothing to publish")
        return 0

    print("[INFO] the report changed")

    if args.dry_run:
        print("[INFO] dry run: not committing, not pushing")
        return 0

    try:
        made = commit("docs: regenerate the release-diff report")
        if not made:
            print("[INFO] nothing staged; nothing to publish")
            return 0
        print("[INFO] committed")
        push()
    except PublishError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 1

    print("[INFO] published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
