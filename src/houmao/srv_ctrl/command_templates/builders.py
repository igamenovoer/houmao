"""Builder helpers for code-first command-template declarations."""

from __future__ import annotations

from collections.abc import Sequence

from .models import CommandTemplate, FieldAction, FieldConflict, TemplateField, ValueType


def _f(
    name: str,
    option: str,
    description: str,
    *,
    value_type: ValueType = "string",
    default_action: FieldAction = "set-if-supplied",
    repeatable: bool = False,
    choices: tuple[str, ...] = (),
    negative_option: str | None = None,
    clears_field: str | None = None,
    omit_semantics: str | None = None,
) -> TemplateField:
    """Build one option-backed template field."""

    return TemplateField(
        name=name,
        option=option,
        description=description,
        value_type=value_type,
        default_action=default_action,
        repeatable=repeatable,
        choices=choices,
        negative_option=negative_option,
        clears_field=clears_field,
        omit_semantics=omit_semantics
        or "Omit this field to leave the target command default in control.",
    )


def _req(
    name: str,
    option: str,
    description: str,
    *,
    value_type: ValueType = "string",
    repeatable: bool = False,
) -> TemplateField:
    """Build one required option field."""

    return _f(
        name,
        option,
        description,
        value_type=value_type,
        default_action="required",
        repeatable=repeatable,
        omit_semantics="This field is required by the target command.",
    )


def _flag(
    name: str,
    option: str,
    description: str,
    *,
    default_action: FieldAction = "set-if-supplied",
    negative_option: str | None = None,
    clears_field: str | None = None,
) -> TemplateField:
    """Build one boolean flag field."""

    return _f(
        name,
        option,
        description,
        value_type="boolean",
        default_action=default_action,
        negative_option=negative_option,
        clears_field=clears_field,
    )


def _choice(
    name: str,
    option: str,
    description: str,
    choices: tuple[str, ...],
    *,
    default_action: FieldAction = "set-if-supplied",
) -> TemplateField:
    """Build one choice-valued option field."""

    return _f(
        name,
        option,
        description,
        value_type="choice",
        choices=choices,
        default_action=default_action,
    )


def _clear(name: str, option: str, field_name: str) -> TemplateField:
    """Build one clear-only flag field."""

    return _flag(
        name,
        option,
        f"Clear stored `{field_name}`.",
        default_action="clear-only",
        clears_field=field_name,
    )


def _many(name: str, option: str, description: str) -> TemplateField:
    """Build one repeatable string option field."""

    return _f(name, option, description, repeatable=True)


def _req_many(name: str, option: str, description: str) -> TemplateField:
    """Build one required repeatable string option field."""

    return _req(name, option, description, repeatable=True)


def _path(name: str, option: str, description: str) -> TemplateField:
    """Build one path-valued option field."""

    return _f(name, option, description, value_type="path")


def _req_path(name: str, option: str, description: str) -> TemplateField:
    """Build one required path-valued option field."""

    return _req(name, option, description, value_type="path")


def _int(name: str, option: str, description: str) -> TemplateField:
    """Build one integer-valued option field."""

    return _f(name, option, description, value_type="integer")


def _req_int(name: str, option: str, description: str) -> TemplateField:
    """Build one required integer-valued option field."""

    return _req(name, option, description, value_type="integer")


def _number(name: str, option: str, description: str) -> TemplateField:
    """Build one numeric option field."""

    return _f(name, option, description, value_type="number")


def _conflict(*fields: str, message: str) -> FieldConflict:
    """Build one field-conflict declaration."""

    return FieldConflict(fields=fields, message=message)


def _template(
    template_id: str,
    target: Sequence[str],
    description: str,
    fields: Sequence[TemplateField],
    *,
    family: str,
    conflicts: Sequence[FieldConflict] = (),
    required_one_of: Sequence[Sequence[str]] = (),
    notes: Sequence[str] = (),
    operation_kind: str = "command",
) -> CommandTemplate:
    """Build one command-template entry."""

    return CommandTemplate(
        template_id=template_id,
        description=description,
        target_argv=("houmao-mgr", *target),
        fields=tuple(fields),
        family=family,
        conflicts=tuple(conflicts),
        required_one_of=tuple(tuple(group) for group in required_one_of),
        notes=tuple(notes),
        operation_kind=operation_kind,
    )
