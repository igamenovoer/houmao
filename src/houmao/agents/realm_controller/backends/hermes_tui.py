"""Control a managed Hermes conversation while Ink supplies the terminal view."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shlex
import time
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from houmao.agents.hermes_configuration import hermes_unattended_launch
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesClient,
    HermesDaemon,
    HermesDaemonIdentity,
    HermesDeadlineExpired,
    HermesNativeError,
    HermesRpcRefused,
    HermesSessionSnapshot,
    read_hermes_evidence,
    write_hermes_evidence,
)
from houmao.agents.realm_controller.backends.hermes_tui_receipts import (
    HERMES_TUI_ADMISSION_FILE,
    HermesTuiAdmission as HermesTuiAdmission,
    normalize_hermes_tui_receipt,
    read_hermes_tui_admission,
)
from houmao.agents.realm_controller.backends.private_provider_exec import (
    prepare_private_provider_command,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    create_tmux_session,
    detached_tool_environment,
    generate_tmux_session_name,
    kill_tmux_session,
    list_tmux_panes,
    prepare_headless_agent_window,
    publish_tmux_launch_environment,
    tmux_session_exists,
)
from houmao.agents.realm_controller.errors import BackendExecutionError, SessionManifestError
from houmao.agents.realm_controller.hermes_self import (
    hermes_tui_native_root,
    publish_verified_hermes_daemon_for_generation,
)
from houmao.agents.realm_controller.startup_rollback import current_runtime_startup
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.manifest import load_session_manifest
from houmao.agents.realm_controller.models import (
    BackendKind,
    LaunchPlan,
    RelaunchChatSessionSelection,
    SessionControlResult,
    SessionEvent,
)
from houmao.agents.realm_controller.owner_admission import (
    OwnerAdmissionError,
    OwnerPromptAttempt,
    OwnerPromptClaim,
    observe_owner_prompt,
    reserve_owner_prompt,
)
from houmao.execution.context import current_execution_deadline, execution_deadline_scope
from houmao.execution.tmux import (
    TmuxPaneRecord,
    capture_tmux_socket_path,
    tmux_command,
    tmux_server_scope,
)

_MAX_HINT_BYTES = 8192
_MAX_EVENTS = 512
_TURN_TIMEOUT = 600.0
_SESSION_ID = re.compile(r"[A-Za-z0-9_.:-]{1,256}")
HermesTerminalAttachment = Literal["attached", "detached", "unverified", "other_session"]


class HermesInputConflict(HermesNativeError):
    """Protect an existing native binding from a second submit for the same request."""


class HermesAdmissionUncertain(HermesNativeError):
    """Retain the original owner claim when native admission cannot be confirmed."""


class HermesTuiSessionState(BaseModel):
    """Persist the independent terminal and managed native conversation addresses."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    session_name: str
    pane_id: str
    window_id: str
    tmux_session_id: str
    tmux_socket_path: str
    pane_pid: int | None = None
    pane_birth_token: str | None = None
    hint_directory: str
    native_session_id: str
    home: str
    working_directory: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> HermesTuiSessionState:
        """Restore the recorded terminal and native binding."""

        return cls.model_validate(payload)

    def to_payload(self) -> dict[str, Any]:
        """Return the backend state's durable, credential-free representation."""

        return self.model_dump(mode="json")

    @property
    def tmux_session_name(self) -> str:
        """Return the recorded handoff session name."""

        return self.session_name

    @property
    def tmux_pane_id(self) -> str:
        """Return the pane reserved for the stock Hermes TUI."""

        return self.pane_id

    @property
    def tmux_window_id(self) -> str:
        """Return the recorded terminal window ID."""

        return self.window_id


