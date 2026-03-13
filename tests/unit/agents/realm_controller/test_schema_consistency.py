from __future__ import annotations

import json
from importlib import resources
from typing import Any

import pytest

from gig_agents.agents.realm_controller.boundary_models import (
    LaunchPlanPayloadV1,
    SessionManifestPayloadV2,
)


@pytest.mark.parametrize(
    ("schema_name", "model"),
    [
        ("launch_plan.v1.schema.json", LaunchPlanPayloadV1),
        ("session_manifest.v2.schema.json", SessionManifestPayloadV2),
    ],
)
def test_packaged_schema_matches_pydantic_model(
    schema_name: str,
    model: type[LaunchPlanPayloadV1] | type[SessionManifestPayloadV2],
) -> None:
    packaged_schema = _load_packaged_schema(schema_name)
    model_schema = model.model_json_schema()
    _assert_schema_alignment(
        packaged_schema=packaged_schema,
        model_schema=model_schema,
        packaged_root=packaged_schema,
        model_root=model_schema,
        path="$",
    )


def _load_packaged_schema(schema_name: str) -> dict[str, Any]:
    schema_path = resources.files("gig_agents.agents.realm_controller.schemas") / schema_name
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _assert_schema_alignment(
    *,
    packaged_schema: dict[str, Any],
    model_schema: dict[str, Any],
    packaged_root: dict[str, Any],
    model_root: dict[str, Any],
    path: str,
) -> None:
    packaged = _resolve_refs(packaged_schema, packaged_root)
    model = _resolve_refs(model_schema, model_root)

    packaged_types = _extract_types(packaged)
    model_types = _extract_types(model)
    if packaged_types:
        assert packaged_types <= model_types, (
            f"{path}: packaged types {packaged_types} are not covered by model types {model_types}"
        )

    if "const" in packaged:
        assert model.get("const") == packaged["const"], (
            f"{path}: const mismatch (packaged={packaged['const']!r}, model={model.get('const')!r})"
        )

    packaged_enum = packaged.get("enum")
    if isinstance(packaged_enum, list):
        model_enum = model.get("enum")
        assert isinstance(model_enum, list), f"{path}: model is missing enum"
        assert set(packaged_enum) == set(model_enum), (
            f"{path}: enum mismatch (packaged={packaged_enum!r}, model={model_enum!r})"
        )

    if "object" in packaged_types:
        packaged_props_raw = packaged.get("properties")
        model_props_raw = model.get("properties")
        packaged_props = packaged_props_raw if isinstance(packaged_props_raw, dict) else {}
        model_props = model_props_raw if isinstance(model_props_raw, dict) else {}

        if isinstance(packaged_props_raw, dict) or isinstance(model_props_raw, dict):
            packaged_required = set(_as_list(packaged.get("required")))
            model_required = set(_as_list(model.get("required")))
            assert packaged_required == model_required, (
                f"{path}: required fields mismatch "
                f"(packaged={sorted(packaged_required)!r}, model={sorted(model_required)!r})"
            )

        if packaged.get("additionalProperties") is False:
            assert model.get("additionalProperties") is False, (
                f"{path}: model must also forbid additionalProperties"
            )

        for key, packaged_child in packaged_props.items():
            assert key in model_props, f"{path}: missing model property `{key}`"
            _assert_schema_alignment(
                packaged_schema=packaged_child,
                model_schema=model_props[key],
                packaged_root=packaged_root,
                model_root=model_root,
                path=f"{path}.{key}",
            )

    if "array" in packaged_types and "items" in packaged:
        _assert_schema_alignment(
            packaged_schema=_as_dict(packaged["items"], path=f"{path}.items"),
            model_schema=_as_dict(model["items"], path=f"{path}.items"),
            packaged_root=packaged_root,
            model_root=model_root,
            path=f"{path}[]",
        )


def _resolve_refs(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    current = schema
    while "$ref" in current:
        ref = current["$ref"]
        assert isinstance(ref, str), "schema $ref must be a string"
        assert ref.startswith("#/"), f"unsupported ref format: {ref}"
        target: Any = root
        for part in ref[2:].split("/"):
            target = target[part]
        current = _as_dict(target, path=ref)
    return current


def _extract_types(schema: dict[str, Any]) -> set[str]:
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return {schema_type}
    if isinstance(schema_type, list):
        return {item for item in schema_type if isinstance(item, str)}

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        merged: set[str] = set()
        for candidate in any_of:
            if isinstance(candidate, dict):
                merged |= _extract_types(candidate)
        return merged
    return set()


def _as_dict(value: object, *, path: str) -> dict[str, Any]:
    assert isinstance(value, dict), f"{path} must be an object schema node"
    return value


def _as_list(value: object) -> list[Any]:
    if value is None:
        return []
    assert isinstance(value, list), "required must be a list"
    return value
