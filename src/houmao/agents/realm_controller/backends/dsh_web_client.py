"""Independent authenticated wire connection to one managed local DSH Web Host."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, cast
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from websockets.sync.client import ClientConnection, connect
from websockets.typing import Origin

from houmao.agents.realm_controller.backends.dsh_diagnostics import sanitize_dsh_diagnostic
from houmao.agents.realm_controller.errors import BackendExecutionError


class DshWebError(BackendExecutionError):
    """Expose a safe native refusal without retaining credential-bearing transport errors."""

    def __init__(self, code: str, message: str, *, secret_values: Sequence[str] = ()) -> None:
        """Retain the machine-readable refusal and its safe message."""

        self.m_code: str = (
            code
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", code)
            and sanitize_dsh_diagnostic(code, secret_values=secret_values) == code
            else "native_failure"
        )
        summary = sanitize_dsh_diagnostic(message, secret_values=secret_values)
        super().__init__(f"{self.m_code}: {summary}" if summary else self.m_code)

    @property
    def code(self) -> str:
        """Return the stable machine-readable native refusal."""

        return self.m_code


class DshWebClient:
    """Own one API cookie and socket without borrowing browser authentication."""

    def __init__(self) -> None:
        """Initialize a disconnected client; use ``from_connection`` to authenticate."""

        self.m_origin: str = ""
        self.m_http: httpx.Client | None = None
        self.m_socket: ClientConnection | None = None
        self.m_timeout: float = 15.0
        self.m_secret_values: tuple[str, ...] = ()
        self.m_lock: threading.RLock = threading.RLock()

    @classmethod
    def from_connection(
        cls,
        origin: str,
        *,
        launch_token: str | None = None,
        cookie_file: Path | None = None,
        timeout_seconds: float = 15.0,
        secret_values: Sequence[str] = (),
    ) -> DshWebClient:
        """Authenticate an independent owner Peer and retain its revocable socket.

        Parameters
        ----------
        origin:
            Verified HTTP origin of an already owned loopback Host.
        launch_token:
            Private native launch token for an explicit new API connection.
        cookie_file:
            Optional private persisted API credential. Its socket must still be live.
        timeout_seconds:
            Bound for each wire operation; mutations are never retried.
        secret_values:
            Resolved provider credentials that must stay out of native error messages.
        """

        try:
            parsed = urlsplit(origin)
            loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
            port = parsed.port
        except ValueError:
            raise DshWebError("invalid_origin", "Managed Web origin is invalid") from None
        if (
            parsed.scheme != "http"
            or not loopback
            or port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or timeout_seconds <= 0
        ):
            raise DshWebError("invalid_origin", "Managed Web requires a loopback HTTP origin")
        client = cls()
        client.m_origin = origin.rstrip("/")
        client.m_timeout = timeout_seconds
        client.m_secret_values = (*secret_values, *((launch_token,) if launch_token else ()))
        client.m_http = httpx.Client(
            base_url=client.m_origin,
            timeout=timeout_seconds,
            trust_env=False,
            follow_redirects=False,
        )
        try:
            if launch_token is not None:
                response = client.m_http.get(
                    "/connect", params={"token": launch_token, "interactions": "none"}
                )
                if (
                    response.status_code != 302
                    or response.headers.get("location") != "./api/remote.mux"
                ):
                    raise DshWebError("authentication_failed", "Native API connection was refused")
            elif cookie_file is not None:
                if cookie_file.stat().st_mode & 0o077:
                    raise DshWebError("invalid_credentials", "API credential file must be private")
                payload = json.loads(cookie_file.read_text())
                if payload.get("version") != 1 or payload.get("origin") != client.m_origin:
                    raise DshWebError("invalid_credentials", "API credential origin does not match")
                client.m_http.cookies.update(payload["cookies"])
            else:
                raise DshWebError("missing_credentials", "Explicit API credentials are required")
            cookie = "; ".join(f"{entry.name}={entry.value}" for entry in client.m_http.cookies.jar)
            client.m_socket = connect(
                client.m_origin.replace("http://", "ws://", 1) + "/api/remote.mux",
                additional_headers={"Cookie": cookie},
                origin=Origin(client.m_origin),
                open_timeout=timeout_seconds,
                close_timeout=min(timeout_seconds, 5.0),
                proxy=None,
            )
            description = client.describe()
            if description.get("protocol_version") != 1:
                raise DshWebError("protocol_mismatch", "Managed Web protocol is incompatible")
            if cookie_file is not None and launch_token is not None:
                cookie_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                descriptor = os.open(cookie_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(descriptor, "w") as stream:
                    json.dump(
                        {
                            "version": 1,
                            "origin": client.m_origin,
                            "cookies": dict(client.m_http.cookies),
                        },
                        stream,
                    )
                cookie_file.chmod(0o600)
            return client
        except DshWebError:
            client.close()
            raise
        except Exception:
            client.close()
            raise DshWebError(
                "connection_unavailable", "Native API connection is unavailable"
            ) from None

    @property
    def origin(self) -> str:
        """Return the token-free verified origin."""

        return self.m_origin

    def close(self) -> None:
        """Release the owned socket, revoking this API Peer independently of the browser."""

        with self.m_lock:
            if self.m_socket is not None:
                try:
                    self.m_socket.close()
                finally:
                    self.m_socket = None
            if self.m_http is not None:
                self.m_http.close()
                self.m_http = None

    def call(self, method: str, payload: Mapping[str, Any]) -> Any:
        """Issue one native managed RPC exactly once; never replay a failed mutation."""

        with self.m_lock:
            if self.m_http is None or self.m_socket is None:
                raise DshWebError("connection_unavailable", "Native API connection is closed")
            submitted_cookies = tuple(entry.value or "" for entry in self.m_http.cookies.jar)
            rpc_id = str(uuid4())
            endpoint = f"managed/v1/{method}"
            try:
                response = self.m_http.post(
                    f"/houmao/{endpoint}",
                    json={
                        "type": "client-request",
                        "rpcId": rpc_id,
                        "method": endpoint,
                        "payload": {**payload, "protocol_version": 1},
                    },
                )
                if response.status_code in {401, 403}:
                    raise DshWebError(
                        "authentication_failed", "Native API authorization is unavailable"
                    )
                if response.status_code != 200:
                    raise DshWebError(
                        "transport_failure",
                        f"Native API request failed (HTTP {response.status_code})",
                    )
                envelope = response.json()
                if envelope.get("type") != "server-response" or envelope.get("rpcId") != rpc_id:
                    raise DshWebError(
                        "protocol_mismatch", "Native API response identity is invalid"
                    )
                result = envelope["result"]
                if result.get("ok") is not True:
                    error = result["error"]
                    raise DshWebError(
                        str(error["code"]),
                        str(error["message"]),
                        secret_values=(
                            *self.m_secret_values,
                            *submitted_cookies,
                            *(entry.value or "" for entry in self.m_http.cookies.jar),
                        ),
                    )
                return result["value"]
            except DshWebError:
                raise
            except Exception:
                raise DshWebError(
                    "outcome_uncertain",
                    "Native API response was lost; inspect the operation receipt",
                ) from None

    def describe(self) -> dict[str, Any]:
        """Read managed protocol capabilities without activating a conversation."""

        return cast(dict[str, Any], self.call("describe", {}))

    def lifecycle_start(
        self,
        *,
        mode: str,
        session_id: str | None = None,
        abandoned_operation_ids: Sequence[str] = (),
        identity: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Explicitly create or restore the selected conversation after reconciliation."""

        return cast(
            dict[str, Any],
            self.call(
                "start",
                {
                    "mode": mode,
                    "session_id": session_id,
                    "abandoned_operation_ids": list(abandoned_operation_ids),
                    "identity": identity,
                },
            ),
        )

    def state(self, identity: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Read a fresh native snapshot without cold activation."""

        return cast(dict[str, Any], self.call("state", {"identity": identity}))

    def observe_common_plugins(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        """Read source/runtime common-resource evidence without initiating reload."""

        return cast(dict[str, Any], self.call("common_state", {"identity": identity}))

    def refresh_common_plugins(
        self,
        identity: Mapping[str, Any],
        *,
        timeout_seconds: float,
        deadline_monotonic: float | None = None,
    ) -> dict[str, Any]:
        """Request one non-restarting native refresh, preserving its partial outcome."""

        if (
            not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or (deadline_monotonic is not None and not math.isfinite(deadline_monotonic))
        ):
            raise DshWebError(
                "invalid_request", "Native refresh timeout must be positive and finite"
            )
        deadline = min(
            deadline_monotonic if deadline_monotonic is not None else float("inf"),
            time.monotonic() + timeout_seconds,
        )
        if not math.isfinite(deadline):
            raise DshWebError("invalid_request", "Native refresh deadline must be finite")
        try:
            with self.m_lock:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise DshWebError("expired", "Native refresh deadline elapsed before handoff")
                return cast(
                    dict[str, Any],
                    self.call(
                        "refresh",
                        {
                            "identity": identity,
                            "timeout_seconds": remaining,
                            "deadline_monotonic_ms": deadline * 1000,
                        },
                    ),
                )
        except DshWebError as exc:
            if exc.code == "outcome_uncertain":
                raise DshWebError(
                    exc.code, "Native refresh response was lost; inspect common state"
                ) from None
            raise

    def history(
        self, identity: Mapping[str, Any], *, after_sequence: int = -1, limit: int = 100
    ) -> dict[str, Any]:
        """Read bounded payload-free native execution evidence."""

        return cast(
            dict[str, Any],
            self.call(
                "history", {"identity": identity, "after_sequence": after_sequence, "limit": limit}
            ),
        )

    def conversation(
        self,
        identity: Mapping[str, Any],
        *,
        after_native_sequence: int = -1,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Read committed native semantic content with a bounded exclusive input cursor."""

        return cast(
            dict[str, Any],
            self.call(
                "conversation",
                {
                    "identity": identity,
                    "after_native_sequence": after_native_sequence,
                    "limit": limit,
                },
            ),
        )

    def prompt(
        self,
        identity: Mapping[str, Any],
        text: str,
        *,
        operation_id: str,
        deadline_epoch_ms: int,
        admission_policy: str = "ready_only",
        operator: bool = False,
        dispatch_permission_path: Path | None = None,
    ) -> dict[str, Any]:
        """Attempt one conditional insertion, returning admission rather than completion."""

        return cast(
            dict[str, Any],
            self.call(
                "prompt",
                {
                    "identity": identity,
                    "text": text,
                    "operation_id": operation_id,
                    "deadline_epoch_ms": deadline_epoch_ms,
                    "admission_policy": admission_policy,
                    "operator": operator,
                    **(
                        {"dispatch_permission_path": str(dispatch_permission_path)}
                        if dispatch_permission_path is not None
                        else {}
                    ),
                },
            ),
        )

    def receipt(self, identity: Mapping[str, Any], operation_id: str) -> dict[str, Any] | None:
        """Inspect existing admission metadata without resubmitting text."""

        return cast(
            dict[str, Any] | None,
            self.call("receipt", {"identity": identity, "operation_id": operation_id}),
        )

    def interrupt(
        self,
        identity: Mapping[str, Any],
        *,
        turn_start_seq: int | None,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        """Cancel only the captured active turn or remove this operation's pending input."""

        return cast(
            dict[str, Any],
            self.call(
                "interrupt",
                {
                    "identity": identity,
                    "turn_start_seq": turn_start_seq,
                    "operation_id": operation_id,
                },
            ),
        )

    def stop(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        """Dispose only the bound native Agent owned by this companion."""

        return cast(dict[str, Any], self.call("stop", {"identity": identity}))

    def lifecycle_reset(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        """Reset only after a native atomic true-idle, empty-inbox admission claim."""

        return cast(
            dict[str, Any],
            self.call("reset", {"identity": identity, "admission_policy": "ready_only"}),
        )

    def set_model(
        self,
        identity: Mapping[str, Any],
        *,
        provider: str,
        model: str,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        """Apply only an explicit operator model selection to the exact live Agent."""

        return cast(
            dict[str, Any],
            self.call(
                "set_model",
                {
                    "identity": identity,
                    "provider": provider,
                    "model": model,
                    "reasoning_effort": reasoning_effort,
                },
            ),
        )
