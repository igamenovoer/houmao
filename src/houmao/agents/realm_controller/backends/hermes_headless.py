"""Run a finite Hermes viewer while tracking its independent native execution."""

from __future__ import annotations

from contextlib import suppress
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.hermes_headless_protocol import (
    HERMES_HEADLESS_INPUT,
    HERMES_HEADLESS_REQUEST,
    reconcile_hermes_headless_turn,
)
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDaemon,
    hermes_daemon_environment,
)
from houmao.agents.realm_controller.backends.service_runtime import write_service_record
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    HeadlessTurnSettlementUnknown,
    SessionManifestError,
)
from houmao.agents.realm_controller.startup_rollback import (
    current_runtime_startup,
    stop_owned_startup_child,
)
from houmao.agents.realm_controller.manifest import commit_hermes_headless_completion
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RelaunchChatSessionSelection,
    SessionControlResult,
    SessionEvent,
)
from houmao.agents.realm_controller.owner_admission import reserve_owner_prompt
from houmao.execution.context import execution_is_read_only


class HermesHeadlessSession(HeadlessInteractiveSession):
    """Preserve the managed conversation across finite native client processes."""

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
        """Create the managed surface or reconstruct its saved binding."""

        self.m_daemon: HermesDaemon = HermesDaemon.from_launch_plan(
            launch_plan, session_manifest_path.parent / "hermes-native"
        )
        fresh = state is None and not execution_is_read_only()
        if fresh:
            self.m_daemon.ensure()
        try:
            super().__init__(
                backend="hermes_headless",
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=session_manifest_path,
                agent_def_dir=agent_def_dir,
                state=state,
                tmux_session_name=tmux_session_name,
                output_format="stream-json",
            )
        except BaseException:
            if fresh and current_runtime_startup() is None and self.m_daemon.m_child is not None:
                with suppress(OSError, subprocess.TimeoutExpired):
                    stop_owned_startup_child(self.m_daemon.m_child)
            raise

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Run one protected finite client and retain an unresolved native turn."""

        if not prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")
        if execution_model is not None and not execution_model.is_empty():
            raise BackendExecutionError("Hermes headless uses the launch-selected model")
        if set(self._plan.env_var_names).difference(self._plan.env):
            raise BackendExecutionError(
                "Hermes launch environment is incomplete. Relaunch the agent."
            )
        turn_id = turn_artifact_dir_name or f"turn-{uuid.uuid4().hex[:12]}"
        if not turn_id or Path(turn_id).name != turn_id or turn_id in {".", ".."}:
            raise BackendExecutionError("Headless turn ID must be one directory name")
        turn_dir = self._turn_artifacts_root / turn_id
        generation, runtime_id = self._manifest_identity()
        claim = None
        if self.m_dispatch_control is None:
            claim = reserve_owner_prompt(
                self._session_manifest_path, generation, request_id=turn_id, origin="runtime"
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
        entered_runner = False
        committed = False
        staged = False
        staged_path = turn_dir / HERMES_HEADLESS_INPUT
        self.m_last_run_result = None
        try:
            if self._manifest_identity() != (generation, runtime_id):
                raise BackendExecutionError("Hermes headless generation changed before dispatch")
            logical = self._prepare_conversation(
                session_selection,
                request_id=hashlib.sha256(f"{runtime_id}:{turn_id}".encode()).hexdigest(),
            )
            turn_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            index = self._state.turn_index + 1
            self._stage_request(
                prompt, turn_dir=turn_dir, turn_index=index, logical=logical, generation=generation
            )
            staged = True
            session_name = self._require_tmux_session_name()
            pane = self._primary_tmux_pane_target()
            entered_runner = True
            result = self._runner.run(
                command=[
                    self._plan.executable,
                    "chat",
                    "--oneshot",
                    "--query-file",
                    "-",
                    "--format",
                    "stream-json",
                    "--resume",
                    logical,
                ],
                env=hermes_daemon_environment(self._plan.home_path, self._plan.env),
                cwd=self._plan.working_directory,
                turn_index=index,
                output_format="stream-json",
                provider="hermes",
                display_style=self._display_style,
                display_detail=self._display_detail,
                tmux_session_name=session_name,
                tmux_pane_target=pane,
                turn_artifacts_root=self._turn_artifacts_root,
                turn_artifact_dir_name=turn_id,
                replace_environment=True,
            )
            self.m_last_run_result = result
            settled = reconcile_hermes_headless_turn(turn_dir, generation_id=generation)
            if settled.status == "failed":
                raise BackendExecutionError(result.stderr)
            if settled.status != "completed" or settled.session_id != logical:
                raise HeadlessTurnSettlementUnknown(
                    "Hermes client exit left native work unresolved"
                )
            try:
                committed = commit_hermes_headless_completion(
                    self._session_manifest_path,
                    generation_id=generation,
                    session_id=logical,
                    turn_index=index,
                )
            except (OSError, SessionManifestError):
                committed = False
            if not committed:
                raise HeadlessTurnSettlementUnknown(
                    "Hermes native work completed before its continuation could be saved"
                )
            self._state.session_id = logical
            self._state.turn_index = index
            self._state.resume_selection_kind = "none"
            self._state.resume_selection_value = None
            self._publish_tmux_session_environment()
            if claim is not None:
                claim.finish("completed", evidence="headless_artifacts")
            return [
                *result.events,
                SessionEvent(
                    "done",
                    "turn completed",
                    index,
                    {
                        "turn_id": turn_id,
                        "session_id": logical,
                        "tmux_session_name": session_name,
                        "stdout_path": str(result.stdout_path),
                        "stderr_path": str(result.stderr_path),
                        "canonical_path": str(result.canonical_path),
                        "completion_source": settled.completion_source,
                    },
                ),
            ]
        except BaseException as exc:
            settlement = reconcile_hermes_headless_turn(turn_dir, generation_id=generation)
            if entered_runner and (
                settlement.status == "uncertain"
                or (settlement.status == "completed" and not committed)
            ):
                if claim is not None:
                    claim.finish("uncertain")
                if isinstance(exc, BackendExecutionError):
                    raise HeadlessTurnSettlementUnknown(
                        "Hermes could not attribute a terminal outcome to this native request"
                    ) from None
            elif claim is not None:
                claim.finish("completed" if settlement.status == "completed" else "failed")
            raise
        finally:
            if staged:
                staged_path.unlink(missing_ok=True)
            if claim is not None:
                self.configure_request_dispatch(None)

    def interrupt(self) -> SessionControlResult:
        """Require an exact native admission before interrupting any work."""

        # Stock Hermes JSONL omits the native admission ID, so client
        # process identity alone cannot authorize native cancellation.
        return SessionControlResult(
            "error", "interrupt", "Hermes headless requires an attributable native admission"
        )

    def terminate(self) -> SessionControlResult:
        """Stop the verified daemon and the selected managed terminal surface."""

        try:
            self.m_daemon.stop()
        except (BackendExecutionError, OSError) as exc:
            return SessionControlResult("error", "terminate", str(exc))
        return super().terminate()

    def relaunch(
        self, *, chat_session: RelaunchChatSessionSelection | None = None
    ) -> SessionControlResult:
        """Validate a selected continuation before altering the managed surface."""

        try:
            if chat_session is not None and chat_session.mode == "tool_last_or_new":
                raise BackendExecutionError(
                    "Hermes headless native latest selection is unsupported"
                )
            self.m_daemon.ensure()
            if chat_session is not None and chat_session.session_id is not None:
                self.m_daemon.resolve_session(chat_session.session_id)
        except (BackendExecutionError, OSError) as exc:
            return SessionControlResult("error", "relaunch", str(exc))
        return super().relaunch(chat_session=chat_session)

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        """Refresh at the same lifecycle seam as other headless providers."""

        super().update_launch_plan(launch_plan)
        self.m_daemon = HermesDaemon.from_launch_plan(
            launch_plan, self._session_manifest_path.parent / "hermes-native"
        )

    def _prepare_conversation(
        self, selection: HeadlessTurnSessionSelection | None, *, request_id: str
    ) -> str:
        """Choose a full native ID and ensure the selected conversation is idle."""

        mode = selection.mode if selection is not None else "auto"
        if mode == "tool_last_or_new" or self._state.resume_selection_kind == "last":
            raise BackendExecutionError("Hermes headless native latest selection is unsupported")
        selected = self._state.session_id or self._state.resume_selection_value
        if mode == "new":
            selected = None
        elif mode == "exact":
            selected = selection.session_id if selection is not None else None
        if mode in {"exact", "current"} and not selected:
            raise BackendExecutionError("Hermes headless requires a verified native conversation")
        if selected == "latest":
            raise BackendExecutionError("Hermes headless requires a full native session ID")
        self.m_daemon.ensure()
        snapshot = (
            self.m_daemon.resolve_session(selected)
            if selected
            else self.m_daemon.create_session(source="oneshot", request_id=request_id)
        )
        if not snapshot.ready:
            raise BackendExecutionError("Hermes native conversation is busy or unresolved")
        return snapshot.session_id

    def _manifest_identity(self) -> tuple[str, str]:
        """Read the current owner and any cursor recovered from earlier native output."""

        try:
            payload = json.loads(self._session_manifest_path.read_text(encoding="utf-8"))
            generation = payload["registry_generation_id"]
            runtime_id = payload["runtime"]["session_id"]
            cursor = payload["headless"]
            if (
                payload.get("backend") != "hermes_headless"
                or payload.get("working_directory") != str(self._plan.working_directory.resolve())
                or not isinstance(generation, str)
                or not generation
                or not isinstance(runtime_id, str)
                or not runtime_id
                or not isinstance(cursor, dict)
                or type(cursor.get("turn_index")) is not int
            ):
                raise ValueError("Hermes generation mismatch")
        except (KeyError, OSError, TypeError, ValueError) as exc:
            raise BackendExecutionError(
                "Hermes headless requires a current managed generation"
            ) from exc
        if cursor["turn_index"] > self._state.turn_index:
            self._state.turn_index = cursor["turn_index"]
            self._state.session_id = cursor["session_id"]
            self._state.resume_selection_kind = cursor["resume_selection_kind"]
            self._state.resume_selection_value = cursor["resume_selection_value"]
        return generation, runtime_id

    def _stage_request(
        self, prompt: str, *, turn_dir: Path, turn_index: int, logical: str, generation: str
    ) -> None:
        """Write literal input and the non-secret evidence the bridge validates."""

        if (turn_dir / HERMES_HEADLESS_REQUEST).exists():
            raise BackendExecutionError("Hermes headless turn ID is already in use")
        path = turn_dir / HERMES_HEADLESS_INPUT
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                stream.write(prompt)
            write_service_record(
                turn_dir / HERMES_HEADLESS_REQUEST,
                {
                    "turn_id": turn_dir.name,
                    "turn_index": turn_index,
                    "session_id": logical,
                    "generation_id": generation,
                },
            )
        except BaseException:
            path.unlink(missing_ok=True)
            raise
