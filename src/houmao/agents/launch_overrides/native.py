"""Recognize native permission aliases and managed startup controls."""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def native_setup_permissions(tool: str, setup: Path) -> dict[str, Any]:
    """Read supported permission keys from the selected setup baseline."""

    if tool == "claude":
        path = setup / "settings.json"
        if path.is_file():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise ValueError(f"{path}: cannot read native permission settings") from exc
            permissions = config.get("permissions") if isinstance(config, dict) else None
            if isinstance(permissions, dict) and "defaultMode" in permissions:
                return {"permission_mode": permissions["defaultMode"]}
    if tool in {"codex", "kimi"}:
        path = setup / "config.toml"
        if path.is_file():
            try:
                with path.open("rb") as stream:
                    config = tomllib.load(stream)
            except ValueError as exc:
                raise ValueError(f"{path}: cannot read native permission settings") from exc
            if tool == "kimi":
                return (
                    {"permission_mode": config["default_permission_mode"]}
                    if "default_permission_mode" in config
                    else {}
                )
            return {
                key: config[key] for key in ("approval_policy", "sandbox_mode") if key in config
            }
    return {}


_FLAGS_WITH_VALUE: Mapping[str, Mapping[str, str]] = {
    "claude": {"--permission-mode": "permission_mode"},
    "codex": {
        "-a": "approval_policy",
        "--ask-for-approval": "approval_policy",
        "-s": "sandbox_mode",
        "--sandbox": "sandbox_mode",
    },
    "dsh": {"--approval-policy": "approval", "--permission-mode": "preset"},
}
_DSH_PRESET_APPROVAL = {"workspace-write": "ask", "danger-full-access": "never"}
_PERMISSION_SWITCHES: Mapping[str, Mapping[str, Mapping[str, str]]] = {
    "claude": {
        "--dangerously-skip-permissions": {"permission_mode": "bypassPermissions"},
    },
    "codex": {
        "--dangerously-bypass-approvals-and-sandbox": {
            "approval_policy": "never",
            "sandbox_mode": "danger-full-access",
        },
        "--yolo": {"approval_policy": "never", "sandbox_mode": "danger-full-access"},
        "--approve-for-me": {"approval_policy": "on-request", "sandbox_mode": "workspace-write"},
        "--not-so-yolo": {"approval_policy": "on-request", "sandbox_mode": "workspace-write"},
    },
    "kimi": {
        "--auto": {"permission_mode": "auto"},
        "--yolo": {"permission_mode": "yolo"},
        "-y": {"permission_mode": "yolo"},
    },
}


def split_permission_args(
    tool: str, args: tuple[str, ...], *, source: str, backend: str | None = None
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Lift recognized permission options while preserving other argument groups."""

    remaining: list[str] = []
    permissions: dict[str, Any] = {}
    values = _FLAGS_WITH_VALUE.get(tool, {})
    switches = _PERMISSION_SWITCHES.get(tool, {})
    index = 0
    while index < len(args):
        argument = args[index]
        option, separator, value = argument.partition("=")
        if option == "--":
            remaining.extend(args[index:])
            break
        if tool == "codex" and len(option) > 2 and option[:2] in {"-a", "-c", "-s"}:
            option, separator, value = option[:2], "=", argument[2:]
        config_option = tool == "codex" and option in {"-c", "--config"}
        if option in values or config_option:
            width = 1 if separator else 2
            if not separator:
                if index + 1 == len(args) or args[index + 1].startswith("-"):
                    raise ValueError(f"{source} {option}: expected a value")
                value = args[index + 1]
            if config_option:
                key, assignment, raw = value.partition("=")
                key = key.strip().strip("\"'")
                if assignment and key == "developer_instructions" and backend is not None:
                    raise ValueError(
                        f"{source} contains backend-reserved Codex config setting `{key}` "
                        f"for backend={backend!r}. Houmao projects the managed role prompt."
                    )
                if assignment and key in {"approval_policy", "sandbox_mode"}:
                    permissions[key] = _codex_config_value(raw)
                else:
                    remaining.extend(args[index : index + width])
            elif tool == "dsh":
                dsh_permissions = permissions.setdefault("permissions", {})
                if option == "--permission-mode":
                    approval = _DSH_PRESET_APPROVAL.get(value)
                    if approval is None:
                        raise ValueError(
                            f"{source} {option}: use a supported built-in DSH preset "
                            "or set tool_params.permissions directly"
                        )
                    dsh_permissions.update(sandbox=value, approval=approval)
                else:
                    dsh_permissions["approval"] = value
            else:
                permissions[values[option]] = value
            index += width
            continue
        if argument in switches:
            permissions.update(switches[argument])
            if tool == "codex" and argument in {"--approve-for-me", "--not-so-yolo"}:
                remaining.append('--config=approvals_reviewer="auto_review"')
        else:
            remaining.append(argument)
        index += 1
    return tuple(remaining), permissions


def _codex_config_value(raw: str) -> Any:
    """Accept a TOML expression or a bare native string."""

    try:
        return tomllib.loads(f"value = {raw}")["value"]
    except tomllib.TOMLDecodeError:
        return raw.strip().strip("\"'")
