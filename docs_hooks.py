"""MkDocs hooks for Houmao documentation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parent
DOCS_ROOT = REPO_ROOT / "docs"
WORKSPACE_PREFIX = "/data1/huangzhe/code/houmao/"
REPO_LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)\s]+)([^)]*)\)")
REWRITABLE_PREFIXES = ("src/", "tests/", "tools/", "scripts/", "context/", "openspec/")


def _repo_ref() -> str:
    """Return the repository ref used for generated GitHub links."""
    return os.environ.get("MKDOCS_REPO_REF", "devel")


def _rewrite_url(url: str, page_abs_path: Path, repo_url: str) -> str:
    """Rewrite repository-local links outside docs to GitHub blob/tree URLs."""
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or parts.path.startswith("#") or parts.path.startswith("mailto:"):
        return url

    path_part = parts.path
    if path_part.startswith("/"):
        if not path_part.startswith(WORKSPACE_PREFIX):
            return url
        repo_rel = path_part[len(WORKSPACE_PREFIX) :]
        is_dir_like = repo_rel.endswith("/")
    else:
        candidate = (page_abs_path.parent / path_part).resolve(strict=False)
        try:
            repo_rel = candidate.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return url
        if repo_rel.startswith("docs/"):
            return url
        if not repo_rel.startswith(REWRITABLE_PREFIXES):
            return url
        is_dir_like = path_part.endswith("/") or candidate.is_dir()

    if not repo_rel:
        return url

    repo_url = repo_url.rstrip("/")
    kind = "tree" if is_dir_like else "blob"
    rewritten_path = f"{repo_url}/{kind}/{_repo_ref()}/{repo_rel}"
    return urlunsplit((parts.scheme, parts.netloc, rewritten_path, parts.query, parts.fragment))


def on_page_markdown(markdown: str, page, config, files):  # noqa: ANN001
    """Rewrite repo-local Markdown links so published docs point at GitHub."""

    page_abs_path = Path(page.file.abs_src_path)
    repo_url = str(config["repo_url"])

    def replace(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2)
        suffix = match.group(3)
        return f"[{label}]({_rewrite_url(url, page_abs_path, repo_url)}{suffix})"

    return REPO_LINK_RE.sub(replace, markdown)