class HermesTuiSession:
    """Control the recorded Hermes session through authenticated native RPC."""

    backend: BackendKind = "hermes_tui"

    def __init__(self) -> None:
        """Initialize empty owner state before launch or reconstruction."""

        self.m_plan: LaunchPlan | None = None
        self.m_manifest_path: Path | None = None
        self.m_state: HermesTuiSessionState | None = None
        self.m_daemon: HermesDaemon | None = None
        self.m_binding_changed_callback: Callable[[], None] | None = None

    @classmethod
    def from_launch_plan(
        cls,
        launch_plan: LaunchPlan,
        *,
        session_manifest_path: Path,
        state: HermesTuiSessionState | None = None,
        provider_start: bool = False,
        tmux_session_name: str | None = None,
    ) -> HermesTuiSession:
        """Start a native conversation and Ink or reconstruct their saved addresses."""

        instance = cls()
        instance.m_plan = launch_plan
        instance.m_manifest_path = session_manifest_path.resolve()
        instance.m_state = state
        if state is not None:
            instance._verify_launch_binding(launch_plan)
        instance.m_daemon = HermesDaemon.from_launch_plan(launch_plan, instance._native_root())
        if provider_start:
            instance._start_view(tmux_session_name)
        elif state is None:
            raise HermesNativeError("Hermes TUI reconstruction requires a saved native binding.")
        return instance

    @property
    def state(self) -> HermesTuiSessionState:
        """Return the saved conversation and terminal address."""

        if self.m_state is None:
            raise HermesNativeError("The managed Hermes TUI has no native binding.")
        return self.m_state

    @property
    def plan(self) -> LaunchPlan:
        """Return the private launch configuration."""

        if self.m_plan is None:
            raise HermesNativeError("Hermes launch configuration is unavailable.")
        return self.m_plan

    @property
    def manifest_path(self) -> Path:
        """Return the owning runtime manifest path."""

        if self.m_manifest_path is None:
            raise HermesNativeError("Hermes runtime authority is unavailable.")
        return self.m_manifest_path

    @property
    def daemon(self) -> HermesDaemon:
        """Return the native owner for the recorded managed home."""

        if self.m_daemon is None:
            raise HermesNativeError("Hermes daemon configuration is unavailable.")
        return self.m_daemon

    def _native_root(self) -> Path:
        """Return the private runtime directory for Hermes native control."""

        return hermes_tui_native_root(self.manifest_path)

    def _verify_launch_binding(self, plan: LaunchPlan) -> None:
        """Reject changes that would retarget an existing native conversation."""

        if plan.home_path.resolve() != Path(
            self.state.home
        ) or plan.working_directory.resolve() != Path(self.state.working_directory):
            raise HermesNativeError("Hermes TUI requires its recorded home and workspace.")

    def _unattended(self) -> bool:
        """Check whether launch should skip native bootstrap prompts."""

        return hermes_unattended_launch(self.plan.metadata)

    def set_binding_changed_callback(self, callback: Callable[[], None]) -> None:
        """Set the controller hook that persists a changed native binding."""

        self.m_binding_changed_callback = callback

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        """Refresh scoped launch inputs without changing the saved target."""

        self._verify_launch_binding(launch_plan)
        self.m_plan = launch_plan
        self.m_daemon = HermesDaemon.from_launch_plan(launch_plan, self._native_root())

    def _start_view(self, name: str | None, *, native_session_id: str | None = None) -> None:
        """Verify the native destination before starting the Ink process."""

        identity = self.daemon.ensure(unattended=self._unattended())
        try:
            self._open_view(name, native_session_id, identity)
        except BaseException:
            if self.daemon.shared and current_runtime_startup() is None:
                self.daemon.stop(expected=identity)
            raise

    def _open_view(
        self,
        name: str | None,
        native_session_id: str | None,
        identity: HermesDaemonIdentity,
    ) -> None:
        """Launch and attest one Ink client on the selected conversation."""

        launch_id = uuid4().hex
        if native_session_id is None:
            snapshot = self.daemon.create_session(source="tui", request_id=launch_id)
        else:
            snapshot = self.daemon.resolve_session(native_session_id)
        session_name = name or generate_tmux_session_name(
            tool="hermes", role_name=self.plan.role_injection.role_name
        )
        launch_root = self._native_root() / "ink" / launch_id
        launch_root.mkdir(mode=0o700, parents=True)
        hint_directory = launch_root / "tmp"
        hint_directory.mkdir(mode=0o700)
        binding = self.plan.execution_binding
        socket_path = (
            binding.tmux_socket if binding is not None else None
        ) or capture_tmux_socket_path()
        with tmux_server_scope(socket_path):
            if tmux_session_exists(session_name=session_name, allow_missing_server=True):
                raise HermesNativeError("Hermes TUI refuses an existing terminal session name.")
            created: TmuxPaneRecord | None = None
            attached_session_id: str | None = None
            try:
                create_tmux_session(
                    session_name=session_name,
                    working_directory=self.daemon.workspace,
                    launch_plan=self.plan,
                )
                created = prepare_headless_agent_window(
                    session_name=session_name, fresh_session=True
                )
                attached_session_id = created.session_id
                if attached_session_id is None:
                    raise HermesNativeError("Could not verify the Hermes terminal session.")
                command, environment = self.daemon.native_command(
                    ["--tui", "--resume", snapshot.session_id]
                )
                if self._unattended():
                    environment["HERMES_NONINTERACTIVE"] = "1"
                for key in ("TMPDIR", "TMP", "TEMP"):
                    environment[key] = str(hint_directory)
                argv, _ = prepare_private_provider_command(
                    session_root=launch_root,
                    environment=detached_tool_environment(environment, session_name=session_name),
                    command=command,
                )
                publish_tmux_launch_environment(session_name=session_name, launch_plan=self.plan)
                if tmux_command(
                    ["set-option", "-w", "-t", created.window_id, "remain-on-exit", "on"]
                ).returncode:
                    raise HermesNativeError("Could not retain the Hermes terminal pane.")
                if tmux_command(
                    ["respawn-pane", "-k", "-t", created.pane_id, "exec " + shlex.join(argv)]
                ).returncode:
                    raise HermesNativeError("Could not start Ink in the managed terminal pane.")
                pane = next(
                    (
                        item
                        for item in list_tmux_panes(session_name=session_name)
                        if item.pane_id == created.pane_id
                    ),
                    None,
                )
                if pane is None or pane.pane_dead:
                    raise HermesNativeError("Ink exited during terminal startup.")
                if self.daemon.shared and (
                    self.daemon.verify_shared_session(snapshot.session_id) != identity
                ):
                    raise HermesNativeError("Ink did not retain the verified Hermes profile.")
                pid = pane.pane_pid
                self.m_state = HermesTuiSessionState(
                    session_name=session_name,
                    pane_id=pane.pane_id,
                    window_id=pane.window_id,
                    tmux_session_id=attached_session_id,
                    tmux_socket_path=socket_path,
                    pane_pid=pid,
                    pane_birth_token=None if pid is None else _dispatch_origin_birth_token(pid),
                    hint_directory=str(hint_directory),
                    native_session_id=snapshot.session_id,
                    home=str(self.plan.home_path.resolve()),
                    working_directory=str(self.daemon.workspace),
                )
                if self.m_binding_changed_callback is not None:
                    self.m_binding_changed_callback()
            except (OSError, ValueError, BackendExecutionError, TmuxCommandError):
                if attached_session_id is not None and current_runtime_startup() is None:
                    with suppress(TmuxCommandError):
                        kill_tmux_session(session_name=session_name, session_id=attached_session_id)
                raise

    def terminal_attachment(self) -> HermesTerminalAttachment:
        """Observe the selected Ink incarnation separately from native readiness."""

        state = self.state
        try:
            with tmux_server_scope(state.tmux_socket_path, allow_start=False):
                if not tmux_session_exists(
                    session_name=state.session_name, allow_missing_server=True
                ):
                    return "detached"
                pane = next(
                    (
                        item
                        for item in list_tmux_panes(session_name=state.session_name)
                        if item.pane_id == state.pane_id
                        and item.session_id == state.tmux_session_id
                    ),
                    None,
                )
        except (OSError, TmuxCommandError):
            return "unverified"
        if pane is None or pane.pane_dead:
            return "detached"
        if (
            pane.pane_pid is None
            or pane.pane_pid != state.pane_pid
            or state.pane_birth_token is None
            or _dispatch_origin_birth_token(pane.pane_pid) != state.pane_birth_token
        ):
            return "unverified"
        hint = _read_terminal_hint(Path(state.hint_directory))
        if hint is None:
            return "unverified"
        return "attached" if hint == state.native_session_id else "other_session"

    def _generation_id(self) -> str:
        """Return the current verified Houmao runtime generation."""

        generation = load_session_manifest(self.manifest_path).payload.get("registry_generation_id")
        if not isinstance(generation, str) or not generation:
            raise HermesNativeError("The managed Hermes TUI generation is unavailable.")
        return generation

    def _turn_path(self, request_id: str) -> Path:
        """Resolve the owner journal locator for this single request."""

        if request_id in {"", ".", ".."} or Path(request_id).name != request_id:
            raise HermesNativeError("Invalid Hermes request identity.")
        return (
            self.manifest_path.parent
            / f"{self.manifest_path.stem}.turn-artifacts"
            / request_id
            / HERMES_TUI_ADMISSION_FILE
        )

    def submit_native_prompt(
        self,
        prompt: str,
        *,
        request_id: str,
        authorize: Callable[[], None] | None = None,
        owner_claim: OwnerPromptClaim | None = None,
        existing_only: bool = False,
    ) -> HermesTuiAdmission:
        """Reserve one native input and return its exact positive admission receipt."""

        generation = self._generation_id()
        claim = owner_claim or reserve_owner_prompt(
            self.manifest_path,
            generation,
            request_id=request_id,
            origin="manager",
            reconcile_tui=self.reconcile_owner_attempt,
        )
        if (
            claim.manifest_path != self.manifest_path
            or claim.generation_id != generation
            or claim.request_id != request_id
            or claim.mode != "tui"
        ):
            raise HermesNativeError("The Hermes prompt claim does not match this runtime.")

        def verify_claim() -> None:
            """Fence every native write to the original managed request authority."""

            if not claim.active():
                raise HermesNativeError("The Hermes managed input claim expired.")
            if authorize is not None:
                authorize()

        path = self._turn_path(request_id)
        admission: HermesTuiAdmission | None = None
        try:
            if not existing_only and self.daemon.shared:
                self.daemon.recover_shared(
                    self.state.native_session_id, unattended=self._unattended()
                )
            elif not existing_only:
                self.daemon.ensure()
            with self.daemon.client() as native:
                if self.daemon.shared:
                    self.daemon.require_recorded_authority(native.identity)
                current = self.daemon.resume_session(native, self.state.native_session_id)
                if not current.ready:
                    raise OwnerAdmissionError(
                        "not_ready", "The Hermes session is busy or its readiness is unverified."
                    )
                verify_claim()
                self._publish_self_daemon(native.identity, generation)
                admission = self._prepare_input(
                    path, prompt, request_id, generation, current, native
                )
                return self._submit_with_recovery(
                    native, admission, prompt, path, claim, verify_claim
                )
        except HermesInputConflict:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            if admission is None:
                claim.finish("failed", evidence="hermes_pre_handoff")
                if existing_only and not isinstance(
                    exc, (OwnerAdmissionError, HermesDeadlineExpired, HermesRpcRefused)
                ):
                    raise OwnerAdmissionError(
                        "unavailable", "The native Hermes conversation could not be verified."
                    ) from exc
            raise

    def _publish_self_daemon(self, identity: HermesDaemonIdentity, generation: str) -> None:
        """Refresh detached self proof for this verified native conversation."""

        with suppress(OSError, SessionManifestError, ValueError):
            publish_verified_hermes_daemon_for_generation(self.manifest_path, generation, identity)

    def _prepare_input(
        self,
        path: Path,
        prompt: str,
        request_id: str,
        generation: str,
        snapshot: HermesSessionSnapshot,
        native: HermesClient,
    ) -> HermesTuiAdmission:
        """Write the stable identity and payload digest before native submission."""

        identity = hashlib.sha256(f"{generation}:{request_id}".encode()).hexdigest()
        epoch = snapshot.payload.get("replay_epoch")
        sequence = snapshot.payload.get("last_sequence")
        admission = HermesTuiAdmission(
            request_id=request_id,
            generation_id=generation,
            native_session_id=snapshot.session_id,
            input_digest=hashlib.sha256(prompt.encode()).hexdigest(),
            submission_id=f"houmao-{identity}",
            daemon_instance_id=native.identity.instance_id,
            replay_epoch=epoch if isinstance(epoch, str) else None,
            last_sequence=sequence if type(sequence) is int else 0,
        )
        with _lock_admission(path):
            if read_hermes_evidence(path) is not None:
                raise HermesInputConflict("The Hermes owner has already seen this input identity.")
            write_hermes_evidence(path, admission.model_dump(mode="json"))
        return admission

    def _submit_with_recovery(
        self,
        native: HermesClient,
        admission: HermesTuiAdmission,
        prompt: str,
        path: Path,
        claim: OwnerPromptClaim,
        verify_claim: Callable[[], None],
    ) -> HermesTuiAdmission:
        """Recover a lost acknowledgment only with the original authenticated submission."""

        try:
            accepted = self._submit_rpc(native, admission, prompt)
        except (HermesDeadlineExpired, HermesRpcRefused):
            rejected = admission.model_copy(update={"status": "failed"})
            write_hermes_evidence(path, rejected.model_dump(mode="json"))
            claim.finish("failed", evidence="hermes_refused")
            raise
        except HermesNativeError:
            try:
                with self.daemon.client() as recovered:
                    if recovered.identity != native.identity:
                        raise HermesNativeError(
                            "The Hermes daemon changed before admission could be verified."
                        )
                    self.daemon.resume_session(recovered, admission.native_session_id)
                    verify_claim()
                    accepted = self._submit_rpc(recovered, admission, prompt)
            except (OSError, ValueError, RuntimeError) as exc:
                unknown = admission.model_copy(update={"status": "uncertain"})
                with suppress(OSError, RuntimeError):
                    write_hermes_evidence(path, unknown.model_dump(mode="json"))
                with suppress(OSError, RuntimeError):
                    claim.finish("uncertain", evidence="hermes_acknowledgment_lost")
                raise HermesAdmissionUncertain(
                    "The exact Hermes admission could not be recovered."
                ) from exc
        try:
            write_hermes_evidence(path, accepted.model_dump(mode="json"))
        except (OSError, RuntimeError, ValueError) as exc:
            raise HermesAdmissionUncertain(
                "Hermes acknowledged the input but Houmao could not finalize its owner evidence."
            ) from exc
        # The durable receipt can reconcile this claim even if its ledger update is blocked.
        with suppress(OwnerAdmissionError):
            claim.handoff()
            self._finish_claim(claim, accepted)
        return accepted

    def _submit_rpc(
        self, native: HermesClient, admission: HermesTuiAdmission, prompt: str
    ) -> HermesTuiAdmission:
        """Use the stable native submission ID and unchanged literal payload."""

        receipt = native.rpc(
            "prompt.submit",
            session_id=admission.native_session_id,
            submission_id=admission.submission_id,
            text=prompt,
        )
        accepted = self._apply_receipt(admission, native, receipt)
        if accepted.terminal:
            with suppress(HermesNativeError):
                settled = native.rpc(
                    "prompt.receipt",
                    session_id=accepted.native_session_id,
                    admission_id=accepted.native_admission_id,
                    include_result=True,
                )
                accepted = self._apply_receipt(accepted, native, settled)
        return accepted

    def _apply_receipt(
        self, admission: HermesTuiAdmission, native: HermesClient, receipt: dict[str, Any]
    ) -> HermesTuiAdmission:
        """Interpret only an exact receipt from the authenticated native home."""

        ref, seen = receipt.get("ref"), receipt.get("admission_id")
        sequence = receipt.get("sequence")
        if (
            not isinstance(ref, dict)
            or ref.get("profile_id") != native.identity.profile_id
            or ref.get("session_id") != admission.native_session_id
            or not isinstance(seen, str)
            or not seen
            or type(sequence) is not int
            or sequence < 1
            or (admission.native_admission_id is not None and seen != admission.native_admission_id)
            or (
                admission.native_admission_sequence is not None
                and sequence != admission.native_admission_sequence
            )
        ):
            raise HermesNativeError("Hermes returned an admission for a different native request.")
        outcome = receipt.get("outcome")
        status = normalize_hermes_tui_receipt(receipt.get("status"), outcome)
        result = receipt.get("result")
        text = result.get("final_response") if isinstance(result, dict) else None
        if not isinstance(text, str):
            text = admission.output_text
        epoch, generation = receipt.get("authority_epoch"), receipt.get("execution_generation")
        if (
            type(epoch) is not int
            or not 1 <= epoch <= native.identity.authority_epoch
            or (admission.native_admission_id is None and epoch != native.identity.authority_epoch)
            or (
                admission.native_authority_epoch is not None
                and epoch < admission.native_authority_epoch
            )
        ):
            raise HermesNativeError("Hermes returned an invalid admission authority epoch.")
        if (
            "outcome" not in receipt
            or "execution_generation" not in receipt
            or (generation is not None and (type(generation) is not int or generation < 1))
            or (status == "queued" and (outcome is not None or generation is not None))
            or (status == "running" and (outcome is not None or generation is None))
            or (status == "completed" and generation is None)
            or (admission.terminal and status != admission.status)
        ):
            raise HermesNativeError("Hermes returned a contradictory admission receipt.")
        return admission.model_copy(
            update={
                "native_admission_id": seen,
                "native_admission_sequence": sequence,
                "native_authority_epoch": epoch,
                "native_execution_generation": generation if type(generation) is int else None,
                "status": status,
                "native_outcome": outcome if isinstance(outcome, str) else None,
                "output_text": self._redact(text),
            }
        )

    def _redact(self, text: str) -> str:
        """Exclude selected credential values from projected Hermes evidence."""

        for name in self.plan.private_env_var_names:
            value = self.plan.env.get(name)
            if value:
                text = text.replace(value, "<redacted>")
        return text

    def read_native_admission(self, request_id: str) -> HermesTuiAdmission | None:
        """Reconcile this exact operation through its receipt and replay window."""

        path = self._turn_path(request_id)
        if not path.exists():
            return None
        with _lock_admission(path):
            admission = read_hermes_tui_admission(
                path,
                request_id=request_id,
                generation_id=self._generation_id(),
                native_session_id=self.state.native_session_id,
            )
            if admission is None:
                return None
            if admission.terminal or admission.native_admission_id is None:
                return admission
            try:
                with self.daemon.client() as native:
                    receipt = native.rpc(
                        "prompt.receipt",
                        session_id=admission.native_session_id,
                        admission_id=admission.native_admission_id,
                        include_result=True,
                    )
                    resolved = self._apply_receipt(admission, native, receipt)
                    with suppress(HermesNativeError):
                        resolved = self._read_replay(native, resolved)
                    write_hermes_evidence(path, resolved.model_dump(mode="json"))
                    return resolved
            except HermesNativeError:
                # Preserve the last durable queued/running disposition for reconnect.
                return admission.model_copy(update={"status": "uncertain"})

    def _read_replay(
        self, native: HermesClient, admission: HermesTuiAdmission
    ) -> HermesTuiAdmission:
        """Accept structured replay frames only for the exact admission."""

        result = native.rpc(
            "session.events.since",
            session_id=admission.native_session_id,
            replay_epoch=admission.replay_epoch,
            last_sequence=admission.last_sequence,
        )
        epoch, latest = result.get("replay_epoch"), result.get("latest_seq")
        if not isinstance(epoch, str) or type(latest) is not int or latest < 0:
            return admission
        gap = result.get("snapshot_required") is True or epoch != admission.replay_epoch
        rows = result.get("events")
        events = list(admission.events)
        if not gap and isinstance(rows, list):
            last_sequence = admission.last_sequence
            for item in rows:
                sequence = item.get("seq") if isinstance(item, dict) else None
                if type(sequence) is not int or sequence <= last_sequence or sequence > latest:
                    continue
                last_sequence = sequence
                event = self._serialize_event(item, admission, native)
                if event is not None:
                    events.append(event)
        return admission.model_copy(
            update={
                "events": tuple(events[-_MAX_EVENTS:]),
                "replay_epoch": epoch,
                "last_sequence": latest,
                "replay_gap": admission.replay_gap or gap,
            }
        )

    def _serialize_event(
        self, item: dict[str, Any], admission: HermesTuiAdmission, native: HermesClient
    ) -> SessionEvent | None:
        """Map only session- and admission-correlated semantic events."""

        payload = item.get("payload")
        if not isinstance(payload, dict):
            return None
        if (
            item.get("session_id") != admission.native_session_id
            or (item.get("admission_id") or payload.get("admission_id"))
            != admission.native_admission_id
            or item.get("authority_epoch") != native.identity.authority_epoch
            or admission.native_execution_generation is None
            or item.get("execution_generation") != admission.native_execution_generation
        ):
            return None
        kind = item.get("type")
        if kind == "message.delta":
            message = payload.get("text") or payload.get("delta") or payload.get("content")
            kind = "assistant_delta"
        elif kind in {"tool.start", "tool.complete"}:
            message = payload.get("tool_name") or payload.get("name")
        else:
            return None
        if not isinstance(message, str) or not message:
            return None
        return SessionEvent(
            kind=kind,
            message=self._redact(message),
            turn_index=1,
            payload={"native_sequence": item["seq"], "admission_id": admission.native_admission_id},
        )

    def reconcile_owner_attempt(self, attempt: OwnerPromptAttempt) -> bool:
        """Reconcile behind the shared owner lock without recursively writing it."""

        admission = self.read_native_admission(attempt.request_id)
        return admission is not None and admission.terminal_outcome is not None

    @staticmethod
    def _finish_claim(claim: OwnerPromptClaim, admission: HermesTuiAdmission) -> None:
        """Release the shared owner slot only after exact native settlement."""

        if (outcome := admission.terminal_outcome) is not None:
            claim.finish(outcome, evidence="hermes_native_receipt")

    def observe_managed_control(self) -> ManagedControlObservationV1:
        """Project current native readiness, pending request, and the separate Ink view."""

        attachment = self.terminal_attachment()
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        request: OwnerPromptAttempt | None = None
        admission: HermesTuiAdmission | None = None
        try:
            request = observe_owner_prompt(
                self.manifest_path,
                self._generation_id(),
                reconcile_tui=self.reconcile_owner_attempt,
            )
            if request is not None:
                admission = self.read_native_admission(request.request_id)
            if self.daemon.shared:
                with self.daemon.client() as native:
                    self.daemon.require_recorded_authority(native.identity)
                    snapshot = self.daemon.resume_session(native, self.state.native_session_id)
            else:
                snapshot = self.daemon.resolve_session(self.state.native_session_id)
            active_turn = _active_turn_id(snapshot)
            return ManagedControlObservationV1(
                source="tui_native",
                freshness="current",
                observed_at_utc=stamp,
                owner_available=True,
                connection_ready=True,
                can_accept_prompt_now=snapshot.ready and request is None,
                service_incarnation=snapshot.daemon_instance_id,
                native_session_id=self.state.native_session_id,
                active_request_id=None if request is None else request.request_id,
                active_turn_id=active_turn,
                native_admission_id=None if admission is None else admission.native_admission_id,
                native_admission_state=None if admission is None else admission.status,
                approval_pending=snapshot.approval_pending,
                terminal_attachment=attachment,
            )
        except (OSError, ValueError, OwnerAdmissionError, BackendExecutionError):
            return ManagedControlObservationV1(
                source="tui_native",
                freshness="unknown",
                observed_at_utc=stamp,
                owner_available=False,
                connection_ready=False,
                can_accept_prompt_now=False,
                native_session_id=self.state.native_session_id,
                active_request_id=None if request is None else request.request_id,
                native_admission_id=None if admission is None else admission.native_admission_id,
                native_admission_state=None if admission is None else admission.status,
                terminal_attachment=attachment,
            )

    def wait_for_native_prompt(
        self, claim: OwnerPromptClaim, admission: HermesTuiAdmission
    ) -> HermesTuiAdmission:
        """Observe an admitted request through terminal evidence or the current deadline."""

        if (
            claim.request_id != admission.request_id
            or claim.generation_id != admission.generation_id
            or claim.manifest_path != self.manifest_path
            or claim.mode != "tui"
            or admission.native_session_id != self.state.native_session_id
        ):
            raise HermesNativeError("The Hermes receipt does not match the owner claim.")
        current = admission
        deadline = time.monotonic() + _TURN_TIMEOUT
        execution_deadline = current_execution_deadline()
        if execution_deadline is not None:
            deadline = min(deadline, execution_deadline)
        while current.status in {"queued", "running"}:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.2, remaining))
            if time.monotonic() >= deadline:
                break
            try:
                with execution_deadline_scope(deadline):
                    updated = self.read_native_admission(claim.request_id)
            except (OSError, RuntimeError, ValueError):
                break
            if updated is None or (
                updated.terminal_outcome is None and updated.status not in {"queued", "running"}
            ):
                break
            if (
                updated.request_id != admission.request_id
                or updated.generation_id != admission.generation_id
                or updated.native_session_id != admission.native_session_id
                or updated.native_admission_id != admission.native_admission_id
                or updated.native_admission_sequence != admission.native_admission_sequence
            ):
                break
            current = updated
            if current.terminal_outcome is not None:
                # A later owner read can settle the claim if the ledger is busy here.
                with execution_deadline_scope(deadline), suppress(OwnerAdmissionError):
                    self._finish_claim(claim, current)
        return current

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Submit a literal native prompt and wait for its exact terminal receipt."""

        request_id = uuid4().hex
        admission = self.submit_native_prompt(prompt, request_id=request_id)
        claim = OwnerPromptClaim(self.manifest_path, admission.generation_id, request_id, "tui")
        current = self.wait_for_native_prompt(claim, admission)
        if current.terminal_outcome is None:
            raise HermesNativeError("Hermes native turn remains unresolved.")
        return [
            *current.events,
            SessionEvent(
                kind="assistant" if current.status == "completed" else current.status,
                message=current.output_text,
                turn_index=1,
                payload={"native_admission_id": current.native_admission_id},
            ),
        ]

    def interrupt_native_admission(self, request_id: str) -> SessionControlResult:
        """Cancel only the managed operation's exact queued or running admission."""

        try:
            admission = self.read_native_admission(request_id)
            if (
                admission is None
                or admission.native_admission_id is None
                or admission.status not in {"queued", "running"}
            ):
                raise HermesNativeError("The exact active Hermes admission is unavailable.")
            with self.daemon.client() as native:
                if self.daemon.shared:
                    self.daemon.require_recorded_authority(native.identity)
                native.rpc(
                    "prompt.cancel",
                    session_id=admission.native_session_id,
                    admission_id=admission.native_admission_id,
                )
            resolved = self.read_native_admission(request_id)
            if resolved is not None:
                claim = OwnerPromptClaim(
                    self.manifest_path, resolved.generation_id, request_id, "tui"
                )
                self._finish_claim(claim, resolved)
            return SessionControlResult(
                "ok", "interrupt", "Sent cancellation for the exact Hermes admission."
            )
        except (OSError, ValueError, BackendExecutionError) as exc:
            return SessionControlResult("error", "interrupt", str(exc))

    def interrupt(self) -> SessionControlResult:
        """Resolve the current managed request and interrupt that exact admission."""

        try:
            attempt = observe_owner_prompt(
                self.manifest_path,
                self._generation_id(),
                reconcile_tui=self.reconcile_owner_attempt,
            )
        except (OSError, ValueError, BackendExecutionError, OwnerAdmissionError) as exc:
            return SessionControlResult("error", "interrupt", str(exc))
        if attempt is None:
            return SessionControlResult(
                "error", "interrupt", "There is no active managed Hermes request."
            )
        return self.interrupt_native_admission(attempt.request_id)

    def terminate(self) -> SessionControlResult:
        """Stop the exact terminal incarnation and the daemon for this home."""

        try:
            state = self.state
            with tmux_server_scope(state.tmux_socket_path, allow_start=False):
                if tmux_session_exists(session_name=state.session_name, allow_missing_server=True):
                    panes = list_tmux_panes(session_name=state.session_name)
                    if all(pane.session_id == state.tmux_session_id for pane in panes):
                        kill_tmux_session(
                            session_name=state.session_name, session_id=state.tmux_session_id
                        )
            self.daemon.stop()
        except (OSError, ValueError, BackendExecutionError, TmuxCommandError) as exc:
            return SessionControlResult("error", "terminate", str(exc))
        return SessionControlResult(
            "ok",
            "terminate",
            "Stopped the managed Hermes terminal and profile."
            if self.daemon.shared
            else "Stopped the managed Hermes terminal and daemon.",
        )

    def relaunch(
        self, *, chat_session: RelaunchChatSessionSelection | None = None
    ) -> SessionControlResult:
        """Reopen a fresh or the exact saved managed conversation."""

        selected = chat_session or RelaunchChatSessionSelection(mode="new")
        previous = self.state
        if not self.daemon.shared:
            return SessionControlResult(
                "error", "relaunch", "Standalone Hermes requires a fresh managed launch."
            )
        if selected.mode != "new" and (
            selected.mode != "exact" or selected.session_id != previous.native_session_id
        ):
            return SessionControlResult(
                "error", "relaunch", "Hermes relaunch requires new or the exact saved ID."
            )
        try:
            if selected.session_id is not None and self.daemon.discover() is not None:
                self.daemon.verify_shared_session(selected.session_id)
            stopped = self.terminate()
            if stopped.status != "ok":
                return SessionControlResult("error", "relaunch", stopped.detail)
            self._start_view(previous.session_name, native_session_id=selected.session_id)
        except (OSError, ValueError, BackendExecutionError, TmuxCommandError) as exc:
            return SessionControlResult("error", "relaunch", str(exc))
        return SessionControlResult("ok", "relaunch", "Relaunched the managed Hermes terminal.")

    def close(self) -> None:
        """Release this control adapter while leaving native work observable."""


