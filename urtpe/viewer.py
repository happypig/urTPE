"""Static viewer data emission: projects.data.js for a file:// page.

The viewer is a static HTML/JS page; a data file is generated into its
directory so it can be opened directly without a local web server (script
tags with relative paths bypass file:// CORS restrictions).
"""

from __future__ import annotations

import json


def write_projects_js(dirpath: str, doc: dict) -> str:
    """Write viewer/projects.data.js and return the output path."""
    js = "window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";"
    path = f"{dirpath}/projects.data.js"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(js)
    return path