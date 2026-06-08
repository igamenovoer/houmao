"""Config-draft JSON intent fix-guide helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from houmao.srv_ctrl.config_drafts.models import ConfigDraft, DraftField
from houmao.srv_ctrl.json_input_fix_guides import (
    JsonInputFixGuide,
    compact_json_object,
    required_field_paths,
)

_INTENT_INPUT_SOURCE = "inline JSON object, `-` for stdin, or path to a JSON file"
_COMMAND = "houmao-mgr internals config-drafts generate"
_EXAMPLE_FIELDS: Mapping[str, Mapping[str, str]] = {
    "project.specialist": {
        "name": "general-kimi",
        "tool": "kimi",
        "credential": "kimi-coding",
    },
    "project.profile": {
        "name": "reviewer-fast",
        "specialist": "reviewer",
        "credential": "reviewer-creds",
    },
    "internals.native-agent.launch-dossier": {
        "name": "reviewer-native",
        "recipe": "reviewer-codex",
        "credential": "reviewer-creds",
    },
}


def render_config_draft_intent_fix_guide(*, problem: str, draft: ConfigDraft) -> str:
    """Return a draft-specific JSON intent repair guide."""

    example_payload = config_draft_intent_example(draft)
    command_example = (
        f"{_COMMAND} --id {draft.draft_id} --intent '{compact_json_object(example_payload)}'"
    )
    guide = JsonInputFixGuide(
        problem=problem,
        command=f"{_COMMAND} --id {draft.draft_id}",
        input_name="--intent",
        input_source=_INTENT_INPUT_SOURCE,
        schema=config_draft_intent_schema(draft),
        example_payload=example_payload,
        required_paths=required_field_paths("fields", draft.required_field_names),
        command_example=command_example,
    )
    return guide.render()


def config_draft_intent_schema(draft: ConfigDraft) -> dict[str, Any]:
    """Return a JSON Schema-style object for one config-draft intent."""

    field_properties: dict[str, Any] = {}
    for field in draft.fields:
        field_properties[field.name] = _field_schema(field)
    return {
        "type": "object",
        "required": ["fields"],
        "properties": {
            "fields": {
                "type": "object",
                "required": list(draft.required_field_names),
                "properties": field_properties,
                "additionalProperties": False,
            }
        },
        "additionalProperties": False,
    }


def config_draft_intent_example(draft: ConfigDraft) -> dict[str, Any]:
    """Return a safe example intent payload for one config draft."""

    selected = _EXAMPLE_FIELDS.get(draft.draft_id, {})
    fields: dict[str, str] = {}
    for field in draft.fields:
        fields[field.name] = selected.get(field.name, _field_example_value(field))
    return {"fields": fields}


def flat_intent_field_names(intent: Mapping[str, object], draft: ConfigDraft) -> tuple[str, ...]:
    """Return draft field names supplied at the top level of an intent object."""

    return tuple(name for name in draft.field_map() if name in intent)


def _field_schema(field: DraftField) -> dict[str, Any]:
    """Return a JSON Schema-style property for one draft field."""

    if field.value_type == "string-list":
        schema: dict[str, Any] = {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ]
        }
    elif field.value_type == "string-mapping":
        schema = {"type": "object", "additionalProperties": {"type": "string"}}
    else:
        schema = {"type": _json_schema_type(field.value_type)}
    if field.choices:
        schema["enum"] = list(field.choices)
    return schema


def _json_schema_type(value_type: str) -> str:
    """Return a JSON Schema scalar type name for one draft field value type."""

    if value_type == "integer":
        return "integer"
    if value_type == "boolean":
        return "boolean"
    return "string"


def _field_example_value(field: DraftField) -> str:
    """Return a safe fallback example value for one draft field."""

    if field.choices:
        return field.choices[0]
    if field.name == "credential":
        return "reviewer-creds"
    if field.name == "recipe":
        return "reviewer-codex"
    if field.name == "specialist":
        return "reviewer"
    return f"example-{field.name}"