def _read_terminal_hint(directory: Path) -> str | None:
    """Read a bounded, owner-private hint from the launch's fresh directory."""

    try:
        matches = tuple(directory.glob("hermes-tui-active-session-*.json"))
        if len(matches) != 1 or matches[0].lstat().st_size > _MAX_HINT_BYTES:
            return None
        record = read_hermes_evidence(matches[0])
    except (OSError, ValueError, HermesNativeError):
        return None
    session = record.get("session_id") if record is not None else None
    return session if isinstance(session, str) and _SESSION_ID.fullmatch(session) else None


def _active_turn_id(snapshot: HermesSessionSnapshot) -> str | None:
    """Return the running native admission even when a human submitted it."""

    pending = snapshot.payload.get("pending")
    if isinstance(pending, list):
        for entry in pending:
            if isinstance(entry, dict) and entry.get("status") == "started":
                identifier = entry.get("admission_id")
                if isinstance(identifier, str) and identifier:
                    return identifier
    return None


@contextmanager
def _lock_admission(path: Path) -> Iterator[None]:
    """Serialize rereads and evidence updates for one exact operation."""

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path.with_suffix(".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "rb+") as handle:
        deadline = current_execution_deadline()
        if deadline is None:
            fcntl.flock(handle, fcntl.LOCK_EX)
        else:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise HermesDeadlineExpired(
                        "The execution deadline expired before receipt access."
                    )
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    time.sleep(min(0.02, remaining))
        yield
