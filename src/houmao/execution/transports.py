"""Finite native execution transports with bounded output and no mutation replay."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import threading
from typing import BinaryIO

from houmao.execution.models import (
    ExecutionProfileV1,
    ExecutionRequestV1,
    ExecutionResponseV1,
    route_fingerprint,
)
from houmao.execution.protocol import (
    MAX_RESPONSE_BYTES,
    ExecutionProtocolError,
    decode_response,
    encode_request,
)

_TRANSPORT_PATH = "/usr/local/bin:/usr/bin:/bin"
_MAX_STDERR_BYTES = 65_536


def transport_environment() -> dict[str, str]:
    """Construct a minimal native transport environment without caller runtime state."""

    return {"PATH": _TRANSPORT_PATH, "LANG": "C", "LC_ALL": "C"}


def build_transport_argv(profile: ExecutionProfileV1) -> list[str]:
    """Build a fixed native entrypoint command without interpreting operation data.

    Parameters
    ----------
    profile : ExecutionProfileV1
        Trusted route configuration, already validated independently of project data.

    Returns
    -------
    list[str]
        Native process arguments. Variable request values are sent only on stdin.
    """

    helper = [
        profile.entrypoint,
        "internals",
        "executor",
        "serve-stdio",
        "--policy",
        profile.policy_path,
    ]
    if profile.transport == "local":
        return helper
    if profile.transport == "sudo":
        return [_native("sudo"), "-n", "-H", "-u", profile.account, "--", *helper]
    if profile.transport == "docker":
        assert profile.container_id is not None
        return [
            _native("docker"),
            "exec",
            "-i",
            "--user",
            profile.account,
            profile.container_id,
            *helper,
        ]
    assert profile.transport == "ssh"
    assert profile.ssh_host is not None and profile.known_hosts_file is not None
    argv = [
        _native("ssh"),
        "-F",
        "/dev/null",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={profile.known_hosts_file}",
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        "-o",
        "PermitLocalCommand=no",
        "-p",
        str(profile.ssh_port),
    ]
    if profile.identity_file is not None:
        argv.extend(("-i", profile.identity_file))
    argv.extend(("-l", profile.account, "--", profile.ssh_host, shlex.join(helper)))
    return argv


def execute_request(
    profile: ExecutionProfileV1, request: ExecutionRequestV1
) -> ExecutionResponseV1:
    """Execute one request once, retaining uncertainty when the result is unavailable.

    Parameters
    ----------
    profile : ExecutionProfileV1
        Trusted configured route; authentication references remain operator-local.
    request : ExecutionRequestV1
        Bounded operation whose owner performs final policy and authority admission.

    Returns
    -------
    ExecutionResponseV1
        Correlated owner result or safe rejection/indeterminate transport result.
        Transport errors never replay a request or expose native stderr contents.
    """

    fingerprint = route_fingerprint(profile)
    if request.expected_route_fingerprint not in {None, fingerprint}:
        return _failure(request, "context_mismatch", admitted=False)
    request = request.model_copy(update={"expected_route_fingerprint": fingerprint})
    if (
        request.expected_binding is not None
        and request.expected_binding.route_fingerprint != fingerprint
    ):
        return _failure(request, "context_mismatch", admitted=False)
    try:
        payload = encode_request(request)
        argv = build_transport_argv(profile)
    except (ExecutionProtocolError, FileNotFoundError):
        return _failure(request, "transport_unavailable", admitted=False)
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=transport_environment(),
            close_fds=True,
        )
    except OSError:
        return _failure(request, "transport_unavailable", admitted=False)

    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    output = bytearray()
    diagnostics = bytearray()
    overflow = threading.Event()

    def read_bounded(stream: BinaryIO, buffer: bytearray, limit: int) -> None:
        """Drain a native pipe while bounding memory and terminating only this helper."""

        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    return
                available = limit - len(buffer)
                buffer.extend(chunk[:available])
                if len(chunk) > available:
                    overflow.set()
                    _terminate(process)
                    return
        finally:
            stream.close()

    def write_request() -> None:
        """Send finite input concurrently so a non-reading helper cannot block the deadline."""

        assert process.stdin is not None
        try:
            process.stdin.write(payload)
            process.stdin.flush()
        except (OSError, ValueError):
            pass
        finally:
            process.stdin.close()

    threads = [
        threading.Thread(
            target=read_bounded, args=(process.stdout, output, MAX_RESPONSE_BYTES), daemon=True
        ),
        threading.Thread(
            target=read_bounded, args=(process.stderr, diagnostics, _MAX_STDERR_BYTES), daemon=True
        ),
        threading.Thread(target=write_request, daemon=True),
    ]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        process.wait(timeout=min(profile.timeout_seconds, request.deadline_seconds))
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate(process)
    finally:
        # Transport grandchildren may retain inherited pipes. Do not wait unboundedly for them.
        for thread in threads:
            thread.join(timeout=0.25)
    if timed_out:
        return _failure(request, "transport_timeout", admitted=None)
    if overflow.is_set():
        return _failure(request, "transport_output_limit", admitted=None)
    if any(thread.is_alive() for thread in threads):
        return _failure(request, "transport_incomplete_result", admitted=None)
    try:
        response = decode_response(bytes(output))
    except ExecutionProtocolError:
        if _native_refusal(profile, process.returncode, bytes(diagnostics)):
            return _failure(request, "transport_authorization_failed", admitted=False)
        return _failure(request, "transport_invalid_result", admitted=None)
    if response.request_id != request.request_id:
        return _failure(request, "transport_uncorrelated_result", admitted=None)
    if response.binding is not None and response.binding.route_fingerprint != route_fingerprint(
        profile
    ):
        return _failure(request, "transport_binding_mismatch", admitted=None)
    if process.returncode != 0:
        # A valid owner rejection is useful; any claimed success with failed transport is uncertain.
        if response.outcome != "rejected":
            return _failure(request, "transport_failed_result", admitted=None)
    return response


def _native(name: str) -> str:
    """Resolve only administrator-installed native tools through a fixed system path."""

    executable = shutil.which(name, path=_TRANSPORT_PATH)
    if executable is None:
        raise FileNotFoundError("Native execution transport is not installed")
    return executable


def _terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop only this transport process, never a server, session, or process group."""

    try:
        process.terminate()
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            # An OS-authorized transport can have a privileged monitor. Failure
            # to signal it never establishes rollback or permits a retry.
            pass
    except OSError:
        pass


