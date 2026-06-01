"""Typed models for code-first ``houmao-mgr`` command templates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FieldAction = Literal["required", "set-if-supplied", "omit-to-inherit", "clear-only", "conditional"]
ValueType = Literal["string", "integer", "number", "boolean", "choice", "path"]

_PROMPT_MODE_CHOICES: tuple[str, ...] = ("unattended", "as_is")
_TOOL_CHOICES: tuple[str, ...] = ("claude", "codex", "gemini")
_RELAUNCH_CHAT_SESSION_MODES: tuple[str, ...] = ("new", "tool_last_or_new", "exact")


@dataclass(frozen=True)
class TemplateField:
    """One structured intent field accepted by a command template."""

    name: str
    option: str | None
    description: str
    value_type: ValueType = "string"
    default_action: FieldAction = "set-if-supplied"
    repeatable: bool = False
    choices: tuple[str, ...] = ()
    negative_option: str | None = None
    clears_field: str | None = None
    omit_semantics: str = "Omit this field to leave the target command default in control."

    def to_payload(self) -> dict[str, object]:
        """Return one JSON-compatible field description."""

        payload: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "value_type": self.value_type,
            "default_action": self.default_action,
            "repeatable": self.repeatable,
            "omit_semantics": self.omit_semantics,
        }
        if self.option is not None:
            payload["option"] = self.option
        if self.negative_option is not None:
            payload["negative_option"] = self.negative_option
        if self.choices:
            payload["choices"] = list(self.choices)
        if self.clears_field is not None:
            payload["clears_field"] = self.clears_field
        return payload


@dataclass(frozen=True)
class FieldConflict:
    """One mutually-exclusive intent-field group."""

    fields: tuple[str, ...]
    message: str

    def to_payload(self) -> dict[str, object]:
        """Return one JSON-compatible conflict description."""

        return {"fields": list(self.fields), "message": self.message}


@dataclass(frozen=True)
class CommandTemplate:
    """One command-template registry entry."""

    template_id: str
    description: str
    target_argv: tuple[str, ...]
    fields: tuple[TemplateField, ...]
    family: str
    command_surface: str = "houmao-mgr"
    operation_kind: str = "command"
    conflicts: tuple[FieldConflict, ...] = ()
    required_one_of: tuple[tuple[str, ...], ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def field_names(self) -> frozenset[str]:
        """Return declared intent field names."""

        return frozenset(field.name for field in self.fields)

    @property
    def target_command_path(self) -> str:
        """Return the target command path without the executable name."""

        return " ".join(self.target_argv[1:])

    def field_map(self) -> dict[str, TemplateField]:
        """Return fields keyed by name."""

        return {field.name: field for field in self.fields}

    def summary_payload(self) -> dict[str, object]:
        """Return one compact list entry."""

        return {
            "id": self.template_id,
            "description": self.description,
            "family": self.family,
            "command_surface": self.command_surface,
            "target_command_path": self.target_command_path,
            "target_argv": list(self.target_argv),
        }

    def to_payload(self) -> dict[str, object]:
        """Return the full template metadata payload."""

        return {
            **self.summary_payload(),
            "operation_kind": self.operation_kind,
            "fields": [field.to_payload() for field in self.fields],
            "conflicts": [conflict.to_payload() for conflict in self.conflicts],
            "required_one_of": [list(group) for group in self.required_one_of],
            "notes": list(self.notes),
        }
