"""High-level session runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .agent_identity import (
    AGENT_MANIFEST_PATH_ENV_VAR,
    is_path_like_agent_identity,
    normalize_agent_identity_name,
)
from .backends.cao_rest import (
    CaoRestSession,
    CaoSessionState,
    cao_backend_state_payload,
)
from .boundary_models import SessionManifestPayloadV2
from .backends.claude_headless import ClaudeHeadlessSession
from .backends.codex_headless import CodexHeadlessSession
from .backends.codex_app_server import (
    CodexAppServerSession,
    codex_backend_state_payload,
)
from .backends.gemini_headless import GeminiHeadlessSession
from .backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
    headless_backend_state_payload,
)
from .backends.tmux_runtime import (
    TmuxCommandError,
    has_tmux_session as has_tmux_session_shared,
    show_tmux_environment as show_tmux_environment_shared,
    tmux_error_detail as tmux_error_detail_shared,
)
from .errors import SessionManifestError
from .launch_plan import (
    LaunchPlanRequest,
    backend_for_tool,
    build_launch_plan,
    configured_cao_parsing_mode,
    resolve_cao_parsing_mode,
)
from .loaders import load_brain_manifest, load_role_package
from .manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    generate_session_id,
    load_session_manifest,
    parse_session_manifest_payload,
    write_session_manifest,
)
from .models import (
    BackendKind,
    CaoParsingMode,
    InteractiveSession,
    LaunchPlan,
    SessionControlResult,
    SessionEvent,
)

_TMUX_BACKED_BACKENDS: frozenset[BackendKind] = frozenset(
    {"codex_headless", "claude_headless", "gemini_headless", "cao_rest"}
)


@dataclass(frozen=True)
class AgentIdentityResolution:
    """Resolved `--agent-identity` details for session-control commands.

    Parameters
    ----------
    session_manifest_path:
        Resolved session manifest path used to resume/control a runtime session.
    canonical_agent_identity:
        Canonical tmux identity when resolved from a name input.
    warnings:
        Non-fatal parsing warnings surfaced to CLI callers.
    """

    session_manifest_path: Path
    canonical_agent_identity: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass
class RuntimeSessionController:
    """Controller that binds a backend session to persisted manifest state."""

    launch_plan: LaunchPlan
    role_name: str
    brain_manifest_path: Path
    manifest_path: Path
    backend_session: InteractiveSession
    agent_identity: str | None = None
    agent_identity_warnings: tuple[str, ...] = ()
    startup_warnings: tuple[str, ...] = ()
    parsing_mode: CaoParsingMode | None = None

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Send a prompt and persist updated session state."""

        events = self.backend_session.send_prompt(prompt)
        self.persist_manifest()
        return events

    def interrupt(self) -> SessionControlResult:
        """Interrupt in-flight backend work and persist state."""

        result = self.backend_session.interrupt()
        self.persist_manifest()
        return result

    def stop(self, *, force_cleanup: bool = False) -> SessionControlResult:
        """Terminate backend resources and persist state."""

        if isinstance(self.backend_session, HeadlessInteractiveSession):
            self.backend_session.configure_stop_force_cleanup(
                force_cleanup=force_cleanup
            )
        result = self.backend_session.terminate()
        self.persist_manifest()
        return result

    def close(self) -> None:
        """Close the backend session."""

        self.backend_session.close()
        self.persist_manifest()

    def persist_manifest(self) -> None:
        """Persist current backend state to session manifest."""

        backend_state = _backend_state_for_session(self.backend_session)
        payload = build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=self.launch_plan,
                role_name=self.role_name,
                brain_manifest_path=self.brain_manifest_path,
                backend_state=backend_state,
            )
        )
        write_session_manifest(self.manifest_path, payload)


