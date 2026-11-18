"""Typed models for raw launch argument overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias, cast

LaunchArgsMode: TypeAlias = Literal["append", "replace"]
SupportedLaunchBackend: TypeAlias = Literal[
    "raw_launch",
    "codex_headless",
    "codex_app_server",
    "claude_headless",
    "kimi_headless",
    "dsh_acp",
    "dsh_web",
    "cao_rest",
]


def parse_launch_overrides(payload: object, *, source: str) -> LaunchOverrides:
    """Parse one launch-overrides payload."""

    return LaunchOverrides.from_payload(payload, source=source)


def parse_launch_defaults(payload: object, *, source: str) -> LaunchDefaults:
    """Parse one launch-defaults payload."""

    return LaunchDefaults.from_payload(payload, source=source)


@dataclass(frozen=True)
class LaunchArgsSection:
    """Structured args override section."""

    mode: LaunchArgsMode
    values: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: object, *, source: str) -> LaunchArgsSection:
        """Parse one args section."""

        mapping = _require_mapping(payload, source=source)
        mode = _require_non_empty_string(mapping.get("mode"), source=f"{source}.mode")
        if mode not in {"append", "replace"}:
            raise ValueError(f"{source}.mode must be `append` or `replace`, got {mode!r}")
        values = _require_string_tuple(mapping.get("values"), source=f"{source}.values")
        return cls(mode=cast(LaunchArgsMode, mode), values=values)

    def to_payload(self) -> dict[str, object]:
        """Serialize one args section."""

        return {"mode": self.mode, "values": list(self.values)}


@dataclass(frozen=True)
class LaunchOverrides:
    """Recipe or direct-build launch overrides."""

    args: LaunchArgsSection | None = None

    @classmethod
    def from_payload(cls, payload: object, *, source: str) -> LaunchOverrides:
        """Parse one launch-overrides mapping."""

        mapping = _require_mapping(payload, source=source)
        if "tool_params" in mapping:
            raise ValueError(
                f"{source}.tool_params was removed. Use separate top-level tool_params."
            )
        if mapping.get("args") is None:
            raise ValueError(f"{source} must declare `args`")
        return cls(args=LaunchArgsSection.from_payload(mapping["args"], source=f"{source}.args"))

    def is_empty(self) -> bool:
        """Return whether the payload contains no sections."""

        return self.args is None

    def to_payload(self) -> dict[str, object]:
        """Serialize one launch-overrides mapping."""

        payload: dict[str, object] = {}
        if self.args is not None:
            payload["args"] = self.args.to_payload()
        return payload


@dataclass(frozen=True)
class LaunchDefaults:
    """Adapter-owned default launch state."""

    args: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: object, *, source: str) -> LaunchDefaults:
        """Parse one defaults payload."""

        mapping = _require_mapping(payload, source=source)
        if mapping.get("tool_params") not in (None, {}):
            raise ValueError(
                f"{source}.tool_params was removed. Rebuild with separate tool_params."
            )
        return cls(args=_require_string_tuple(mapping.get("args"), source=f"{source}.args"))

    def to_payload(self) -> dict[str, object]:
        """Serialize one defaults payload."""

        return {"args": list(self.args)}


def _require_mapping(payload: object, *, source: str) -> dict[str, object]:
    """Require one mapping payload."""

    if not isinstance(payload, dict):
        raise ValueError(f"{source} must be a mapping")
    return cast(dict[str, object], payload)


def _require_non_empty_string(value: object, *, source: str) -> str:
    """Require one non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source} must be a non-empty string")
    return value.strip()


def _require_string_tuple(value: object, *, source: str) -> tuple[str, ...]:
    """Require one tuple of strings."""

    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{source} must be a list of strings")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{source}[{index}] must be a string")
        normalized.append(item)
    return tuple(normalized)
