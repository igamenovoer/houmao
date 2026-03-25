"""Typed launch-override models and declarative tool metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, TypeAlias, cast

LaunchArgsMode: TypeAlias = Literal["append", "replace"]
SupportedLaunchBackend: TypeAlias = Literal[
    "raw_launch",
    "codex_headless",
    "codex_app_server",
    "claude_headless",
    "gemini_headless",
    "cao_rest",
    "houmao_server_rest",
]
ToolParamValueType: TypeAlias = Literal["boolean"]
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

_SUPPORTED_LAUNCH_BACKENDS: Final[frozenset[str]] = frozenset(
    {
        "raw_launch",
        "codex_headless",
        "codex_app_server",
        "claude_headless",
        "gemini_headless",
        "cao_rest",
        "houmao_server_rest",
    }
)
_SUPPORTED_TOOL_PARAM_TYPES: Final[frozenset[str]] = frozenset({"boolean"})


def parse_launch_overrides(payload: object, *, source: str) -> LaunchOverrides:
    """Parse one launch-overrides payload."""

    return LaunchOverrides.from_payload(payload, source=source)


def parse_launch_defaults(payload: object, *, source: str) -> LaunchDefaults:
    """Parse one launch-defaults payload."""

    return LaunchDefaults.from_payload(payload, source=source)


def parse_tool_launch_metadata(payload: object, *, source: str) -> ToolLaunchMetadata:
    """Parse one tool-launch metadata payload."""

    return ToolLaunchMetadata.from_payload(payload, source=source)


def clone_json_mapping(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Return a deep copy of one JSON-compatible mapping."""

    return {key: _clone_json_value(value) for key, value in payload.items()}


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
    tool_params: dict[str, JsonValue] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: object, *, source: str) -> LaunchOverrides:
        """Parse one launch-overrides mapping."""

        mapping = _require_mapping(payload, source=source)
        args_payload = mapping.get("args")
        args = (
            LaunchArgsSection.from_payload(args_payload, source=f"{source}.args")
            if args_payload is not None
            else None
        )
        raw_tool_params = mapping.get("tool_params")
        if raw_tool_params is None:
            tool_params: dict[str, JsonValue] = {}
        else:
            tool_params_mapping = _require_mapping(
                raw_tool_params,
                source=f"{source}.tool_params",
            )
            tool_params = {}
            for key, value in tool_params_mapping.items():
                if not key.strip():
                    raise ValueError(f"{source}.tool_params contains a blank key")
                tool_params[key] = _normalize_json_value(
                    value,
                    source=f"{source}.tool_params.{key}",
                )
        instance = cls(args=args, tool_params=tool_params)
        if instance.is_empty():
            raise ValueError(f"{source} must declare `args` or `tool_params`")
        return instance

    def is_empty(self) -> bool:
        """Return whether the payload contains no sections."""

        return self.args is None and not self.tool_params

    def to_payload(self) -> dict[str, object]:
        """Serialize one launch-overrides mapping."""

        payload: dict[str, object] = {}
        if self.args is not None:
            payload["args"] = self.args.to_payload()
        if self.tool_params:
            payload["tool_params"] = clone_json_mapping(self.tool_params)
        return payload


@dataclass(frozen=True)
class LaunchDefaults:
    """Adapter-owned default launch state."""

    args: tuple[str, ...] = ()
    tool_params: dict[str, JsonValue] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: object, *, source: str) -> LaunchDefaults:
        """Parse one defaults payload."""

        mapping = _require_mapping(payload, source=source)
        args = _require_string_tuple(mapping.get("args"), source=f"{source}.args")
        raw_tool_params = mapping.get("tool_params")
        if raw_tool_params is None:
            tool_params: dict[str, JsonValue] = {}
        else:
            tool_params_mapping = _require_mapping(
                raw_tool_params,
                source=f"{source}.tool_params",
            )
            tool_params = {}
            for key, value in tool_params_mapping.items():
                if not key.strip():
                    raise ValueError(f"{source}.tool_params contains a blank key")
                tool_params[key] = _normalize_json_value(
                    value,
                    source=f"{source}.tool_params.{key}",
                )
        return cls(args=args, tool_params=tool_params)

    def to_payload(self) -> dict[str, object]:
        """Serialize one defaults payload."""

        return {
            "args": list(self.args),
            "tool_params": clone_json_mapping(self.tool_params),
        }


@dataclass(frozen=True)
class ToolParamBackendProjection:
    """Backend-specific projection for one typed tool param."""

    args_when_true: tuple[str, ...] = ()
    args_when_false: tuple[str, ...] = ()

    @classmethod
    def from_payload(
        cls,
        payload: object,
        *,
        source: str,
    ) -> ToolParamBackendProjection:
        """Parse one backend projection."""

        mapping = _require_mapping(payload, source=source)
        args_when_true = _require_string_tuple(
            mapping.get("args_when_true"),
            source=f"{source}.args_when_true",
        )
        args_when_false = _require_string_tuple(
            mapping.get("args_when_false"),
            source=f"{source}.args_when_false",
        )
        return cls(args_when_true=args_when_true, args_when_false=args_when_false)

    def project(self, value: JsonValue, *, source: str) -> tuple[str, ...]:
        """Translate one validated value into backend args."""

        if not isinstance(value, bool):
            raise ValueError(f"{source} must be boolean for this projection")
        return self.args_when_true if value else self.args_when_false

    def to_payload(self) -> dict[str, object]:
        """Serialize one backend projection."""

        payload: dict[str, object] = {}
        if self.args_when_true:
            payload["args_when_true"] = list(self.args_when_true)
        if self.args_when_false:
            payload["args_when_false"] = list(self.args_when_false)
        return payload