def start_runtime_session(
    *,
    agent_def_dir: Path,
    brain_manifest_path: Path,
    role_name: str,
    runtime_root: Path,
    backend: BackendKind | None = None,
    working_directory: Path | None = None,
    api_base_url: str = "http://localhost:9889",
    cao_profile_store_dir: Path | None = None,
    agent_identity: str | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
) -> RuntimeSessionController:
    """Start a new runtime session and persist its session manifest."""

    manifest = load_brain_manifest(brain_manifest_path)
    role_package = load_role_package(agent_def_dir, role_name)

    tool = str(manifest.get("inputs", {}).get("tool", ""))
    selected_backend = backend or backend_for_tool(tool)
    selected_workdir = (working_directory or Path.cwd()).resolve()

    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=selected_backend,
            working_directory=selected_workdir,
        )
    )

    session_id = generate_session_id(prefix=selected_backend)
    manifest_path = default_manifest_path(runtime_root, selected_backend, session_id)
    manifest_path = manifest_path.resolve()

    canonical_agent_identity: str | None = None
    agent_identity_warnings: tuple[str, ...] = ()
    if selected_backend in _TMUX_BACKED_BACKENDS:
        if agent_identity is not None:
            if is_path_like_agent_identity(agent_identity):
                raise SessionManifestError(
                    "start-session --agent-identity must be a name for "
                    f"backend={selected_backend}, not a manifest path."
                )
            normalized = normalize_agent_identity_name(agent_identity)
            canonical_agent_identity = normalized.canonical_name
            agent_identity_warnings = normalized.warnings
    elif agent_identity is not None:
        raise SessionManifestError(
            "start-session --agent-identity is only supported for tmux-backed "
            f"backends: {sorted(_TMUX_BACKED_BACKENDS)}."
        )

    backend_session = _create_backend_session(
        launch_plan=launch_plan,
        role_name=role_name,
        role_prompt=role_package.system_prompt,
        api_base_url=api_base_url,
        cao_profile_store_dir=cao_profile_store_dir,
        session_manifest_path=manifest_path,
        agent_identity=canonical_agent_identity,
        cao_parsing_mode=cao_parsing_mode,
    )

    resolved_agent_identity: str | None = None
    resolved_parsing_mode: CaoParsingMode | None = None
    startup_warnings: tuple[str, ...] = ()
    if isinstance(backend_session, CaoRestSession):
        resolved_agent_identity = backend_session.state.session_name
        resolved_parsing_mode = backend_session.state.parsing_mode
        startup_warnings = backend_session.startup_warnings
    elif isinstance(backend_session, HeadlessInteractiveSession):
        resolved_agent_identity = backend_session.state.tmux_session_name

    controller = RuntimeSessionController(
        launch_plan=launch_plan,
        role_name=role_name,
        brain_manifest_path=brain_manifest_path.resolve(),
        manifest_path=manifest_path,
        backend_session=backend_session,
        agent_identity=resolved_agent_identity,
        agent_identity_warnings=agent_identity_warnings,
        startup_warnings=startup_warnings,
        parsing_mode=resolved_parsing_mode,
    )
    controller.persist_manifest()
    return controller


def resolve_agent_identity(
    *, agent_identity: str, base: Path
) -> AgentIdentityResolution:
    """Resolve an `--agent-identity` into a concrete session manifest path.

    Parameters
    ----------
    agent_identity:
        Raw CLI identity value (manifest path or agent name).
    base:
        Base path used for resolving relative manifest paths.

    Returns
    -------
    AgentIdentityResolution
        Resolved manifest path and optional canonical name metadata.
    """

    if is_path_like_agent_identity(agent_identity):
        manifest_path = _resolve_manifest_path(agent_identity, base=base)
        if not manifest_path.is_file():
            raise SessionManifestError(f"Session manifest not found: {manifest_path}")
        return AgentIdentityResolution(session_manifest_path=manifest_path.resolve())

    normalized = normalize_agent_identity_name(agent_identity)
    manifest_path = _resolve_manifest_path_from_tmux_session(
        session_name=normalized.canonical_name
    )
    _validate_resolved_manifest_matches_tmux_session(
        manifest_path=manifest_path,
        session_name=normalized.canonical_name,
    )
    return AgentIdentityResolution(
        session_manifest_path=manifest_path,
        canonical_agent_identity=normalized.canonical_name,
        warnings=normalized.warnings,
    )


