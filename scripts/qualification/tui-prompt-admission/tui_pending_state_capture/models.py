"""Dataclasses and validation for the pending-state capture runner."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, cast

ProviderName = Literal["claude", "codex", "kimi"]
StepKind = Literal[
    "wait_seconds",
    "wait_for_pattern",
    "wait_for_pattern_absent",
    "send_text",
    "send_key",
]
TristateLabel = Literal["yes", "no", "unknown"]


PendingCountLabel = Literal[0, 1, 2, 3, "unknown"]


@dataclass(frozen=True)
class PendingCountPatterns:
    """Provider-specific rules for estimating queue depth from visible text."""

    extractor: Literal["count_markers", "regex_group"]
    marker_regex: str | None = None
    regex: str | None = None
    group_index: int = 1

    def compile(self) -> re.Pattern[str] | None:
        """Compile the configured regex when one is present."""

        if self.regex:
            return re.compile(self.regex, re.IGNORECASE)
        if self.marker_regex:
            return re.compile(self.marker_regex, re.MULTILINE | re.IGNORECASE)
        return None


@dataclass(frozen=True)
class PatternSpec:
    """One provider-visible regex and a human-readable note."""

    name: str
    regex: str
    description: str
    flags: int = field(default=re.IGNORECASE)

    def compile(self) -> re.Pattern[str]:
        """Compile the configured regex."""

        return re.compile(self.regex, self.flags)


@dataclass(frozen=True)
class WaitSecondsStep:
    """Sleep for a fixed duration."""

    kind: Literal["wait_seconds"]
    seconds: float
    note: str | None = None


@dataclass(frozen=True)
class WaitForPatternStep:
    """Poll the pane until a configured regex appears."""

    kind: Literal["wait_for_pattern"]
    pattern: str
    timeout_seconds: float
    required: bool = True
    non_fatal_on_timeout: bool = False
    note: str | None = None


@dataclass(frozen=True)
class WaitForPatternAbsentStep:
    """Poll the pane until a configured regex disappears."""

    kind: Literal["wait_for_pattern_absent"]
    pattern: str
    timeout_seconds: float
    required: bool = True
    note: str | None = None


@dataclass(frozen=True)
class SendTextStep:
    """Type literal text into the provider pane."""

    kind: Literal["send_text"]
    text: str
    note: str | None = None


@dataclass(frozen=True)
class SendKeyStep:
    """Send one tmux special key."""

    kind: Literal["send_key"]
    key: str
    note: str | None = None


LifecycleStep = (
    WaitSecondsStep | WaitForPatternStep | WaitForPatternAbsentStep | SendTextStep | SendKeyStep
)


@dataclass(frozen=True)
class LifecycleManifest:
    """Provider-specific capture script and matching surface patterns."""

    schema_version: int
    provider: ProviderName
    calibrated_version: str
    patterns: dict[str, PatternSpec]
    prompts: dict[str, str]
    steps: tuple[LifecycleStep, ...]
    pending_count_patterns: PendingCountPatterns | None = None
    target_pending_count: int | None = None


@dataclass(frozen=True)
class LabelRow:
    """One per-snapshot binary label template with optional queue-depth estimate."""

    can_accept_input: TristateLabel
    has_pending_message: TristateLabel
    pending_count: PendingCountLabel
    evidence_note: str


@dataclass(frozen=True)
class SpanSummary:
    """One contiguous run of identical binary labels."""

    can_accept_input: TristateLabel
    has_pending_message: TristateLabel
    pending_count: PendingCountLabel
    first_sample_id: str
    last_sample_id: str
    sample_count: int
    start_elapsed_seconds: float
    end_elapsed_seconds: float


@dataclass(frozen=True)
class LabelSummary:
    """Aggregate statistics over a labeled recording."""

    schema_version: int
    provider: ProviderName
    calibrated_version: str
    total_samples: int
    counts: dict[str, int]
    spans: tuple[SpanSummary, ...]


@dataclass(frozen=True)
class FileDigest:
    """SHA-256 digest and size for one frozen artifact."""

    path: str
    sha256: str
    bytes: int
    rows: int | None = None


@dataclass(frozen=True)
class FrozenEvidence:
    """Immutable evidence gate written after the recorder stops."""

    schema_version: int
    provider: ProviderName
    calibrated_version: str
    run_tainted: bool
    taint_reasons: tuple[str, ...]
    generated_at_utc: str
    artifacts: tuple[FileDigest, ...]
    transition_times: dict[str, float | None]
    observed_pending_count: int | None = None
    target_pending_count: int | None = None
    video: FileDigest | None = None


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _require_provider(value: Any) -> ProviderName:
    if value not in ("claude", "codex", "kimi"):
        raise ValueError(f"provider must be one of claude, codex, kimi: {value!r}")
    return cast(ProviderName, value)


def _load_pattern_spec(name: str, payload: Any) -> PatternSpec:
    if not isinstance(payload, dict):
        raise ValueError(f"pattern {name!r} must be an object")
    return PatternSpec(
        name=name,
        regex=_require_string(payload.get("regex"), f"patterns.{name}.regex"),
        description=str(payload.get("description", "")),
        flags=int(payload.get("flags", re.IGNORECASE)),
    )


def _load_step(payload: Any, prompts: dict[str, str]) -> LifecycleStep:
    if not isinstance(payload, dict):
        raise ValueError("each step must be an object")
    kind = _require_string(payload.get("kind"), "step.kind")
    if kind == "wait_seconds":
        return WaitSecondsStep(
            kind=cast(Literal["wait_seconds"], kind),
            seconds=float(payload.get("seconds", 0.0)),
            note=_optional_string(payload.get("note")),
        )
    if kind == "wait_for_pattern":
        return WaitForPatternStep(
            kind=cast(Literal["wait_for_pattern"], kind),
            pattern=_require_string(payload.get("pattern"), "step.pattern"),
            timeout_seconds=float(payload.get("timeout_seconds", 0.0)),
            required=bool(payload.get("required", True)),
            non_fatal_on_timeout=bool(payload.get("non_fatal_on_timeout", False)),
            note=_optional_string(payload.get("note")),
        )
    if kind == "wait_for_pattern_absent":
        return WaitForPatternAbsentStep(
            kind=cast(Literal["wait_for_pattern_absent"], kind),
            pattern=_require_string(payload.get("pattern"), "step.pattern"),
            timeout_seconds=float(payload.get("timeout_seconds", 0.0)),
            required=bool(payload.get("required", True)),
            note=_optional_string(payload.get("note")),
        )
    if kind == "send_text":
        text = _require_string(payload.get("text"), "step.text")
        return SendTextStep(
            kind=cast(Literal["send_text"], kind),
            text=_resolve_prompts(text, prompts),
            note=_optional_string(payload.get("note")),
        )
    if kind == "send_key":
        return SendKeyStep(
            kind=cast(Literal["send_key"], kind),
            key=_require_string(payload.get("key"), "step.key"),
            note=_optional_string(payload.get("note")),
        )
    raise ValueError(f"unknown step kind: {kind!r}")


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"expected string or null, got {type(value).__name__}")
    return value if value else None


def _resolve_prompts(text: str, prompts: dict[str, str]) -> str:
    """Replace ``{{name}}`` placeholders with configured prompt strings."""

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in prompts:
            raise ValueError(f"prompt placeholder {{{{{key}}}}} not defined in manifest")
        return prompts[key]

    return re.sub(r"\{\{([A-Za-z0-9_]+)\}\}", replacer, text)


def _load_pending_count_patterns(payload: Any) -> PendingCountPatterns | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError("pending_count_patterns must be an object or null")
    extractor = _require_string(payload.get("extractor"), "pending_count_patterns.extractor")
    if extractor not in ("count_markers", "regex_group"):
        raise ValueError(f"unknown pending_count_patterns extractor: {extractor!r}")
    return PendingCountPatterns(
        extractor=cast(Literal["count_markers", "regex_group"], extractor),
        marker_regex=_optional_string(payload.get("marker_regex")),
        regex=_optional_string(payload.get("regex")),
        group_index=int(payload.get("group_index", 1)),
    )


def load_lifecycle_manifest(payload: dict[str, Any]) -> LifecycleManifest:
    """Validate and parse one lifecycle manifest payload."""

    provider = _require_provider(payload.get("provider"))
    patterns_raw = payload.get("patterns")
    if not isinstance(patterns_raw, dict):
        raise ValueError("patterns must be an object")
    patterns = {name: _load_pattern_spec(name, value) for name, value in patterns_raw.items()}
    pending_count_patterns = _load_pending_count_patterns(payload.get("pending_count_patterns"))
    prompts_raw = payload.get("prompts", {})
    if not isinstance(prompts_raw, dict):
        raise ValueError("prompts must be an object")
    prompts = {name: str(value) for name, value in prompts_raw.items() if isinstance(value, str)}
    steps_raw = payload.get("steps")
    if not isinstance(steps_raw, list):
        raise ValueError("steps must be a list")
    steps = tuple(_load_step(item, prompts) for item in steps_raw)
    return LifecycleManifest(
        schema_version=int(payload.get("schema_version", 1)),
        provider=provider,
        calibrated_version=_require_string(payload.get("calibrated_version"), "calibrated_version"),
        patterns=patterns,
        pending_count_patterns=pending_count_patterns,
        prompts=prompts,
        steps=steps,
        target_pending_count=payload.get("target_pending_count"),
    )
