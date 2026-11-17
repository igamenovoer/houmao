"""Managed tmux-backed DSH sessions with an ACP worker for each explicit turn."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import sys
from typing import Any

from houmao.agents.dsh_configuration import DshSetup, load_dsh_home
from houmao.agents.model_mapping_policy import resolve_reasoning_mapping
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.dsh_acp_driver import _write_private_json
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    SessionControlResult,
    SessionEvent,
)


class DshAcpSession(HeadlessInteractiveSession):
    """Reuse the headless lifecycle while keeping DSH as the probed executable."""

    @property
    def native_invocation_active(self) -> bool:
        """Observe native ownership without starting or resuming a conversation."""

        try:
            try:
                stream = (self._plan.home_path / "houmao-invocation.lock").open("r+b")
            except FileNotFoundError:
                return False
            with stream:
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return True
            return False
        except OSError as exc:
            raise BackendExecutionError("DSH native invocation ownership is unavailable") from exc

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
        """Restore native identity without launching or resuming a worker."""

        self.m_turn_dir: Path | None = None
        self.m_execution_model: ModelConfig | None = None
        native = launch_plan.home_path / "houmao-native-session.json"
        if native.is_file():
            payload = json.loads(native.read_text(encoding="utf-8"))
            if payload.get("working_directory") != str(launch_plan.working_directory.resolve()):
                raise BackendExecutionError("DSH continuation requires its recorded workspace")
            if state is not None:
                state.session_id = payload["native_session_id"]
        super().__init__(
            backend="dsh_acp",
            launch_plan=launch_plan,
            role_name=role_name,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            state=state,
            tmux_session_name=tmux_session_name,
        )

    def interrupt(self) -> SessionControlResult:
        """Cancel only the exact native attempt bound to this managed generation."""

        try:
            if not self._restore_active_invocation():
                return SessionControlResult(
                    status="ok", action="interrupt", detail="No in-flight DSH attempt"
                )
        except BackendExecutionError as exc:
            return SessionControlResult(status="error", action="interrupt", detail=str(exc))
        return super().interrupt()

    def terminate(self) -> SessionControlResult:
        """Recover owned execution before bounded forced stop or envelope cleanup."""

        try:
            self._restore_active_invocation()
        except BackendExecutionError as exc:
            return SessionControlResult(status="error", action="terminate", detail=str(exc))
        return super().terminate()

    def _restore_active_invocation(self) -> bool:
        """Restore control from an exact private binding, never directory recency."""

        self._runner.m_active_provider = "dsh"
        if not self.native_invocation_active:
            try:
                candidate = json.loads(
                    (self._plan.home_path / "houmao-native-session.json").read_text(
                        encoding="utf-8"
                    )
                )
                pid = candidate.get("process_id") if isinstance(candidate, dict) else None
                birth = (
                    candidate.get("process_birth_token") if isinstance(candidate, dict) else None
                )
                if (
                    type(pid) is not int
                    or pid <= 0
                    or not isinstance(birth, str)
                    or not birth
                    or _dispatch_origin_birth_token(pid) != birth
                ):
                    return False
                # A surviving native worker remains owned execution even if
                # its controller died and released the invocation lock.
            except (OSError, ValueError, TypeError):
                return False
        try:
            binding = json.loads(
                (self._plan.home_path / "houmao-native-session.json").read_text(encoding="utf-8")
            )
            manifest = json.loads(self._session_manifest_path.read_text(encoding="utf-8"))
            if not isinstance(binding, dict) or not isinstance(manifest, dict):
                raise ValueError("Invalid native authority")
            runtime = manifest.get("runtime")
            workspace = str(self._plan.working_directory.resolve())
            if (
                manifest.get("tool") != "dsh"
                or manifest.get("backend") != "dsh_acp"
                or manifest.get("working_directory") != workspace
                or not isinstance(runtime, dict)
                or not isinstance(manifest.get("registry_generation_id"), str)
                or not manifest["registry_generation_id"]
                or binding.get("version") != 1
                or binding.get("working_directory") != workspace
                or binding.get("runtime_session_id") != runtime.get("session_id")
                or not binding.get("runtime_session_id")
                or binding.get("generation") != manifest["registry_generation_id"]
            ):
                raise ValueError("Mismatched native authority")
            attempt = binding.get("attempt_id")
            native_id = binding.get("native_session_id")
            if (
                not isinstance(attempt, str)
                or not attempt
                or Path(attempt).name != attempt
                or attempt in {".", ".."}
                or not isinstance(native_id, str)
                or not native_id
            ):
                raise ValueError("Invalid native attempt identity")
            root = self._turn_artifacts_root.resolve()
            turn_dir = (root / attempt).resolve()
            if turn_dir.parent != root or binding.get("evidence_path") != str(
                turn_dir / "dsh-native-evidence.jsonl"
            ):
                raise ValueError("Native attempt is outside its managed artifact root")
            recorded = json.loads(
                (turn_dir / "dsh-native-binding.json").read_text(encoding="utf-8")
            )
            if recorded != binding or (turn_dir / "exitcode").exists():
                raise ValueError("Native attempt is not the active bound execution")
            native_pid = binding.get("process_id")
            native_birth = binding.get("process_birth_token")
            if (
                type(native_pid) is not int
                or native_pid <= 0
                or not isinstance(native_birth, str)
                or not native_birth
                or _dispatch_origin_birth_token(native_pid) != native_birth
                or os.getpgid(native_pid) != native_pid
            ):
                raise ValueError("Native worker birth identity changed")
            self._runner.restore_dsh_attempt(
                turn_dir=turn_dir, tmux_session_name=self._state.tmux_session_name
            )
            self._state.session_id = native_id
            saved_state = manifest.get("backend_state")
            saved_index = saved_state.get("turn_index") if isinstance(saved_state, dict) else None
            if type(saved_index) is int and saved_index >= 0:
                self._state.turn_index = max(self._state.turn_index, saved_index)
            return True
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            raise BackendExecutionError(
                "DSH active attempt identity is unavailable or mismatched"
            ) from exc

    def _execute_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Prepare a private invocation and retain identity even after worker loss."""

        self.m_turn_dir = self._turn_artifacts_root / turn_artifact_dir_name
        self.m_execution_model = execution_model
        projection_model = execution_model
        if (
            execution_model is not None
            and execution_model.name is None
            and execution_model.reasoning is not None
        ):
            setup = self._plan.metadata.get("dsh")
            if not isinstance(setup, dict) or not isinstance(setup.get("setup_path"), str):
                raise BackendExecutionError("DSH setup projection is unavailable")
            current = load_dsh_home(
                self._plan.home_path,
                DshSetup.from_file(Path(setup["setup_path"])),
                self._plan.env,
            )
            projection_model = ModelConfig(
                name=current.model[1], reasoning=execution_model.reasoning
            )
        try:
            return super()._execute_prompt(
                prompt,
                turn_artifact_dir_name=turn_artifact_dir_name,
                session_selection=session_selection,
                execution_model=projection_model,
            )
        finally:
            binding_path = self.m_turn_dir / "dsh-native-binding.json"
            if binding_path.is_file():
                binding = json.loads(binding_path.read_text(encoding="utf-8"))
                if binding.get("attempt_id") == turn_artifact_dir_name:
                    self._state.session_id = binding["native_session_id"]

    def _build_command(
        self,
        *,
        prompt: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
        extra_args: list[str] | None = None,
    ) -> tuple[list[str], str]:
        """Select only new or exact continuation and pass no prompt bytes in argv."""

        if self.m_turn_dir is None:
            raise BackendExecutionError("DSH invocation has no managed artifact directory")
        if extra_args:
            raise BackendExecutionError("DSH model controls require native configuration")
        if session_selection is not None and session_selection.mode == "tool_last_or_new":
            raise BackendExecutionError(
                "DSH latest-session selection is unsupported; use exact or new"
            )
        session_id = self._state.session_id
        if session_selection is not None:
            session_id = session_selection.session_id if session_selection.mode == "exact" else None
        manifest = json.loads(self._session_manifest_path.read_text(encoding="utf-8"))
        generation = manifest.get("registry_generation_id")
        runtime_session_id = manifest.get("runtime", {}).get("session_id")
        if (
            not isinstance(generation, str)
            or not generation
            or not isinstance(runtime_session_id, str)
            or not runtime_session_id
        ):
            raise BackendExecutionError("DSH requires a persisted managed execution identity")
        setup = self._plan.metadata.get("dsh")
        if not isinstance(setup, dict) or not isinstance(setup.get("setup_path"), str):
            raise BackendExecutionError("DSH setup projection is unavailable")
        model = self.m_execution_model
        reasoning_key = None
        if model is not None and model.reasoning is not None:
            model_name = model.name
            if model_name is None:
                current = load_dsh_home(
                    self._plan.home_path,
                    DshSetup.from_file(Path(setup["setup_path"])),
                    self._plan.env,
                )
                model_name = current.model[1]
            mapping = resolve_reasoning_mapping(
                tool="dsh",
                requested_level=model.reasoning.level,
                model_name=model_name,
                home_path=self._plan.home_path,
            )
            reasoning_key = mapping.get("profile_key")
        self.m_turn_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        private: dict[str, Any] = {
            "executable": self._plan.executable,
            "working_directory": str(self._plan.working_directory),
            "home_path": str(self._plan.home_path),
            "setup_path": setup["setup_path"],
            "prompt": prompt,
            "session_id": session_id,
            "attempt_id": self.m_turn_dir.name,
            "runtime_session_id": runtime_session_id,
            "generation": generation,
            "turn_dir": str(self.m_turn_dir),
            "model": model.name if model is not None else None,
            "reasoning_level": (
                reasoning_key if model is not None and model.reasoning is not None else None
            ),
        }
        input_path = self.m_turn_dir / "dsh-driver-input.json"
        _write_private_json(input_path, private)
        return [
            sys.executable,
            "-m",
            "houmao.agents.realm_controller.backends.dsh_acp_entry",
            "--input",
            str(input_path),
        ], prompt
