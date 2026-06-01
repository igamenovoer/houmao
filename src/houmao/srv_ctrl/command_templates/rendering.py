"""Rendering and intent loading for command templates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import shlex
import sys

import click

from .models import CommandTemplate, TemplateField
from .registry import get_command_template


def load_render_intent(raw_intent: str) -> dict[str, object]:
    """Load render intent from inline JSON, stdin, or a JSON file path."""

    raw_value = raw_intent.strip()
    if raw_value == "-":
        document = sys.stdin.read()
    elif raw_value.startswith("{"):
        document = raw_value
    else:
        path = Path(raw_intent).expanduser()
        try:
            document = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise click.ClickException(f"Failed to read intent JSON `{raw_intent}`: {exc}") from exc
    try:
        payload = json.loads(document)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid intent JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise click.ClickException("Intent JSON must be an object.")
    return dict(payload)


def render_command_template(template_id: str, intent: Mapping[str, object]) -> dict[str, object]:
    """Render one sparse intent into argv without executing the target command."""

    template = get_command_template(template_id)
    fields = _intent_fields(intent)
    blockers = _render_blockers(template=template, fields=fields)
    normalized_fields = {name: fields[name] for name in sorted(fields)}
    if blockers:
        return {
            "template_id": template.template_id,
            "argv": [],
            "command": "",
            "normalized_intent": {"fields": normalized_fields},
            "applied_fields": [],
            "omitted_fields": _omitted_field_payloads(template=template, fields=fields),
            "warnings": [],
            "blockers": blockers,
        }

    argv: list[str] = list(template.target_argv)
    applied_fields: list[dict[str, object]] = []
    for field in template.fields:
        if field.name not in fields:
            continue
        rendered = _render_field(field, fields[field.name])
        if not rendered:
            continue
        argv.extend(rendered)
        applied_fields.append({"name": field.name, "argv": rendered})

    return {
        "template_id": template.template_id,
        "argv": argv,
        "command": shlex.join(argv),
        "normalized_intent": {"fields": normalized_fields},
        "applied_fields": applied_fields,
        "omitted_fields": _omitted_field_payloads(template=template, fields=fields),
        "warnings": _render_warnings(template=template, fields=fields),
        "blockers": [],
    }


def _intent_fields(intent: Mapping[str, object]) -> dict[str, object]:
    """Return the sparse render fields mapping from one intent payload."""

    raw_fields = intent.get("fields", {})
    if not isinstance(raw_fields, dict):
        raise click.ClickException("Intent JSON must contain an object-valued `fields` mapping.")
    return {str(name): value for name, value in raw_fields.items()}


def _render_blockers(
    *,
    template: CommandTemplate,
    fields: Mapping[str, object],
) -> list[dict[str, object]]:
    """Return render blockers for unsupported, missing, invalid, or conflicting fields."""

    field_map = template.field_map()
    blockers: list[dict[str, object]] = []
    unknown_fields = sorted(set(fields).difference(field_map))
    if unknown_fields:
        blockers.append(
            {
                "kind": "unsupported_fields",
                "fields": unknown_fields,
                "message": "Intent supplied fields that this command template does not support.",
            }
        )
    for field in template.fields:
        if field.default_action == "required" and not _field_is_active(
            field=field,
            value=fields.get(field.name),
            supplied=field.name in fields,
        ):
            blockers.append(
                {
                    "kind": "missing_required_field",
                    "field": field.name,
                    "message": f"Required field `{field.name}` was not supplied.",
                }
            )
        if field.name in fields:
            validation_message = _validate_field_value(field=field, value=fields[field.name])
            if validation_message is not None:
                blockers.append(
                    {
                        "kind": "invalid_field_value",
                        "field": field.name,
                        "message": validation_message,
                    }
                )
    for required_group in template.required_one_of:
        active_fields = [
            name
            for name in required_group
            if name in field_map
            and _field_is_active(
                field=field_map[name], value=fields.get(name), supplied=name in fields
            )
        ]
        if not active_fields:
            blockers.append(
                {
                    "kind": "missing_required_alternative",
                    "fields": list(required_group),
                    "message": (
                        "Supply at least one of: "
                        + ", ".join(f"`{name}`" for name in required_group)
                    ),
                }
            )
    for conflict in template.conflicts:
        active_fields = [
            name
            for name in conflict.fields
            if name in field_map
            and _field_is_active(
                field=field_map[name], value=fields.get(name), supplied=name in fields
            )
        ]
        if len(active_fields) > 1:
            blockers.append(
                {
                    "kind": "conflicting_fields",
                    "fields": active_fields,
                    "message": conflict.message,
                }
            )
    return blockers


def _validate_field_value(*, field: TemplateField, value: object) -> str | None:
    """Return a validation message for one supplied field value when invalid."""

    if field.repeatable:
        if isinstance(value, (str, int, bool)):
            values: Sequence[object] = (value,)
        elif isinstance(value, Sequence):
            values = value
        else:
            return f"Field `{field.name}` must be a scalar or list."
    else:
        values = (value,)
    for item in values:
        if item is None:
            continue
        if field.value_type == "boolean" and not isinstance(item, bool):
            return f"Field `{field.name}` must be a boolean."
        if field.value_type == "integer" and (not isinstance(item, int) or isinstance(item, bool)):
            return f"Field `{field.name}` must be an integer."
        if field.value_type == "number" and (
            not isinstance(item, (int, float)) or isinstance(item, bool)
        ):
            return f"Field `{field.name}` must be a number."
        if field.value_type in {"string", "path", "choice"} and not isinstance(item, str):
            return f"Field `{field.name}` must be a string."
        if field.choices and isinstance(item, str) and item not in field.choices:
            choices = ", ".join(field.choices)
            return f"Field `{field.name}` must be one of: {choices}."
    return None


def _field_is_active(*, field: TemplateField, value: object, supplied: bool) -> bool:
    """Return whether a supplied field should count for requirements and conflicts."""

    if not supplied:
        return False
    if value is None:
        return False
    if field.value_type == "boolean":
        if field.negative_option is not None and isinstance(value, bool):
            return True
        return value is True
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, Sequence):
        return bool(value)
    return True


def _render_field(field: TemplateField, value: object) -> list[str]:
    """Render one field value to argv fragments."""

    if field.option is None:
        return []
    if field.value_type == "boolean":
        if value is True:
            return [field.option]
        if value is False and field.negative_option is not None:
            return [field.negative_option]
        return []
    if value is None:
        return []
    if field.repeatable and not isinstance(value, str) and isinstance(value, Sequence):
        fragments: list[str] = []
        for item in value:
            if item is None:
                continue
            fragments.extend((field.option, str(item)))
        return fragments
    return [field.option, str(value)]


def _omitted_field_payloads(
    *,
    template: CommandTemplate,
    fields: Mapping[str, object],
) -> list[dict[str, object]]:
    """Return omitted supported fields and their omission semantics."""

    omitted: list[dict[str, object]] = []
    for field in template.fields:
        if field.default_action == "required" or field.name in fields:
            continue
        omitted.append(
            {
                "name": field.name,
                "default_action": field.default_action,
                "omit_semantics": field.omit_semantics,
            }
        )
    return omitted


def _render_warnings(
    *,
    template: CommandTemplate,
    fields: Mapping[str, object],
) -> list[str]:
    """Return informational render warnings for one template invocation."""

    del fields
    warnings: list[str] = []
    if any(field.default_action == "omit-to-inherit" for field in template.fields):
        warnings.append(
            "Omitted inherit/default fields were intentionally left out of argv; the target command "
            "and launch policy will resolve them."
        )
    return warnings
