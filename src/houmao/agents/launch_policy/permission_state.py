"""Retain the native permission baseline across launches that reuse a home."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from houmao.agents.launch_policy.provider_hooks import (
    load_json_state,
    load_toml_state,
    write_json_state,
    write_toml_state,
)

_PROJECTIONS = {
    "claude": ("settings.json", {"permission_mode": "defaultMode"}),
    "codex": (
        "config.toml",
        {"approval_policy": "approval_policy", "sandbox_mode": "sandbox_mode"},
    ),
    "kimi": ("config.toml", {"permission_mode": "default_permission_mode"}),
}
_STATE_FILE = ".houmao-launch-permissions.json"


@contextmanager
def permission_projection(*, tool: str, home: Path, effective: Mapping[str, Any]) -> Iterator[None]:
    """Restore projected omissions and remember which startup fields Houmao wrote."""

    projection = _PROJECTIONS.get(tool)
    if projection is None:
        yield
        return
    name, projected_keys = projection
    ledger = home / _STATE_FILE
    if not effective and not ledger.is_file():
        yield
        return
    path = home / name
    prior = load_json_state(ledger)
    before, values = _read_native_permissions(path)
    baseline = {}
    restored = False
    for field, key in projected_keys.items():
        previous = prior.get(field)
        current = values.get(key)
        if (
            isinstance(previous, dict)
            and isinstance(current, str)
            and current == previous.get("projected")
        ):
            original = previous.get("original")
            if field not in effective:
                if original is None:
                    values.pop(key, None)
                else:
                    values[key] = original
                restored = True
        else:
            original = current
        if field in effective:
            baseline[field] = original if isinstance(original, str) else None
    if restored:
        if path.suffix == ".json":
            write_json_state(path, before)
        else:
            write_toml_state(path, before)
    try:
        yield
    finally:
        _, applied = _read_native_permissions(path)
        owned = {
            field: {"original": original, "projected": applied[key]}
            for field, original in baseline.items()
            if isinstance(applied.get(key := projected_keys[field]), str)
            and applied[key] != original
        }
        if owned:
            write_json_state(ledger, owned)
        else:
            ledger.unlink(missing_ok=True)


def _read_native_permissions(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the native document and the mapping containing its permission fields."""

    if path.suffix == ".json":
        try:
            payload = load_json_state(path)
        except RuntimeError:
            payload = {}
        permissions = payload.get("permissions")
        return payload, permissions if isinstance(permissions, dict) else {}
    payload = load_toml_state(path, repair_invalid=True)
    return payload, payload
