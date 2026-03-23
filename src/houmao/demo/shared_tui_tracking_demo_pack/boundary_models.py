"""Pydantic boundary models for the shared tracked-TUI demo config."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from houmao.agents.launch_policy.models import OperatorPromptMode
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from houmao.shared_tui_tracking.models import TrackedLastTurnResult
from houmao.terminal_record.models import DEFAULT_SAMPLE_INTERVAL_SECONDS

DemoSweepStateLabel = Literal[
    "ready",
    "active",
    "ready_success",
    "ready_interrupted",
    "ready_known_failure",
    "tui_down",
    "unavailable",
    "error",
    "unknown",
]

_DEFAULT_FIXTURES_ROOT = "tests/fixtures/shared_tui_tracking/recorded"
_DEFAULT_RECORDED_ROOT = "tmp/demo/shared-tui-tracking-demo-pack/recorded"
_DEFAULT_LIVE_ROOT = "tmp/demo/shared-tui-tracking-demo-pack/live"
_DEFAULT_SWEEPS_ROOT = "tmp/demo/shared-tui-tracking-demo-pack/sweeps"
_DEFAULT_DEMO_ID = "shared-tui-tracking-demo-pack"


class _DemoConfigBoundaryModel(BaseModel):
    """Base class for strict demo-config boundary parsing."""

    model_config = ConfigDict(extra="forbid")


class DemoToolConfigV1(_DemoConfigBoundaryModel):
    """Full tool config for one supported tool."""

    recipe_path: str
    launch_args_override: list[str] = Field(default_factory=list)
    operator_prompt_mode: OperatorPromptMode | None = None

    @field_validator("recipe_path")
    @classmethod
    def _recipe_path_not_blank(cls, value: str) -> str:
        """Reject blank recipe paths."""

        return _require_non_blank(value)

    @field_validator("launch_args_override")
    @classmethod
    def _launch_args_not_blank(cls, value: list[str]) -> list[str]:
        """Reject blank launch-arg items."""

        return [_require_non_blank(item) for item in value]


class DemoToolConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment for one tool config."""

    recipe_path: str | None = None
    launch_args_override: list[str] | None = None
    operator_prompt_mode: OperatorPromptMode | None = None

    @field_validator("recipe_path")
    @classmethod
    def _optional_recipe_path_not_blank(cls, value: str | None) -> str | None:
        """Reject blank optional recipe paths."""

        if value is None:
            return None
        return _require_non_blank(value)

    @field_validator("launch_args_override")
    @classmethod
    def _optional_launch_args_not_blank(cls, value: list[str] | None) -> list[str] | None:
        """Reject blank optional launch-arg items."""

        if value is None:
            return None
        return [_require_non_blank(item) for item in value]


class DemoToolsConfigV1(_DemoConfigBoundaryModel):
    """Full tool section for the demo config."""

    claude: DemoToolConfigV1
    codex: DemoToolConfigV1


class DemoToolsConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment for the tool section."""

    claude: DemoToolConfigOverrideV1 | None = None
    codex: DemoToolConfigOverrideV1 | None = None


class DemoPathsConfigV1(_DemoConfigBoundaryModel):
    """Full path section for the demo config."""

    fixtures_root: str = _DEFAULT_FIXTURES_ROOT
    recorded_root: str = _DEFAULT_RECORDED_ROOT
    live_root: str = _DEFAULT_LIVE_ROOT
    sweeps_root: str = _DEFAULT_SWEEPS_ROOT

    @field_validator("fixtures_root", "recorded_root", "live_root", "sweeps_root")
    @classmethod
    def _paths_not_blank(cls, value: str) -> str:
        """Reject blank configured paths."""

        return _require_non_blank(value)


class DemoPathsConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment for the path section."""

    fixtures_root: str | None = None
    recorded_root: str | None = None
    live_root: str | None = None
    sweeps_root: str | None = None

    @field_validator("fixtures_root", "recorded_root", "live_root", "sweeps_root")
    @classmethod
    def _optional_paths_not_blank(cls, value: str | None) -> str | None:
        """Reject blank optional configured paths."""

        if value is None:
            return None
        return _require_non_blank(value)


