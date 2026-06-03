"""Typed models for code-first config-draft generation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

FieldValueType = Literal["string", "integer", "boolean", "string-list", "string-mapping"]


@dataclass(frozen=True)
class DraftField:
    """One supported field accepted by a config draft."""

    name: str
    value_type: FieldValueType = "string"
    required: bool = False
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class DraftConflict:
    """One mutually-exclusive draft-field group."""

    fields: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class DraftBlocker:
    """One reason a config draft cannot be generated."""

    kind: str
    message: str
    field: str | None = None
    fields: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        """Return one JSON-compatible blocker payload."""

        payload: dict[str, object] = {
            "kind": self.kind,
            "message": self.message,
        }
        if self.field is not None:
            payload["field"] = self.field
        if self.fields:
            payload["fields"] = list(self.fields)
        return payload


@dataclass(frozen=True)
class ConfigDraft:
    """One concrete config-draft generator entry."""

    draft_id: str
    description: str
    config_kind: str
    fields: tuple[DraftField, ...]
    render: Callable[[Mapping[str, object]], Mapping[str, Any]]
    conflicts: tuple[DraftConflict, ...] = ()

    @property
    def required_field_names(self) -> tuple[str, ...]:
        """Return required input field names."""

        return tuple(field.name for field in self.fields if field.required)

    def field_map(self) -> dict[str, DraftField]:
        """Return supported fields keyed by name."""

        return {field.name: field for field in self.fields}

    def summary_payload(self) -> dict[str, object]:
        """Return one compact list entry."""

        return {
            "id": self.draft_id,
            "description": self.description,
            "config_kind": self.config_kind,
            "required_intent_keys": list(self.required_field_names),
        }


@dataclass(frozen=True)
class ConfigDraftRenderResult:
    """Rendered YAML or blockers for one config draft."""

    draft_id: str
    yaml: str
    payload: Mapping[str, Any]
    blockers: tuple[DraftBlocker, ...] = ()

    @property
    def has_blockers(self) -> bool:
        """Return whether generation was blocked."""

        return bool(self.blockers)

    def to_payload(self) -> dict[str, object]:
        """Return a compact JSON-compatible render result."""

        if self.blockers:
            return {
                "draft_id": self.draft_id,
                "blockers": [blocker.to_payload() for blocker in self.blockers],
            }
        return {
            "draft_id": self.draft_id,
            "yaml": self.yaml,
        }
