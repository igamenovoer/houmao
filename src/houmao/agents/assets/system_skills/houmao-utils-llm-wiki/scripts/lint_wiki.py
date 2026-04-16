#!/usr/bin/env python3
"""
lint_wiki.py — Health check for an LLM Wiki.

Usage:
    python3 lint_wiki.py <wiki-root>

Example:
    python3 lint_wiki.py ~/wikis/ai-research

Checks:
  1. Dead wikilinks — [[Target]] where Target doesn't exist in the vault
  2. Orphan pages — wiki pages with no inbound links
  3. Missing index entries — wiki pages not listed in wiki/index.md
  4. Unlinked concepts — terms mentioned 3+ times but lacking their own page
  5. log/ shape — every file matches YYYYMMDD.md and has the right H1
  6. audit/ shape — every audit/*.md parses as a valid AuditEntry
  7. Audit targets — every open audit's `target` file must exist
  8. Non-canonical legacy links — resolvable wiki-relative links missing wiki/

Exit codes:
  0 — no issues found
  1 — issues found (printed to stdout)
"""

import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
LOG_FILENAME_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})\.md$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
ARTICLE_LEGACY_PREFIXES = ("concepts/", "entities/", "summaries/")
RECOGNIZED_ROOTS = {"wiki", "raw", "log", "audit", "outputs"}

# Required audit frontmatter fields
AUDIT_REQUIRED_FIELDS = {
    "id", "target", "target_lines", "anchor_before", "anchor_text",
    "anchor_after", "severity", "author", "source", "created", "status",
}
VALID_SEVERITIES = {"info", "suggest", "warn", "error"}
VALID_STATUSES = {"open", "resolved"}
VALID_SOURCES = {"obsidian-plugin", "web-viewer", "manual"}


@dataclass(frozen=True)
class Wikilink:
    raw: str
    target: str
    anchor: str
    alias: str


@dataclass(frozen=True)
class ResolvedTarget:
    kind: str
    exists: bool
    canonical: str
    file_path: Path | None
    legacy: bool = False


def split_wikilink(inner: str) -> Wikilink:
    target_part, _, alias = inner.strip().partition("|")
    target, _, anchor = target_part.strip().partition("#")
    return Wikilink(
        raw=inner.strip(),
        target=target.strip(),
        anchor=anchor.strip(),
        alias=alias.strip(),
    )


def extract_wikilinks(text: str) -> list[Wikilink]:
    return [split_wikilink(match.group(1)) for match in WIKILINK_RE.finditer(text)]


def canonical_rel(root_path: Path, path: Path) -> str:
    rel = path.relative_to(root_path).as_posix()
    if path.suffix == ".md":
        rel = rel[:-3]
    return rel


def target_kind(canonical: str) -> str:
    top = canonical.split("/", 1)[0]
    return {
        "wiki": "article",
        "raw": "source",
        "log": "log",
        "audit": "audit",
        "outputs": "output",
    }.get(top, "unknown")


def build_vault_index(root_path: Path) -> tuple[dict[str, ResolvedTarget], dict[str, Path]]:
    by_key: dict[str, ResolvedTarget] = {}
    article_pages: dict[str, Path] = {}

    for top in sorted(RECOGNIZED_ROOTS):
        base = root_path / top
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file() and p.name != ".gitkeep"):
            canonical = canonical_rel(root_path, path)
            kind = target_kind(canonical)
            resolved = ResolvedTarget(kind=kind, exists=True, canonical=canonical, file_path=path)

            keys = {canonical}
            if path.suffix == ".md":
                keys.add(canonical + ".md")
            else:
                keys.add(path.relative_to(root_path).as_posix())
            for key in keys:
                by_key.setdefault(key, resolved)

            if kind == "article":
                article_pages[canonical] = path
                rel_from_wiki = path.relative_to(root_path / "wiki").as_posix()
                legacy = rel_from_wiki[:-3] if rel_from_wiki.endswith(".md") else rel_from_wiki
                stem = path.stem
                legacy_keys = {
                    legacy,
                    legacy + ".md",
                    stem,
                    stem + ".md",
                }
                for key in legacy_keys:
                    legacy_resolved = ResolvedTarget(
                        kind=kind,
                        exists=True,
                        canonical=canonical,
                        file_path=path,
                        legacy=not key.startswith("wiki/"),
                    )
                    by_key.setdefault(key, legacy_resolved)

    return by_key, article_pages


