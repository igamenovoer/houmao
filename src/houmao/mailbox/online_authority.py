"""Cross-process online admission, immutable connections, and worker fencing."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator
from uuid import uuid4

from houmao.agents.mailbox_runtime_models import MailboxSlotConfig, StalwartMailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import mailboxes_resolved_config_from_payload
from houmao.agents.realm_controller.manifest import _session_manifest_lock, load_session_manifest
from houmao.mailbox.online_models import (
    OnlineAuthorityContext as OnlineAuthorityContext,
)
from houmao.mailbox.online_models import (
    OnlineBindingError,
)
from houmao.mailbox.online_models import (
    OnlineFence as OnlineFence,
)
from houmao.mailbox.stalwart import StalwartError, StalwartJmapClient


@dataclass(frozen=True)
class OnlineConnection:
    """An immutable account client and the fence captured before observation."""

    client: StalwartJmapClient
    fence: OnlineFence
    config: StalwartMailboxResolvedConfig


_CLIENTS: dict[tuple[str, str], StalwartJmapClient] = {}
_CLIENT_LOCK = threading.RLock()
_CLIENT_INITIALIZERS: dict[tuple[str, str], threading.Lock] = {}


class OnlineConnectionAuthority:
    """Coordinate managed online operations independently of terminal admission."""

    def __init__(self) -> None:
        self.m_context: OnlineAuthorityContext
        self.m_root: Path

    @classmethod
    def from_context(cls, context: OnlineAuthorityContext) -> OnlineConnectionAuthority:
        """Bind an explicit agent/session authority without provider I/O."""

        instance = cls()
        instance.m_context = context
        instance.m_root = context.manifest_path.resolve().parent / ".online-mail"
        return instance

    @property
    def context(self) -> OnlineAuthorityContext:
        """Return the immutable local authority."""

        return self.m_context

    def snapshot(self) -> tuple[MailboxSlotConfig, StalwartMailboxResolvedConfig | None]:
        """Read one complete current snapshot, preserving configured outages."""

        handle = load_session_manifest(self.m_context.manifest_path)
        payload = handle.payload
        if (
            payload["agent_id"] != self.m_context.agent_id
            or payload["runtime"]["session_id"] != self.m_context.session_id
        ):
            raise OnlineBindingError(
                "mail_binding_conflict", "Online authority belongs to another agent or session"
            )
        slots = mailboxes_resolved_config_from_payload(
            payload["launch_plan"]["mailboxes"], manifest_path=handle.path
        )
        binding = slots.online.binding
        if binding is not None and not isinstance(binding, StalwartMailboxResolvedConfig):
            raise OnlineBindingError(
                "unsupported_provider", "Configured online provider is unsupported"
            )
        return slots.online, binding

    def state(self) -> dict[str, Any]:
        """Read derived epoch/admission state without consulting a provider."""

        try:
            result = json.loads((self.m_root / "state.json").read_text())
            return result if isinstance(result, dict) else {}
        except (OSError, ValueError):
            return {}

    def _publish_state(self, *, closing: bool, force_epoch: bool = False) -> dict[str, Any]:
        """Atomically publish derived state while holding control/exclusive admission."""

        slot, binding = self.snapshot()
        previous = self.state()
        same = (
            previous.get("agent_id") == self.m_context.agent_id
            and previous.get("session_id") == self.m_context.session_id
            and previous.get("revision") == slot.revision
            and previous.get("binding_id") == (binding.binding_id if binding else None)
        )
        epoch = previous.get("epoch_id") if same and not force_epoch else uuid4().hex
        value = {
            "agent_id": self.m_context.agent_id,
            "session_id": self.m_context.session_id,
            "revision": slot.revision,
            "binding_id": binding.binding_id if binding else None,
            "epoch_id": epoch or uuid4().hex,
            "closing": closing,
        }
        self.m_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.m_root.chmod(0o700)
        descriptor, name = tempfile.mkstemp(prefix="state-", dir=self.m_root)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w") as stream:
                json.dump(value, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.m_root / "state.json")
        finally:
            temporary.unlink(missing_ok=True)
        return value

    @contextmanager
    def _lease(self, name: str, *, shared: bool, deadline: float) -> Iterator[None]:
        """Acquire an OS-owned lease within a finite monotonic deadline."""

        self.m_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.m_root / name, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            while True:
                try:
                    fcntl.flock(
                        descriptor, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB
                    )
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise OnlineBindingError(
                            "online_retirement_busy",
                            "Online operations could not quiesce before the deadline",
                            uncertain=not shared,
                        )
                    time.sleep(min(0.01, max(0, deadline - time.monotonic())))
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _reconcile(self, deadline: float) -> None:
        """Recover an orphaned intent only when no live controller owns its mutex."""

        with self._lease(
            "control.lock", shared=False, deadline=min(deadline, time.monotonic() + 0.05)
        ):
            with self._lease("admission.lock", shared=False, deadline=deadline):
                self._publish_state(closing=False)

    @contextmanager
    def control(self, *, expected_revision: str, timeout_seconds: float) -> Iterator[None]:
        """Close new admission, drain existing I/O, and guard one revision mutation."""

        deadline = time.monotonic() + timeout_seconds
        with self._lease("control.lock", shared=False, deadline=deadline):
            slot, _ = self.snapshot()
            if slot.revision != expected_revision:
                raise OnlineBindingError("mail_binding_conflict", "Online slot revision changed")
            self._publish_state(closing=True)
            try:
                with self._lease("admission.lock", shared=False, deadline=deadline):
                    slot, _ = self.snapshot()
                    if slot.revision != expected_revision:
                        raise OnlineBindingError(
                            "mail_binding_conflict", "Online slot revision changed"
                        )
                    yield
            finally:
                self._publish_state(closing=False)

    def advance_epoch(self) -> None:
        """Invalidate old callbacks while control owns exclusive admission."""

        self._publish_state(closing=True, force_epoch=True)
        self.retire_cached_connections()

    def retire_cached_connections(self) -> None:
        """Drop this process's retired cache while captured observations retain their inputs."""

        manifest = str(self.m_context.manifest_path.resolve())
        with _CLIENT_LOCK:
            for key in tuple(_CLIENTS):
                if key[0] == manifest:
                    del _CLIENTS[key]
                    _CLIENT_INITIALIZERS.pop(key, None)

    def _client(
        self, config: StalwartMailboxResolvedConfig, epoch: str, timeout: float
    ) -> StalwartJmapClient:
        """Cache validated discovery and roles for one immutable connection epoch."""

        key = (str(self.m_context.manifest_path.resolve()), epoch)
        with _CLIENT_LOCK:
            initializer = _CLIENT_INITIALIZERS.setdefault(key, threading.Lock())
        with initializer:
            cached = _CLIENTS.get(key)
            if cached is not None:
                return cached
            if config.credential_file is None:
                raise OnlineBindingError(
                    "online_credentials_unavailable", "Online credential snapshot is unavailable"
                )
            try:
                client = StalwartJmapClient(
                    jmap_url=config.jmap_url,
                    login_identity=config.login_identity,
                    credential_file=config.credential_file,
                    timeout_seconds=timeout,
                    sender_address=config.address,
                    account_id=config.account_id,
                    identity_id=config.identity_id,
                )
                client.validate_binding(sender_address=config.address)
            except (StalwartError, OSError, ValueError):
                raise OnlineBindingError(
                    "online_connection_failed",
                    "Online account authentication or connection validation failed",
                ) from None
            with _CLIENT_LOCK:
                for old_key in tuple(_CLIENTS):
                    if old_key[0] == key[0] and old_key != key:
                        del _CLIENTS[old_key]
                        _CLIENT_INITIALIZERS.pop(old_key, None)
                _CLIENTS[key] = client
            return client

    @contextmanager
    def operation(
        self, *, expected_binding_id: str, timeout_seconds: float = 10.0
    ) -> Iterator[OnlineConnection]:
        """Pin a managed operation under shared admission through bounded provider I/O."""

        from houmao.mailbox.delivery_policy import require_open_provider_binding
        from houmao.mailbox.online_binding import OnlineBindingService

        with require_open_provider_binding(self.m_context.manifest_path):
            pass

        deadline = time.monotonic() + timeout_seconds
        _, initial = self.snapshot()
        if initial is not None and (initial.account_id is None or initial.identity_id is None):
            OnlineBindingService.from_context(self.m_context).adopt(
                expected_binding_id=expected_binding_id, timeout_seconds=timeout_seconds
            )
        while True:
            with self._lease("admission.lock", shared=True, deadline=deadline):
                slot, config = self.snapshot()
                if config is None or config.binding_id != expected_binding_id:
                    raise OnlineBindingError(
                        "mail_binding_conflict", "Online binding changed or was detached"
                    )
                state = self.state()
                matches = (
                    state.get("agent_id") == self.m_context.agent_id
                    and state.get("session_id") == self.m_context.session_id
                    and state.get("revision") == slot.revision
                    and state.get("binding_id") == config.binding_id
                )
                if matches and not state.get("closing"):
                    epoch = str(state["epoch_id"])
                    client = self._client(config, epoch, max(0.01, deadline - time.monotonic()))
                    fence = OnlineFence(
                        config.agent_id,
                        self.m_context.session_id,
                        config.binding_id,
                        slot.revision,
                        epoch,
                        str(config.account_id),
                    )
                    yield OnlineConnection(client, fence, config)
                    return
            self._reconcile(deadline)

    def capture_connection(
        self, *, expected_binding_id: str, timeout_seconds: float = 10.0
    ) -> OnlineConnection:
        """Capture immutable observation inputs, releasing admission before provider work."""

        with self.operation(
            expected_binding_id=expected_binding_id, timeout_seconds=timeout_seconds
        ) as connection:
            return connection

    @contextmanager
    def effect_lease(self, fence: OnlineFence, *, timeout_seconds: float = 0.5) -> Iterator[None]:
        """Fence body effects through handoff without provider discovery or a manifest lock.

        Retirement waits for already admitted effects or fails at its finite
        deadline. A closing or superseded origin cannot begin a new effect.
        """

        with self._lease(
            "admission.lock", shared=True, deadline=time.monotonic() + timeout_seconds
        ):
            with _session_manifest_lock(self.m_context.manifest_path):
                slot, config = self.snapshot()
                state = self.state()
                if (
                    config is None
                    or state.get("closing")
                    or (
                        config.agent_id,
                        self.m_context.session_id,
                        config.binding_id,
                        slot.revision,
                        state.get("epoch_id"),
                        config.account_id,
                    )
                    != (
                        fence.agent_id,
                        fence.session_id,
                        fence.binding_id,
                        fence.revision,
                        fence.epoch_id,
                        fence.account_id,
                    )
                ):
                    raise OnlineBindingError(
                        "mail_binding_conflict", "Online effect belongs to a retired connection"
                    )
            yield

    def commit_observation(self, fence: OnlineFence, callback: Callable[[], None]) -> bool:
        """Commit derived state only while its binding revision and epoch remain current."""

        try:
            with self._lease("admission.lock", shared=True, deadline=time.monotonic() + 0.5):
                with _session_manifest_lock(self.m_context.manifest_path):
                    slot, config = self.snapshot()
                    state = self.state()
                    if (
                        config is None
                        or state.get("closing")
                        or (
                            config.agent_id,
                            self.m_context.session_id,
                            config.binding_id,
                            slot.revision,
                            state.get("epoch_id"),
                            config.account_id,
                        )
                        != (
                            fence.agent_id,
                            fence.session_id,
                            fence.binding_id,
                            fence.revision,
                            fence.epoch_id,
                            fence.account_id,
                        )
                    ):
                        return False
                    callback()
                    return True
        except OnlineBindingError:
            return False
