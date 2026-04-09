"""Launch-owned unified model-selection helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelReasoningConfig:
    """Normalized reasoning configuration."""

    level: int

    def to_payload(self) -> dict[str, int]:
        """Return one operator-facing payload."""

        return {"level": self.level}


@dataclass(frozen=True)
class ModelConfig:
    """Launch-owned unified model configuration."""

    name: str | None = None
    reasoning: ModelReasoningConfig | None = None

    def is_empty(self) -> bool:
        """Return whether this config carries no launch-owned fields."""

        return self.name is None and self.reasoning is None

    def to_payload(self) -> dict[str, Any]:
        """Return one operator-facing payload."""

        payload: dict[str, Any] = {}
        if self.name is not None:
            payload["name"] = self.name
        if self.reasoning is not None:
            payload["reasoning"] = self.reasoning.to_payload()
        return payload


@dataclass(frozen=True)
class ResolvedModelConfig:
    """Resolved model configuration plus per-subfield provenance."""

    config: ModelConfig | None
    name_source: str | None
    reasoning_source: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return one secret-free resolved payload."""

        return {
            "effective": model_config_to_payload(self.config),
            "sources": {
                "name": self.name_source,
                "reasoning_level": self.reasoning_source,
            },
        }


def parse_reasoning_level(raw_value: object, *, source: str) -> int | None:
    """Parse one optional normalized reasoning level."""

    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        raise ValueError(f"{source}: reasoning.level must be an integer from 1 through 10")

    parsed_value: int | None = None
    if isinstance(raw_value, int):
        parsed_value = raw_value
    elif isinstance(raw_value, str) and raw_value.strip():
        try:
            parsed_value = int(raw_value.strip())
        except ValueError as exc:
            raise ValueError(
                f"{source}: reasoning.level must be an integer from 1 through 10"
            ) from exc

    if parsed_value is None or parsed_value < 1 or parsed_value > 10:
        raise ValueError(f"{source}: reasoning.level must be an integer from 1 through 10")
    return parsed_value


def parse_model_config(raw_value: object, *, source: str) -> ModelConfig | None:
    """Parse one optional unified model-configuration value."""

    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            raise ValueError(f"{source}: launch.model must not be empty when set")
        return ModelConfig(name=stripped)
    if not isinstance(raw_value, dict):
        raise ValueError(f"{source}: launch.model must be a string or mapping when set")

    unknown_fields = sorted(key for key in raw_value if key not in {"name", "reasoning"})
    if unknown_fields:
        joined = ", ".join(str(key) for key in unknown_fields)
        raise ValueError(
            f"{source}: launch.model supports only `name` and `reasoning`, got {joined}"
        )

    name = raw_value.get("name")
    resolved_name: str | None
    if name is None:
        resolved_name = None
    elif isinstance(name, str) and name.strip():
        resolved_name = name.strip()
    else:
        raise ValueError(f"{source}: launch.model.name must be a non-empty string when set")

    reasoning_payload = raw_value.get("reasoning")
    reasoning: ModelReasoningConfig | None = None
    if reasoning_payload is not None:
        if not isinstance(reasoning_payload, dict):
            raise ValueError(f"{source}: launch.model.reasoning must be a mapping when set")
        unknown_reasoning_fields = sorted(key for key in reasoning_payload if key != "level")
        if unknown_reasoning_fields:
            joined = ", ".join(str(key) for key in unknown_reasoning_fields)
            raise ValueError(
                f"{source}: launch.model.reasoning supports only `level`, got {joined}"
            )
        reasoning_level = parse_reasoning_level(
            reasoning_payload.get("level"),
            source=f"{source}:launch.model.reasoning",
        )
        if reasoning_level is not None:
            reasoning = ModelReasoningConfig(level=reasoning_level)

    config = ModelConfig(name=resolved_name, reasoning=reasoning)
    return None if config.is_empty() else config


def normalize_model_config(
    *,
    name: str | None = None,
    reasoning_level: int | None = None,
) -> ModelConfig | None:
    """Build one normalized model config from explicit fields."""

    resolved_name = name.strip() if name is not None and name.strip() else None
    resolved_reasoning: ModelReasoningConfig | None = None
    if reasoning_level is not None:
        normalized_reasoning_level = parse_reasoning_level(
            reasoning_level,
            source="reasoning_level",
        )
        assert normalized_reasoning_level is not None
        resolved_reasoning = ModelReasoningConfig(level=normalized_reasoning_level)
    config = ModelConfig(name=resolved_name, reasoning=resolved_reasoning)
    return None if config.is_empty() else config


def model_config_to_payload(config: ModelConfig | None) -> dict[str, Any] | None:
    """Return one payload for optional model configuration."""

    if config is None or config.is_empty():
        return None
    return config.to_payload()


def merge_model_configs(
    base: ModelConfig | None, override: ModelConfig | None
) -> ModelConfig | None:
    """Overlay one model config onto another on a per-subfield basis."""

    if base is None:
        return override
    if override is None:
        return base
    merged = ModelConfig(
        name=override.name if override.name is not None else base.name,
        reasoning=override.reasoning if override.reasoning is not None else base.reasoning,
    )
    return None if merged.is_empty() else merged


def resolve_model_config_layers(
    layers: Sequence[tuple[str, ModelConfig | None]],
) -> ResolvedModelConfig:
    """Resolve one ordered set of model-config layers."""

    effective_name: str | None = None
    effective_reasoning: ModelReasoningConfig | None = None
    name_source: str | None = None
    reasoning_source: str | None = None

    for layer_name, layer_config in layers:
        if layer_config is None:
            continue
        if layer_config.name is not None:
            effective_name = layer_config.name
            name_source = layer_name
        if layer_config.reasoning is not None:
            effective_reasoning = layer_config.reasoning
            reasoning_source = layer_name

    config = ModelConfig(name=effective_name, reasoning=effective_reasoning)
    return ResolvedModelConfig(
        config=None if config.is_empty() else config,
        name_source=name_source,
        reasoning_source=reasoning_source,
    )


def extract_resolved_model_config_from_brain_manifest(
    manifest: Mapping[str, Any],
    *,
    source: str,
) -> ModelConfig | None:
    """Extract the launch-resolved effective model config from one brain manifest."""

    runtime_payload = manifest.get("runtime")
    if not isinstance(runtime_payload, Mapping):
        return None
    launch_contract_payload = runtime_payload.get("launch_contract")
    if not isinstance(launch_contract_payload, Mapping):
        return None
    model_selection_payload = launch_contract_payload.get("model_selection")
    if not isinstance(model_selection_payload, Mapping):
        return None
    resolved_payload = model_selection_payload.get("resolved")
    if not isinstance(resolved_payload, Mapping):
        return None
    return parse_model_config(
        resolved_payload.get("effective"),
        source=f"{source}:runtime.launch_contract.model_selection.resolved.effective",
    )


def resolve_execution_model_config(
    *,
    launch_model: ModelConfig | None,
    request_override: ModelConfig | None,
) -> ResolvedModelConfig:
    """Resolve one request-scoped execution override atop launch-owned defaults."""

    return resolve_model_config_layers(
        (
            ("launch", launch_model),
            ("request", request_override),
        )
    )
