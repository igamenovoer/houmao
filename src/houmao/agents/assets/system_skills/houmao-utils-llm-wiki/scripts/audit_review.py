#!/usr/bin/env python3
"""
audit_review.py — List and group audit feedback by target file.

Usage:
    python3 audit_review.py <wiki-root> [--open|--resolved|--all]

Examples:
    python3 audit_review.py ~/wikis/ai-research --open
    python3 audit_review.py ~/wikis/ai-research --resolved
    python3 audit_review.py ~/wikis/ai-research --all

Reads every file under `<wiki-root>/audit/` (open) and `<wiki-root>/audit/resolved/`
(resolved), parses the YAML frontmatter, and prints a report grouped by target
file. Use this at the start of an `audit` operation to decide processing order.

Exit codes:
  0 — done (always, regardless of audit count)
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    body = m.group(1)
    result: dict = {}
    for line in body.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        val = rest.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            result[key] = [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()]
        elif val.startswith('"') and val.endswith('"'):
            result[key] = val[1:-1].replace("\\n", "\n").replace('\\"', '"')
        elif val.startswith("'") and val.endswith("'"):
            result[key] = val[1:-1]
        else:
            result[key] = val
    return result


def extract_comment_one_line(text: str) -> str:
    """Pull the first non-empty line of the # Comment section."""
    in_comment = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("# comment"):
            in_comment = True
            continue
        if not in_comment:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            break
        return stripped[:100]
    return "(no comment body)"


SEVERITY_ORDER = {"error": 0, "warn": 1, "suggest": 2, "info": 3}


def main(root: str, mode: str) -> int:
    root_path = Path(root)
    audit_dir = root_path / "audit"
    if not audit_dir.exists():
        print(f"ERROR: audit/ not found at {audit_dir}", file=sys.stderr)
        return 1

    files: list[Path] = []
    if mode in ("open", "all"):
        files.extend(sorted(p for p in audit_dir.glob("*.md") if p.name != ".gitkeep"))
    if mode in ("resolved", "all"):
        resolved = audit_dir / "resolved"
        if resolved.exists():
            files.extend(sorted(p for p in resolved.glob("*.md") if p.name != ".gitkeep"))

    if not files:
        print(f"No {mode} audit files found.")
        return 0

    grouped: dict[str, list[dict]] = defaultdict(list)
    for p in files:
        text = p.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            print(f"⚠️  {p.relative_to(root_path)} — missing frontmatter", file=sys.stderr)
            continue
        fm["_path"] = str(p.relative_to(root_path))
        fm["_one_liner"] = extract_comment_one_line(text)
        grouped[fm.get("target", "(no-target)")].append(fm)

    total = sum(len(v) for v in grouped.values())
    print(f"{mode.upper()} audits: {total} across {len(grouped)} target files\n")

    for target in sorted(grouped.keys()):
        entries = grouped[target]
        entries.sort(key=lambda e: (
            SEVERITY_ORDER.get(e.get("severity", "info"), 99),
            e.get("created", ""),
        ))
        print(f"{target}  ({len(entries)} {mode})")
        for e in entries:
            sev = e.get("severity", "?")
            aid = e.get("id", "?")
            author = e.get("author", "?")
            created = e.get("created", "?")[:10]  # date only
            line = e.get("_one_liner", "")
            print(f"   [{aid}] {sev}: {line}  —  {author}, {created}")
        print()

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    root = sys.argv[1]
    mode = "open"
    for arg in sys.argv[2:]:
        if arg == "--open":
            mode = "open"
        elif arg == "--resolved":
            mode = "resolved"
        elif arg == "--all":
            mode = "all"
        else:
            print(f"Unknown flag: {arg}", file=sys.stderr)
            sys.exit(1)
    sys.exit(main(root, mode))

