"""Find which transcript WROTE a given code line. Read-only."""
import json
import pathlib
import sys

ROOT = pathlib.Path.home() / ".claude" / "projects" / "D--project-urTPE"
needle = sys.argv[1] if len(sys.argv) > 1 else 'kwargs.get("publisher_url"'

for path in sorted(ROOT.glob("*.jsonl")):
    hits = []
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                if needle not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message") or {}
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") == "tool_use":
                        cmd = (part.get("input") or {}).get("command") or ""
                        if isinstance(cmd, str) and needle in cmd:
                            hits.append((lineno, "WROTE", cmd.replace("\n", " ")[:260]))
                    elif part.get("type") == "tool_result":
                        body = json.dumps(part.get("content"), ensure_ascii=False)
                        if needle in body:
                            hits.append((lineno, "saw", body.replace("\\n", " ")[:200]))
    except OSError:
        continue
    if hits:
        print("=" * 72)
        print(path.name)
        for lineno, kind, text in hits[:5]:
            print("  line %-6d %-6s %s" % (lineno, kind, text))
