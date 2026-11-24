"""Resolve native Kimi configuration before preparing a managed home."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path
import tomllib
from typing import Any

from houmao.agents.definition_parser import ToolAdapter

KIMI_CONFIG_FILENAME = "config.toml"
_ATOMIC_ENTRY_TABLES = frozenset({"providers", "models", "services"})


def load_kimi_config(path: Path) -> dict[str, Any]:
    """Read optional native TOML without including its contents in diagnostics."""

    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        raise ValueError(f"Could not read Kimi TOML configuration at `{path}`.") from None


def resolve_kimi_config(*, setup_dir: Path, auth_dir: Path, adapter: ToolAdapter) -> dict[str, Any]:
    """Overlay adapter-mapped credential config on the native setup config."""

    config = (
        load_kimi_config(setup_dir / KIMI_CONFIG_FILENAME)
        if Path(adapter.setup_destination) == Path(".")
        else {}
    )
    for mapping in adapter.auth_file_mappings:
        if Path(mapping.destination) == Path(KIMI_CONFIG_FILENAME):
            credential = load_kimi_config(auth_dir / adapter.auth_files_dir / mapping.source)
            config = _overlay_kimi_config(config, credential)
    if "thinking" in config and not isinstance(config["thinking"], dict):
        raise ValueError("Kimi config.toml requires a table for `thinking`.")
    return config


def select_kimi_model_alias(config: Mapping[str, Any], model_name: str | None = None) -> str | None:
    """Resolve an explicit or native default model through the TOML catalog."""

    selected = model_name if model_name is not None else config.get("default_model")
    if selected is None:
        return None
    if not isinstance(selected, str) or not selected.strip():
        raise ValueError("Kimi config.toml requires a non-empty `default_model` alias.")
    models = config.get("models")
    if not isinstance(models, dict) or not isinstance(models.get(selected), dict):
        raise ValueError(f"Kimi model alias `{selected}` is absent from config.toml `models`.")
    return selected


def validate_kimi_config_credentials(
    config: Mapping[str, Any],
    env_values: Mapping[str, str],
    allowlist: Collection[str],
) -> frozenset[str]:
    """Return private API key references satisfied by the selected credential input."""

    providers = config.get("providers", {})
    if not isinstance(providers, dict):
        raise ValueError("Kimi config.toml requires a table for `providers`.")
    references = set[str]()
    for alias, provider in providers.items():
        if not isinstance(provider, dict) or "api_key_env" not in provider:
            continue
        reference = provider["api_key_env"]
        if not isinstance(reference, str) or reference not in allowlist:
            raise ValueError(
                f"Kimi provider `{alias}` requires an allowlisted `api_key_env` reference."
            )
        if not env_values.get(reference, "").strip():
            raise ValueError(f"Kimi provider `{alias}` requires private credential `{reference}`.")
        references.add(reference)
    return frozenset(references)


def _overlay_kimi_config(
    setup: dict[str, Any], credential: dict[str, Any], *, root: bool = True
) -> dict[str, Any]:
    """Recursively overlay tables and replace provider, model, and service entries."""

    merged = dict(setup)
    for key, value in credential.items():
        baseline = merged.get(key)
        if isinstance(baseline, dict) and isinstance(value, dict):
            if root and key in _ATOMIC_ENTRY_TABLES:
                merged[key] = {**baseline, **value}
            else:
                merged[key] = _overlay_kimi_config(baseline, value, root=False)
        else:
            merged[key] = value
    return merged


def kimi_launch_diagnostic_secrets(environment: Mapping[str, str]) -> tuple[str, ...]:
    """Collect known Kimi credential values for native diagnostic redaction."""

    secrets = {
        value
        for name, value in environment.items()
        if name.startswith("KIMI_") and ("TOKEN" in name or "API_KEY" in name) and value
    }
    home = environment.get("KIMI_CODE_HOME")
    if not home:
        return tuple(sorted(secrets))
    try:
        config = load_kimi_config(Path(home) / KIMI_CONFIG_FILENAME)
    except ValueError:
        return tuple(sorted(secrets))
    for table in ("providers", "services"):
        entries = config.get(table)
        if not isinstance(entries, dict):
            continue
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            key = entry.get("api_key")
            if isinstance(key, str) and key:
                secrets.add(key)
            reference = entry.get("api_key_env")
            if isinstance(reference, str) and environment.get(reference):
                secrets.add(environment[reference])
            for field in ("env", "custom_headers"):
                values = entry.get(field)
                if isinstance(values, dict):
                    secrets.update(value for value in values.values() if isinstance(value, str))
    secrets.discard("")
    return tuple(sorted(secrets))
