# deployment-verification

## Why

`https://happypig.github.io/urtPE/viewer/index.html` served a stale build, and it took a
person noticing a missing link to find out. Nothing in the repository recorded the deployed
address at all: `AGENTS.md` describes the viewer only as "a static `file://` site", so the
canonical URL, its branch, and the fact that the thing being looked at was a *deployed copy*
rather than the local artifact were all knowledge that existed only in one browser tab.

The URL that was actually open, `.../urtPE/...`, is the wrong capitalisation. The repository
is `urTPE`, and GitHub Pages paths are case-sensitive:

```
200  https://happypig.github.io/urTPE/viewer/index.html
404  https://happypig.github.io/urtPE/viewer/index.html
```

So the page was serving GitHub's "Page not found" document, and the browser was displaying a
cached render of a build from before the fix. The link the user was checking — a Taipei case
that had been present in the committed payload for several commits — looked missing because
the request 404'd and the stale render was still on screen.

Two things went unverified, and only the second is interesting:

- **The deploy target is unrecorded.** Nothing states where the site lives, so nothing can
  notice a wrong path, and nothing pins its capitalisation to the repository name.
- **A deployed build is never compared to the committed build.** There is no CI, and
  `AGENTS.md` records that no browser test exists, so "what is deployed" and "what is
  committed" were two facts nobody ever held side by side.

The check is worth building because the comparison is exact rather than heuristic: the
served bytes are byte-identical to the `HEAD` blob, verified today
(`ec37a29fe5624d8851e439595c7ed8ab8f57a86c` on both sides). Staleness is therefore a decidable
question, not a judgement call.

The capitalisation point is worth making enforceable offline. A test can read
`git remote get-url origin`, take the repository name, and require that the recorded Pages
path uses that exact case — which would have failed the moment anyone wrote the URL down
wrong, with no network involved. The network half stays out of `pytest`, which is offline
and must stay that way.

## What changes

- `viewer/deploy.json` becomes the single recorded statement of the deploy target: owner,
  repository, Pages base URL, and the artifact list. One place, so the script and the docs
  cannot drift apart.
- `tests/test_deploy_target.py` verifies offline that the recorded Pages path's final segment
  equals the git remote's repository name **case-sensitively**, that the base is a well-formed
  Pages URL for that repository, that every listed artifact is tracked in git, and that the
  verdict logic distinguishes fresh / stale / missing.
- `scripts/check_deploy.py` fetches each artifact from the canonical URL and compares its
  SHA-256 against the `HEAD` blob of the same path, reporting per artifact and exiting
  non-zero when any artifact is stale, missing, or unreachable. A 404 is reported with the
  case-sensitivity hint rather than as a bare status code, because that was the actual cause.
- `AGENTS.md` records the canonical URL, the check, and the case-sensitivity trap.
- `openspec/config.yaml`'s approval count is corrected to the emitted value.

## Deliberately not included

- **No CI.** The repository has no workflow files and no lint or typecheck configuration;
  inventing a pipeline is a larger decision than this change. The script is a command a
  person or a future workflow runs.
- **No browser rendering check.** This verifies that the deployed bytes are the committed
  bytes. It does not prove the page renders, which `AGENTS.md` already records as untested;
  adding a headless-browser dependency for one check is not warranted here.
- **No polling or alerting.** One check, run deliberately, reports one state.

## Impact

- Affected spec: `deployment-verification` (new capability)
- Affected code: `viewer/deploy.json`, `scripts/check_deploy.py`,
  `tests/test_deploy_target.py`
- Affected docs: `AGENTS.md`, `openspec/config.yaml`, `docs/portal_operations_log.md`
- No change to emitted data or pipeline behaviour.