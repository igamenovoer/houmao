"""CAO REST backend with runtime-generated profile support."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, Protocol, cast

from gig_agents.cao.models import CaoTerminalOutputResponse, CaoTerminalStatus
from gig_agents.cao.no_proxy import (
    inject_loopback_no_proxy_env_for_cao_base_url,
)
from gig_agents.cao.rest_client import CaoApiError, CaoRestClient

from ..agent_identity import (
    AGENT_MANIFEST_PATH_ENV_VAR,
    normalize_agent_identity_name,
)
from ..errors import BackendExecutionError
from ..launch_plan import configured_cao_shadow_policy
from ..loaders import parse_env_file
from ..models import CaoParsingMode, LaunchPlan, SessionControlResult, SessionEvent
from .claude_bootstrap import ensure_claude_home_bootstrap
from .codex_bootstrap import ensure_codex_home_bootstrap
from .shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    ANOMALY_STALLED_ENTERED,
    ANOMALY_STALLED_RECOVERED,
    ShadowParserAnomaly,
    ShadowParserError,
    ShadowParserMetadata,
    ShadowRuntimeStatus,
)
from .shadow_parser_stack import (
    ShadowParser,
    ShadowParserStack,
)
from .tmux_runtime import (
    TmuxCommandError,
    cleanup_tmux_session as cleanup_tmux_session_shared,
    create_tmux_session as create_tmux_session_shared,
    ensure_tmux_available as ensure_tmux_available_shared,
    generate_tmux_session_name as generate_tmux_session_name_shared,
    list_tmux_sessions as list_tmux_sessions_shared,
    run_tmux as run_tmux_shared,
    set_tmux_session_environment as set_tmux_session_environment_shared,
    tmux_error_detail as tmux_error_detail_shared,
)

_CAO_PROVIDER_BY_TOOL: Final[dict[str, str]] = {
    "codex": "codex",
    "claude": "claude_code",
}
_CAO_ONLY_READY_STATUSES: Final[set[CaoTerminalStatus]] = {
    CaoTerminalStatus.IDLE,
    CaoTerminalStatus.COMPLETED,
}
_PARSER_FAMILY_CAO_NATIVE: Final[str] = "cao_native"
_DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS: Final[float] = 30.0
_DEFAULT_STALLED_IS_TERMINAL: Final[bool] = False

_CANONICAL_STATUS_BY_BACKEND_STATUS: Final[dict[str, str]] = {
    "idle": "completed",
    "completed": "completed",
    "processing": "processing",
    "waiting_user_answer": "waiting_user_answer",
    "unknown": "unknown",
    "stalled": "stalled",
    "error": "error",
}

_TMUX_WINDOW_FORMAT: Final[str] = "#{window_id}\t#{window_index}\t#{window_name}"
_TMUX_WINDOW_RESOLVE_MAX_ATTEMPTS: Final[int] = 5
_TMUX_WINDOW_RESOLVE_RETRY_SECONDS: Final[float] = 0.1


@dataclass
class CaoSessionState:
    """Persisted CAO backend state."""

    api_base_url: str
    session_name: str
    terminal_id: str
    profile_name: str
    profile_path: str
    parsing_mode: CaoParsingMode
    turn_index: int = 0


@dataclass(frozen=True)
class _EngineTurnResult:
    output_text: str
    output_source_mode: Literal["last", "full"]
    raw_backend_status: str
    parser_family: str
    parser_metadata: dict[str, object]
    diagnostics: dict[str, object]


class _TurnEngine(Protocol):
    def execute_turn(
        self,
        prompt: str,
        *,
        turn_index: int,
    ) -> tuple[list[SessionEvent], _EngineTurnResult]:
        """Run one mode-specific turn."""


class CaoOnlyTurnEngine:
    """Execute turns using CAO-native status/output paths only."""

    def __init__(self, session: "CaoRestSession") -> None:
        self._session = session

    def execute_turn(
        self,
        prompt: str,
        *,
        turn_index: int,
    ) -> tuple[list[SessionEvent], _EngineTurnResult]:
        events: list[SessionEvent] = []

        self._session._wait_for_cao_ready_status(during_turn=False)
        submit_result = self._session._client.send_terminal_input(
            self._session._terminal_id,
            prompt,
        )
        if not submit_result.success:
            raise BackendExecutionError("CAO terminal rejected input submission")
        events.append(
            SessionEvent(
                kind="submitted",
                message="Prompt submitted to CAO terminal",
                turn_index=turn_index,
                payload={"terminal_id": self._session._terminal_id},
            )
        )

        completion_status = self._session._wait_for_cao_ready_status(during_turn=True)
        output = self._session._get_terminal_output_last()
        output_text = output.output.strip()

        return events, _EngineTurnResult(
            output_text=output_text,
            output_source_mode="last",
            raw_backend_status=completion_status.value,
            parser_family=_PARSER_FAMILY_CAO_NATIVE,
            parser_metadata={},
            diagnostics={
                "readiness_source": "cao_terminal_status",
                "completion_source": "cao_terminal_status",
                "extraction_source": "cao_output_mode_last",
            },
        )


class ShadowOnlyTurnEngine:
    """Execute turns using runtime-owned shadow parser paths only."""

    def __init__(self, session: "CaoRestSession") -> None:
        self._session = session

    def execute_turn(
        self,
        prompt: str,
        *,
        turn_index: int,
    ) -> tuple[list[SessionEvent], _EngineTurnResult]:
        events: list[SessionEvent] = []

        parser, parser_family = self._session._select_shadow_parser()
        readiness_anomalies = self._session._wait_for_shadow_ready_status(
            parser=parser,
            parser_family=parser_family,
        )
        baseline_output = self._session._get_terminal_output_full()
        baseline_pos = self._session._capture_shadow_baseline(
            parser=parser,
            parser_family=parser_family,
            output=baseline_output.output,
        )

        submit_result = self._session._client.send_terminal_input(
            self._session._terminal_id,
            prompt,
        )
        if not submit_result.success:
            raise BackendExecutionError("CAO terminal rejected input submission")
        events.append(
            SessionEvent(
                kind="submitted",
                message="Prompt submitted to CAO terminal",
                turn_index=turn_index,
                payload={"terminal_id": self._session._terminal_id},
            )
        )

        output, shadow_status, completion_anomalies = (
            self._session._wait_for_shadow_completion(
                parser=parser,
                parser_family=parser_family,
                baseline_pos=baseline_pos,
            )
        )
        extraction = self._session._extract_shadow_answer(
            parser=parser,
            parser_family=parser_family,
            output=output.output,
            baseline_pos=baseline_pos,
            allow_baseline_fallback=True,
        )

        output_text = extraction.answer_text.strip()
        if not output_text:
            excerpt = self._session._shadow_tail_excerpt(
                parser=parser, output=output.output
            )
            detail = (
                f"{parser_family} extraction returned an empty answer "
                "(parsing_mode=shadow_only)"
            )
            if excerpt:
                detail = f"{detail}\n\nTail excerpt:\n{excerpt}"
            raise BackendExecutionError(detail)

        merged_anomalies = self._session._merge_anomalies(
            readiness_anomalies,
            completion_anomalies,
            shadow_status.metadata.anomalies,
            extraction.metadata.anomalies,
        )
        parser_metadata: dict[str, object] = {
            "shadow_parser_preset": extraction.metadata.parser_preset_id,
            "shadow_parser_version": extraction.metadata.parser_preset_version,
            "shadow_output_format": extraction.metadata.output_format,
            "shadow_output_variant": extraction.metadata.output_variant,
            "shadow_output_format_match": extraction.metadata.output_format_match,
            "shadow_selection_source": extraction.metadata.selection_source,
            "shadow_detected_version": extraction.metadata.detected_version,
            "shadow_requested_version": extraction.metadata.requested_version,
            "shadow_parser_anomalies": self._session._serialize_anomalies(
                merged_anomalies
            ),
            "baseline_invalidated": extraction.metadata.baseline_invalidated,
            "unknown_to_stalled_timeout_seconds": (
                self._session._shadow_stall_policy.unknown_to_stalled_timeout_seconds
            ),
            "stalled_is_terminal": self._session._shadow_stall_policy.stalled_is_terminal,
        }
        if shadow_status.waiting_user_answer_excerpt:
            parser_metadata["waiting_user_answer_excerpt"] = (
                shadow_status.waiting_user_answer_excerpt
            )

        return events, _EngineTurnResult(
            output_text=output_text,
            output_source_mode="full",
            raw_backend_status=shadow_status.status,
            parser_family=parser_family,
            parser_metadata=parser_metadata,
            diagnostics={
                "readiness_source": "runtime_shadow_mode_full",
                "completion_source": "runtime_shadow_mode_full",
                "extraction_source": "runtime_shadow_mode_full",
                "baseline_pos": baseline_pos,
                "baseline_invalidated": extraction.metadata.baseline_invalidated,
                "unknown_to_stalled_timeout_seconds": (
                    self._session._shadow_stall_policy.unknown_to_stalled_timeout_seconds
                ),
                "stalled_is_terminal": (
                    self._session._shadow_stall_policy.stalled_is_terminal
                ),
            },
        )


@dataclass(frozen=True)
class _ShadowStatusResult:
    status: str
    metadata: ShadowParserMetadata
    waiting_user_answer_excerpt: str | None = None


@dataclass(frozen=True)
class _ShadowExtractionResult:
    answer_text: str
    metadata: ShadowParserMetadata


@dataclass(frozen=True)
class _ShadowStallPolicy:
    """Runtime policy for unknown-to-stalled lifecycle handling."""

    unknown_to_stalled_timeout_seconds: float
    stalled_is_terminal: bool


@dataclass(frozen=True)
class _TmuxWindowRecord:
    """Stable tmux window identity plus human-readable diagnostics."""

    window_id: str
    window_index: str
    window_name: str


@dataclass
class _ShadowLifecycleTracker:
    """Track unknown/stalled lifecycle transitions for one polling phase."""

    phase: Literal["readiness", "completion"]
    unknown_started_at: float | None = None
    stalled_started_at: float | None = None
    anomalies: list[ShadowParserAnomaly] = field(default_factory=list)

    def observe(
        self,
        *,
        parser_status: str,
        parser_family: str,
        now_monotonic: float,
        timeout_seconds: float,
    ) -> ShadowRuntimeStatus:
        """Map parser status to runtime lifecycle status and record anomalies."""

        if parser_status == "unknown":
            if self.unknown_started_at is None:
                self.unknown_started_at = now_monotonic
            elapsed_unknown_seconds = max(now_monotonic - self.unknown_started_at, 0.0)
            if elapsed_unknown_seconds >= timeout_seconds:
                if self.stalled_started_at is None:
                    self.stalled_started_at = now_monotonic
                    self.anomalies.append(
                        ShadowParserAnomaly(
                            code=ANOMALY_STALLED_ENTERED,
                            message=(
                                "Shadow status remained unknown and entered "
                                "stalled lifecycle state"
                            ),
                            details={
                                "phase": self.phase,
                                "elapsed_unknown_seconds": _format_seconds(
                                    elapsed_unknown_seconds
                                ),
                                "parser_family": parser_family,
                            },
                        )
                    )
                return "stalled"
            return "unknown"

        if self.stalled_started_at is not None:
            elapsed_stalled_seconds = max(now_monotonic - self.stalled_started_at, 0.0)
            self.anomalies.append(
                ShadowParserAnomaly(
                    code=ANOMALY_STALLED_RECOVERED,
                    message="Shadow status recovered from stalled to known state",
                    details={
                        "phase": self.phase,
                        "elapsed_stalled_seconds": _format_seconds(
                            elapsed_stalled_seconds
                        ),
                        "parser_family": parser_family,
                        "recovered_to": parser_status,
                    },
                )
            )

        self.unknown_started_at = None
        self.stalled_started_at = None
        return cast(ShadowRuntimeStatus, parser_status)

    def elapsed_unknown_seconds(self, *, now_monotonic: float) -> float | None:
        """Return current continuous unknown duration, if any."""

        if self.unknown_started_at is None:
            return None
        return max(now_monotonic - self.unknown_started_at, 0.0)

    def elapsed_stalled_seconds(self, *, now_monotonic: float) -> float | None:
        """Return current stalled duration, if any."""

        if self.stalled_started_at is None:
            return None
        return max(now_monotonic - self.stalled_started_at, 0.0)


def default_cao_agent_store(cao_home: Path | None = None) -> Path:
    """Return the CAO local agent-store path.

    Parameters
    ----------
    cao_home:
        Optional CAO home override.

    Returns
    -------
    Path
        Agent store directory path.
    """

    if cao_home is not None:
        return cao_home / "agent-store"
    return Path.home() / ".aws" / "cli-agent-orchestrator" / "agent-store"


def render_cao_profile(
    *,
    role_name: str,
    role_prompt: str,
    prepend: str | None = None,
    append: str | None = None,
    substitutions: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Render a per-session CAO profile from a role prompt template.

    Parameters
    ----------
    role_name:
        Role package name.
    role_prompt:
        Role prompt source text.
    prepend:
        Optional text prepended to the role prompt body.
    append:
        Optional text appended to the role prompt body.
    substitutions:
        Optional string replacement map applied to the role prompt.

    Returns
    -------
    tuple[str, str]
        `(profile_name, profile_markdown)`.
    """

    safe_role_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", role_name).strip("_") or "role"
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    profile_name = f"{safe_role_name}_{timestamp}_{uuid.uuid4().hex}"
    description = f"Runtime-generated profile for role {safe_role_name}"

    rendered_body = role_prompt
    if substitutions:
        for key, value in substitutions.items():
            rendered_body = rendered_body.replace(key, value)

    if prepend:
        rendered_body = f"{prepend}\n\n{rendered_body}"
    if append:
        rendered_body = f"{rendered_body}\n\n{append}"

    markdown = (
        "---\n"
        f"name: {profile_name}\n"
        f'description: "{description}"\n'
        "type: runtime-generated\n"
        f"source_role: {safe_role_name}\n"
        "---\n\n"
        f"{rendered_body.strip()}\n"
    )
    return profile_name, markdown