def resume_runtime_session(
    *,
    agent_def_dir: Path,
    session_manifest_path: Path,
    cao_profile_store_dir: Path | None = None,
) -> RuntimeSessionController:
    """Resume a runtime session from a persisted manifest."""

    handle = load_session_manifest(session_manifest_path)
    manifest_payload = parse_session_manifest_payload(
        handle.payload,
        source=str(handle.path),
    )

    backend = manifest_payload.backend
    role_name = manifest_payload.role_name
    brain_manifest_path = Path(manifest_payload.brain_manifest_path).resolve()
    manifest = load_brain_manifest(brain_manifest_path)
    role_package = load_role_package(agent_def_dir, role_name)

    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=backend,
            working_directory=Path(manifest_payload.working_directory),
        )
    )

    backend_session = _create_backend_session(
        launch_plan=launch_plan,
        role_name=role_name,
        role_prompt=role_package.system_prompt,
        cao_profile_store_dir=cao_profile_store_dir,
        resume_state=manifest_payload,
        session_manifest_path=session_manifest_path.resolve(),
    )

    resolved_agent_identity: str | None = None
    if isinstance(backend_session, CaoRestSession):
        resolved_agent_identity = backend_session.state.session_name
    elif isinstance(backend_session, HeadlessInteractiveSession):
        resolved_agent_identity = backend_session.state.tmux_session_name

    return RuntimeSessionController(
        launch_plan=launch_plan,
        role_name=role_name,
        brain_manifest_path=brain_manifest_path,
        manifest_path=session_manifest_path.resolve(),
        backend_session=backend_session,
        agent_identity=resolved_agent_identity,
        parsing_mode=(
            backend_session.state.parsing_mode
            if isinstance(backend_session, CaoRestSession)
            else None
        ),
    )


def _create_backend_session(
    *,
    launch_plan: LaunchPlan,
    role_name: str,
    role_prompt: str,
    api_base_url: str | None = None,
    cao_profile_store_dir: Path | None,
    resume_state: SessionManifestPayloadV2 | None = None,
    session_manifest_path: Path | None = None,
    agent_identity: str | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
) -> InteractiveSession:
    """Create a concrete backend session for start/resume flows."""

    if launch_plan.backend == "codex_app_server":
        if resume_state is not None:
            raise SessionManifestError(
                "Resuming codex_app_server from persisted manifest is not supported "
                "because stdio channel state is not recoverable."
            )
        return cast(InteractiveSession, CodexAppServerSession(launch_plan=launch_plan))

    if launch_plan.backend == "codex_headless":
        state = _resume_headless_state(resume_state, launch_plan=launch_plan)
        return cast(
            InteractiveSession,
            CodexHeadlessSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path,
                    backend=launch_plan.backend,
                ),
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "claude_headless":
        state = _resume_headless_state(resume_state, launch_plan=launch_plan)
        return cast(
            InteractiveSession,
            ClaudeHeadlessSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path,
                    backend=launch_plan.backend,
                ),
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "gemini_headless":
        state = _resume_headless_state(resume_state, launch_plan=launch_plan)
        if (
            state is not None
            and Path(state.working_directory).resolve() != launch_plan.working_directory
        ):
            raise SessionManifestError(
                "Gemini resume requires the same working directory as the persisted session"
            )
        return cast(
            InteractiveSession,
            GeminiHeadlessSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path,
                    backend=launch_plan.backend,
                ),
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "cao_rest":
        existing_state = _resume_cao_state(resume_state)
        configured_mode = configured_cao_parsing_mode(launch_plan)
        resolved_parsing_mode = resolve_cao_parsing_mode(
            tool=launch_plan.tool,
            requested_mode=cao_parsing_mode,
            configured_mode=configured_mode,
        )
        if existing_state is not None and existing_state.parsing_mode != resolved_parsing_mode:
            raise SessionManifestError(
                "CAO parsing mode mismatch on resume: "
                f"manifest requires {existing_state.parsing_mode!r}, "
                f"but current configuration resolves to {resolved_parsing_mode!r}."
            )
        resolved_api_base_url = (
            existing_state.api_base_url if existing_state is not None else api_base_url
        )
        if resolved_api_base_url is None or not resolved_api_base_url.strip():
            raise SessionManifestError(
                "CAO start requires a non-empty api_base_url for backend=cao_rest"
            )
        return cast(
            InteractiveSession,
            CaoRestSession(
                launch_plan=launch_plan,
                api_base_url=resolved_api_base_url.strip(),
                role_name=role_name,
                role_prompt=role_prompt,
                profile_store_dir=cao_profile_store_dir,
                existing_state=existing_state,
                session_manifest_path=session_manifest_path,
                agent_identity=agent_identity,
                parsing_mode=resolved_parsing_mode,
            ),
        )

    raise SessionManifestError(f"Unsupported backend: {launch_plan.backend}")