class DemoEvidenceConfigV1(_DemoConfigBoundaryModel):
    """Full evidence section for the demo config."""

    sample_interval_seconds: float = DEFAULT_SAMPLE_INTERVAL_SECONDS
    runtime_observer_interval_seconds: float | None = None
    ready_timeout_seconds: float = 45.0
    cleanup_session: bool = True

    @field_validator(
        "sample_interval_seconds",
        "runtime_observer_interval_seconds",
        "ready_timeout_seconds",
    )
    @classmethod
    def _positive_floats(cls, value: float | None) -> float | None:
        """Require positive evidence timing values when present."""

        if value is None:
            return None
        return _require_positive_float(value)

    @model_validator(mode="after")
    def _default_runtime_observer_interval(self) -> "DemoEvidenceConfigV1":
        """Default runtime-observer cadence to sample cadence."""

        if self.runtime_observer_interval_seconds is None:
            self.runtime_observer_interval_seconds = self.sample_interval_seconds
        return self


class DemoEvidenceConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment for the evidence section."""

    sample_interval_seconds: float | None = None
    runtime_observer_interval_seconds: float | None = None
    ready_timeout_seconds: float | None = None
    cleanup_session: bool | None = None

    @field_validator(
        "sample_interval_seconds",
        "runtime_observer_interval_seconds",
        "ready_timeout_seconds",
    )
    @classmethod
    def _optional_positive_floats(cls, value: float | None) -> float | None:
        """Require positive optional evidence timing values when present."""

        if value is None:
            return None
        return _require_positive_float(value)


class DemoSemanticsConfigV1(_DemoConfigBoundaryModel):
    """Full semantics section for the demo config."""

    settle_seconds: float = 1.0

    @field_validator("settle_seconds")
    @classmethod
    def _non_negative_settle_seconds(cls, value: float) -> float:
        """Require non-negative settle timing."""

        if value < 0:
            raise ValueError("must be greater than or equal to 0")
        return value


class DemoSemanticsConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment for the semantics section."""

    settle_seconds: float | None = None

    @field_validator("settle_seconds")
    @classmethod
    def _optional_non_negative_settle_seconds(cls, value: float | None) -> float | None:
        """Require non-negative optional settle timing."""

        if value is None:
            return None
        if value < 0:
            raise ValueError("must be greater than or equal to 0")
        return value


class DemoReviewVideoConfigV1(_DemoConfigBoundaryModel):
    """Full review-video config for the demo config."""

    width: int = 1920
    height: int = 1080
    match_capture_cadence: bool = True
    fps: float | None = None
    codec: str = "libx264"
    pixel_format: str = "yuv420p"
    keep_frames: bool = True

    @field_validator("width", "height")
    @classmethod
    def _positive_ints(cls, value: int) -> int:
        """Require positive frame dimensions."""

        if value <= 0:
            raise ValueError("must be greater than 0")
        return value

    @field_validator("fps")
    @classmethod
    def _optional_positive_fps(cls, value: float | None) -> float | None:
        """Require positive fps when present."""

        if value is None:
            return None
        return _require_positive_float(value)

    @field_validator("codec", "pixel_format")
    @classmethod
    def _rendering_strings_not_blank(cls, value: str) -> str:
        """Reject blank rendering strings."""

        return _require_non_blank(value)

    @model_validator(mode="after")
    def _validate_cadence_or_fps(self) -> "DemoReviewVideoConfigV1":
        """Require explicit fps when cadence matching is disabled."""

        if not self.match_capture_cadence and self.fps is None:
            raise ValueError("fps is required when match_capture_cadence is false")
        return self


class DemoReviewVideoConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment for the review-video config."""

    width: int | None = None
    height: int | None = None
    match_capture_cadence: bool | None = None
    fps: float | None = None
    codec: str | None = None
    pixel_format: str | None = None
    keep_frames: bool | None = None

    @field_validator("width", "height")
    @classmethod
    def _optional_positive_ints(cls, value: int | None) -> int | None:
        """Require positive optional frame dimensions."""

        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be greater than 0")
        return value

    @field_validator("fps")
    @classmethod
    def _optional_positive_fps(cls, value: float | None) -> float | None:
        """Require positive optional fps."""

        if value is None:
            return None
        return _require_positive_float(value)

    @field_validator("codec", "pixel_format")
    @classmethod
    def _optional_rendering_strings_not_blank(cls, value: str | None) -> str | None:
        """Reject blank optional rendering strings."""

        if value is None:
            return None
        return _require_non_blank(value)


class DemoPresentationConfigV1(_DemoConfigBoundaryModel):
    """Full presentation section for the demo config."""

    review_video: DemoReviewVideoConfigV1


class DemoPresentationConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment for the presentation section."""

    review_video: DemoReviewVideoConfigOverrideV1 | None = None


class DemoSweepVariantConfigV1(_DemoConfigBoundaryModel):
    """One sweep variant in the full config."""

    name: str
    use_source_cadence: bool = False
    sample_interval_seconds: float | None = None
    runtime_observer_interval_seconds: float | None = None

    @field_validator("name")
    @classmethod
    def _variant_name_not_blank(cls, value: str) -> str:
        """Reject blank variant names."""

        return _require_non_blank(value)

    @field_validator("sample_interval_seconds", "runtime_observer_interval_seconds")
    @classmethod
    def _variant_positive_floats(cls, value: float | None) -> float | None:
        """Require positive variant timing values when present."""

        if value is None:
            return None
        return _require_positive_float(value)

    @model_validator(mode="after")
    def _validate_cadence_source_choice(self) -> "DemoSweepVariantConfigV1":
        """Require one cadence source declaration."""

        if self.use_source_cadence:
            self.sample_interval_seconds = None
            return self
        if self.sample_interval_seconds is None:
            raise ValueError("sample_interval_seconds is required when use_source_cadence is false")
        return self


class DemoSweepContractConfigV1(_DemoConfigBoundaryModel):
    """One sweep contract in the full config."""

    required_labels: list[DemoSweepStateLabel] = Field(default_factory=list)
    required_sequence: list[DemoSweepStateLabel] = Field(default_factory=list)
    required_terminal_result: TrackedLastTurnResult | None = None
    forbidden_terminal_results: list[TrackedLastTurnResult] = Field(default_factory=list)
    max_first_occurrence_drift_seconds: float = 2.0

    @field_validator("required_labels", "required_sequence")
    @classmethod
    def _require_labels_not_empty(
        cls, value: list[DemoSweepStateLabel]
    ) -> list[DemoSweepStateLabel]:
        """Require each configured label list to be non-empty when present."""

        if not value:
            return value
        return value

    @field_validator("max_first_occurrence_drift_seconds")
    @classmethod
    def _drift_tolerance_positive(cls, value: float) -> float:
        """Require positive drift tolerance."""

        return _require_positive_float(value)

    @model_validator(mode="after")
    def _require_contract_expectations(self) -> "DemoSweepContractConfigV1":
        """Require at least one transition expectation."""

        if not self.required_labels and not self.required_sequence:
            raise ValueError("must declare required_labels or required_sequence")
        return self


