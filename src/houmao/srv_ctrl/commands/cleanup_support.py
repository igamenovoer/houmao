"""Shared structured cleanup payload helpers for `houmao-mgr`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from houmao.owned_mutation import remove_tree_or_path

from .output import emit
from .renderers.cleanup import render_cleanup_payload_fancy, render_cleanup_payload_plain


@dataclass(frozen=True)
class CleanupAction:
    """One structured cleanup action or preservation decision."""

    artifact_kind: str
    path: Path
    proposed_action: str
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-compatible action payload."""

        payload: dict[str, object] = {
            "artifact_kind": self.artifact_kind,
            "path": str(self.path),
            "proposed_action": self.proposed_action,
            "reason": self.reason,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload


def remove_path(path: Path, *, allowed_roots: Sequence[Path] | None = None) -> None:
    """Remove one filesystem path whether it is a file, symlink, or directory."""

    remove_tree_or_path(path.expanduser(), allowed_roots=allowed_roots)


def build_cleanup_payload(
    *,
    dry_run: bool,
    scope: dict[str, object],
    resolution: dict[str, object],
    planned_actions: Sequence[CleanupAction] = (),
    applied_actions: Sequence[CleanupAction] = (),
    blocked_actions: Sequence[CleanupAction] = (),
    preserved_actions: Sequence[CleanupAction] = (),
    extra_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build one normalized structured cleanup payload."""

    summary: dict[str, object] = {
        "planned_count": len(planned_actions),
        "applied_count": len(applied_actions),
        "blocked_count": len(blocked_actions),
        "preserved_count": len(preserved_actions),
    }
    if extra_summary:
        summary.update(extra_summary)
    return {
        "dry_run": dry_run,
        "scope": dict(scope),
        "resolution": dict(resolution),
        "planned_actions": [action.to_payload() for action in planned_actions],
        "applied_actions": [action.to_payload() for action in applied_actions],
        "blocked_actions": [action.to_payload() for action in blocked_actions],
        "preserved_actions": [action.to_payload() for action in preserved_actions],
        "summary": summary,
    }


def emit_cleanup_payload(payload: dict[str, object]) -> None:
    """Emit one cleanup payload with curated cleanup renderers."""

    emit(
        payload,
        plain_renderer=render_cleanup_payload_plain,
        fancy_renderer=render_cleanup_payload_fancy,
    )
