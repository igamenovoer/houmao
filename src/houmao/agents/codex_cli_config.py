"""Helpers for Codex CLI `--config` override arguments."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias, TypeGuard

CodexCliConfigScalar: TypeAlias = str | bool | int

_CODEX_PROVIDER_OVERRIDE_FIELDS: tuple[str, ...] = (
    "name",
    "base_url",
    "env_key",
    "env_key_instructions",
    "requires_openai_auth",
    "wire_api",
)
_SECRET_KEY_SEGMENTS: frozenset[str] = frozenset(
    {
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "password",
        "secret",
        "token",
    }
)
_SECRET_VALUE_MARKERS: tuple[str, ...] = (
    "sk-",
    "bearer ",
    "access_token",
    "refresh_token",
    "id_token",
    "session_token",
    "token=",
    "cookie:",
    "set-cookie",
    "auth.json",
)


@dataclass(frozen=True)
class CodexCliConfigOverride:
    """One secret-free Codex CLI config override."""

    key_path: tuple[str, ...]
    value: CodexCliConfigScalar

    def __post_init__(self) -> None:
        """Validate the override payload."""

        if not self.key_path:
            raise ValueError("Codex CLI config override key_path must not be empty.")
        for key in self.key_path:
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Codex CLI config override key_path entries must be non-empty.")
        if not isinstance(self.value, (str, bool, int)):
            raise ValueError("Codex CLI config override value must be a TOML scalar.")
        _validate_secret_free_key_path(self.key_path)
        _validate_secret_free_value(self.value)

    @classmethod
    def from_raw(
        cls,
        key_path: Iterable[str],
        value: CodexCliConfigScalar,
    ) -> CodexCliConfigOverride:
        """Build an override from an arbitrary iterable key path."""

        return cls(key_path=tuple(key_path), value=value)

    @property
    def rendered_key_path(self) -> str:
        """Return the TOML dotted key path used by Codex `--config`."""

        return render_codex_config_key_path(self.key_path)

    def to_arg(self) -> str:
        """Return one `--config=key=value` CLI argument."""

        return f"--config={self.rendered_key_path}={render_codex_config_scalar_value(self.value)}"

    def to_payload(self) -> dict[str, Any]:
        """Return a secret-free metadata payload."""

        return {
            "key_path": list(self.key_path),
            "value": self.value,
            "arg": self.to_arg(),
        }


def render_codex_config_key_path(key_path: Iterable[str]) -> str:
    """Render one TOML dotted key path for Codex CLI config overrides."""

    parts = tuple(key_path)
    if not parts:
        raise ValueError("Codex CLI config override key_path must not be empty.")
    return ".".join(_render_toml_key_part(part) for part in parts)


def render_codex_config_scalar_value(value: CodexCliConfigScalar) -> str:
    """Render one TOML scalar value for Codex CLI config overrides."""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    raise TypeError(f"Unsupported Codex CLI config scalar: {value!r}")


def codex_config_override_arg(
    key_path: Iterable[str],
    value: CodexCliConfigScalar,
) -> str:
    """Return one Codex `--config=key=value` CLI argument."""

    return CodexCliConfigOverride.from_raw(key_path, value).to_arg()


def codex_config_override_args(
    overrides: Iterable[CodexCliConfigOverride],
) -> list[str]:
    """Return CLI arguments for a sequence of Codex config overrides."""

    return [override.to_arg() for override in overrides]


def codex_config_override_payload(
    overrides: Iterable[CodexCliConfigOverride],
) -> dict[str, Any]:
    """Return manifest-friendly metadata for Codex config overrides."""

    override_tuple = tuple(overrides)
    return {
        "args": codex_config_override_args(override_tuple),
        "overrides": [override.to_payload() for override in override_tuple],
    }


def append_or_replace_codex_config_overrides(
    args: list[str],
    overrides: Iterable[CodexCliConfigOverride],
) -> None:
    """Remove existing overrides for the same keys and append final replacements."""

    override_tuple = tuple(overrides)
    if not override_tuple:
        return

    target_keys = {override.rendered_key_path for override in override_tuple}
    canonicalized: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        next_token = args[index + 1] if index + 1 < len(args) else None

        if token.startswith("--config="):
            if _raw_config_override_key(token.partition("=")[2]) in target_keys:
                index += 1
                continue
        elif token in {"-c", "--config"} and next_token is not None:
            if _raw_config_override_key(next_token) in target_keys:
                index += 2
                continue

        canonicalized.append(token)
        index += 1

    args[:] = [*canonicalized, *codex_config_override_args(override_tuple)]


def codex_provider_cli_config_overrides(
    config_payload: Mapping[str, Any],
) -> tuple[CodexCliConfigOverride, ...]:
    """Return secret-free CLI overrides for a selected Codex provider config."""

    model_provider = _non_empty_str(config_payload.get("model_provider"))
    if model_provider is None:
        return ()

    overrides: list[CodexCliConfigOverride] = [
        CodexCliConfigOverride(("model_provider",), model_provider)
    ]
    providers_payload = config_payload.get("model_providers")
    if not isinstance(providers_payload, Mapping):
        return tuple(overrides)
    provider_payload = providers_payload.get(model_provider)
    if not isinstance(provider_payload, Mapping):
        return tuple(overrides)

    for field_name in _CODEX_PROVIDER_OVERRIDE_FIELDS:
        value = provider_payload.get(field_name)
        if _is_supported_scalar(value):
            overrides.append(
                CodexCliConfigOverride(
                    ("model_providers", model_provider, field_name),
                    value,
                )
            )

    return tuple(overrides)


def _render_toml_key_part(value: str) -> str:
    """Render one TOML key path part."""

    if (
        value
        and value[0].isalpha()
        and all(character.isalnum() or character in {"_", "-"} for character in value)
    ):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _raw_config_override_key(raw_override: str) -> str | None:
    """Return the key path from one raw `key=value` override."""

    key, separator, _value = raw_override.partition("=")
    if not separator:
        return None
    stripped = key.strip()
    return stripped if stripped else None


def _is_supported_scalar(value: object) -> TypeGuard[CodexCliConfigScalar]:
    """Return whether a value is safe to serialize as a TOML scalar."""

    return isinstance(value, (str, bool, int))


def _non_empty_str(value: object) -> str | None:
    """Return a stripped non-empty string when available."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _validate_secret_free_key_path(key_path: tuple[str, ...]) -> None:
    """Reject override key paths that clearly target secret-bearing fields."""

    secret_segments = [
        segment
        for segment in key_path
        if segment.strip().lower().replace("-", "_") in _SECRET_KEY_SEGMENTS
    ]
    if secret_segments:
        joined = ".".join(key_path)
        raise ValueError(
            f"Refusing to emit Codex CLI config override for secret-like key path `{joined}`."
        )


def _validate_secret_free_value(value: CodexCliConfigScalar) -> None:
    """Reject string values that look like credentials."""

    if not isinstance(value, str):
        return
    lowered = value.strip().lower()
    if any(marker in lowered for marker in _SECRET_VALUE_MARKERS):
        raise ValueError("Refusing to emit Codex CLI config override with secret-like value.")
