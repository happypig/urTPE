"""Compare the published site against the build this repository holds.

Answers one question: is what is deployed the same bytes as what is committed? On
2026-10-06 it was not, for several commits, and the only reason anyone found out was a
person noticing a link missing from a page served at the wrong capitalisation -- which
returns GitHub's "Page not found" document while the browser renders a cached copy.

Staleness is decidable rather than a judgement call. Pages publishes from a branch of this
repository, so a correct deploy serves bytes byte-identical to the `HEAD` blob; the served
`projects.data.js` and the committed blob hashed identically on that day. Comparing exact
bytes therefore distinguishes three states that matter differently:

    fresh     served bytes == HEAD blob
    stale     served, but different -- a superseded build reading as current
    missing   not served at all

`missing` and `stale` are kept apart because the responses differ, and collapsing them
would let a stale site pass as a healthy one.

This reaches the network, so it is a command and not a pytest case: `AGENTS.md` records
that the suite is offline and must stay that way. The part that can be checked offline --
that the recorded address's capitalisation equals the repository name -- is a test, in
tests/test_deploy_target.py.

    python scripts/check_deploy.py              # the recorded target
    python scripts/check_deploy.py --url URL    # some other address

Exit codes: 0 every artifact fresh, 1 anything stale/missing/unfetchable, 2 usage or a
malformed deploy record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "viewer" / "deploy.json"
TIMEOUT = 60


# --- pure logic, imported directly by the offline tests ---------------------

def verdict(served: bytes | None, committed: bytes | None) -> str:
    """Classify one artifact from its exact bytes."""
    if committed is None:
        return "untracked"
    if served is None:
        return "missing"
    return "fresh" if served == committed else "stale"


def case_mismatch_note(url: str) -> str:
    """Explain a 404 as what it usually is here: the wrong capitalisation."""
    try:
        data = json.loads(TARGET.read_text(encoding="utf-8"))
        base = data["pages_base"].rstrip("/")
    except (OSError, json.JSONDecodeError):
        base = ""
    return (
        "GitHub Pages paths are case-sensitive, and this looks like a capitalisation "
        "mismatch rather than a missing build: the repository name is not spelled this "
        "way here. A wrong-case path serves GitHub's 'Page not found' document, and a "
        "browser will keep rendering a cached copy over it, so a stale page reads as a "
        "working one. The canonical address is %s/ -- compare it with viewer/deploy.json."
        % base
    )


def describe_fetch(status: int, url: str) -> str:
    """A human-readable reason for a non-200, naming the likely cause."""
    if status == 404:
        return "HTTP 404 -- " + case_mismatch_note(url)
    return "HTTP %d" % status


# --- IO --------------------------------------------------------------------

def remote_repo() -> tuple[str, str]:
    """owner and repository name, exactly as git spells them.

    Handles both remote spellings -- https://github.com/owner/repo.git and
    git@github.com:owner/repo.git -- because a fork or a rewritten remote may use either,
    and reading the owner out of the wrong half of the URL would compare against nothing.
    """
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    slug = url.split("://")[-1].replace(":", "/").rstrip("/")
    if slug.endswith(".git"):
        slug = slug[:-4]
    parts = slug.split("/")
    return (parts[-2], parts[-1]) if len(parts) >= 2 else ("", parts[-1])


def head_blob_bytes(path: str) -> bytes | None:
    """The committed bytes, unmodified.

    Deliberately not read through the working tree and not through shell redirection:
    both can rewrite line endings, and then every artifact would report as stale.
    """
    proc = subprocess.run(
        ["git", "show", "HEAD:" + path], cwd=ROOT, capture_output=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def fetch(url: str) -> tuple[int, bytes | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "urtpe-check-deploy"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, None


def digest(data: bytes | None) -> str:
    return "--------" if data is None else hashlib.sha256(data).hexdigest()[:12]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", help="override the base URL from viewer/deploy.json")
    args = ap.parse_args(argv)

    try:
        data = json.loads(TARGET.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print("cannot read %s: %s" % (TARGET, e), file=sys.stderr)
        return 2

    owner, name = remote_repo()
    base = (args.url or data["pages_base"]).rstrip("/")

    # The part that needs no network, run first so a wrong address is reported before
    # anything is fetched.
    if args.url is None:
        recorded = base.rsplit("/", 1)[-1]
        if recorded != name:
            print("FAIL  the recorded address is not the repository name's spelling")
            print("      repository : %s" % name)
            print("      recorded   : %s" % recorded)
            print("      " + case_mismatch_note(base + "/"))
            return 1
        if data.get("owner") != owner or data.get("repo") != name:
            print("FAIL  deploy.json describes %s/%s but the remote is %s/%s"
                  % (data.get("owner"), data.get("repo"), owner, name))
            return 1
        print("target  %s   (repository %s, %s/%s)" % (base, name, owner, name))
    else:
        print("target  %s   (overridden)" % base)

    print()
    width = max(len(a) for a in data["artifacts"])
    bad = 0
    for art in data["artifacts"]:
        committed = head_blob_bytes(art)
        url = "%s/%s" % (base, art)
        status, served = fetch(url)
        state = verdict(served, committed) if status == 200 else "missing"
        note = "" if status == 200 else describe_fetch(status, url)
        if state != "fresh":
            bad += 1
        print("%-6s %-*s  served %s  committed %s%s"
              % (state.upper(), width, art, digest(served), digest(committed),
                 ("  -- " + note) if note else ""))

    print()
    if bad:
        print("%d of %d artifacts are not the committed build."
              % (bad, len(data["artifacts"])))
        print("A stale site reads as a working one, so this is worth resolving before")
        print("quoting anything from it. Re-run the CLI with --viewer and push.")
        return 1
    print("all %d artifacts match the committed build." % len(data["artifacts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())