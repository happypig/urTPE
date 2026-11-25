"""Commit the emission of a finished ingest, and publish it.

The PDF cycle (`scripts/run_cycle.py`, scheduled as `urtpe-cycle`) runs this step after it has
recorded a gazette's hash as finished, and before `publish_release_diff.py`, so one push carries
the viewer's data and the four generated pages that describe it. A person may run it by hand,
for example to retry a failed push. openspec change a5-cycle-emission-publication; the user's
decision of 2026-11-23 reversed U-D2 ("generate and stop") for the emission.

It does **not** ingest and writes no file. It reads the payload's record count, runs `git`,
and nothing else: the emission was written by the ingest and checked by the cycle before this
step started. The coordinator's own git use stays read-only; the commit and the push belong to
this child command, as the pages' do to `publish_release_diff.py`.

The commit is **path-limited**, for the reason the pages publisher names (measured 2026-11-09):
a `git commit` without a path limit takes the whole index, and the index holds whatever another
session has staged. The step names its eight emission paths on the commit command itself, so
another session's staged file is neither committed nor discarded, and stays staged for them.

Two guards run before anything is committed:

- **The code is clean.** A tracked file under `urtpe/` or `scripts/` with an uncommitted change
  means the code that wrote the emission is not the code a commit would record, so the commit
  would be one no history explains. The dirty-tree check watches this before the ingest; this
  re-check closes the window between that check and now. Untracked files do not count.
- **The record count does not drop.** A payload with fewer records than the committed one is
  not published. The dataset's measured trajectory only grows (1,444, 1,448, 1,450 over
  2026-10-15, 2026-11-12, 2026-11-19), so a drop names a defect: a truncated gazette that was
  accepted, or a reconcile block that was missed. Equal and higher counts proceed. This is the
  one extra check the board left open; it is deliberately narrow, so a legitimate gazette is
  never blocked.

A failed push is reported as a failure, never swallowed, and a push is only believed after the
remote has been asked whether it holds the commit (`git push origin main` on a detached HEAD
says "Everything up-to-date" and exits 0 while the remote never moves).

    python scripts/publish_emission.py [--dry-run]

Exit codes: 0 published (or nothing to publish), 1 the push failed (a retry pushes the commit
that is already ahead), 2 the step is not in a state to publish from (uncommitted code, a count
that dropped, a count that cannot be read): a person decides.

Rollback of an emission that is already served: `git revert` its commit, push, and fix the cause.
The cycle never rewrites history, and it does not ingest a finished hash again.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The paths this step owns. Nothing else is ever staged by it. The dirty-tree check of the
# cycle (`urtpe.cycle.OWNED_PATHS`) must watch every one of them: a test asserts it does.
OWNED_PATHS = ["data/projects.json", "data/raw.tsv", "data/clean.tsv", "data/merged.tsv",
               "data/review_report.txt", "viewer/projects.data.js", "viewer/index.html",
               "viewer/dashboard.html"]
# The code an ingest runs. An uncommitted change here stops the step (see the module docstring).
CODE_PATHS = ["urtpe", "scripts"]
PAYLOAD = "viewer/projects.data.js"


class PublishError(RuntimeError):
    """The step could not publish: the state is not fit to publish from. Exit 2."""


class PushError(RuntimeError):
    """The push did not land. Exit 1."""


#: Seconds a git command that talks to the remote may take. Unattended, a push that is still
#: waiting after this is a credential problem, not a slow network.
GIT_NETWORK_TIMEOUT = 120
_NETWORK_GIT = {"push", "ls-remote", "fetch", "pull"}
#: Git Credential Manager would open a browser if the stored credential were revoked or expired.
#: Unattended, nobody answers it, so the step would wait. Refuse the prompt and fail fast.
_NO_PROMPT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}


def run(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    kwargs: dict = {}
    if args and args[0] == "git":
        kwargs["env"] = {**os.environ, **_NO_PROMPT_ENV}
        if len(args) > 1 and args[1] in _NETWORK_GIT:
            kwargs["timeout"] = GIT_NETWORK_TIMEOUT
    return subprocess.run(
        list(args), cwd=str(cwd or ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", **kwargs)


def git(*args: str) -> subprocess.CompletedProcess:
    return run("git", *args)


# --- the guards ----------------------------------------------------------------------------

def dirty_code() -> list[str]:
    """The TRACKED files under the code directories with uncommitted changes."""
    proc = git("status", "--porcelain", "--untracked-files=no", "--", *CODE_PATHS)
    out = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        out.append(path.strip('"'))
    return out


def check_code_clean() -> None:
    dirty = dirty_code()
    if dirty:
        raise PublishError(
            "the code that wrote the emission has uncommitted changes (%s); a commit now would "
            "record an emission that no commit explains. Commit or stash them first."
            % ", ".join(dirty))


_RECORDS_RE = re.compile(r'"counts"\s*:\s*\{[^}]*?"records"\s*:\s*(\d+)')
_PROJECTS_RE = re.compile(r'"counts"\s*:\s*\{[^}]*?"projects"\s*:\s*(\d+)')
_DATE_RE = re.compile(r'"published_date"\s*:\s*"(\d{4}-\d{2}-\d{2})"')


def payload_records(text: str) -> int:
    """The record count from the head of a payload. An unreadable count is an error: the step
    never guesses whether the dataset shrank."""
    m = _RECORDS_RE.search(text[:8192])
    if not m:
        raise PublishError("the payload carries no readable record count; refusing to guess "
                           "whether the dataset shrank")
    return int(m.group(1))


def check_count_not_dropped() -> None:
    """Stop when the payload's record count is below the committed payload's."""
    path = ROOT / PAYLOAD
    if not path.exists():
        raise PublishError("the payload %s does not exist; there is no emission to publish" % PAYLOAD)
    new = payload_records(path.read_text(encoding="utf-8"))
    proc = git("show", "HEAD:" + PAYLOAD)
    if proc.returncode != 0:
        return                                    # nothing committed yet: no count to compare
    old = payload_records(proc.stdout)
    if new < old:
        raise PublishError(
            "the payload's record count dropped from %d to %d. The dataset's trajectory only "
            "grows, so a drop names a defect; nothing is committed or pushed. A person "
            "diagnoses it (a truncated gazette accepted? a reconcile block missed?)." % (old, new))


def commit_message() -> str:
    text = (ROOT / PAYLOAD).read_text(encoding="utf-8")[:8192]
    date = _DATE_RE.search(text)
    records, projects = _RECORDS_RE.search(text), _PROJECTS_RE.search(text)
    what = "the %s gazette" % date.group(1) if date else "the gazette"
    counts = (" (%s records / %s projects)" % (format(int(records.group(1)), ","),
                                                format(int(projects.group(1)), ","))
              if records and projects else "")
    return "chore: emit %s%s" % (what, counts)


# --- the commit and the push ---------------------------------------------------------------

def stageable_paths() -> list[str]:
    """The owned paths that exist or are tracked. `git add` fails on a path that is neither."""
    tracked = set(git("ls-files", "--", *OWNED_PATHS).stdout.split())
    return [p for p in OWNED_PATHS if (ROOT / p).exists() or p in tracked]


def unpushed_owned() -> bool:
    """Whether a commit that touches an owned path is ahead of `origin/main`. After a failed
    push the commit already exists, so a retry has nothing new to commit but must still push."""
    proc = git("rev-list", "origin/main..HEAD", "--", *OWNED_PATHS)
    return proc.returncode == 0 and bool(proc.stdout.split())


def commit(message: str) -> bool:
    """Commit the owned paths. Returns whether a commit was made. Path-limited: see the
    module docstring."""
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
    """Push to the branch Pages publishes from. Raises PushError on failure, and only returns
    when the remote has been asked and holds the commit."""
    head = git("rev-parse", "HEAD").stdout.strip()
    try:
        proc = git("push", "origin", "main")
    except subprocess.TimeoutExpired:
        raise PushError(
            "git push timed out after %d s. Unattended, that usually means the stored GitHub "
            "credential was refused and git was waiting for a prompt (revoked or expired token, "
            "or no session to unlock it). Sign in again with `gh auth login` or push once by "
            "hand. The committed emission is ahead of the served one; scripts/check_deploy.py "
            "will report it stale until the push lands." % GIT_NETWORK_TIMEOUT)
    if proc.returncode != 0:
        raise PushError(
            "git push failed: %s\nThe committed emission is ahead of the served one; "
            "scripts/check_deploy.py will report it stale until the push lands."
            % (proc.stderr or proc.stdout).strip()[-2000:])
    try:
        remote = git("ls-remote", "origin", "refs/heads/main").stdout.split()
    except subprocess.TimeoutExpired:
        raise PushError(
            "git ls-remote timed out after %d s, so the push cannot be confirmed. The emission "
            "may or may not have landed; run scripts/check_deploy.py." % GIT_NETWORK_TIMEOUT)
    if not remote or remote[0] != head:
        raise PushError(
            "git push reported success but the remote does not hold the commit (%s). The "
            "committed emission is ahead of the served one; scripts/check_deploy.py will report "
            "it stale until the push lands." % (remote[0] if remote else "no refs/heads/main"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="apply the guards and report what would be published, without "
                         "committing or pushing")
    args = ap.parse_args(argv)

    try:
        check_code_clean()
        check_count_not_dropped()
    except PublishError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 2

    if args.dry_run:
        print("[INFO] dry run: the guards passed; not committing, not pushing")
        return 0

    try:
        made = commit(commit_message())
        if made:
            print("[INFO] committed the emission")
        if made or unpushed_owned():
            if not made:
                print("[INFO] a commit of the emission is ahead of the remote; pushing it")
            push()
            print("[INFO] published")
            return 0
    except PublishError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 2
    except PushError as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 1

    print("[INFO] the emission is unchanged; nothing to publish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