def resolve_target(root_path: Path, index: dict[str, ResolvedTarget], target: str) -> ResolvedTarget:
    target = target.strip().strip("/")
    if not target:
        return ResolvedTarget(kind="unknown", exists=False, canonical=target, file_path=None)

    if target in index:
        return index[target]
    no_suffix = target[:-3] if target.endswith(".md") else target
    if no_suffix in index:
        return index[no_suffix]

    top = no_suffix.split("/", 1)[0]
    if top in RECOGNIZED_ROOTS:
        return ResolvedTarget(kind=target_kind(no_suffix), exists=False, canonical=no_suffix, file_path=None)

    if no_suffix.startswith(ARTICLE_LEGACY_PREFIXES):
        return ResolvedTarget(kind="article", exists=False, canonical=f"wiki/{no_suffix}", file_path=None, legacy=True)

    return ResolvedTarget(kind="unknown", exists=False, canonical=no_suffix, file_path=None)


def parse_frontmatter(text: str) -> dict | None:
    """Minimal YAML-ish frontmatter parser. Handles the flat key:value fields
    and one-level lists/arrays actually used by audit files. Does not handle
    arbitrary YAML — intentional, to avoid a pyyaml dependency."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    body = m.group(1)
    result: dict = {}
    # Track multi-line folded strings via simple heuristic: quoted scalars
    # can contain \n; unquoted values are single-line.
    i = 0
    lines = body.split("\n")
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        val = rest.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if not inner:
                result[key] = []
            else:
                parts = [p.strip() for p in inner.split(",")]
                parsed: list = []
                for p in parts:
                    if p.isdigit() or (p.startswith("-") and p[1:].isdigit()):
                        parsed.append(int(p))
                    else:
                        parsed.append(p.strip('"').strip("'"))
                result[key] = parsed
        elif val.startswith('"') and val.endswith('"'):
            result[key] = val[1:-1].replace("\\n", "\n").replace('\\"', '"')
        elif val.startswith("'") and val.endswith("'"):
            result[key] = val[1:-1]
        else:
            result[key] = val
        i += 1
    return result


def lint(root: str) -> int:
    root_path = Path(root)
    wiki_path = root_path / "wiki"
    log_path = root_path / "log"
    audit_path = root_path / "audit"

    if not wiki_path.exists():
        print(f"ERROR: wiki/ directory not found at {wiki_path}", file=sys.stderr)
        return 1

    vault_index, article_pages = build_vault_index(root_path)
    all_wiki_files = sorted(wiki_path.rglob("*.md"))
    index_path = wiki_path / "index.md"

    issues = 0
    inbound: dict[str, list[str]] = defaultdict(list)

    # ── Pass 1: dead wikilinks ──────────────────────────────────────────────
    dead_links: list[tuple[str, str]] = []
    noncanonical_links: list[tuple[str, str, str]] = []
    for md_file in all_wiki_files:
        text = md_file.read_text(encoding="utf-8")
        for link in extract_wikilinks(text):
            if not link.target or link.target.startswith("#"):
                continue
            resolved = resolve_target(root_path, vault_index, link.target)
            if not resolved.exists:
                dead_links.append((str(md_file.relative_to(root_path)), link.raw))
                continue
            if resolved.kind == "article":
                inbound[resolved.canonical].append(canonical_rel(root_path, md_file))
            if resolved.legacy:
                noncanonical_links.append((
                    str(md_file.relative_to(root_path)),
                    link.raw,
                    resolved.canonical,
                ))

    if dead_links:
        print(f"\n🔴 Dead wikilinks ({len(dead_links)}):")
        for source, link in dead_links:
            print(f"   {source} → [[{link}]]")
        issues += len(dead_links)
    else:
        print("✅ No dead wikilinks")

    if noncanonical_links:
        print(f"\n🟡 Non-canonical wikilinks ({len(noncanonical_links)}):")
        for source, link, canonical in noncanonical_links:
            print(f"   {source} → [[{link}]] should use [[{canonical}]]")
        issues += len(noncanonical_links)
    else:
        print("✅ Wikilinks use canonical vault-root targets")

    # ── Pass 2: orphan pages ────────────────────────────────────────────────
    skip_orphan = {"wiki/index"}
    orphans = [
        p for canonical, p in article_pages.items()
        if canonical not in inbound and canonical not in skip_orphan
    ]
    if orphans:
        print(f"\n🟡 Orphan pages ({len(orphans)}) — no inbound wikilinks:")
        for p in orphans:
            print(f"   {p.relative_to(root_path)}")
        issues += len(orphans)
    else:
        print("✅ No orphan pages")

    # ── Pass 3: missing index entries ───────────────────────────────────────
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")
        not_in_index = [
            p for canonical, p in article_pages.items()
            if p != index_path
            and canonical not in index_text
            and str(p.relative_to(wiki_path).with_suffix("")) not in index_text
            and f"[[{p.stem}]]" not in index_text
        ]
        if not_in_index:
            print(f"\n🟡 Pages missing from index.md ({len(not_in_index)}):")
            for p in not_in_index:
                print(f"   {p.relative_to(root_path)}")
            issues += len(not_in_index)
        else:
            print("✅ All pages in index.md")
    else:
        print("⚠️  wiki/index.md not found — skipping index check")

    # ── Pass 4: unlinked concepts ───────────────────────────────────────────
    all_text = " ".join(p.read_text(encoding="utf-8") for p in all_wiki_files)
    all_links = extract_wikilinks(all_text)
    link_counts: dict[str, int] = defaultdict(int)
    for link in all_links:
        if link.target and not link.target.startswith("#"):
            link_counts[link.target] += 1

    missing_pages = [
        (link, count) for link, count in link_counts.items()
        if count >= 3 and not resolve_target(root_path, vault_index, link).exists
    ]
    if missing_pages:
        print(f"\n🟡 Frequently linked but no page ({len(missing_pages)}):")
        for link, count in sorted(missing_pages, key=lambda x: -x[1]):
            print(f"   [[{link}]] — mentioned {count}x")
        issues += len(missing_pages)
    else:
        print("✅ No frequently-linked missing pages")

    # ── Pass 5: log/ shape ───────────────────────────────────────────────────
    if log_path.exists() and log_path.is_dir():
        log_issues: list[str] = []
        for p in sorted(log_path.iterdir()):
            if p.is_dir():
                continue
            if p.name == ".gitkeep":
                continue
            m = LOG_FILENAME_RE.match(p.name)
            if not m:
                log_issues.append(f"   {p.relative_to(root_path)} — filename doesn't match YYYYMMDD.md")
                continue
            y, mo, d = m.groups()
            iso = f"{y}-{mo}-{d}"
            first_line = p.read_text(encoding="utf-8").splitlines()[:1]
            if not first_line or first_line[0].strip() != f"# {iso}":
                log_issues.append(f"   {p.relative_to(root_path)} — expected H1 '# {iso}'")
        if log_issues:
            print(f"\n🟡 log/ shape issues ({len(log_issues)}):")
            for s in log_issues:
                print(s)
            issues += len(log_issues)
        else:
            print("✅ log/ shape OK")
    else:
        print("⚠️  log/ directory not found — skipping log shape check")

    # ── Pass 6: audit/ shape ─────────────────────────────────────────────────
    audit_targets_to_check: list[tuple[str, str]] = []  # (audit_id, target)
    if audit_path.exists() and audit_path.is_dir():
        audit_files = [
            p for p in audit_path.rglob("*.md") if p.name != ".gitkeep"
        ]
        audit_issues: list[str] = []
        for p in audit_files:
            text = p.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            rel = p.relative_to(root_path)
            if fm is None:
                audit_issues.append(f"   {rel} — missing YAML frontmatter")
                continue
            missing = AUDIT_REQUIRED_FIELDS - set(fm.keys())
            if missing:
                audit_issues.append(
                    f"   {rel} — missing fields: {', '.join(sorted(missing))}"
                )
                continue
            if fm["severity"] not in VALID_SEVERITIES:
                audit_issues.append(
                    f"   {rel} — invalid severity '{fm['severity']}' (expected {sorted(VALID_SEVERITIES)})"
                )
            if fm["source"] not in VALID_SOURCES:
                audit_issues.append(
                    f"   {rel} — invalid source '{fm['source']}'"
                )
            expected_status = "resolved" if "resolved" in p.parts else "open"
            if fm["status"] != expected_status:
                audit_issues.append(
                    f"   {rel} — status '{fm['status']}' doesn't match directory (expected '{expected_status}')"
                )
            if fm["status"] == "open":
                audit_targets_to_check.append((fm["id"], fm["target"]))

        if audit_issues:
            print(f"\n🔴 audit/ shape issues ({len(audit_issues)}):")
            for s in audit_issues:
                print(s)
            issues += len(audit_issues)
        else:
            print(f"✅ audit/ shape OK ({len(audit_files)} files)")
    else:
        print("⚠️  audit/ directory not found — skipping audit shape check")

    # ── Pass 7: audit targets exist ──────────────────────────────────────────
    missing_targets: list[tuple[str, str]] = []
    for audit_id, target in audit_targets_to_check:
        resolved = resolve_target(root_path, vault_index, target)
        if not resolved.exists:
            missing_targets.append((audit_id, target))
    if missing_targets:
        print(f"\n🔴 Open audits with missing target files ({len(missing_targets)}):")
        for audit_id, target in missing_targets:
            print(f"   {audit_id} → {target}")
        issues += len(missing_targets)
    elif audit_targets_to_check:
        print("✅ All open-audit targets exist")

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'─'*40}")
    if issues == 0:
        print("✅ Wiki is healthy — no issues found")
    else:
        print(f"⚠️  {issues} issue(s) found — review above and fix before next ingest")

    return 0 if issues == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(lint(sys.argv[1]))
