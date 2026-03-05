"""JSON Schema loading and lightweight validation helpers."""

from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any

from .errors import SchemaValidationError


def load_schema(schema_name: str) -> dict[str, Any]:
    """Load a packaged JSON Schema document.

    Parameters
    ----------
    schema_name:
        File name under `schemas/`.

    Returns
    -------
    dict[str, Any]
        Parsed JSON Schema.
    """

    if not schema_name.endswith(".json"):
        raise SchemaValidationError(
            f"Schema name must be a JSON file name, got {schema_name!r}"
        )

    package_files = resources.files(
        "gig_agents.agents.brain_launch_runtime.schemas"
    )
    schema_path = package_files / schema_name
    if not schema_path.is_file():
        raise SchemaValidationError(f"Unknown schema: {schema_name}")

    with schema_path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)

    if not isinstance(loaded, dict):
        raise SchemaValidationError(f"Schema {schema_name} must be a JSON object")
    return loaded


def validate_payload(payload: Any, schema_name: str) -> None:
    """Validate a payload against a packaged schema.

    Parameters
    ----------
    payload:
        Runtime-generated structured payload.
    schema_name:
        Schema file name under `schemas/`.

    Raises
    ------
    SchemaValidationError
        If validation fails.
    """

    schema = load_schema(schema_name)
    _validate_node(payload, schema, path="$")


def _validate_node(value: Any, schema: dict[str, Any], *, path: str) -> None:
    if "const" in schema and value != schema["const"]:
        raise SchemaValidationError(f"{path}: expected const value {schema['const']!r}")

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        raise SchemaValidationError(f"{path}: expected one of {enum!r}, got {value!r}")

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        raise SchemaValidationError(
            f"{path}: expected type {expected_type!r}, got {type(value).__name__}"
        )

    if isinstance(value, dict):
        _validate_object(value, schema, path=path)
    elif isinstance(value, list):
        _validate_array(value, schema, path=path)
    elif isinstance(value, str):
        _validate_string(value, schema, path=path)


def _validate_object(
    value: dict[str, Any], schema: dict[str, Any], *, path: str
) -> None:
    required = schema.get("required", [])
    if isinstance(required, list):
        for key in required:
            if key not in value:
                raise SchemaValidationError(f"{path}: missing required field `{key}`")

    properties = schema.get("properties")
    if properties is None:
        return
    if not isinstance(properties, dict):
        raise SchemaValidationError(f"{path}: schema `properties` must be an object")

    additional = schema.get("additionalProperties", True)
    if additional is False:
        unknown = sorted(set(value.keys()) - set(properties.keys()))
        if unknown:
            raise SchemaValidationError(
                f"{path}: unknown field(s): {', '.join(unknown)}"
            )

    for key, property_schema in properties.items():
        if key not in value:
            continue
        if not isinstance(property_schema, dict):
            raise SchemaValidationError(
                f"{path}.{key}: property schema must be an object"
            )
        _validate_node(value[key], property_schema, path=f"{path}.{key}")


def _validate_array(value: list[Any], schema: dict[str, Any], *, path: str) -> None:
    min_items = schema.get("minItems")
    if isinstance(min_items, int) and len(value) < min_items:
        raise SchemaValidationError(
            f"{path}: expected at least {min_items} item(s), got {len(value)}"
        )

    items = schema.get("items")
    if items is None:
        return
    if not isinstance(items, dict):
        raise SchemaValidationError(f"{path}: schema `items` must be an object")

    for idx, item in enumerate(value):
        _validate_node(item, items, path=f"{path}[{idx}]")


def _validate_string(value: str, schema: dict[str, Any], *, path: str) -> None:
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and re.search(pattern, value) is None:
        raise SchemaValidationError(f"{path}: value does not match pattern {pattern!r}")


def _matches_type(value: Any, expected_type: str | list[str]) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(value, item) for item in expected_type)

    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(
            value, float
        )
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return False
