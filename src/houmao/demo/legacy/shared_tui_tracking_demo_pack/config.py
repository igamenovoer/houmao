"""Demo-owned configuration for the shared tracked-TUI demo pack."""

from __future__ import annotations

import copy
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, Literal, cast

from houmao.agents.launch_overrides import LaunchOverrides, parse_launch_overrides
from houmao.agents.launch_policy.models import OperatorPromptMode
from houmao.shared_tui_tracking.models import TrackedLastTurnResult
from houmao.terminal_record.models import DEFAULT_SAMPLE_INTERVAL_SECONDS

from .models import ToolName
from .schema_validation import validate_demo_config_document, validate_demo_config_override


SweepStateLabel = Literal[
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

_DEFAULT_CONFIG_RELATIVE_PATH: Final[Path] = Path(
    "scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml"
)
_DEFAULT_RECORDED_ROOT: Final[str] = "tmp/demo/shared-tui-tracking-demo-pack/recorded"
_DEFAULT_LIVE_ROOT: Final[str] = "tmp/demo/shared-tui-tracking-demo-pack/live"
_DEFAULT_SWEEPS_ROOT: Final[str] = "tmp/demo/shared-tui-tracking-demo-pack/sweeps"
_DEFAULT_FIXTURES_ROOT: Final[str] = "tests/fixtures/shared_tui_tracking/recorded"
_DEFAULT_DEMO_ID: Final[str] = "shared-tui-tracking-demo-pack"


@dataclass(frozen=True)
class DemoToolConfig:
    """Tool-specific launch defaults for the demo pack."""

    recipe_path: str
    launch_overrides: LaunchOverrides | None = None
    operator_prompt_mode: OperatorPromptMode | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class DemoPathsConfig:
    """Repo-relative default path roots for the demo pack."""

    fixtures_root: str
    recorded_root: str
    live_root: str
    sweeps_root: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class DemoEvidenceConfig:
    """Evidence-production defaults for capture and watch workflows."""

    sample_interval_seconds: float
    runtime_observer_interval_seconds: float
    ready_timeout_seconds: float
    cleanup_session: bool
    live_watch_recorder_enabled: bool

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class DemoSemanticsConfig:
    """Tracker-semantic timing defaults for the demo pack."""

    settle_seconds: float

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class DemoReviewVideoConfig:
    """Presentation settings for review-video generation."""

    width: int
    height: int
    match_capture_cadence: bool
    fps: float | None
    codec: str
    pixel_format: str
    keep_frames: bool

    def effective_fps(self, *, capture_sample_interval_seconds: float) -> float:
        """Return the effective review-video cadence for one run."""

        if self.fps is not None:
            return self.fps
        if not self.match_capture_cadence:
            raise ValueError("review video fps is undefined when cadence matching is disabled")
        if capture_sample_interval_seconds <= 0:
            raise ValueError("capture_sample_interval_seconds must be positive")
        return 1.0 / capture_sample_interval_seconds

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class DemoPresentationConfig:
    """Human-facing artifact presentation defaults."""

    review_video: DemoReviewVideoConfig

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return {"review_video": self.review_video.to_payload()}


@dataclass(frozen=True)
class SweepVariantConfig:
    """One cadence variant inside one named sweep."""

    name: str
    sample_interval_seconds: float | None
    runtime_observer_interval_seconds: float | None

    @property
    def uses_source_cadence(self) -> bool:
        """Return whether this variant uses the source recording cadence."""

        return self.sample_interval_seconds is None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class SweepContractConfig:
    """Transition-contract expectations for one case id."""

    required_labels: tuple[SweepStateLabel, ...]
    required_sequence: tuple[SweepStateLabel, ...]
    required_terminal_result: TrackedLastTurnResult | None
    forbidden_terminal_results: tuple[TrackedLastTurnResult, ...]
    max_first_occurrence_drift_seconds: float

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class SweepDefinitionConfig:
    """Named sweep definition loaded from the demo config."""

    name: str
    description: str
    baseline_variant: str | None
    variants: tuple[SweepVariantConfig, ...]
    contracts: dict[str, SweepContractConfig]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return {
            "name": self.name,
            "description": self.description,
            "baseline_variant": self.baseline_variant,
            "variants": [item.to_payload() for item in self.variants],
            "contracts": {
                case_id: contract.to_payload() for case_id, contract in self.contracts.items()
            },
        }


@dataclass(frozen=True)
class ResolvedDemoConfig:
    """Fully resolved demo configuration after all overrides are applied."""

    schema_version: int
    demo_id: str
    repo_root: str
    source_config_path: str
    selected_profile: str | None
    selected_scenario_id: str | None
    tools: dict[ToolName, DemoToolConfig]
    paths: DemoPathsConfig
    evidence: DemoEvidenceConfig
    semantics: DemoSemanticsConfig
    presentation: DemoPresentationConfig
    sweeps: dict[str, SweepDefinitionConfig]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return {
            "schema_version": self.schema_version,
            "demo_id": self.demo_id,
            "repo_root": self.repo_root,
            "source_config_path": self.source_config_path,
            "selected_profile": self.selected_profile,
            "selected_scenario_id": self.selected_scenario_id,
            "tools": {tool: config.to_payload() for tool, config in self.tools.items()},
            "paths": self.paths.to_payload(),
            "evidence": self.evidence.to_payload(),
            "semantics": self.semantics.to_payload(),
            "presentation": self.presentation.to_payload(),
            "sweeps": {name: sweep.to_payload() for name, sweep in self.sweeps.items()},
        }

    @property
    def repo_root_path(self) -> Path:
        """Return the resolved repository root."""

        return Path(self.repo_root)

    @property
    def source_config_path_obj(self) -> Path:
        """Return the resolved source config path."""

        return Path(self.source_config_path)

    def resolve_repo_path(self, value: str) -> Path:
        """Resolve one repo-relative or absolute config path."""

        path = Path(value).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.repo_root_path / path).resolve()

    def fixtures_root_path(self) -> Path:
        """Return the configured fixture-root path."""

        return self.resolve_repo_path(self.paths.fixtures_root)

    def recorded_root_path(self) -> Path:
        """Return the configured recorded-root parent path."""

        return self.resolve_repo_path(self.paths.recorded_root)

    def live_root_path(self) -> Path:
        """Return the configured live-root parent path."""

        return self.resolve_repo_path(self.paths.live_root)

    def sweeps_root_path(self) -> Path:
        """Return the configured sweeps-root parent path."""

        return self.resolve_repo_path(self.paths.sweeps_root)

    def tool_config(self, *, tool: ToolName) -> DemoToolConfig:
        """Return the resolved config for one tool."""

        return self.tools[tool]