def _resume_headless_state(
    payload: SessionManifestPayloadV2 | None,
    *,
    launch_plan: LaunchPlan,
) -> HeadlessSessionState | None:
    if payload is None:
        return None

    headless = payload.headless
    if headless is None:
        raise SessionManifestError("Headless session manifest missing `headless` state")

    session_id = headless.session_id
    turn_index = headless.turn_index
    if (session_id is None or not session_id.strip()) and turn_index > 0:
        raise SessionManifestError(
            "Headless resume requires a non-empty headless.session_id after turn 0"
        )
    tmux_session_name = payload.backend_state.get("tmux_session_name")
    if not isinstance(tmux_session_name, str) or not tmux_session_name.strip():
        raise SessionManifestError(
            "Headless resume requires non-empty backend_state.tmux_session_name"
        )

    return HeadlessSessionState(
        session_id=session_id.strip() if session_id else None,
        turn_index=turn_index,
        role_bootstrap_applied=headless.role_bootstrap_applied,
        working_directory=headless.working_directory
        or str(launch_plan.working_directory),
        tmux_session_name=tmux_session_name.strip(),
    )


def _require_session_manifest_path(
    session_manifest_path: Path | None, *, backend: BackendKind
) -> Path:
    if session_manifest_path is None:
        raise SessionManifestError(
            f"backend={backend} requires a resolved session manifest path."
        )
    return session_manifest_path.resolve()


def _resume_cao_state(
    payload: SessionManifestPayloadV2 | None,
) -> CaoSessionState | None:
    if payload is None:
        return None

    cao = payload.cao
    if cao is None:
        raise SessionManifestError("CAO session manifest missing `cao` state")

    persisted_api_base_url = cao.api_base_url.strip()
    if not persisted_api_base_url:
        raise SessionManifestError(
            "CAO session manifest missing or blank cao.api_base_url"
        )

    terminal_id = cao.terminal_id.strip()
    if not terminal_id:
        raise SessionManifestError(
            "CAO session manifest missing or blank cao.terminal_id"
        )

    session_name = cao.session_name.strip()
    if not session_name:
        raise SessionManifestError(
            "CAO session manifest missing or blank cao.session_name"
        )

    profile_name = cao.profile_name.strip()
    if not profile_name:
        raise SessionManifestError(
            "CAO session manifest missing or blank cao.profile_name"
        )

    profile_path = cao.profile_path.strip()
    if not profile_path:
        raise SessionManifestError(
            "CAO session manifest missing or blank cao.profile_path"
        )

    parsing_mode = cao.parsing_mode

    backend_api_base_url = payload.backend_state.get("api_base_url")
    if not isinstance(backend_api_base_url, str) or not backend_api_base_url.strip():
        raise SessionManifestError(
            "CAO session manifest missing or blank backend_state.api_base_url"
        )
    if persisted_api_base_url != backend_api_base_url.strip():
        raise SessionManifestError(
            "CAO session manifest api_base_url mismatch: "
            "cao.api_base_url must equal backend_state.api_base_url"
        )
    backend_parsing_mode = payload.backend_state.get("parsing_mode")
    if not isinstance(backend_parsing_mode, str) or not backend_parsing_mode.strip():
        raise SessionManifestError(
            "CAO session manifest missing or blank backend_state.parsing_mode"
        )
    if parsing_mode != backend_parsing_mode.strip():
        raise SessionManifestError(
            "CAO session manifest parsing_mode mismatch: "
            "cao.parsing_mode must equal backend_state.parsing_mode"
        )

    return CaoSessionState(
        api_base_url=persisted_api_base_url,
        session_name=session_name,
        terminal_id=terminal_id,
        profile_name=profile_name,
        profile_path=profile_path,
        parsing_mode=parsing_mode,
        turn_index=cao.turn_index,
    )


def _backend_state_for_session(session: InteractiveSession) -> dict[str, object]:
    if isinstance(session, CodexAppServerSession):
        return codex_backend_state_payload(session.state)
    if isinstance(session, HeadlessInteractiveSession):
        return headless_backend_state_payload(session.state)
    if isinstance(session, CaoRestSession):
        return cao_backend_state_payload(session.state)
    return {}