@dataclass(frozen=True)
class ToolParamDefinition:
    """Declarative definition for one typed tool param."""

    value_type: ToolParamValueType
    backends: dict[SupportedLaunchBackend, ToolParamBackendProjection] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: object, *, source: str) -> ToolParamDefinition:
        """Parse one tool-param definition."""

        mapping = _require_mapping(payload, source=source)
        value_type = _require_non_empty_string(mapping.get("type"), source=f"{source}.type")
        if value_type not in _SUPPORTED_TOOL_PARAM_TYPES:
            raise ValueError(
                f"{source}.type must be one of {sorted(_SUPPORTED_TOOL_PARAM_TYPES)}, got "
                f"{value_type!r}"
            )
        raw_backends = _require_mapping(mapping.get("backends"), source=f"{source}.backends")
        backends: dict[SupportedLaunchBackend, ToolParamBackendProjection] = {}
        for backend_name, backend_payload in raw_backends.items():
            if backend_name not in _SUPPORTED_LAUNCH_BACKENDS:
                raise ValueError(
                    f"{source}.backends.{backend_name} is unsupported; expected one of "
                    f"{sorted(_SUPPORTED_LAUNCH_BACKENDS)}"
                )
            backends[cast(SupportedLaunchBackend, backend_name)] = (
                ToolParamBackendProjection.from_payload(
                    backend_payload,
                    source=f"{source}.backends.{backend_name}",
                )
            )
        return cls(
            value_type=cast(ToolParamValueType, value_type),
            backends=backends,
        )

    def validate_value(self, value: JsonValue, *, source: str) -> None:
        """Validate one requested value against the declared type."""

        if self.value_type == "boolean":
            if isinstance(value, bool):
                return
            raise ValueError(f"{source} must be boolean, got {type(value).__name__}")
        raise ValueError(f"{source}: unsupported tool param type {self.value_type!r}")

    def to_payload(self) -> dict[str, object]:
        """Serialize one tool-param definition."""

        return {
            "type": self.value_type,
            "backends": {
                backend: projection.to_payload()
                for backend, projection in sorted(self.backends.items())
            },
        }


@dataclass(frozen=True)
class ToolLaunchMetadata:
    """Declarative metadata for tool-specific launch params."""

    tool_params: dict[str, ToolParamDefinition] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: object, *, source: str) -> ToolLaunchMetadata:
        """Parse one tool-launch metadata payload."""

        mapping = _require_mapping(payload, source=source)
        raw_tool_params = mapping.get("tool_params")
        if raw_tool_params is None:
            return cls(tool_params={})
        tool_params_mapping = _require_mapping(
            raw_tool_params,
            source=f"{source}.tool_params",
        )
        tool_params: dict[str, ToolParamDefinition] = {}
        for key, value in tool_params_mapping.items():
            if not key.strip():
                raise ValueError(f"{source}.tool_params contains a blank key")
            tool_params[key] = ToolParamDefinition.from_payload(
                value,
                source=f"{source}.tool_params.{key}",
            )
        return cls(tool_params=tool_params)

    def validate_requested_tool_params(
        self,
        *,
        tool: str,
        tool_params: dict[str, JsonValue],
        source: str,
    ) -> None:
        """Validate one requested tool-params mapping."""

        if not tool_params:
            return
        if not self.tool_params:
            raise ValueError(
                f"{source}: tool `{tool}` exposes no supported `launch_overrides.tool_params` in v1"
            )
        for key, value in tool_params.items():
            definition = self.tool_params.get(key)
            if definition is None:
                supported = ", ".join(sorted(self.tool_params))
                raise ValueError(
                    f"{source}: unsupported `launch_overrides.tool_params.{key}` for tool "
                    f"`{tool}`. Supported keys: {supported}"
                )
            definition.validate_value(value, source=f"{source}.{key}")

    def to_payload(self) -> dict[str, object]:
        """Serialize one tool-launch metadata payload."""

        return {
            "tool_params": {
                key: definition.to_payload() for key, definition in sorted(self.tool_params.items())
            }
        }


def _clone_json_value(value: JsonValue) -> JsonValue:
    """Return a deep copy of one JSON-compatible value."""

    if isinstance(value, list):
        return [_clone_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _clone_json_value(item) for key, item in value.items()}
    return value


def _normalize_json_value(value: object, *, source: str) -> JsonValue:
    """Normalize one JSON-compatible value."""

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, list):
        return [
            _normalize_json_value(item, source=f"{source}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        normalized: dict[str, JsonValue] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{source} must use string keys, got {type(key).__name__}")
            normalized[key] = _normalize_json_value(child, source=f"{source}.{key}")
        return normalized
    raise ValueError(f"{source} must be JSON-compatible, got {type(value).__name__}")


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
