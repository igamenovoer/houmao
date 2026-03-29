"""Helpers for persistent and one-off launch environment records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os


_HOUMAO_RESERVED_ENV_PREFIXES: tuple[str, ...] = ("AGENTSYS_", "HOUMAO_")


def parse_persistent_env_record_specs(
    values: Sequence[str],
    *,
    option_name: str = "--env-set",
) -> dict[str, str]:
    """Parse literal persistent env specs from CLI input.

    Parameters
    ----------
    values:
        Raw repeated CLI values.
    option_name:
        Flag name for operator-facing errors.

    Returns
    -------
    dict[str, str]
        Parsed env-record mapping in input order.
    """

    records: dict[str, str] = {}
    for raw_value in values:
        if "=" not in raw_value:
            raise ValueError(
                f"`{option_name}` for specialist launch config requires `NAME=value`, got {raw_value!r}."
            )
        name, value = raw_value.split("=", 1)
        normalized_name = _normalized_env_name(name, option_name=option_name, raw_value=raw_value)
        if normalized_name in records:
            raise ValueError(f"Duplicate `{option_name}` env name `{normalized_name}`.")
        records[normalized_name] = value
    return records


def resolve_runtime_env_set_specs(
    values: Sequence[str],
    *,
    option_name: str = "--env-set",
    process_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve one-off runtime env specs from CLI input.

    Parameters
    ----------
    values:
        Raw repeated CLI values.
    option_name:
        Flag name for operator-facing errors.
    process_env:
        Environment used to resolve inherited bindings. Defaults to `os.environ`.

    Returns
    -------
    dict[str, str]
        Resolved env-value mapping in input order.
    """

    resolved_process_env = process_env if process_env is not None else os.environ
    resolved: dict[str, str] = {}
    for raw_value in values:
        if "=" in raw_value:
            name, value = raw_value.split("=", 1)
            normalized_name = _normalized_env_name(name, option_name=option_name, raw_value=raw_value)
            if normalized_name in resolved:
                raise ValueError(f"Duplicate `{option_name}` env name `{normalized_name}`.")
            resolved[normalized_name] = value
            continue
        normalized_name = _normalized_env_name(
            raw_value,
            option_name=option_name,
            raw_value=raw_value,
        )
        if normalized_name in resolved:
            raise ValueError(f"Duplicate `{option_name}` env name `{normalized_name}`.")
        inherited_value = resolved_process_env.get(normalized_name)
        if inherited_value is None:
            raise ValueError(
                f"`{option_name}` inherited binding `{normalized_name}` is not set in the invoking environment."
            )
        resolved[normalized_name] = inherited_value
    return resolved


def validate_persistent_env_records(
    env_records: Mapping[str, str],
    *,
    auth_env_allowlist: Sequence[str],
    source: str,
) -> dict[str, str]:
    """Validate durable specialist-owned env records.

    Parameters
    ----------
    env_records:
        Candidate persistent env mapping.
    auth_env_allowlist:
        Credential-owned env names reserved by the selected tool adapter.
    source:
        Error-source prefix.

    Returns
    -------
    dict[str, str]
        Normalized validated env mapping.
    """

    normalized: dict[str, str] = {}
    auth_names = {name.strip() for name in auth_env_allowlist if name.strip()}
    for raw_name, raw_value in env_records.items():
        normalized_name = _normalized_env_name(
            raw_name,
            option_name=source,
            raw_value=str(raw_name),
        )
        if normalized_name in normalized:
            raise ValueError(f"{source}: duplicate env name `{normalized_name}`.")
        if _is_houmao_reserved_env_name(normalized_name):
            raise ValueError(f"{source}: `{normalized_name}` is reserved for Houmao-owned runtime env.")
        if normalized_name in auth_names:
            raise ValueError(
                f"{source}: `{normalized_name}` belongs to credential env for the selected tool."
            )
        normalized[normalized_name] = _validated_env_value(
            raw_value,
            source=source,
            env_name=normalized_name,
        )
    return normalized


def _normalized_env_name(name: str, *, option_name: str, raw_value: str) -> str:
    """Return one normalized env name or raise."""

    normalized = name.strip()
    if not normalized:
        raise ValueError(f"Invalid `{option_name}` env spec `{raw_value}`.")
    return normalized


def _validated_env_value(value: object, *, source: str, env_name: str) -> str:
    """Validate one persistent env value."""

    if not isinstance(value, str):
        raise ValueError(f"{source}: env value for `{env_name}` must be a string.")
    return value


def _is_houmao_reserved_env_name(name: str) -> bool:
    """Return whether one env name is reserved by Houmao-owned runtime state."""

    return any(name.startswith(prefix) for prefix in _HOUMAO_RESERVED_ENV_PREFIXES)