def _resolve_manifest_path(value: str, *, base: Path) -> Path:
    """Resolve a manifest path relative to the provided base directory."""

    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _resolve_manifest_path_from_tmux_session(*, session_name: str) -> Path:
    """Resolve a session manifest path from tmux session environment state."""

    try:
        has_result = has_tmux_session_shared(session_name=session_name)
    except TmuxCommandError as exc:
        raise SessionManifestError(
            "Agent-name resolution requires `tmux` on PATH for session "
            f"`{session_name}`."
        ) from exc
    if has_result.returncode != 0:
        if has_result.returncode == 1:
            raise SessionManifestError(
                f"Agent not found: tmux session `{session_name}` does not exist. "
                "Run `tmux ls` to discover active agents or pass a manifest path."
            )
        detail = tmux_error_detail_shared(has_result)
        raise SessionManifestError(
            f"Failed to query tmux session `{session_name}`: "
            f"{detail or 'unknown tmux error'}"
        )

    try:
        env_result = show_tmux_environment_shared(
            session_name=session_name,
            variable_name=AGENT_MANIFEST_PATH_ENV_VAR,
        )
    except TmuxCommandError as exc:
        raise SessionManifestError(
            "Agent-name resolution requires `tmux` on PATH for session "
            f"`{session_name}`."
        ) from exc
    env_detail = tmux_error_detail_shared(env_result)
    if env_result.returncode != 0:
        if "unknown variable" in env_detail.lower():
            raise SessionManifestError(
                f"Manifest pointer missing: tmux session `{session_name}` has no "
                f"`{AGENT_MANIFEST_PATH_ENV_VAR}` value. "
                "Use an explicit manifest path or restart the session."
            )
        raise SessionManifestError(
            f"Failed reading `{AGENT_MANIFEST_PATH_ENV_VAR}` from tmux session "
            f"`{session_name}`: {env_detail or 'unknown tmux error'}"
        )

    line = ""
    for raw_line in env_result.stdout.splitlines():
        stripped = raw_line.strip()
        if stripped:
            line = stripped
            break

    missing_line = f"-{AGENT_MANIFEST_PATH_ENV_VAR}"
    if not line or line == missing_line:
        raise SessionManifestError(
            f"Manifest pointer missing: tmux session `{session_name}` has blank "
            f"`{AGENT_MANIFEST_PATH_ENV_VAR}`."
        )

    prefix = f"{AGENT_MANIFEST_PATH_ENV_VAR}="
    if not line.startswith(prefix):
        raise SessionManifestError(
            f"Unexpected tmux environment output for `{session_name}`: {line}"
        )

    manifest_raw = line[len(prefix) :].strip()
    if not manifest_raw:
        raise SessionManifestError(
            f"Manifest pointer missing: tmux session `{session_name}` has blank "
            f"`{AGENT_MANIFEST_PATH_ENV_VAR}`."
        )

    manifest_path = Path(manifest_raw)
    if not manifest_path.is_absolute():
        raise SessionManifestError(
            f"Invalid manifest pointer in tmux session `{session_name}`: "
            f"`{AGENT_MANIFEST_PATH_ENV_VAR}` must be an absolute path."
        )
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise SessionManifestError(
            f"Manifest pointer stale: `{AGENT_MANIFEST_PATH_ENV_VAR}` in tmux "
            f"session `{session_name}` points to missing file `{manifest_path}`."
        )
    return manifest_path


def _validate_resolved_manifest_matches_tmux_session(
    *, manifest_path: Path, session_name: str
) -> None:
    """Validate tmux-resolved manifest backend and session-name invariants."""

    handle = load_session_manifest(manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    if payload.backend not in _TMUX_BACKED_BACKENDS:
        raise SessionManifestError(
            "Resolved manifest mismatch: name-based resolution requires a tmux-backed "
            f"manifest, got backend={payload.backend!r} from `{manifest_path}`."
        )

    persisted_session_name = _persisted_tmux_session_name(
        payload=payload,
        manifest_path=manifest_path,
    )
    if persisted_session_name != session_name:
        raise SessionManifestError(
            "Resolved manifest mismatch: persisted tmux session name "
            f"({persisted_session_name!r}) does not match addressed tmux session "
            f"{session_name!r}."
        )

def _persisted_tmux_session_name(
    *, payload: SessionManifestPayloadV2, manifest_path: Path
) -> str:
    if payload.backend == "cao_rest":
        cao = payload.cao
        if cao is None:
            raise SessionManifestError(
                f"Resolved manifest mismatch: `{manifest_path}` is missing `cao` payload."
            )
        persisted = cao.session_name.strip()
        if not persisted:
            raise SessionManifestError(
                f"Resolved manifest mismatch: `{manifest_path}` has blank "
                "`payload.cao.session_name`."
            )
        return persisted

    persisted_backend = payload.backend_state.get("tmux_session_name")
    if not isinstance(persisted_backend, str) or not persisted_backend.strip():
        raise SessionManifestError(
            f"Resolved manifest mismatch: `{manifest_path}` is missing non-empty "
            "`payload.backend_state.tmux_session_name`."
        )
    return persisted_backend.strip()
