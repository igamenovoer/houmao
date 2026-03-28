"""Schema and boundary validation helpers for the demo config."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .boundary_models import DemoConfigDocumentV1, DemoConfigOverrideV1


DEMO_CONFIG_SCHEMA = "demo_config.v1.schema.json"


def load_schema(schema_name: str = DEMO_CONFIG_SCHEMA) -> dict[str, Any]:
    """Load one packaged JSON Schema for the demo pack."""

    if not schema_name.endswith(".json"):
        raise ValueError(f"Schema name must be a JSON file name, got {schema_name!r}")

    package_files = resources.files("houmao.demo.legacy.shared_tui_tracking_demo_pack.schemas")
    schema_path = package_files / schema_name
    if not schema_path.is_file():
        raise ValueError(f"Unknown schema: {schema_name}")

    loaded = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Schema {schema_name} must be a JSON object")
    return loaded


def validate_demo_config_document(
    *,
    payload: dict[str, Any],
    config_path: Path,
) -> DemoConfigDocumentV1:
    """Validate one full demo-config payload."""

    try:
        return DemoConfigDocumentV1.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(
            f"Demo config {config_path} is invalid: {_format_validation_error(exc)}"
        ) from exc


def validate_demo_config_override(
    *,
    payload: dict[str, Any],
    context: str,
) -> DemoConfigOverrideV1:
    """Validate one override fragment used by config resolution."""

    try:
        return DemoConfigOverrideV1.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(
            f"Demo config override {context} is invalid: {_format_validation_error(exc)}"
        ) from exc


def _format_validation_error(error: ValidationError) -> str:
    """Return one compact validation-error summary."""

    messages: list[str] = []
    for item in error.errors(include_url=False):
        path = _format_error_path(item.get("loc", ()))
        message = str(item.get("msg", "validation error"))
        messages.append(f"{path}: {message}")
    return "; ".join(messages)


def _format_error_path(location: tuple[Any, ...] | list[Any]) -> str:
    """Render one Pydantic error path using JSON-style roots."""

    parts = ["$"]
    for component in location:
        if isinstance(component, int):
            parts.append(f"[{component}]")
            continue
        parts.append(f".{component}")
    return "".join(parts)
