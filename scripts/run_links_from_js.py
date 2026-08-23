"""Run official-link discovery starting from an existing projects.data.js.

Standalone variant of `python -m urtpe.cli --from-js viewer/projects.data.js --links`.
Writes the crawl log to data/crawl_log_from_js.tsv instead of overwriting
the PDF pipeline's crawl_log.tsv.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import LinksDiscovery
from urtpe.models import CleanRecord, Project

JS_PATH = "viewer/projects.data.js"
CACHE_DIR = "data/.link_cache"
CRAWL_LOG = "data/crawl_log_from_js.tsv"


def load_projects(js_path: str) -> list[Project]:
    text = Path(js_path).read_text(encoding="utf-8")
    json_text = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    json_text = re.sub(r";\s*$", "", json_text)
    doc = json.loads(json_text)

    projects = []
    for pg in doc["projects"]:
        members = []
        for node in pg["nodes"]:
            rec = CleanRecord(
                recno=node["recno"],
                date=node.get("date", ""),
                iso_date=node.get("iso_date", ""),
                ymd=tuple(node.get("ymd", (0, 0, 0))) if "ymd" in node else (0, 0, 0),
                district=node.get("district", ""),
                district_land=node.get("district_land", node.get("district", "")),
                name=node.get("case_name", node.get("name", "")),
                name_raw=node.get("name_raw", ""),
                land=node.get("land", ""),
                section=node.get("section", ""),
                first_parcel=node.get("first_parcel", ""),
                parcels=node.get("parcels", []),
                aliases=node.get("aliases", {}),
                land_count=node.get("land_count"),
                orig_count=node.get("orig_count"),
                named_anchor=node.get("named_anchor", ""),
                area_section=node.get("area_section", ""),
                stage=node.get("stage", ""),
                stage_index=node.get("stage_index", -1),
                track=node.get("track", ""),
                implementer=node.get("implementer", ""),
                planner=node.get("planner", ""),
                auto_fixes=node.get("auto_fixes", []),
                review_flags=node.get("review_flags", []),
            )
            members.append(rec)
        projects.append(Project(
            project_id=pg["project_id"],
            anchor_recno=pg["anchor_recno"],
            members=members,
        ))
    return projects


def main() -> None:
    js_path = sys.argv[1] if len(sys.argv) > 1 else JS_PATH
    projects = load_projects(js_path)
    print(f"Loaded {len(projects)} projects from {js_path}")

    discovery = LinksDiscovery(cache_dir=CACHE_DIR)
    results = discovery.run(projects)
    discovery.write_crawl_log(results, CRAWL_LOG)

    resolved = sum(1 for r in results.values() if r.status == "resolved")
    unresolved = sum(1 for r in results.values() if r.status == "unresolved")
    print(f"Resolved: {resolved}, Unresolved: {unresolved}")
    print(f"Done. Crawl log written to {CRAWL_LOG}")


if __name__ == "__main__":
    main()