def install_cao_profile(
    *, profile_name: str, markdown: str, agent_store_dir: Path
) -> Path:
    """Install a rendered CAO profile markdown to the local agent store."""

    agent_store_dir.mkdir(parents=True, exist_ok=True)
    profile_path = agent_store_dir / f"{profile_name}.md"
    profile_path.write_text(markdown, encoding="utf-8")
    return profile_path


class CaoRestSession:
    """CAO-backed interactive session using REST endpoints."""

    backend = "cao_rest"

    def __init__(
        self,
        *,
        launch_plan: LaunchPlan,
        api_base_url: str,
        role_name: str,
        role_prompt: str,
        parsing_mode: CaoParsingMode,
        session_manifest_path: Path | None = None,
        agent_identity: str | None = None,
        profile_store_dir: Path | None = None,
        poll_interval_seconds: float = 0.4,
        timeout_seconds: float = 120.0,
        prepend_role_text: str | None = None,
        append_role_text: str | None = None,
        substitutions: dict[str, str] | None = None,
        existing_state: CaoSessionState | None = None,
    ) -> None:
        self._plan = launch_plan
        self._api_base_url = api_base_url
        self._poll_interval_seconds = poll_interval_seconds
        self._timeout_seconds = timeout_seconds
        self._client = CaoRestClient(api_base_url, timeout_seconds=timeout_seconds)
        self._profile_store_dir = profile_store_dir or default_cao_agent_store()
        self._provider = _provider_for_tool(launch_plan.tool)
        self._parsing_mode = self._require_supported_parsing_mode(parsing_mode)
        self._shadow_stall_policy = _resolve_shadow_stall_policy(launch_plan)
        self._shadow_parser_stack = (
            ShadowParserStack(tool=launch_plan.tool)
            if launch_plan.tool in {"claude", "codex"}
            else None
        )
        self._turn_engines: dict[CaoParsingMode, _TurnEngine] = {
            "cao_only": CaoOnlyTurnEngine(self),
            "shadow_only": ShadowOnlyTurnEngine(self),
        }
        self._startup_warnings: list[str] = []

        if existing_state is not None:
            if existing_state.parsing_mode != self._parsing_mode:
                raise BackendExecutionError(
                    "CAO parsing_mode mismatch between constructor input and "
                    f"persisted state: {self._parsing_mode!r} vs "
                    f"{existing_state.parsing_mode!r}."
                )
            self._profile_name = existing_state.profile_name
            self._profile_path = Path(existing_state.profile_path)
            self._session_name = existing_state.session_name
            self._terminal_id = existing_state.terminal_id
            self._turn_index = existing_state.turn_index
            self._session_manifest_path: Path | None = None
            return

        if session_manifest_path is None:
            raise BackendExecutionError(
                "CAO session start requires an absolute session manifest path."
            )
        self._session_manifest_path = session_manifest_path.resolve()

        profile_name, markdown = render_cao_profile(
            role_name=role_name,
            role_prompt=role_prompt,
            prepend=prepend_role_text,
            append=append_role_text,
            substitutions=substitutions,
        )
        self._profile_name = profile_name
        profile_path = install_cao_profile(
            profile_name=profile_name,
            markdown=markdown,
            agent_store_dir=self._profile_store_dir,
        )
        self._profile_path = profile_path

        session_name = _select_cao_session_name(
            tool=self._plan.tool,
            role_name=role_name,
            requested_identity=agent_identity,
        )
        self._session_name = session_name
        self._terminal_id = self._start_terminal(session_name=session_name)
        self._turn_index = 0

    @property
    def state(self) -> CaoSessionState:
        """Return current CAO backend state."""

        return CaoSessionState(
            api_base_url=self._api_base_url,
            session_name=self._session_name,
            terminal_id=self._terminal_id,
            profile_name=self._profile_name,
            profile_path=str(self._profile_path),
            parsing_mode=self._parsing_mode,
            turn_index=self._turn_index,
        )

    @property
    def startup_warnings(self) -> tuple[str, ...]:
        """Return non-fatal warnings captured during CAO session startup."""

        return tuple(self._startup_warnings)

    def _record_startup_warning(self, warning: str) -> None:
        self._startup_warnings.append(warning)

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Send one prompt turn via CAO direct input endpoints."""

        if not prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")

        turn_index = self._turn_index + 1
        engine = self._select_turn_engine()
        events, result = engine.execute_turn(prompt, turn_index=turn_index)
        done_payload = self._post_process_turn_result(result)
        events.append(
            SessionEvent(
                kind="done",
                message=result.output_text or "prompt completed",
                turn_index=turn_index,
                payload=done_payload,
            )
        )
        self._turn_index = turn_index
        return events

    def _select_turn_engine(self) -> _TurnEngine:
        engine = self._turn_engines.get(self._parsing_mode)
        if engine is None:
            raise BackendExecutionError(
                "Unsupported CAO parsing mode "
                f"{self._parsing_mode!r}; expected one of ['cao_only', 'shadow_only']."
            )
        return engine

    def _post_process_turn_result(self, result: _EngineTurnResult) -> dict[str, object]:
        canonical_status = _CANONICAL_STATUS_BY_BACKEND_STATUS.get(
            result.raw_backend_status,
            "unknown",
        )
        return {
            "terminal_id": self._terminal_id,
            "parsing_mode": self._parsing_mode,
            "parser_family": result.parser_family,
            "output_source_mode": result.output_source_mode,
            "raw_backend_status": result.raw_backend_status,
            "canonical_runtime_status": canonical_status,
            "parser_metadata": result.parser_metadata,
            "mode_diagnostics": result.diagnostics,
        }

    @staticmethod
    def _serialize_anomalies(
        anomalies: tuple[ShadowParserAnomaly, ...],
    ) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for anomaly in anomalies:
            payload.append(
                {
                    "code": anomaly.code,
                    "message": anomaly.message,
                    "details": dict(anomaly.details),
                }
            )
        return payload

    @staticmethod
    def _merge_anomalies(
        *groups: tuple[ShadowParserAnomaly, ...],
    ) -> tuple[ShadowParserAnomaly, ...]:
        merged: list[ShadowParserAnomaly] = []
        seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
        for group in groups:
            for anomaly in group:
                key = (
                    anomaly.code,
                    anomaly.message,
                    tuple(sorted(anomaly.details.items())),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(anomaly)
        return tuple(merged)

    def _get_terminal_output_last(self) -> CaoTerminalOutputResponse:
        try:
            return self._client.get_terminal_output(self._terminal_id, mode="last")
        except CaoApiError as exc:
            raise BackendExecutionError(
                "Failed to fetch CAO terminal output "
                f"(terminal_id={self._terminal_id}, mode=last): {exc.detail}"
            ) from exc

    def _get_terminal_output_full(self) -> CaoTerminalOutputResponse:
        try:
            return self._client.get_terminal_output(self._terminal_id, mode="full")
        except CaoApiError as exc:
            raise BackendExecutionError(
                "Failed to fetch CAO terminal output "
                f"(terminal_id={self._terminal_id}, mode=full): {exc.detail}"
            ) from exc

    def _wait_for_cao_ready_status(self, *, during_turn: bool) -> CaoTerminalStatus:
        deadline = time.monotonic() + self._timeout_seconds
        while time.monotonic() < deadline:
            terminal = self._client.get_terminal(self._terminal_id)
            status = terminal.status
            if status in _CAO_ONLY_READY_STATUSES:
                return status
            if status == CaoTerminalStatus.WAITING_USER_ANSWER:
                raise BackendExecutionError(
                    self._format_cao_waiting_user_answer_error(during_turn=during_turn)
                )
            if status == CaoTerminalStatus.ERROR:
                raise BackendExecutionError(
                    "CAO terminal entered error state "
                    f"(terminal_id={self._terminal_id}, parsing_mode=cao_only)"
                )
            time.sleep(self._poll_interval_seconds)

        phase = "turn completion" if during_turn else "readiness"
        raise BackendExecutionError(
            "Timed out waiting for CAO terminal "
            f"{self._terminal_id} {phase} in parsing_mode=cao_only"
        )

    def _wait_for_shadow_ready_status(
        self,
        *,
        parser: ShadowParser,
        parser_family: str,
    ) -> tuple[ShadowParserAnomaly, ...]:
        deadline = time.monotonic() + self._timeout_seconds
        lifecycle = _ShadowLifecycleTracker(phase="readiness")
        last_runtime_status: ShadowRuntimeStatus = "unknown"
        last_output: CaoTerminalOutputResponse | None = None
        while time.monotonic() < deadline:
            output = self._get_terminal_output_full()
            now_monotonic = time.monotonic()
            shadow_status = self._classify_shadow_status(
                parser=parser,
                parser_family=parser_family,
                output=output.output,
                baseline_pos=0,
            )
            runtime_status = lifecycle.observe(
                parser_status=shadow_status.status,
                parser_family=parser_family,
                now_monotonic=now_monotonic,
                timeout_seconds=self._shadow_stall_policy.unknown_to_stalled_timeout_seconds,
            )
            last_runtime_status = runtime_status
            last_output = output

            if runtime_status in {"idle", "completed"}:
                return tuple(lifecycle.anomalies)
            if runtime_status == "waiting_user_answer":
                raise BackendExecutionError(
                    self._format_shadow_waiting_user_answer_error(
                        parser_family=parser_family,
                        shadow_status=shadow_status,
                        output=output.output,
                        during_turn=False,
                    )
                )
            if (
                runtime_status == "stalled"
                and self._shadow_stall_policy.stalled_is_terminal
            ):
                raise BackendExecutionError(
                    self._format_shadow_stalled_error(
                        parser=parser,
                        parser_family=parser_family,
                        output=output.output,
                        phase="readiness",
                        parser_status=shadow_status.status,
                        elapsed_unknown_seconds=lifecycle.elapsed_unknown_seconds(
                            now_monotonic=now_monotonic
                        ),
                        elapsed_stalled_seconds=lifecycle.elapsed_stalled_seconds(
                            now_monotonic=now_monotonic
                        ),
                    )
                )
            time.sleep(self._poll_interval_seconds)

        detail = (
            "Timed out waiting for shadow-ready state from mode=full output "
            f"(terminal_id={self._terminal_id}, parser_family={parser_family}, "
            f"shadow_status={last_runtime_status})"
        )
        if last_output is not None:
            excerpt = self._shadow_tail_excerpt(
                parser=parser, output=last_output.output
            )
            if excerpt:
                detail = f"{detail}\n\nTail excerpt:\n{excerpt}"
        raise BackendExecutionError(detail)

    def _wait_for_shadow_completion(
        self,
        *,
        parser: ShadowParser,
        parser_family: str,
        baseline_pos: int,
    ) -> tuple[
        CaoTerminalOutputResponse, _ShadowStatusResult, tuple[ShadowParserAnomaly, ...]
    ]:
        deadline = time.monotonic() + self._timeout_seconds
        last_shadow_status: _ShadowStatusResult | None = None
        last_output: CaoTerminalOutputResponse | None = None
        saw_processing = False
        lifecycle = _ShadowLifecycleTracker(phase="completion")

        while time.monotonic() < deadline:
            output = self._get_terminal_output_full()
            now_monotonic = time.monotonic()
            shadow_status = self._classify_shadow_status(
                parser=parser,
                parser_family=parser_family,
                output=output.output,
                baseline_pos=baseline_pos,
            )
            parser_status = shadow_status.status
            runtime_status = lifecycle.observe(
                parser_status=parser_status,
                parser_family=parser_family,
                now_monotonic=now_monotonic,
                timeout_seconds=self._shadow_stall_policy.unknown_to_stalled_timeout_seconds,
            )
            shadow_status = replace(shadow_status, status=runtime_status)
            last_shadow_status = shadow_status
            last_output = output

            if runtime_status == "completed":
                return output, shadow_status, tuple(lifecycle.anomalies)
            if runtime_status == "waiting_user_answer":
                raise BackendExecutionError(
                    self._format_shadow_waiting_user_answer_error(
                        parser_family=parser_family,
                        shadow_status=shadow_status,
                        output=output.output,
                        during_turn=True,
                    )
                )
            if runtime_status == "stalled":
                if self._shadow_stall_policy.stalled_is_terminal:
                    raise BackendExecutionError(
                        self._format_shadow_stalled_error(
                            parser=parser,
                            parser_family=parser_family,
                            output=output.output,
                            phase="completion",
                            parser_status=parser_status,
                            elapsed_unknown_seconds=lifecycle.elapsed_unknown_seconds(
                                now_monotonic=now_monotonic
                            ),
                            elapsed_stalled_seconds=lifecycle.elapsed_stalled_seconds(
                                now_monotonic=now_monotonic
                            ),
                        )
                    )
                time.sleep(self._poll_interval_seconds)
                continue

            if runtime_status == "processing":
                saw_processing = True
            if runtime_status == "idle" and saw_processing:
                try:
                    extraction = self._extract_shadow_answer(
                        parser=parser,
                        parser_family=parser_family,
                        output=output.output,
                        baseline_pos=baseline_pos,
                        allow_baseline_fallback=True,
                    )
                except BackendExecutionError:
                    extraction = None
                if extraction is not None and extraction.answer_text.strip():
                    return (
                        output,
                        _ShadowStatusResult(
                            status="completed",
                            metadata=shadow_status.metadata,
                        ),
                        tuple(lifecycle.anomalies),
                    )

            time.sleep(self._poll_interval_seconds)

        status_text = last_shadow_status.status if last_shadow_status else "unknown"
        detail = (
            "Timed out waiting for shadow turn completion "
            f"(terminal_id={self._terminal_id}, parser_family={parser_family}, "
            f"shadow_status={status_text})"
        )
        if last_output is not None:
            excerpt = self._shadow_tail_excerpt(
                parser=parser, output=last_output.output
            )
            if excerpt:
                detail = f"{detail}\n\nTail excerpt:\n{excerpt}"
        raise BackendExecutionError(detail)

    def _classify_shadow_status(
        self,
        *,
        parser: ShadowParser,
        parser_family: str,
        output: str,
        baseline_pos: int,
    ) -> _ShadowStatusResult:
        try:
            status_result = parser.classify_shadow_status(
                output,
                baseline_pos=baseline_pos,
            )
            return _ShadowStatusResult(
                status=status_result.status,
                metadata=status_result.metadata,
                waiting_user_answer_excerpt=status_result.waiting_user_answer_excerpt,
            )
        except ShadowParserError as exc:
            raise BackendExecutionError(
                self._format_shadow_parse_error(
                    parser=parser,
                    parser_family=parser_family,
                    error=exc,
                    output=output,
                )
            ) from exc

    def _capture_shadow_baseline(
        self,
        *,
        parser: ShadowParser,
        parser_family: str,
        output: str,
    ) -> int:
        try:
            return parser.capture_baseline_pos(output)
        except ShadowParserError as exc:
            raise BackendExecutionError(
                self._format_shadow_parse_error(
                    parser=parser,
                    parser_family=parser_family,
                    error=exc,
                    output=output,
                )
            ) from exc

    def _extract_shadow_answer(
        self,
        *,
        parser: ShadowParser,
        parser_family: str,
        output: str,
        baseline_pos: int,
        allow_baseline_fallback: bool = False,
    ) -> _ShadowExtractionResult:
        try:
            extraction = parser.extract_last_answer(
                output,
                baseline_pos=baseline_pos,
            )
            return _ShadowExtractionResult(
                answer_text=extraction.answer_text,
                metadata=extraction.metadata,
            )
        except ShadowParserError as exc:
            if allow_baseline_fallback and baseline_pos > 0:
                try:
                    extraction = parser.extract_last_answer(
                        output,
                        baseline_pos=0,
                    )
                    metadata = self._metadata_with_baseline_fallback(
                        extraction.metadata
                    )
                    return _ShadowExtractionResult(
                        answer_text=extraction.answer_text,
                        metadata=metadata,
                    )
                except ShadowParserError:
                    pass
            raise BackendExecutionError(
                self._format_shadow_parse_error(
                    parser=parser,
                    parser_family=parser_family,
                    error=exc,
                    output=output,
                )
            ) from exc

    @staticmethod
    def _metadata_with_baseline_fallback(
        metadata: ShadowParserMetadata,
    ) -> ShadowParserMetadata:
        if metadata.baseline_invalidated and any(
            anomaly.code == ANOMALY_BASELINE_INVALIDATED
            for anomaly in metadata.anomalies
        ):
            return metadata

        anomalies = list(metadata.anomalies)
        if not any(
            anomaly.code == ANOMALY_BASELINE_INVALIDATED for anomaly in anomalies
        ):
            anomalies.append(
                ShadowParserAnomaly(
                    code=ANOMALY_BASELINE_INVALIDATED,
                    message="Extraction retried with baseline reset after parser drift",
                    details={
                        "provider": metadata.provider_id,
                        "preset": metadata.parser_preset_id,
                    },
                )
            )

        return replace(
            metadata,
            anomalies=tuple(anomalies),
            baseline_invalidated=True,
        )

    def _format_shadow_parse_error(
        self,
        *,
        parser: ShadowParser,
        parser_family: str,
        error: ShadowParserError,
        output: str,
    ) -> str:
        excerpt = self._shadow_tail_excerpt(parser=parser, output=output)
        detail = (
            f"Shadow parser error (parser_family={parser_family}, "
            f"parsing_mode=shadow_only): {error}"
        )
        metadata = error.metadata
        if metadata is not None:
            anomaly_codes = [anomaly.code for anomaly in metadata.anomalies]
            detail = (
                f"{detail} [error_code={error.error_code}, "
                f"preset={metadata.parser_preset_id}, "
                f"preset_version={metadata.parser_preset_version}, "
                f"output_format={metadata.output_format}, "
                f"output_variant={metadata.output_variant}, "
                f"output_format_match={metadata.output_format_match}, "
                f"anomalies={anomaly_codes}]"
            )
        else:
            detail = f"{detail} [error_code={error.error_code}]"
        detail = f"{detail}. No fallback to parsing_mode=cao_only is performed."
        if excerpt:
            detail = f"{detail}\n\nTail excerpt:\n{excerpt}"
        return detail

    def _shadow_tail_excerpt(self, *, parser: ShadowParser, output: str) -> str:
        return parser.ansi_stripped_tail_excerpt(output)

    def _format_shadow_waiting_user_answer_error(
        self,
        *,
        parser_family: str,
        shadow_status: _ShadowStatusResult,
        output: str,
        during_turn: bool,
    ) -> str:
        phase = "during turn execution" if during_turn else "before prompt submission"
        detail = (
            "Backend is waiting for user interaction in shadow mode "
            f"(parser_family={parser_family}, phase={phase})"
        )
        excerpt = shadow_status.waiting_user_answer_excerpt
        if not excerpt:
            parser, _ = self._select_shadow_parser()
            excerpt = self._shadow_tail_excerpt(parser=parser, output=output)
        if excerpt:
            detail = f"{detail}\n\nOptions excerpt:\n{excerpt}"
        return detail

    def _format_shadow_stalled_error(
        self,
        *,
        parser: ShadowParser,
        parser_family: str,
        output: str,
        phase: Literal["readiness", "completion"],
        parser_status: str,
        elapsed_unknown_seconds: float | None,
        elapsed_stalled_seconds: float | None,
    ) -> str:
        detail = (
            "Shadow parser entered stalled state "
            f"(parser_family={parser_family}, phase={phase}, "
            f"parsing_mode=shadow_only, parser_status={parser_status}, "
            f"stalled_is_terminal={self._shadow_stall_policy.stalled_is_terminal})"
        )
        if elapsed_unknown_seconds is not None:
            detail = (
                f"{detail}, elapsed_unknown_seconds="
                f"{_format_seconds(elapsed_unknown_seconds)}"
            )
        if elapsed_stalled_seconds is not None:
            detail = (
                f"{detail}, elapsed_stalled_seconds="
                f"{_format_seconds(elapsed_stalled_seconds)}"
            )

        excerpt = self._shadow_tail_excerpt(parser=parser, output=output)
        if excerpt:
            detail = f"{detail}\n\nTail excerpt:\n{excerpt}"
        return detail

    def _format_cao_waiting_user_answer_error(self, *, during_turn: bool) -> str:
        phase = "during turn execution" if during_turn else "before prompt submission"
        return (
            "CAO terminal requires interactive user selection "
            f"{phase} (parsing_mode=cao_only)."
        )

    def _select_shadow_parser(self) -> tuple[ShadowParser, str]:
        stack = self._require_shadow_parser_stack()
        selection = stack.selection()
        return selection.parser, selection.parser_family

    def _require_shadow_parser_stack(self) -> ShadowParserStack:
        if self._shadow_parser_stack is None:
            raise BackendExecutionError(
                "Shadow parsing is unsupported for tool "
                f"{self._plan.tool!r}; no parser family is available."
            )
        return self._shadow_parser_stack

    @staticmethod
    def _require_supported_parsing_mode(parsing_mode: str) -> CaoParsingMode:
        if parsing_mode in {"cao_only", "shadow_only"}:
            return cast(CaoParsingMode, parsing_mode)
        raise BackendExecutionError(
            "Unsupported CAO parsing mode "
            f"{parsing_mode!r}; expected one of ['cao_only', 'shadow_only']."
        )

    def interrupt(self) -> SessionControlResult:
        """Interrupt a CAO terminal turn by requesting exit."""

        try:
            result = self._client.exit_terminal(self._terminal_id)
        except CaoApiError as exc:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"CAO interrupt failed: {exc.detail}",
            )
        if not result.success:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail="CAO interrupt returned success=false",
            )
        return SessionControlResult(
            status="ok",
            action="interrupt",
            detail="Requested terminal exit",
        )

    def terminate(self) -> SessionControlResult:
        """Terminate CAO terminal/session resources."""

        errors: list[str] = []
        try:
            result = self._client.delete_terminal(self._terminal_id)
            if not result.success:
                errors.append("delete terminal returned success=false")
        except CaoApiError as exc:
            errors.append(f"delete terminal failed: {exc.detail}")

        try:
            result = self._client.delete_session(self._session_name)
            if not result.success:
                errors.append("delete session returned success=false")
        except CaoApiError as exc:
            errors.append(f"delete session failed: {exc.detail}")

        if errors:
            return SessionControlResult(
                status="error",
                action="terminate",
                detail="; ".join(errors),
            )

        return SessionControlResult(
            status="ok",
            action="terminate",
            detail="Deleted CAO terminal and session",
        )

    def close(self) -> None:
        """Release CAO resources."""

        self.terminate()

    def _start_terminal(self, *, session_name: str) -> str:
        launch_env = _compose_tmux_launch_env(
            self._plan,
            api_base_url=self._api_base_url,
        )
        if self._session_manifest_path is None:
            raise BackendExecutionError(
                "CAO start missing session manifest path for tmux env propagation."
            )
        launch_env[AGENT_MANIFEST_PATH_ENV_VAR] = str(self._session_manifest_path)

        if self._plan.tool == "claude":
            ensure_claude_home_bootstrap(
                home_path=self._plan.home_path,
                env=launch_env,
            )
        if self._plan.tool == "codex":
            ensure_codex_home_bootstrap(
                home_path=self._plan.home_path,
                working_directory=self._plan.working_directory,
            )

        bootstrap_window: _TmuxWindowRecord | None = None
        try:
            _ensure_required_executable(
                executable="cao-server",
                flow="CAO-backed runtime flow",
            )
            _ensure_required_executable(
                executable=self._plan.executable,
                flow=f"CAO-backed `{self._plan.tool}` flow",
            )
            self._client.health()
            _ensure_tmux_available()
            _create_tmux_session(
                session_name=session_name,
                working_directory=self._plan.working_directory,
            )
            try:
                bootstrap_window = _read_bootstrap_tmux_window(session_name=session_name)
            except BackendExecutionError as exc:
                self._record_startup_warning(
                    "Failed to capture bootstrap tmux window "
                    f"for session `{session_name}`: {exc}"
                )
            _set_tmux_session_environment(
                session_name=session_name,
                env_vars=launch_env,
            )
            terminal = self._client.create_terminal(
                session_name,
                provider=self._provider,
                agent_profile=self._profile_name,
                working_directory=str(self._plan.working_directory),
            )
        except (CaoApiError, BackendExecutionError, TimeoutError, OSError) as exc:
            _cleanup_tmux_session(session_name)
            raise BackendExecutionError(f"Failed to start CAO session: {exc}") from exc

        try:
            terminal_window = _resolve_tmux_window_by_name(
                session_name=session_name,
                window_name=terminal.name,
            )
        except BackendExecutionError as exc:
            self._record_startup_warning(
                "Failed to resolve CAO terminal tmux window "
                f"`{terminal.name}` in session `{session_name}`: {exc}"
            )
            return terminal.id

        if terminal_window is None:
            self._record_startup_warning(
                "Unable to resolve CAO terminal tmux window "
                f"`{terminal.name}` in session `{session_name}` after "
                f"{_TMUX_WINDOW_RESOLVE_MAX_ATTEMPTS} attempts; "
                "bootstrap pruning skipped."
            )
            return terminal.id

        try:
            _select_tmux_window(window_id=terminal_window.window_id)
        except BackendExecutionError as exc:
            self._record_startup_warning(
                "Failed to select CAO terminal tmux window "
                f"{_describe_tmux_window(terminal_window)} in session "
                f"`{session_name}`: {exc}"
            )

        if bootstrap_window is None:
            return terminal.id
        if bootstrap_window.window_id == terminal_window.window_id:
            return terminal.id

        try:
            _kill_tmux_window(window_id=bootstrap_window.window_id)
        except BackendExecutionError as exc:
            self._record_startup_warning(
                "Failed to prune bootstrap tmux window "
                f"{_describe_tmux_window(bootstrap_window)} in session "
                f"`{session_name}`: {exc}"
            )

        return terminal.id


def _resolve_shadow_stall_policy(launch_plan: LaunchPlan) -> _ShadowStallPolicy:
    """Resolve shadow stall policy from launch metadata with runtime defaults."""

    configured = configured_cao_shadow_policy(launch_plan) or {}
    timeout_raw = configured.get("unknown_to_stalled_timeout_seconds")
    if timeout_raw is None:
        timeout_seconds = _DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS
    elif isinstance(timeout_raw, (int, float)) and not isinstance(timeout_raw, bool):
        timeout_seconds = float(timeout_raw)
    else:
        raise BackendExecutionError(
            "Invalid launch metadata for shadow stall policy: "
            "`unknown_to_stalled_timeout_seconds` must be numeric."
        )
    if timeout_seconds <= 0:
        raise BackendExecutionError(
            "Invalid launch metadata for shadow stall policy: "
            "`unknown_to_stalled_timeout_seconds` must be > 0."
        )

    stalled_terminal_raw = configured.get("stalled_is_terminal")
    if stalled_terminal_raw is None:
        stalled_is_terminal = _DEFAULT_STALLED_IS_TERMINAL
    elif isinstance(stalled_terminal_raw, bool):
        stalled_is_terminal = stalled_terminal_raw
    else:
        raise BackendExecutionError(
            "Invalid launch metadata for shadow stall policy: "
            "`stalled_is_terminal` must be boolean."
        )

    return _ShadowStallPolicy(
        unknown_to_stalled_timeout_seconds=timeout_seconds,
        stalled_is_terminal=stalled_is_terminal,
    )


def _format_seconds(value: float) -> str:
    """Render one duration as a fixed-precision seconds string."""

    return f"{value:.3f}"


def generate_cao_session_name(
    *,
    tool: str,
    role_name: str,
    existing_sessions: set[str] | None = None,
) -> str:
    """Generate a canonical CAO tmux session identity.

    Parameters
    ----------
    tool:
        Backend tool id (`codex`, `claude`, ...).
    role_name:
        Selected role package name.
    existing_sessions:
        Optional pre-fetched tmux session names.

    Returns
    -------
    str
        Canonical session identity (`AGENTSYS-...`), unique among tmux sessions.
    """

    occupied = (
        existing_sessions if existing_sessions is not None else _list_tmux_sessions()
    )
    try:
        return generate_tmux_session_name_shared(
            tool=tool,
            role_name=role_name,
            existing_sessions=occupied,
        )
    except TmuxCommandError as exc:
        raise BackendExecutionError(str(exc)) from exc


def _select_cao_session_name(
    *, tool: str, role_name: str, requested_identity: str | None
) -> str:
    """Select a unique canonical CAO tmux session name."""

    _ensure_tmux_available()
    occupied = _list_tmux_sessions()
    if requested_identity is None:
        return generate_cao_session_name(
            tool=tool,
            role_name=role_name,
            existing_sessions=occupied,
        )

    normalized = normalize_agent_identity_name(requested_identity)
    session_name = normalized.canonical_name
    if session_name in occupied:
        raise BackendExecutionError(
            f"Explicit agent identity `{session_name}` is already in use by an "
            "existing tmux session. Choose a different name or stop the existing "
            "session first."
        )
    return session_name


def _provider_for_tool(tool: str) -> str:
    mapped = _CAO_PROVIDER_BY_TOOL.get(tool)
    if mapped is not None:
        return mapped

    supported = ", ".join(sorted(_CAO_PROVIDER_BY_TOOL))
    raise BackendExecutionError(
        f"Unsupported CAO provider mapping for tool `{tool}`. "
        f"Supported tools: {supported}."
    )


def _compose_tmux_launch_env(
    plan: LaunchPlan,
    *,
    api_base_url: str | None = None,
) -> dict[str, str]:
    """Build tmux session env using platform precedence rules.

    Precedence:
    1) Calling process env (`os.environ`)
    2) Credential profile env file values (`vars.env`)
    3) Launch-specific overlays (allowlisted launch env + home selector)
    """

    launch_env = dict(os.environ)
    launch_env.update(_credential_env_overlay(plan))
    launch_env.update(plan.env)
    launch_env[plan.home_env_var] = str(plan.home_path)
    if api_base_url is not None:
        inject_loopback_no_proxy_env_for_cao_base_url(
            launch_env,
            base_url=api_base_url,
        )
    return launch_env


def _credential_env_overlay(plan: LaunchPlan) -> dict[str, str]:
    source = plan.metadata.get("env_source_file")
    if not isinstance(source, str) or not source.strip():
        return dict(plan.env)

    try:
        return parse_env_file(Path(source).resolve())
    except Exception as exc:
        raise BackendExecutionError(
            "Failed to load credential env overlay for CAO/tmux launch from "
            f"`{source}`: {exc}"
        ) from exc


def _ensure_tmux_available() -> None:
    try:
        ensure_tmux_available_shared()
    except TmuxCommandError as exc:
        raise BackendExecutionError(
            "CAO backend requires tmux for per-session env propagation, "
            "but `tmux` was not found on PATH. Install tmux and verify with "
            "`command -v tmux`."
        ) from exc


def _ensure_required_executable(*, executable: str, flow: str) -> None:
    if shutil.which(executable) is not None:
        return
    raise BackendExecutionError(
        f"{flow} requires `{executable}` on PATH. Install CAO/tooling as needed "
        f"and verify with `command -v {executable}`."
    )


def _list_tmux_sessions() -> set[str]:
    """Return currently active tmux session names."""

    try:
        return list_tmux_sessions_shared()
    except TmuxCommandError as exc:
        raise BackendExecutionError(
            "Failed to list tmux sessions for CAO identity allocation: "
            f"{exc}"
        ) from exc


def _create_tmux_session(*, session_name: str, working_directory: Path) -> None:
    try:
        create_tmux_session_shared(
            session_name=session_name,
            working_directory=working_directory,
        )
    except TmuxCommandError as exc:
        raise BackendExecutionError(
            f"Failed to create tmux session `{session_name}`: {exc}"
        ) from exc


def _list_tmux_windows(*, session_name: str) -> list[_TmuxWindowRecord]:
    try:
        result = run_tmux_shared(
            ["list-windows", "-t", session_name, "-F", _TMUX_WINDOW_FORMAT]
        )
    except TmuxCommandError as exc:
        raise BackendExecutionError(
            f"Failed to run tmux list-windows for session `{session_name}`: {exc}"
        ) from exc

    if result.returncode != 0:
        raise BackendExecutionError(
            f"Failed to list tmux windows for session `{session_name}`: "
            f"{_tmux_error_detail(result)}"
        )

    windows: list[_TmuxWindowRecord] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t", maxsplit=2)
        if len(parts) != 3:
            raise BackendExecutionError(
                "Failed to parse tmux window listing for session "
                f"`{session_name}`: unexpected row `{line}`."
            )
        window_id, window_index, window_name = parts
        windows.append(
            _TmuxWindowRecord(
                window_id=window_id,
                window_index=window_index,
                window_name=window_name,
            )
        )
    return windows


def _read_bootstrap_tmux_window(*, session_name: str) -> _TmuxWindowRecord:
    windows = _list_tmux_windows(session_name=session_name)
    if not windows:
        raise BackendExecutionError(
            f"Failed to capture bootstrap tmux window for session `{session_name}`: "
            "session has no windows."
        )
    return windows[0]


def _resolve_tmux_window_by_name(
    *,
    session_name: str,
    window_name: str,
    max_attempts: int = _TMUX_WINDOW_RESOLVE_MAX_ATTEMPTS,
    retry_sleep_seconds: float = _TMUX_WINDOW_RESOLVE_RETRY_SECONDS,
) -> _TmuxWindowRecord | None:
    if max_attempts <= 0:
        raise BackendExecutionError("tmux window resolution requires max_attempts > 0")
    if retry_sleep_seconds < 0:
        raise BackendExecutionError(
            "tmux window resolution requires retry_sleep_seconds >= 0"
        )

    for attempt in range(max_attempts):
        windows = _list_tmux_windows(session_name=session_name)
        for window in windows:
            if window.window_name == window_name:
                return window
        if attempt + 1 < max_attempts and retry_sleep_seconds > 0:
            time.sleep(retry_sleep_seconds)
    return None


def _select_tmux_window(*, window_id: str) -> None:
    try:
        result = run_tmux_shared(["select-window", "-t", window_id])
    except TmuxCommandError as exc:
        raise BackendExecutionError(
            f"Failed to run tmux select-window for `{window_id}`: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = _tmux_error_detail(result)
        raise BackendExecutionError(
            f"Failed to select tmux window `{window_id}`: {detail or 'unknown tmux error'}"
        )


def _kill_tmux_window(*, window_id: str) -> None:
    try:
        result = run_tmux_shared(["kill-window", "-t", window_id])
    except TmuxCommandError as exc:
        raise BackendExecutionError(
            f"Failed to run tmux kill-window for `{window_id}`: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = _tmux_error_detail(result)
        raise BackendExecutionError(
            f"Failed to kill tmux window `{window_id}`: {detail or 'unknown tmux error'}"
        )


def _tmux_error_detail(result: subprocess.CompletedProcess[str]) -> str:
    detail = tmux_error_detail_shared(result)
    return detail or "unknown tmux error"


def _describe_tmux_window(window: _TmuxWindowRecord) -> str:
    return (
        f"[id={window.window_id}, index={window.window_index}, "
        f"name={window.window_name!r}]"
    )


def _set_tmux_session_environment(
    *, session_name: str, env_vars: dict[str, str]
) -> None:
    try:
        set_tmux_session_environment_shared(
            session_name=session_name,
            env_vars=env_vars,
        )
    except TmuxCommandError as exc:
        raise BackendExecutionError(str(exc)) from exc


def _cleanup_tmux_session(session_name: str) -> None:
    cleanup_tmux_session_shared(session_name=session_name)


def cao_backend_state_payload(state: CaoSessionState) -> dict[str, object]:
    """Convert CAO state to manifest backend payload."""

    return {
        "api_base_url": state.api_base_url,
        "session_name": state.session_name,
        "terminal_id": state.terminal_id,
        "profile_name": state.profile_name,
        "profile_path": state.profile_path,
        "parsing_mode": state.parsing_mode,
        "turn_index": state.turn_index,
    }
