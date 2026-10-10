"""Workspace-trust pre-seeding for managed Kimi Code homes.

Kimi Code 0.34 gates project-level MCP config behind a per-workspace trust
record and, in the TUI, blocks startup on a "Trust this folder?" modal when
the record is absent. The trust check is presence-only: the workspace is
trusted when a JSON document exists at
``$KIMI_CODE_HOME/workspace-trust/<encodeWorkDirKey(cwd)>``.

Houmao pre-seeds that record for unattended managed launches so the modal
never mounts. The key algorithm mirrors Kimi's ``encodeWorkDirKey``
(``packages/agent-core-v2/src/_base/utils/workdir-slug.ts``) and is pinned by
a live-recorded test vector.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Final, Literal

KIMI_WORKSPACE_TRUST_DIRNAME: Final[str] = "workspace-trust"
_KIMI_WORKDIR_KEY_PREFIX: Final[str] = "wd_"
_KIMI_WORKDIR_HASH_LENGTH: Final[int] = 12
_KIMI_WORKDIR_SLUG_MAX_LENGTH: Final[int] = 40
_KIMI_SLUG_UNSAFE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9._-]+")
_KIMI_SLUG_EDGE_DASHES_PATTERN: Final[re.Pattern[str]] = re.compile(r"^-+|-+$")


class KimiWorkspaceTrustError(ValueError):
    """Raised when Houmao cannot pre-seed Kimi's workspace-trust record."""


@dataclass(frozen=True)
class KimiWorkspaceTrustProjection:
    """Result and provenance for one workspace-trust pre-seed."""

    state: Literal["projected", "unchanged"]
    path: Path
    workspace_key: str
    workdir: Path
    changed: bool

    def to_payload(self) -> dict[str, str | bool]:
        """Return a JSON-serializable provenance payload."""

        return {
            "state": self.state,
            "path": str(self.path),
            "workspace_key": self.workspace_key,
            "workdir": str(self.workdir),
            "changed": self.changed,
        }


def kimi_workdir_slug(name: str) -> str:
    """Mirror Kimi's ``slugifyWorkDirName`` for one path basename."""

    slug = _KIMI_SLUG_UNSAFE_PATTERN.sub("-", name.lower())
    slug = _KIMI_SLUG_EDGE_DASHES_PATTERN.sub("", slug)
    slug = slug[:_KIMI_WORKDIR_SLUG_MAX_LENGTH]
    slug = _KIMI_SLUG_EDGE_DASHES_PATTERN.sub("", slug)
    if slug in {"", ".", ".."}:
        return "workspace"
    return slug


def kimi_workdir_key(workdir: Path | str) -> str:
    """Mirror Kimi's ``encodeWorkDirKey`` for one working directory."""

    normalized = str(workdir).replace("\\", "/").rstrip("/")
    base = normalized.split("/")[-1] if normalized.split("/") else normalized
    slug = kimi_workdir_slug(base)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:_KIMI_WORKDIR_HASH_LENGTH]
    return f"{_KIMI_WORKDIR_KEY_PREFIX}{slug}_{digest}"


def render_kimi_workspace_trust(workdir: Path, *, trusted_at_ms: int) -> str:
    """Render the canonical trust-record bytes for one working directory."""

    return json.dumps({"root": str(workdir), "trustedAt": trusted_at_ms}, separators=(",", ":"))


def ensure_kimi_workspace_trust(
    *,
    home_path: Path,
    working_directory: Path,
    trusted_at_ms: int | None = None,
) -> KimiWorkspaceTrustProjection:
    """Atomically pre-seed Kimi's workspace-trust record for one workdir.

    The record is content-stable apart from ``trustedAt``: an existing record
    for the same workdir is left untouched so repeated provider starts do not
    churn the file.
    """

    resolved_workdir = working_directory.resolve()
    key = kimi_workdir_key(resolved_workdir)
    target = home_path.resolve() / KIMI_WORKSPACE_TRUST_DIRNAME / key
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise KimiWorkspaceTrustError(
            f"Cannot pre-seed Kimi workspace trust at `{target}`: path is not a regular file."
        )
    if target.is_file() and _record_matches(target, resolved_workdir):
        return KimiWorkspaceTrustProjection(
            state="unchanged",
            path=target,
            workspace_key=key,
            workdir=resolved_workdir,
            changed=False,
        )
    rendered = render_kimi_workspace_trust(
        resolved_workdir,
        trusted_at_ms=trusted_at_ms if trusted_at_ms is not None else int(time.time() * 1000),
    )
    try:
        _atomic_write_text(target, rendered)
    except OSError as exc:
        raise KimiWorkspaceTrustError(
            f"Cannot pre-seed Kimi workspace trust at `{target}`: {exc}."
        ) from exc
    return KimiWorkspaceTrustProjection(
        state="projected",
        path=target,
        workspace_key=key,
        workdir=resolved_workdir,
        changed=True,
    )


def _record_matches(path: Path, workdir: Path) -> bool:
    """Return True when an existing record already trusts *workdir*.

    Kimi treats record presence as trusted state; Houmao additionally repairs
    records whose payload names a different root or cannot be parsed.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("root") == str(workdir)


def _atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8 text through same-directory atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        temp_path.chmod(0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
