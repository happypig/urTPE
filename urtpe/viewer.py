"""Static viewer data emission: projects.data.js for a file:// page.

The viewer is a static HTML/JS page; a data file is generated into its
directory so it can be opened directly without a local web server (script
tags with relative paths bypass file:// CORS restrictions).

The page loads exactly four files — index.html, app.css, app.js and
projects.data.js — and only this module writes the last one. Two things then
have to hold for the page to show the truth: the data file must be rewritten
whenever the dataset changes, and index.html's asset version must name the
publication that data carries. Both used to depend on a human remembering an
optional flag and a hand-edited literal, so both are handled here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

# ?v=... on a <script src>. Only the version is rewritten; the paths are left alone.
_ASSET_VERSION_RE = re.compile(r"(\?v=)([0-9a-zA-Z]+)")


def _asset_version(doc: dict) -> str:
    """A cache-bust derived from the dataset itself.

    The publication date leads, so the version is readable, and a short digest of
    the date and the counts follows so that two datasets sharing a date — or a
    re-emit with a new generated_at — still separate. Identical data yields an
    identical version, so an unchanged re-run does not churn index.html.
    """
    published = str(doc.get("published_date") or "")[:10].replace("-", "")
    counts = doc.get("counts") or {}
    fingerprint = f"{published}|{counts.get('projects')}|{counts.get('records')}"
    return f"{published}{hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()[:4]}"


def write_projects_js(dirpath: str, doc: dict) -> str:
    """Write viewer/projects.data.js and return the output path.

    When the directory holds an index.html, its asset version is rewritten from
    the dataset. Without that, a browser keeps serving the previous file however
    many times the data is regenerated.
    """
    js = "window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";"
    os.makedirs(dirpath, exist_ok=True)
    path = f"{dirpath}/projects.data.js"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(js)

    index = f"{dirpath}/index.html"
    if os.path.exists(index):
        version = _asset_version(doc)
        with open(index, encoding="utf-8") as fh:
            html = fh.read()
        with open(index, "w", encoding="utf-8") as fh:
            fh.write(_ASSET_VERSION_RE.sub(r"\g<1>" + version, html))
    return path


def consistency_faults(doc: dict, js_path: str) -> list[str]:
    """Report a viewer whose data file disagrees with the dataset just emitted.

    The viewer is a separate file from projects.json, so a run that refreshed one
    and not the other leaves the page showing a dataset nobody emitted — and
    nothing else in the pipeline notices. Both values are named so the fault can
    be acted on without re-running anything.
    """
    if not os.path.exists(js_path):
        return [f"viewer data missing: {js_path} was never emitted"]
    try:
        with open(js_path, encoding="utf-8") as fh:
            text = fh.read()
        emitted = json.loads(text[len("window.PROJECTS = "):].rstrip().rstrip(";"))
    except (OSError, ValueError) as exc:
        return [f"viewer data unreadable: {js_path}: {exc}"]

    faults: list[str] = []
    for field in ("published_date", "counts"):
        want, have = doc.get(field), emitted.get(field)
        if want != have:
            faults.append(
                f"viewer out of step with the dataset: {js_path} has {field}="
                f"{have!r} but this run emitted {want!r}; the page would show a "
                f"dataset the run did not produce")
    return faults