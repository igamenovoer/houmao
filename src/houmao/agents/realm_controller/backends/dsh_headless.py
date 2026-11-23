"""Managed DSH headless envelopes that own one native CLI worker per turn."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from houmao.agents.dsh_configuration import DshEffectiveToolParams, load_dsh_home
from houmao.agents.model_mapping_policy import resolve_reasoning_mapping
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dispatch_control import (
    HeadlessDispatchControl,
    _dispatch_origin_birth_token,
)
from houmao.agents.realm_controller.backends.dsh_acp_driver import _write_private_json
from houmao.agents.realm_controller.backends.dsh_diagnostics import (
    dsh_diagnostic_secrets,
    sanitize_dsh_diagnostic,
)
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    interrupt_owned_headless_attempt,
    load_headless_process_metadata,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    SessionControlResult,
    SessionEvent,
)
from houmao.agents.realm_controller.owner_admission import reserve_owner_prompt


class DshHeadlessSession(HeadlessInteractiveSession):
    """Resume exact private DSH identity and leave native adoption to the CLI."""

    def __init__(
        self,
        *,
        launch_plan: LaunchPlan,
        role_name: str,
        session_manifest_path: Path,
        agent_def_dir: Path | None = None,
        state: HeadlessSessionState | None = None,
        tmux_session_name: str | None = None,
    ) -> None:
        """Build or reconstruct just the managed envelope."""

        self.m_turn_dir: Path | None = None
        self.m_invocation_model: ModelConfig | None = None
        super().__init__(
            backend="dsh_headless",
            launch_plan=launch_plan,
            role_name=role_name,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            state=state,
            tmux_session_name=tmux_session_name,
            output_format="dsh-cli",
        )
        if session_manifest_path.is_file():
            self._read_native_session()

    @property
    def native_invocation_active(self) -> bool:
        """Observe the captured native process without starting a worker."""

        return self._active_native_attempt() is not None

    def interrupt(self) -> SessionControlResult:
        """Interrupt only the exact captured attempt under the current generation."""

        try:
            attempt = self._active_native_attempt()
            if attempt is not None:
                return interrupt_owned_headless_attempt(attempt)
        except (OSError, ValueError, BackendExecutionError):
            return SessionControlResult(
                status="error", action="interrupt", detail="DSH worker identity is unavailable"
            )
        return SessionControlResult(status="ok", action="interrupt", detail="No active DSH worker")

    def terminate(self) -> SessionControlResult:
        """Settle the captured worker before cleaning up this managed envelope."""

        attempt = self._active_native_attempt()
        if attempt is not None:
            result = interrupt_owned_headless_attempt(attempt)
            if result.status != "ok":
                return SessionControlResult(
                    status="error", action="terminate", detail=result.detail
                )
        return super().terminate()

    def _manifest_identity(self) -> tuple[str, str]:
        """Read the runtime identity used to bind per-attempt native files."""

        try:
            payload = json.loads(self._session_manifest_path.read_text(encoding="utf-8"))
            generation = payload["registry_generation_id"]
            runtime_id = payload["runtime"]["session_id"]
            if (
                payload.get("backend") != "dsh_headless"
                or payload.get("working_directory") != str(self._plan.working_directory.resolve())
                or not isinstance(generation, str)
                or not isinstance(runtime_id, str)
                or not generation
                or not runtime_id
            ):
                raise ValueError("invalid generation")
        except (KeyError, OSError, TypeError, ValueError):
            raise BackendExecutionError(
                "DSH headless requires a current managed generation"
            ) from None
        return runtime_id, generation

    def _read_native_session(self) -> None:
        """Restore only a previously admitted native ID for this exact runtime body."""

        try:
            source = self._plan.home_path / "houmao-native-session.json"
            native = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            raise BackendExecutionError("DSH native continuation identity is unavailable") from None
        if not isinstance(native, dict):
            raise BackendExecutionError("DSH native continuation identity is invalid")
        runtime_id, generation = self._manifest_identity()
        if native.get("runtime_session_id") != runtime_id or native.get("generation") != generation:
            return
        if native.get("working_directory") != str(self._plan.working_directory.resolve()):
            raise BackendExecutionError("DSH continuation requires its recorded workspace")
        native_id = native.get("native_session_id")
        if not isinstance(native_id, str) or not native_id:
            raise BackendExecutionError("DSH native continuation identity is unavailable")
        self._state.session_id = native_id

    def _active_native_attempt(self) -> Path | None:
        """Pin the home marker to an active bridge child in this runtime generation."""

        try:
            source = self._plan.home_path / "houmao-native-attempt.json"
            native = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        if not isinstance(native, dict):
            raise BackendExecutionError("DSH native attempt identity is invalid")
        pid = native.get("process_id")
        birth = native.get("process_birth_token")
        if type(pid) is not int or not isinstance(birth, str):
            raise BackendExecutionError("DSH native attempt identity is invalid")
        if _dispatch_origin_birth_token(pid) != birth:
            return None
        runtime_id, generation = self._manifest_identity()
        attempt = native.get("attempt_id")
        if (
            not isinstance(attempt, str)
            or Path(attempt).name != attempt
            or attempt in {"", ".", ".."}
            or native.get("generation") != generation
            or native.get("runtime_session_id") != runtime_id
            or native.get("working_directory") != str(self._plan.working_directory.resolve())
        ):
            raise BackendExecutionError("DSH worker belongs to a different runtime attempt")
        turn_dir = self._turn_artifacts_root / attempt
        if (turn_dir / "exitcode").is_file():
            return None
        metadata = load_headless_process_metadata(process_path=turn_dir / "process.json")
        if (
            metadata.child_pid != pid
            or metadata.child_birth_token != birth
            or os.getsid(pid) != pid
        ):
            raise BackendExecutionError("DSH worker does not match its bridge process identity")
        return turn_dir

    def _execute_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Prepare one invocation and use the caller's existing managed reservation."""

        self.m_turn_dir = self._turn_artifacts_root / turn_artifact_dir_name
        self.m_invocation_model = execution_model
        self._read_native_session()
        claim = None
        if self.m_dispatch_control is None:
            _, generation = self._manifest_identity()
            claim = reserve_owner_prompt(
                self._session_manifest_path,
                generation,
                request_id=turn_artifact_dir_name,
                origin="runtime",
            )
            self.configure_request_dispatch(
                HeadlessDispatchControl.from_callbacks(
                    allowed=claim.active,
                    confirmed=claim.handoff,
                    deadline=time.monotonic() + 300,
                    manifest_path=self._session_manifest_path,
                    generation_id=generation,
                )
            )
        try:
            events = super()._execute_prompt(
                prompt,
                turn_artifact_dir_name=turn_artifact_dir_name,
                session_selection=session_selection,
            )
            if claim is not None:
                claim.finish("completed", evidence="headless_artifacts")
            return events
        except BaseException as exc:
            result = self.m_last_run_result
            if (
                isinstance(exc, BackendExecutionError)
                and result is not None
                and result.returncode == 130
            ):
                # The bridge publishes this code only after observing the owned process exit.
                self._state.turn_index += 1
                if claim is not None:
                    claim.finish("interrupted", evidence="owner_process")
                return [
                    *result.events,
                    SessionEvent(
                        kind="done",
                        message="Owned DSH worker interrupted",
                        turn_index=self._state.turn_index,
                        payload={
                            "turn_id": turn_artifact_dir_name,
                            "outcome": "interrupted",
                            "interruption_source": "owner_process",
                        },
                    ),
                ]
            if claim is not None:
                claim.finish(
                    "uncertain"
                    if (self.m_turn_dir / "dsh-native-handoff.json").is_file()
                    else "failed"
                )
            if isinstance(exc, BackendExecutionError):
                setup = self._plan.metadata.get("dsh")
                key = setup.get("api_key_env") if isinstance(setup, dict) else None
                secrets = dsh_diagnostic_secrets(
                    self._plan.env, key_name=key if isinstance(key, str) else None
                )
                detail = sanitize_dsh_diagnostic(str(exc), secret_values=secrets, max_length=640)
                raise type(exc)(detail) from None
            raise
        finally:
            self._read_native_session()
            if claim is not None:
                self.configure_request_dispatch(None)

    def _build_command(
        self,
        *,
        prompt: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
        extra_args: list[str] | None = None,
    ) -> tuple[list[str], str]:
        """Pass prompt only through private input and preserve exact continuation."""

        if self.m_turn_dir is None or extra_args:
            raise BackendExecutionError(
                "DSH invocation requires a private attempt and native model options"
            )
        if session_selection is not None and session_selection.mode == "tool_last_or_new":
            raise BackendExecutionError(
                "DSH latest-session selection is unsupported; use exact or new"
            )
        session_id = self._state.session_id
        if session_selection is not None:
            session_id = session_selection.session_id if session_selection.mode == "exact" else None
        runtime_id, generation = self._manifest_identity()
        setup = self._plan.metadata.get("dsh")
        if not isinstance(setup, dict) or not isinstance(setup.get("setup_path"), str):
            raise BackendExecutionError("DSH native setup is unavailable")
        model = self.m_invocation_model
        reasoning = None
        if model is not None and model.reasoning is not None:
            name = model.name
            if name is None:
                params = DshEffectiveToolParams.from_file(Path(setup["setup_path"]))
                name = load_dsh_home(
                    self._plan.home_path, params, self._plan.env, native_profile="headless"
                ).model[1]
            reasoning = resolve_reasoning_mapping(
                tool="dsh",
                requested_level=model.reasoning.level,
                model_name=name,
                home_path=self._plan.home_path,
            ).get("profile_key")
        private: dict[str, Any] = {
            "executable": self._plan.executable,
            "working_directory": str(self._plan.working_directory.resolve()),
            "home_path": str(self._plan.home_path),
            "setup_path": setup["setup_path"],
            "credential_env_source": self._plan.metadata.get("env_source_file"),
            "public_environment_names": sorted(self._plan.public_env or {}),
            "prompt": prompt,
            "session_id": session_id,
            "runtime_session_id": runtime_id,
            "generation": generation,
            "manifest_path": str(self._session_manifest_path),
            "model": model.name if model is not None else None,
            "reasoning_level": reasoning,
        }
        self.m_turn_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        input_path = self.m_turn_dir / "dsh-driver-input.json"
        _write_private_json(input_path, private)
        return [
            sys.executable,
            "-m",
            "houmao.agents.realm_controller.backends.dsh_headless_entry",
            "--input",
            str(input_path),
        ], prompt
