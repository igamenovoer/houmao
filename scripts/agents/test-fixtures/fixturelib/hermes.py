"""Exercise stock Hermes clients inside run-owned fixture state."""

from __future__ import annotations

from contextlib import ExitStack
import json
import os
from pathlib import Path
import signal
import socket
import sys
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from houmao.agents.realm_controller.backends.dsh_acp_connection import DshAcpConnection  # noqa: E402
from houmao.agents.realm_controller.backends.hermes_native import HermesDaemon  # noqa: E402
from fixturelib.auth import write_json  # noqa: E402
from fixturelib.config import FixtureError  # noqa: E402

ACP_SOCKET = "raw-acp.sock"
ACP_READY = "raw-acp-ready.json"
_MAX_FRAME = 1024 * 1024


def raw_hermes_daemon(run: dict[str, Any], env: dict[str, str]) -> HermesDaemon:
    """Resolve native process control for this fixture's exact private home."""

    return HermesDaemon.from_inputs(
        executable=run["executable"],
        home=Path(run["home_path"]),
        workspace=Path(run["workdir"]),
        env=env,
        root=Path(run["run_dir"]),
    )


def raw_hermes_result(path: Path, prior: str | None) -> str | None:
    """Read exact successful settlement from a stock one-shot JSONL stream."""

    try:
        with path.open(encoding="utf-8") as stream:
            result = None
            for line in stream:
                frame = json.loads(line)
                if result is not None or not isinstance(frame, dict):
                    return None
                if frame.get("type") == "result":
                    result = frame
    except (OSError, UnicodeError, ValueError):
        return None
    if result is None or result.get("exit_code") != 0 or result.get("error"):
        return None
    session = result.get("session_id")
    return session if isinstance(session, str) and session and prior in {None, session} else None


def raw_acp_prompt(run: dict[str, Any], prompt: str, timeout: float) -> dict[str, str]:
    """Send one plain prompt to the stock ACP worker started for this run."""

    path = Path(run["run_dir"])
    directory_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(timeout + 1)
            # Resolve the pathname through a directory fd to keep the AF_UNIX
            # address short, even when the operator selects a long run root.
            connection.connect(f"/proc/self/fd/{directory_fd}/{ACP_SOCKET}")
            with connection.makefile("rwb") as stream:
                body = json.dumps({"prompt": prompt, "timeout": timeout}).encode()
                if len(body) >= _MAX_FRAME:
                    raise FixtureError("Raw ACP fixture prompt exceeds its frame limit")
                stream.write(body + b"\n")
                stream.flush()
                result = json.loads(stream.readline(_MAX_FRAME))
                if not isinstance(result, dict) or result.get("status") != "completed":
                    raise FixtureError("Raw ACP prompt failed; inspect private ACP artifacts")
                return result
    except (OSError, ValueError) as exc:
        raise FixtureError("Raw ACP fixture connection failed; inspect private artifacts") from exc
    finally:
        os.close(directory_fd)


def _request_prompt(connection: DshAcpConnection, session: str, stream: Any) -> None:
    """Validate one fixture request and report only its observed settlement."""

    response = {"status": "failed"}
    try:
        request = json.loads(stream.readline(_MAX_FRAME))
        prompt, timeout = request["prompt"], request["timeout"]
        if not isinstance(prompt, str) or not 0 < timeout <= 3600:
            raise ValueError("Invalid ACP fixture request")
        result = connection.request(
            "session/prompt",
            {"sessionId": session, "prompt": [{"type": "text", "text": prompt}]},
        ).result(timeout=timeout)
        reason = result.get("stopReason")
        if reason in {"end_turn", "max_tokens", "max_turn_requests"}:
            response = {
                "status": "completed",
                "stop_reason": reason,
                "provider_session_id": session,
            }
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        pass
    stream.write((json.dumps(response) + "\n").encode())
    stream.flush()


def serve_raw_acp(run: dict[str, Any], environment: dict[str, str]) -> None:
    """Own one native ACP process and keep its protocol captures private."""

    root = Path(run["run_dir"])
    os.umask(0o077)
    os.chdir(root)

    def stop(_signal: int, _frame: object) -> None:
        """Close the native process on this fixture worker's termination."""

        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        with ExitStack() as stack:
            log = stack.enter_context(
                (root / "raw-acp.jsonl").open("x", encoding="utf-8", buffering=1)
            )
            stderr = stack.enter_context(
                (root / "raw-acp.stderr").open("x", encoding="utf-8", buffering=1)
            )
            connection = DshAcpConnection.from_command(
                [run["executable"], "acp"],
                cwd=Path(run["workdir"]),
                env=environment,
                frame_sink=lambda line: log.write(line.rstrip("\n") + "\n"),
                stderr_sink=stderr.write,
                retain_notifications=False,
                write_timeout=5,
            )
            stack.callback(connection.close)
            initialized = connection.request(
                "initialize", {"protocolVersion": 1, "clientCapabilities": {}}
            ).result(timeout=30)
            if initialized.get("protocolVersion") != 1:
                raise FixtureError("Unexpected stock Hermes ACP protocol")
            opened = connection.request(
                "session/new", {"cwd": run["workdir"], "mcpServers": []}
            ).result(timeout=30)
            session = opened.get("sessionId")
            if not isinstance(session, str) or not session:
                raise FixtureError("Stock Hermes ACP did not provide a session identity")
            raw_hermes_daemon(run, environment).resolve_session(session)

            listener = stack.enter_context(socket.socket(socket.AF_UNIX))
            listener.bind(ACP_SOCKET)
            listener.listen()
            listener.settimeout(0.2)
            stack.callback((root / ACP_SOCKET).unlink, missing_ok=True)
            write_json(root / ACP_READY, {"provider_session_id": session, "protocol_version": 1})
            while connection.healthy:
                try:
                    client, _ = listener.accept()
                except TimeoutError:
                    continue
                with client:
                    client.settimeout(3)
                    try:
                        with client.makefile("rwb") as stream:
                            _request_prompt(connection, session, stream)
                    except OSError:
                        continue
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    from fixturelib.launch import run_environment
    from fixturelib.prepare import load_run

    prepared = load_run(Path(sys.argv[1]))
    serve_raw_acp(prepared, run_environment(prepared))