def default_demo_config_path(*, repo_root: Path) -> Path:
    """Return the default demo-config path."""

    return (repo_root / _DEFAULT_CONFIG_RELATIVE_PATH).resolve()


def resolve_demo_config(
    *,
    repo_root: Path,
    config_path: Path | None = None,
    profile_name: str | None = None,
    scenario_id: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> ResolvedDemoConfig:
    """Load and resolve the demo-owned config with overrides."""

    effective_path = (
        config_path.expanduser().resolve()
        if config_path is not None
        else default_demo_config_path(repo_root=repo_root)
    )
    raw = _load_toml_mapping(effective_path)
    validated_raw = validate_demo_config_document(payload=raw, config_path=effective_path)
    merged = copy.deepcopy(raw)
    if profile_name is not None:
        if profile_name not in validated_raw.profiles:
            raise ValueError(f"Unknown demo config profile: {profile_name}")
        profile_payload = validated_raw.profiles[profile_name].model_dump(
            mode="python",
            exclude_none=True,
        )
        merged = _deep_merge(merged, copy.deepcopy(profile_payload))
    if scenario_id is not None:
        if scenario_id in validated_raw.scenario_overrides:
            merged = _deep_merge(
                merged,
                copy.deepcopy(
                    validated_raw.scenario_overrides[scenario_id].model_dump(
                        mode="python",
                        exclude_none=True,
                    )
                ),
            )
    if cli_overrides:
        validated_cli_overrides = validate_demo_config_override(
            payload=cli_overrides,
            context="cli_overrides",
        )
        merged = _deep_merge(
            merged,
            copy.deepcopy(validated_cli_overrides.model_dump(mode="python", exclude_none=True)),
        )
    validated_merged = validate_demo_config_document(payload=merged, config_path=effective_path)
    merged = validated_merged.model_dump(mode="python", exclude_none=True)
    return ResolvedDemoConfig(
        schema_version=int(validated_merged.schema_version),
        demo_id=str(validated_merged.demo_id),
        repo_root=str(repo_root.resolve()),
        source_config_path=str(effective_path),
        selected_profile=profile_name,
        selected_scenario_id=scenario_id,
        tools=_parse_tools(_require_mapping(merged.get("tools"), context="tools")),
        paths=_parse_paths(_require_mapping(merged.get("paths"), context="paths")),
        evidence=_parse_evidence(_require_mapping(merged.get("evidence"), context="evidence")),
        semantics=_parse_semantics(_require_mapping(merged.get("semantics"), context="semantics")),
        presentation=_parse_presentation(
            _require_mapping(merged.get("presentation"), context="presentation")
        ),
        sweeps=_parse_sweeps(_require_mapping(merged.get("sweeps", {}), context="sweeps")),
    )


def _parse_tools(payload: dict[str, Any]) -> dict[ToolName, DemoToolConfig]:
    """Parse tool defaults from raw config."""

    tools: dict[ToolName, DemoToolConfig] = {}
    for tool_name in ("claude", "codex"):
        tool_payload = _require_mapping(payload.get(tool_name), context=f"tools.{tool_name}")
        raw_launch_overrides = tool_payload.get("launch_overrides")
        launch_overrides = (
            parse_launch_overrides(
                raw_launch_overrides,
                source=f"tools.{tool_name}.launch_overrides",
            )
            if raw_launch_overrides is not None
            else None
        )
        tools[tool_name] = DemoToolConfig(
            recipe_path=_require_string(tool_payload.get("recipe_path"), context="recipe_path"),
            launch_overrides=launch_overrides,
            operator_prompt_mode=cast(
                OperatorPromptMode | None,
                tool_payload.get("operator_prompt_mode"),
            ),
        )
    return tools


def _parse_paths(payload: dict[str, Any]) -> DemoPathsConfig:
    """Parse path defaults from raw config."""

    return DemoPathsConfig(
        fixtures_root=str(payload.get("fixtures_root", _DEFAULT_FIXTURES_ROOT)),
        recorded_root=str(payload.get("recorded_root", _DEFAULT_RECORDED_ROOT)),
        live_root=str(payload.get("live_root", _DEFAULT_LIVE_ROOT)),
        sweeps_root=str(payload.get("sweeps_root", _DEFAULT_SWEEPS_ROOT)),
    )


def _parse_evidence(payload: dict[str, Any]) -> DemoEvidenceConfig:
    """Parse evidence defaults from raw config."""

    sample_interval_seconds = float(
        payload.get("sample_interval_seconds", DEFAULT_SAMPLE_INTERVAL_SECONDS)
    )
    runtime_observer_interval_seconds = float(
        payload.get("runtime_observer_interval_seconds", sample_interval_seconds)
    )
    return DemoEvidenceConfig(
        sample_interval_seconds=sample_interval_seconds,
        runtime_observer_interval_seconds=runtime_observer_interval_seconds,
        ready_timeout_seconds=float(payload.get("ready_timeout_seconds", 45.0)),
        cleanup_session=bool(payload.get("cleanup_session", True)),
        live_watch_recorder_enabled=bool(payload.get("live_watch_recorder_enabled", False)),
    )


def _parse_semantics(payload: dict[str, Any]) -> DemoSemanticsConfig:
    """Parse semantic timing defaults from raw config."""

    return DemoSemanticsConfig(settle_seconds=float(payload.get("settle_seconds", 1.0)))


def _parse_presentation(payload: dict[str, Any]) -> DemoPresentationConfig:
    """Parse presentation defaults from raw config."""

    review_payload = _require_mapping(
        payload.get("review_video"), context="presentation.review_video"
    )
    fps_value = review_payload.get("fps")
    return DemoPresentationConfig(
        review_video=DemoReviewVideoConfig(
            width=int(review_payload.get("width", 1920)),
            height=int(review_payload.get("height", 1080)),
            match_capture_cadence=bool(review_payload.get("match_capture_cadence", True)),
            fps=_optional_float(fps_value),
            codec=str(review_payload.get("codec", "libx264")),
            pixel_format=str(review_payload.get("pixel_format", "yuv420p")),
            keep_frames=bool(review_payload.get("keep_frames", True)),
        )
    )


def _parse_sweeps(payload: dict[str, Any]) -> dict[str, SweepDefinitionConfig]:
    """Parse named sweep definitions from raw config."""

    sweeps: dict[str, SweepDefinitionConfig] = {}
    for sweep_name, raw_value in payload.items():
        if not isinstance(raw_value, dict):
            raise ValueError(f"sweeps.{sweep_name} must be a table")
        variants_raw = raw_value.get("variants", [])
        if not isinstance(variants_raw, list):
            raise ValueError(f"sweeps.{sweep_name}.variants must be an array of tables")
        variants = tuple(
            _parse_sweep_variant(sweep_name=sweep_name, payload=item) for item in variants_raw
        )
        contracts_raw = _require_mapping(
            raw_value.get("contracts", {}), context=f"sweeps.{sweep_name}.contracts"
        )
        contracts = {
            case_id: _parse_sweep_contract(
                sweep_name=sweep_name,
                case_id=case_id,
                payload=_require_mapping(
                    raw_contract, context=f"sweeps.{sweep_name}.contracts.{case_id}"
                ),
            )
            for case_id, raw_contract in contracts_raw.items()
        }
        sweeps[sweep_name] = SweepDefinitionConfig(
            name=sweep_name,
            description=str(raw_value.get("description", "")),
            baseline_variant=_optional_string(raw_value.get("baseline_variant")),
            variants=variants,
            contracts=contracts,
        )
    return sweeps


def _parse_sweep_variant(*, sweep_name: str, payload: Any) -> SweepVariantConfig:
    """Parse one sweep variant."""

    mapping = _require_mapping(payload, context=f"sweeps.{sweep_name}.variants[]")
    use_source_cadence = bool(mapping.get("use_source_cadence", False))
    sample_interval = _optional_float(mapping.get("sample_interval_seconds"))
    if use_source_cadence:
        sample_interval = None
    elif sample_interval is None:
        raise ValueError(
            f"sweeps.{sweep_name}.variants `{mapping.get('name', '<unnamed>')}` must declare "
            "sample_interval_seconds or use_source_cadence = true"
        )
    return SweepVariantConfig(
        name=_require_string(mapping.get("name"), context=f"sweeps.{sweep_name}.variants[].name"),
        sample_interval_seconds=sample_interval,
        runtime_observer_interval_seconds=_optional_float(
            mapping.get("runtime_observer_interval_seconds")
        ),
    )


def _parse_sweep_contract(
    *,
    sweep_name: str,
    case_id: str,
    payload: dict[str, Any],
) -> SweepContractConfig:
    """Parse one case-specific sweep contract."""

    required_labels = tuple(
        cast(SweepStateLabel, item)
        for item in _require_string_list(payload.get("required_labels", []))
    )
    required_sequence = tuple(
        cast(SweepStateLabel, item)
        for item in _require_string_list(payload.get("required_sequence", []))
    )
    forbidden_terminal_results = tuple(
        cast(TrackedLastTurnResult, item)
        for item in _require_string_list(payload.get("forbidden_terminal_results", []))
    )
    terminal_result_value = _optional_string(payload.get("required_terminal_result"))
    required_terminal_result = (
        cast(TrackedLastTurnResult, terminal_result_value)
        if terminal_result_value is not None
        else None
    )
    return SweepContractConfig(
        required_labels=required_labels,
        required_sequence=required_sequence,
        required_terminal_result=required_terminal_result,
        forbidden_terminal_results=forbidden_terminal_results,
        max_first_occurrence_drift_seconds=float(
            payload.get("max_first_occurrence_drift_seconds", 2.0)
        ),
    )


def _load_toml_mapping(path: Path) -> dict[str, Any]:
    """Load one TOML file as a mapping."""

    try:
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    except FileNotFoundError as exc:  # pragma: no cover - direct filesystem error
        raise ValueError(f"Demo config not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Failed to parse demo config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Demo config {path} must parse to a table")
    return payload


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two config mappings, replacing lists and scalars."""

    merged = copy.deepcopy(base)
    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(
                cast(dict[str, Any], base_value),
                cast(dict[str, Any], value),
            )
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _require_mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one validated mapping."""

    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a table")
    return cast(dict[str, Any], value)


def _require_string(value: Any, *, context: str) -> str:
    """Return one required string value."""

    if value is None:
        raise ValueError(f"{context} is required")
    return str(value)


def _require_string_list(value: Any) -> list[str]:
    """Return one validated list of strings."""

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a list[str]")
    return [str(item) for item in value]


def _optional_float(value: Any) -> float | None:
    """Return one optional float value."""

    if value is None or isinstance(value, bool):
        return None
    return float(value)


def _optional_string(value: Any) -> str | None:
    """Return one optional string value."""

    if value is None:
        return None
    return str(value)
