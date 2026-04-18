"""Core runtime models and interfaces.

The runtime keeps these types backend-agnostic so higher-level callers can use
one interface for local and CAO-backed sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from houmao.agents.launch_policy.models import LaunchPolicyProvenance
from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig

BackendKind = Literal[
    "local_interactive",
    "codex_headless",
    "codex_app_server",
    "claude_headless",
    "gemini_headless",
    "cao_rest",
    "houmao_server_rest",
]
CaoParsingMode = Literal["cao_only", "shadow_only"]
RoleInjectionMethod = Literal[
    "native_developer_instructions",
    "native_append_system_prompt",
    "bootstrap_message",
    "cao_profile",
]
JoinedSessionOrigin = Literal["joined_tmux"]
JoinedLaunchPostureKind = Literal[
    "runtime_launch_plan",
    "tui_launch_options",
    "headless_launch_options",
    "unavailable",
]
JoinedLaunchEnvBindingMode = Literal["literal", "inherit"]
HeadlessResumeSelectionKind = Literal["none", "last", "exact"]
HeadlessTurnSessionSelectionMode = Literal["new", "tool_last_or_new", "exact"]
RelaunchChatSessionSelectionMode = Literal["new", "tool_last_or_new", "exact"]


@dataclass(frozen=True)
class JoinedLaunchEnvBinding:
    """One persisted launch-env binding for joined-session relaunch."""

    mode: JoinedLaunchEnvBindingMode
    name: str
    value: str | None = None


@dataclass(frozen=True)
class HeadlessResumeSelection:
    """Persisted resume selector for joined headless sessions."""

    kind: HeadlessResumeSelectionKind
    value: str | None = None


@dataclass(frozen=True)
class HeadlessTurnSessionSelection:
    """Resolved per-turn session selection for native headless execution."""

    mode: HeadlessTurnSessionSelectionMode
    session_id: str | None = None

    def __post_init__(self) -> None:
        """Validate one resolved headless turn-session selection."""

        if self.mode == "exact":
            if self.session_id is None or not self.session_id.strip():
                raise ValueError("exact headless turn selection requires session_id")
            return
        if self.session_id is not None:
            raise ValueError("only exact headless turn selection may include session_id")


@dataclass(frozen=True)
class RelaunchChatSessionSelection:
    """Resolved provider chat-session selection for one managed-agent relaunch."""

    mode: RelaunchChatSessionSelectionMode
    session_id: str | None = None

    def __post_init__(self) -> None:
        """Validate one resolved relaunch chat-session selection."""

        if self.mode == "exact":
            if self.session_id is None or not self.session_id.strip():
                raise ValueError("exact relaunch chat-session selection requires session_id")
            return
        if self.session_id is not None:
            raise ValueError("only exact relaunch chat-session selection may include session_id")

    def to_headless_turn_selection(self) -> HeadlessTurnSessionSelection:
        """Return the equivalent one-turn selector for a headless provider prompt."""

        return HeadlessTurnSessionSelection(mode=self.mode, session_id=self.session_id)


@dataclass(frozen=True)
class RoleInjectionPlan:
    """Describe how a role prompt is applied.

    Parameters
    ----------
    method:
        Backend-specific strategy for role prompt application.
    role_name:
        Repository role package name.
    prompt:
        Raw role prompt text loaded from `roles/<role>/system-prompt.md`.
    bootstrap_message:
        Optional derived first-turn message used for fallback bootstrap mode.
    """

    method: RoleInjectionMethod
    role_name: str
    prompt: str
    bootstrap_message: str | None = None


@dataclass(frozen=True)
class LaunchPlan:
    """Backend-agnostic launch plan.

    Parameters
    ----------
    backend:
        Concrete backend selected for session execution.
    tool:
        Tool identity from the brain manifest (`codex`, `claude`, `gemini`).
    executable:
        Executable name/path for the backend command.
    args:
        Base arguments for process invocation.
    working_directory:
        Working directory used for launch and resume invariants.
    home_env_var:
        Tool home selector environment variable (for example `CODEX_HOME`).
    home_path:
        Constructed brain home path.
    env:
        Effective launch environment values (contains secrets in-memory).
    env_var_names:
        Env variable names that were selected by the allowlist.
    role_injection:
        Role prompt application strategy.
    metadata:
        Additional backend-specific options and resolved runtime fields.
    mailbox:
        Optional resolved mailbox binding for the session.
    """

    backend: BackendKind
    tool: str
    executable: str
    args: list[str]
    working_directory: Path
    home_env_var: str
    home_path: Path
    env: dict[str, str]
    env_var_names: list[str]
    role_injection: RoleInjectionPlan
    metadata: dict[str, Any] = field(default_factory=dict)
    mailbox: MailboxResolvedConfig | None = None
    launch_policy_provenance: LaunchPolicyProvenance | None = None
    transient_env_var_names: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def for_joined_session(
        cls,
        *,
        backend: BackendKind,
        tool: str,
        executable: str,
        args: list[str],
        working_directory: Path,
        home_env_var: str,
        home_path: Path,
        env: dict[str, str],
        env_var_names: list[str],
        role_name: str,
        role_prompt: str,
        metadata: dict[str, Any] | None = None,
        mailbox: MailboxResolvedConfig | None = None,
    ) -> LaunchPlan:
        """Build a join-derived launch plan without brain-manifest reconstruction."""

        joined_metadata = dict(metadata or {})
        joined_metadata.setdefault("session_origin", "joined_tmux")
        return cls(
            backend=backend,
            tool=tool,
            executable=executable,
            args=list(args),
            working_directory=working_directory.resolve(),
            home_env_var=home_env_var,
            home_path=home_path.resolve(),
            env=dict(env),
            env_var_names=sorted(set(env_var_names)),
            role_injection=RoleInjectionPlan(
                # Joined sessions do not reconstruct launch-time role injection.
                method="cao_profile",
                role_name=role_name,
                prompt=role_prompt,
            ),
            metadata=joined_metadata,
            mailbox=mailbox,
        )

    def redacted_payload(self) -> dict[str, Any]:
        """Return a secret-free payload suitable for persistence.

        Returns
        -------
        dict[str, Any]
            Launch-plan representation without env values.
        """

        return {
            "backend": self.backend,
            "tool": self.tool,
            "executable": self.executable,
            "args": list(self.args),
            "working_directory": str(self.working_directory),
            "home_selector": {
                "env_var": self.home_env_var,
                "home_path": str(self.home_path),
            },
            "env_var_names": sorted(
                name for name in self.env_var_names if name not in self.transient_env_var_names
            ),
            "role_injection": {
                "method": self.role_injection.method,
                "role_name": self.role_injection.role_name,
            },
            "metadata": _redact_metadata(self.metadata),
            "mailbox": self.mailbox.redacted_payload() if self.mailbox is not None else None,
            "launch_policy_provenance": (
                self.launch_policy_provenance.to_payload()
                if self.launch_policy_provenance is not None
                else None
            ),
        }


def _redact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in metadata.items():
        if "secret" in key.lower() or "token" in key.lower() or "password" in key.lower():
            continue
        if isinstance(value, dict):
            redacted[key] = _redact_metadata(value)
            continue
        if isinstance(value, list):
            redacted[key] = [
                _redact_metadata(item) if isinstance(item, dict) else item for item in value
            ]
            continue
        redacted[key] = value
    return redacted


@dataclass(frozen=True)
class SessionEvent:
    """Streaming event produced by an interactive session."""

    kind: str
    message: str
    turn_index: int
    payload: dict[str, Any] | None = None
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )


@dataclass(frozen=True)
class SessionControlResult:
    """Outcome for runtime control operations."""

    status: Literal["ok", "error"]
    action: Literal["interrupt", "terminate", "control_input", "relaunch"]
    detail: str


@dataclass(frozen=True)
class GatewayControlResult:
    """Outcome for gateway lifecycle and explicit gateway-managed control actions."""

    status: Literal["ok", "error"]
    action: Literal[
        "gateway_attach",
        "gateway_detach",
        "gateway_prompt",
        "gateway_interrupt",
    ]
    detail: str
    gateway_root: str | None = None
    gateway_host: str | None = None
    gateway_port: int | None = None


@dataclass(frozen=True)
class SessionResult:
    """Result summary for one prompt turn."""

    backend: BackendKind
    turn_index: int
    completed: bool
    interrupted: bool
    output_text: str
    session_id: str | None = None
    diagnostics: str = ""


class InteractiveSession(Protocol):
    """Backend-agnostic interactive session interface.

    Notes
    -----
    Implementations may keep a long-lived process (for example Codex app-server)
    or spawn one process per turn while preserving logical continuity through
    persisted backend state (for example headless `session_id`).
    """

    backend: BackendKind

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Send one prompt turn and return streaming events.

        Parameters
        ----------
        prompt:
            User prompt for the backend.

        Returns
        -------
        list[SessionEvent]
            Ordered events emitted during the turn.
        """

    def interrupt(self) -> SessionControlResult:
        """Best-effort interruption of in-flight backend work."""

    def terminate(self) -> SessionControlResult:
        """Terminate the backend session/process."""

    def close(self) -> None:
        """Release backend resources."""


@dataclass(frozen=True)
class SessionManifestHandle:
    """Resolved session manifest location and payload."""

    path: Path
    payload: dict[str, Any]
