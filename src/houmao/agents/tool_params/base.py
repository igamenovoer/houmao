"""Strict per-tool settings and their layered merge contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError


class StrictToolParams(BaseModel):
    """Common validation rules for authored per-tool settings."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


PartialT = TypeVar("PartialT", bound=StrictToolParams)
EffectiveT = TypeVar("EffectiveT", bound=StrictToolParams)
ModelT = TypeVar("ModelT", bound=StrictToolParams)

_MANAGED_FIELDS = {
    "session_id": "Houmao binds native session identity. Use the Houmao relaunch session selector",
    "output_format": "Houmao selects the managed output protocol",
}


class ToolParamsAdapter(Generic[PartialT, EffectiveT]):
    """Resolve settings for one tool and project its backend-specific arguments."""

    partial_model: type[PartialT]
    effective_model: type[EffectiveT]
    keyed_lists: ClassVar[Mapping[str, str]] = {}

    def parse_partial(self, raw: Mapping[str, Any], *, source: str) -> PartialT:
        """Validate one authoring layer while retaining explicit field presence."""

        for field, reason in _MANAGED_FIELDS.items():
            if field in raw:
                raise ValueError(f"{source}.{field}: reserved managed setting. {reason}.")
        partial = _validate_model(self.partial_model, raw, source)
        payload = partial.model_dump(mode="json", exclude_unset=True)
        for field_name, identity in self.keyed_lists.items():
            items = payload.get(field_name)
            if isinstance(items, list):
                _index_items(items, identity=identity, source=f"{source}.{field_name}")
        return partial

    def parse_effective(self, raw: Mapping[str, Any], *, source: str) -> EffectiveT:
        """Validate a complete set of tool settings."""

        return _validate_model(self.effective_model, raw, source)

    def merge_partial(self, layers: Sequence[tuple[str, PartialT]]) -> PartialT:
        """Apply a sequence of partial layers from lowest to highest precedence."""

        merged: dict[str, Any] = {}
        for source, layer in layers:
            _merge_fields(
                merged,
                layer.model_dump(mode="json", exclude_unset=True),
                keyed_lists=self.keyed_lists,
                source=source,
            )
        return self.parse_partial(merged, source="merged tool_params")

    def merge_layers(self, layers: Sequence[tuple[str, PartialT]]) -> EffectiveT:
        """Validate the effective result of applying the supplied partial layers."""

        merged = self.merge_partial(layers).model_dump(mode="json", exclude_unset=True)
        return self.parse_effective(merged, source="effective tool_params")

    def prepare_launch(self, effective: EffectiveT, *, backend: str) -> tuple[str, ...]:
        """Return the backend arguments for tools that need no additional flags."""

        return ()


def _validate_model(model: type[ModelT], raw: Mapping[str, Any], source: str) -> ModelT:
    """Raise a value-free error at the first invalid schema field."""

    try:
        return model.model_validate(dict(raw))
    except ValidationError as exc:
        error = exc.errors(include_input=False, include_context=False, include_url=False)[0]
        location = error["loc"]
        if error["type"] == "extra_forbidden":
            location = (*location[:-1], "<unknown field>")
        path = ".".join(str(part) for part in location)
        reason = error["msg"]
        field = f".{path}" if path else ""
        raise ValueError(f"{source}{field}: {reason}") from None


def _merge_fields(
    current: dict[str, Any],
    patch: Mapping[str, Any],
    *,
    keyed_lists: Mapping[str, str],
    source: str,
) -> None:
    """Apply a validated patch to a detached mapping."""

    for field, value in patch.items():
        previous = current.get(field)
        identity = keyed_lists.get(field)
        if isinstance(previous, dict) and isinstance(value, dict):
            _merge_fields(previous, value, keyed_lists={}, source=f"{source}.{field}")
        elif identity and isinstance(previous, list) and isinstance(value, list):
            entries = _index_items(previous, identity=identity, source=f"{source}.{field}")
            for key, item in _index_items(
                value, identity=identity, source=f"{source}.{field}"
            ).items():
                existing = entries.get(key)
                if existing is None:
                    entries[key] = item
                else:
                    _merge_fields(existing, item, keyed_lists={}, source=f"{source}.{field}")
            current[field] = list(entries.values())
        else:
            current[field] = value


def _index_items(items: list[Any], *, identity: str, source: str) -> dict[str, dict[str, Any]]:
    """Index keyed items in order and reject duplicate identities."""

    indexed: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        key = item.get(identity) if isinstance(item, dict) else None
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{source}.{index}.{identity}: expected a nonempty identifier")
        if key in indexed:
            raise ValueError(f"{source}.{index}.{identity}: duplicate identifier")
        indexed[key] = item
    return indexed