class DemoSweepDefinitionConfigV1(_DemoConfigBoundaryModel):
    """One named sweep definition in the full config."""

    description: str = ""
    baseline_variant: str | None = None
    variants: list[DemoSweepVariantConfigV1]
    contracts: dict[str, DemoSweepContractConfigV1]

    @field_validator("description")
    @classmethod
    def _description_trimmed(cls, value: str) -> str:
        """Normalize optional description text."""

        return value.strip()

    @field_validator("baseline_variant")
    @classmethod
    def _optional_baseline_variant_not_blank(cls, value: str | None) -> str | None:
        """Reject blank optional baseline names."""

        if value is None:
            return None
        return _require_non_blank(value)

    @field_validator("contracts")
    @classmethod
    def _contract_keys_not_blank(
        cls, value: dict[str, DemoSweepContractConfigV1]
    ) -> dict[str, DemoSweepContractConfigV1]:
        """Reject blank contract case ids."""

        _validate_mapping_keys(value)
        if not value:
            raise ValueError("must define at least one contract")
        return value

    @model_validator(mode="after")
    def _validate_variant_layout(self) -> "DemoSweepDefinitionConfigV1":
        """Require usable variant layout and baseline selection."""

        if not self.variants:
            raise ValueError("must define at least one variant")
        variant_names = [item.name for item in self.variants]
        if len(set(variant_names)) != len(variant_names):
            raise ValueError("variant names must be unique")
        if self.baseline_variant is not None and self.baseline_variant not in variant_names:
            raise ValueError("baseline_variant must name one declared variant")
        return self


class DemoConfigOverrideV1(_DemoConfigBoundaryModel):
    """Override fragment used by profiles, scenario overrides, and CLI overrides."""

    tools: DemoToolsConfigOverrideV1 | None = None
    paths: DemoPathsConfigOverrideV1 | None = None
    evidence: DemoEvidenceConfigOverrideV1 | None = None
    semantics: DemoSemanticsConfigOverrideV1 | None = None
    presentation: DemoPresentationConfigOverrideV1 | None = None
    sweeps: dict[str, DemoSweepDefinitionConfigV1] | None = None

    @field_validator("sweeps")
    @classmethod
    def _optional_sweep_keys_not_blank(
        cls, value: dict[str, DemoSweepDefinitionConfigV1] | None
    ) -> dict[str, DemoSweepDefinitionConfigV1] | None:
        """Reject blank optional sweep names."""

        if value is None:
            return None
        _validate_mapping_keys(value)
        return value


class DemoConfigDocumentV1(_DemoConfigBoundaryModel):
    """Full demo-config document."""

    schema_version: Literal[1] = 1
    demo_id: str = _DEFAULT_DEMO_ID
    paths: DemoPathsConfigV1
    tools: DemoToolsConfigV1
    evidence: DemoEvidenceConfigV1
    semantics: DemoSemanticsConfigV1
    presentation: DemoPresentationConfigV1
    profiles: dict[str, DemoConfigOverrideV1] = Field(default_factory=dict)
    scenario_overrides: dict[str, DemoConfigOverrideV1] = Field(default_factory=dict)
    sweeps: dict[str, DemoSweepDefinitionConfigV1] = Field(default_factory=dict)

    @field_validator("demo_id")
    @classmethod
    def _demo_id_not_blank(cls, value: str) -> str:
        """Reject blank demo ids."""

        return _require_non_blank(value)

    @field_validator("profiles", "scenario_overrides", "sweeps")
    @classmethod
    def _mapping_keys_not_blank(cls, value: dict[str, object]) -> dict[str, object]:
        """Reject blank keys in named mapping sections."""

        _validate_mapping_keys(value)
        return value


def _require_non_blank(value: str) -> str:
    """Return a non-blank string or raise."""

    if not value.strip():
        raise ValueError("must not be empty")
    return value


def _require_positive_float(value: float) -> float:
    """Return a positive float or raise."""

    if value <= 0:
        raise ValueError("must be greater than 0")
    return value


def _validate_mapping_keys(value: Mapping[str, object]) -> None:
    """Reject blank mapping keys."""

    for key in value:
        if not key.strip():
            raise ValueError("mapping keys must not be empty")
