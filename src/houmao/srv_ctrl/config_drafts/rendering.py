"""Intent loading, validation, and YAML generation for config drafts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any

import click
import yaml

from houmao.srv_ctrl.config_drafts.models import (
    ConfigDraft,
    ConfigDraftRenderResult,
    DraftBlocker,
    DraftField,
)
from houmao.srv_ctrl.config_drafts.registry import get_config_draft


def load_draft_intent(raw_intent: str) -> dict[str, object]:
    """Load draft intent from inline JSON, stdin, or a JSON file path."""

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


def generate_config_draft(draft_id: str, intent: Mapping[str, object]) -> ConfigDraftRenderResult:
    """Generate one config draft without mutating project state."""

    draft = get_config_draft(draft_id)
    fields = _intent_fields(intent)
    blockers = _draft_blockers(draft=draft, fields=fields)
    if blockers:
        return ConfigDraftRenderResult(
            draft_id=draft.draft_id,
            yaml="",
            payload={},
            blockers=tuple(blockers),
        )
    payload = dict(draft.render(fields))
    return ConfigDraftRenderResult(
        draft_id=draft.draft_id,
        yaml=dump_config_draft_yaml(payload),
        payload=payload,
    )


def dump_config_draft_yaml(payload: Mapping[str, Any]) -> str:
    """Dump one config-draft payload as deterministic YAML."""

    document = yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=False)
    return document if document.endswith("\n") else f"{document}\n"


def _intent_fields(intent: Mapping[str, object]) -> dict[str, object]:
    """Return the sparse draft fields mapping from one intent payload."""

    raw_fields = intent.get("fields", {})
    if not isinstance(raw_fields, dict):
        raise click.ClickException("Intent JSON must contain an object-valued `fields` mapping.")
    return {str(name): value for name, value in raw_fields.items()}


def _draft_blockers(*, draft: ConfigDraft, fields: Mapping[str, object]) -> list[DraftBlocker]:
    """Return generation blockers for missing, unknown, invalid, or conflicting fields."""

    field_map = draft.field_map()
    blockers: list[DraftBlocker] = []
    unknown_fields = tuple(sorted(set(fields).difference(field_map)))
    if unknown_fields:
        blockers.append(
            DraftBlocker(
                kind="unsupported_fields",
                fields=unknown_fields,
                message="Intent supplied fields that this config draft does not support.",
            )
        )
    for field in draft.fields:
        supplied = field.name in fields
        value = fields.get(field.name)
        if field.required and not _field_is_active(value=value, supplied=supplied):
            blockers.append(
                DraftBlocker(
                    kind="missing_required_field",
                    field=field.name,
                    message=f"Required field `{field.name}` was not supplied.",
                )
            )
        if supplied:
            validation_message = _validate_field_value(field=field, value=value)
            if validation_message is not None:
                blockers.append(
                    DraftBlocker(
                        kind="invalid_field_value",
                        field=field.name,
                        message=validation_message,
                    )
                )
    for conflict in draft.conflicts:
        active_fields = tuple(
            name
            for name in conflict.fields
            if name in fields and _field_is_active(value=fields.get(name), supplied=True)
        )
        if len(active_fields) > 1:
            blockers.append(
                DraftBlocker(
                    kind="conflicting_fields",
                    fields=active_fields,
                    message=conflict.message,
                )
            )
    return blockers


def _validate_field_value(*, field: DraftField, value: object) -> str | None:
    """Return a validation message for one supplied field value when invalid."""

    if value is None:
        return None
    if field.value_type == "boolean":
        if not isinstance(value, bool):
            return f"Field `{field.name}` must be a boolean."
        return None
    if field.value_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return f"Field `{field.name}` must be an integer."
        return None
    if field.value_type == "string":
        if not isinstance(value, str):
            return f"Field `{field.name}` must be a string."
        if field.choices and value not in field.choices:
            choices = ", ".join(field.choices)
            return f"Field `{field.name}` must be one of: {choices}."
        return None
    if field.value_type == "string-list":
        values: Sequence[object]
        if isinstance(value, str):
            values = (value,)
        elif isinstance(value, Sequence):
            values = value
        else:
            return f"Field `{field.name}` must be a string or list of strings."
        if not all(isinstance(item, str) for item in values):
            return f"Field `{field.name}` must be a string or list of strings."
        return None
    if field.value_type == "string-mapping":
        if not isinstance(value, dict):
            return f"Field `{field.name}` must be an object with string keys and values."
        if not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
            return f"Field `{field.name}` must be an object with string keys and values."
        return None
    return None


def _field_is_active(*, value: object, supplied: bool) -> bool:
    """Return whether a supplied field counts for requirements and conflicts."""

    if not supplied or value is None:
        return False
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, Sequence):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return True