def _failure(
    request: ExecutionRequestV1, code: str, *, admitted: bool | None
) -> ExecutionResponseV1:
    """Return a correlation-safe failure without reproducing command/input/credential data."""

    return ExecutionResponseV1(
        request_id=request.request_id,
        outcome="rejected" if admitted is False else "indeterminate",
        admitted=admitted,
        error_code=code,
        error_message=(
            "Execution transport rejected the request before owner admission."
            if admitted is False
            else "Execution result is indeterminate; inspect the owner before any deliberate retry."
        ),
    )


def _native_refusal(profile: ExecutionProfileV1, returncode: int | None, stderr: bytes) -> bool:
    """Recognize native refusals known to occur before the fixed helper can execute."""

    if returncode == 0:
        return False
    if profile.transport == "sudo":
        return stderr.startswith(b"sudo:") and any(
            marker in stderr
            for marker in (
                b"a password is required",
                b"not allowed to execute",
                b"not in the sudoers",
                b"unknown user",
                b"authentication failure",
            )
        )
    if profile.transport == "ssh":
        return any(
            marker in stderr
            for marker in (
                b"Host key verification failed",
                b"Permission denied (",
                b"Could not resolve hostname",
                b"Connection refused",
                b"Connection timed out",
            )
        )
    return False
