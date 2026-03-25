"""Typed models for versioned launch-policy resolution and application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version


OperatorPromptMode = Literal["interactive", "unattended"]
LaunchSurface = Literal[
    "raw_launch",
    "codex_headless",
    "codex_app_server",
    "claude_headless",
    "gemini_headless",
    "cao_rest",
    "houmao_server_rest",
]
LaunchPolicySelectionSource = Literal["registry", "env_override"]


class LaunchPolicyError(RuntimeError):
    """Raised when launch-policy resolution or application fails."""


class LaunchPolicyCompatibilityError(LaunchPolicyError):
    """Raised when unattended strategy compatibility cannot be satisfied."""

    def __init__(
        self,
        *,
        tool: str,
        backend: LaunchSurface,
        detected_version: str,
        requested_operator_prompt_mode: OperatorPromptMode,
        reason: str,
    ) -> None:
        self.tool = tool
        self.backend = backend
        self.detected_version = detected_version
        self.requested_operator_prompt_mode = requested_operator_prompt_mode
        self.reason = reason
        super().__init__(
            f"{reason} for tool={tool!r}, backend={backend!r}, version={detected_version!r}, "
            f"requested_operator_prompt_mode={requested_operator_prompt_mode!r}."
        )


@dataclass(frozen=True, order=True)
class ToolVersion:
    """Parsed comparable tool version."""

    parts: tuple[int, ...]
    raw: str

    @classmethod
    def parse(cls, value: str) -> ToolVersion:
        """Parse one dotted numeric version string."""

        cleaned = value.strip()
        if not cleaned:
            raise LaunchPolicyError("Tool version must not be empty.")

        pieces = cleaned.split(".")
        parsed_parts: list[int] = []
        for piece in pieces:
            if not piece.isdigit():
                raise LaunchPolicyError(f"Unsupported version component `{piece}` in `{value}`.")
            parsed_parts.append(int(piece))
        return cls(parts=tuple(parsed_parts), raw=cleaned)


@dataclass(frozen=True)
class SupportedVersionSpec:
    """Dependency-style supported-version declaration for one strategy."""

    raw: str
    _specifier_set: SpecifierSet = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate and cache the supported-version declaration."""

        cleaned = self.raw.strip()
        if not cleaned:
            raise LaunchPolicyError("supported_versions must not be empty.")
        try:
            specifier_set = SpecifierSet(cleaned)
        except InvalidSpecifier as exc:
            raise LaunchPolicyError(
                f"Unsupported supported_versions specifier `{cleaned}`."
            ) from exc
        object.__setattr__(self, "raw", cleaned)
        object.__setattr__(self, "_specifier_set", specifier_set)

    @classmethod
    def parse(cls, value: str) -> "SupportedVersionSpec":
        """Parse one dependency-style supported-version declaration."""

        return cls(raw=value)

    def contains(self, version: ToolVersion) -> bool:
        """Return whether one tool version matches the declaration."""

        try:
            parsed_version = Version(version.raw)
        except InvalidVersion as exc:
            raise LaunchPolicyError(
                f"Could not convert tool version `{version.raw}` into a dependency-style version."
            ) from exc
        return parsed_version in self._specifier_set

    def to_payload(self) -> str:
        """Return a JSON-serializable payload."""

        return self.raw


@dataclass(frozen=True)
class StrategyEvidence:
    """Evidence metadata for one strategy assumption."""

    kind: Literal["official_docs", "source_reference", "live_probe"]
    ref: str
    note: str

    def to_payload(self) -> dict[str, str]:
        """Return a JSON-serializable payload."""

        return {"kind": self.kind, "ref": self.ref, "note": self.note}


@dataclass(frozen=True)
class MinimalInputContract:
    """Declared minimal-input contract for one strategy."""

    credential_forms: tuple[str, ...]
    requires_user_prepared_state: bool
    notes: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return {
            "credential_forms": list(self.credential_forms),
            "requires_user_prepared_state": self.requires_user_prepared_state,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class OwnedPathSpec:
    """Runtime-owned path and logical subpaths for one strategy."""

    path: str
    keys: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return {"path": self.path, "keys": list(self.keys)}


@dataclass(frozen=True)
class LaunchPolicyAction:
    """One ordered strategy action."""

    kind: Literal[
        "cli_arg.ensure_present",
        "cli_arg.ensure_absent",
        "json.set",
        "toml.set",
        "validate.reject_conflicting_launch_args",
        "provider_hook.call",
    ]
    params: Mapping[str, Any]


@dataclass(frozen=True)
class LaunchPolicyStrategy:
    """One registry strategy entry."""

    strategy_id: str
    operator_prompt_mode: OperatorPromptMode
    backends: tuple[LaunchSurface, ...]
    supported_versions: SupportedVersionSpec
    minimal_inputs: MinimalInputContract
    evidence: tuple[StrategyEvidence, ...]
    owned_paths: tuple[OwnedPathSpec, ...]
    actions: tuple[LaunchPolicyAction, ...]

    def to_metadata_payload(self) -> dict[str, Any]:
        """Return diagnostic metadata for one resolved strategy."""

        return {
            "strategy_id": self.strategy_id,
            "operator_prompt_mode": self.operator_prompt_mode,
            "backends": list(self.backends),
            "supported_versions": self.supported_versions.to_payload(),
            "minimal_inputs": self.minimal_inputs.to_payload(),
            "evidence": [item.to_payload() for item in self.evidence],
            "owned_paths": [item.to_payload() for item in self.owned_paths],
        }


@dataclass(frozen=True)
class LaunchPolicyRegistryDocument:
    """One tool-scoped registry YAML document."""

    schema_version: int
    tool: str
    strategies: tuple[LaunchPolicyStrategy, ...]


@dataclass(frozen=True)
class LaunchPolicyRequest:
    """Inputs required to resolve and apply one launch policy."""

    tool: str
    backend: LaunchSurface
    executable: str
    base_args: tuple[str, ...]
    requested_operator_prompt_mode: OperatorPromptMode | None
    working_directory: Path
    home_path: Path
    env: Mapping[str, str]


@dataclass(frozen=True)
class LaunchPolicyProvenance:
    """Typed provenance for one resolved launch-policy strategy."""

    requested_operator_prompt_mode: OperatorPromptMode
    detected_tool_version: str
    selected_strategy_id: str
    selection_source: LaunchPolicySelectionSource
    override_env_var_name: str | None = None

    def to_payload(self) -> dict[str, str | None]:
        """Return a JSON-serializable payload."""

        return {
            "requested_operator_prompt_mode": self.requested_operator_prompt_mode,
            "detected_tool_version": self.detected_tool_version,
            "selected_strategy_id": self.selected_strategy_id,
            "selection_source": self.selection_source,
            "override_env_var_name": self.override_env_var_name,
        }


@dataclass(frozen=True)
class LaunchPolicyResult:
    """Resolved launch-policy output."""

    executable: str
    args: tuple[str, ...]
    provenance: LaunchPolicyProvenance | None
    strategy: LaunchPolicyStrategy | None
