"""Qualify CCCC chat with two real fixture-launched coding agents.

Run with an external environment containing independently installed Houmao and
houmao-cccc wheels. Model credentials and native output remain in private runs.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import sys
import time
import traceback
from typing import Any
import uuid

import httpx


class SmokeError(RuntimeError):
    """Report a safe qualification failure without native diagnostic contents."""


def _require(value: bool, message: str) -> None:
    """Reject a failed contract without echoing credentials or provider responses."""

    if not value:
        raise SmokeError(message)


def _result(response: httpx.Response) -> dict[str, Any]:
    """Extract a successful provider envelope without leaking response contents."""

    _require(response.status_code == 200, f"CCCC returned HTTP {response.status_code}")
    value = response.json()
    _require(value.get("ok") is True, "CCCC operation failed")
    return dict(value["result"])


def _wait(callback: Any, timeout: float, message: str) -> Any:
    """Poll an explicit bounded observation without issuing chat mutations."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = callback()
        if value:
            return value
        time.sleep(0.5)
    raise SmokeError(message)


def _exchange(
    mode: str,
    cli: Path,
    gateways: list[str],
    bindings: list[dict[str, Any]],
    run_paths: list[Path],
    marker: str,
    timeout: float,
    prompt_run: Any,
) -> dict[str, Any]:
    """Ask real agents to send and reply, with an explicit agent-authored Mail read."""

    prefix = "/v1/plugins/cccc"
    before: dict[str, Any] | None = None
    if mode == "mail":
        response = httpx.get(gateways[1] + prefix + "/mail/cursor", trust_env=False, timeout=20)
        _require(response.status_code == 200, "Qualified Mail cursor is unavailable")
        before = response.json()
        authority = ["--binding-id", bindings[0]["binding_id"]]
    else:
        response = httpx.get(gateways[0] + prefix + "/members", trust_env=False, timeout=20)
        _require(response.status_code == 200, "Qualified chat membership is unavailable")
        token = response.json().get("connection_token")
        _require(
            isinstance(token, str) and bool(token), "Qualified chat connection token is unavailable"
        )
        authority = ["--connection-token", token]
    command = [
        str(cli),
        "--gateway-url",
        gateways[0],
        mode,
        "send",
        *authority,
        "--operation-id",
        marker,
        "--to",
        "receiver",
        "--text",
        f"Please reply with exactly this marker: {marker}.",
    ]
    if mode == "chat":
        command.extend(["--mode", "request_reply"])
    prompt_run(
        run_paths[0],
        prompt="Run this command using a shell tool, then finish your turn immediately. "
        "Do not poll or wait for the peer.\n" + shlex.join(command),
        timeout=timeout,
    )
    read_operation = "read-" + marker
    if mode == "mail":
        assert before is not None
        peek_response = httpx.get(
            gateways[1] + prefix + "/mail/peek", params={"limit": 1}, trust_env=False, timeout=20
        )
        _require(peek_response.status_code == 200, "Deferred Mail inspection failed")
        peek = peek_response.json()
        _require(
            peek.get("consumed") is False and len(peek.get("messages", [])) == 1,
            "Mail did not remain pending before the explicit agent read",
        )
        _require(
            peek["cursor"]["event_id"] == before["cursor"]["event_id"],
            "Mail was consumed before the explicit real-agent read",
        )
        _wait(
            lambda: (
                httpx.get(gateways[1] + "/v1/control/headless/state", trust_env=False, timeout=20)
                .json()
                .get("can_accept_prompt_now")
                is True
            ),
            timeout,
            "Real recipient did not become ready for explicit Mail work",
        )
        read_command = [
            str(cli),
            "--gateway-url",
            gateways[1],
            "mail",
            "read",
            "--binding-id",
            bindings[1]["binding_id"],
            "--operation-id",
            read_operation,
            "--expected-cursor",
            before["cursor_ref"],
            "--limit",
            "1",
            "--max-bytes",
            "262144",
        ]
        reply_prefix = [
            str(cli),
            "--gateway-url",
            gateways[1],
            "mail",
            "reply",
            "--binding-id",
            bindings[1]["binding_id"],
            "--operation-id",
            "reply-" + marker,
        ]
        prompt_run(
            run_paths[1],
            prompt="Explicitly read your next deferred CCCC Mail batch by executing "
            "the following CLI command with a shell tool. Inspect the complete result, then author "
            "a Mail reply using the returned messages[0].event_ref and the reply command prefix "
            "below. Add --event-ref with that returned handle and --text containing exactly the "
            f"marker {marker}. Do not use chat reply or read another batch.\nREAD: "
            + shlex.join(read_command)
            + "\nREPLY PREFIX: "
            + shlex.join(reply_prefix),
            timeout=timeout,
        )

    def observed_reply() -> dict[str, Any] | None:
        """Read native history without manufacturing either real agent's event."""

        response = httpx.get(
            gateways[0] + prefix + "/chat/history",
            params={"limit": 100},
            trust_env=False,
            timeout=20,
        )
        if response.status_code != 200:
            return None
        messages = response.json().get("messages", [])
        sent = next(
            (
                e
                for e in messages
                if e.get("by") == "sender" and marker in e.get("data", {}).get("text", "")
            ),
            None,
        )
        if sent is None:
            return None
        reply = next(
            (
                e
                for e in messages
                if e.get("by") == "receiver"
                and e.get("data", {}).get("reply_to") == sent["id"]
                and marker in e.get("data", {}).get("text", "")
            ),
            None,
        )
        return {"sent": sent, "reply": reply} if reply else None

    observed = _wait(observed_reply, timeout, "No real agent-authored reply observed")
    result: dict[str, Any] = {
        "result": "passed",
        "native_event_id": observed["sent"]["id"],
        "native_reply_event_id": observed["reply"]["id"],
        "reply_to": observed["reply"]["data"]["reply_to"],
        "agent_authored_reply": True,
    }
    if mode == "chat":
        receipts = httpx.get(
            gateways[0] + prefix + "/chat/deliveries",
            params={"event_ref": observed["sent"]["event_ref"]},
            trust_env=False,
            timeout=20,
        ).json()
        _require(
            any(
                r.get("actor_id") == "receiver" and r.get("state") == "accepted"
                for r in receipts["deliveries"]
            ),
            "Real-agent ordinary handoff was not confirmed",
        )
        result["ordinary_handoff"] = "accepted"
    else:
        assert before is not None
        receipt_response = httpx.get(
            gateways[1] + prefix + "/mail/reads/" + read_operation, trust_env=False, timeout=20
        )
        _require(receipt_response.status_code == 200, "Real-agent read receipt is unavailable")
        receipt = receipt_response.json().get("receipt", {})
        _require(
            receipt.get("outcome") == "consumed"
            and receipt.get("event_ids") == [observed["sent"]["id"]],
            "Real agent did not explicitly consume the selected Mail batch",
        )
        _require(
            receipt["before_cursor"] == before["cursor"]["event_id"]
            and receipt["after_cursor"] == observed["sent"]["id"],
            "Real-agent Mail cursor did not advance through the consumed event",
        )
        _require(
            all(observed[key]["data"].get("message_mode") == "mail" for key in ("sent", "reply")),
            "Real agents did not preserve deferred Mail mode",
        )
        result.update(
            deferred_mode="mail",
            agent_authored_explicit_read=True,
            cursor_before=receipt["before_cursor"],
            cursor_after=receipt["after_cursor"],
            read_operation_id=read_operation,
            native_read_event_id=receipt["read_event_id"],
        )
    return result


def qualify(arguments: argparse.Namespace) -> dict[str, Any]:
    """Launch real bodies, attach installed plugins, and verify an authored reply."""

    import houmao
    import houmao_cccc

    source = arguments.source_root.resolve()
    work = arguments.work_root.expanduser().resolve()
    _require(not work.is_relative_to(source), "Real-agent state must be outside the checkout")
    prefix = Path(sys.prefix).resolve()
    for module in (houmao, houmao_cccc):
        origin = Path(module.__file__ or "").resolve()
        _require(origin.is_relative_to(prefix), "Require independently installed wheels")
        _require(not origin.is_relative_to(source), "Checkout imports are forbidden")
    _require(not work.exists(), "Select a fresh private real-agent work root")
    work.mkdir(parents=True, mode=0o700)
    sys.path.insert(0, str(source / "scripts/agents/test-fixtures"))
    from fixturelib.auth import write_json
    from fixturelib.config import resolve_config
    from fixturelib.launch import launch_run, prompt_run, run_environment, stop_run
    from fixturelib.prepare import load_run, manager_root_call, prepare_run

    cli = prefix / "bin/houmao-cccc"
    _require(cli.is_file(), "Installed CCCC CLI is missing")
    config = resolve_config(
        case=arguments.case,
        client=arguments.client,
        model=arguments.model,
        env_file=arguments.env_file.resolve(),
    )
    role = work / "role.md"
    role.write_text(
        "You are a coding agent participating in a real CCCC integration smoke. "
        "Perform requested local tool commands. The incoming CCCC request fence contains a "
        "messages list. For each entry with mode=request_reply, wait 8 seconds using a shell "
        "tool, then author a reply with the requested marker using the local plugin POST "
        "/chat/reply from the header or installed CLI chat reply. Use that entry's handle "
        "and a fresh operation_id. Do not look for provider "
        "credentials or use CCCC administrator/MCP interfaces. "
        "A content-free CCCC Mail notice does not ask you to read Mail yet. Acknowledge "
        "the notice and finish; consume Mail only when the operator explicitly asks. "
        f"The installed CLI is {cli}.\n"
    )
    marker = "cccc-real-" + uuid.uuid4().hex
    run_paths: list[Path] = []
    gateways: list[str] = []
    bindings: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    group_id: str | None = None
    report: dict[str, Any] = {
        "result": "failed",
        "kind": "two-real-coding-agent-" + arguments.mode,
        "profile": config.summary(),
        "houmao_version": importlib.metadata.version("houmao"),
        "plugin_version": importlib.metadata.version("houmao-cccc"),
        "protocol_version": 2,
    }
    endpoint = arguments.endpoint.rstrip("/")
    _require(endpoint.startswith("http://127.0.0.1:"), "Select the dedicated loopback service")
    with httpx.Client(
        base_url=endpoint,
        headers={"Origin": endpoint, "Referer": endpoint + "/"},
        trust_env=False,
        follow_redirects=False,
        timeout=30,
    ) as provider:
        try:
            group_id = _result(
                provider.post("/api/v1/groups", json={"title": "real-agent-smoke-" + marker})
            )["group_id"]
            for actor_id in ("sender", "receiver"):
                prepared = prepare_run(
                    config, run_root=work / "runs", prompt_file=role, tmux_server="new"
                )
                run_path = Path(prepared["run_dir"])
                run_paths.append(run_path)
                launch_run(run_path)
                run = load_run(run_path)
                owner = run["identity"]["agent_id"]
                _result(
                    provider.post(
                        f"/api/v1/groups/{group_id}/actors",
                        json={"actor_id": actor_id, "runtime": "custom", "command": ["/bin/true"]},
                    )
                )
                grant = _result(
                    provider.post(
                        "/api/v1/external-receiver/v2/grants",
                        json={"group_id": group_id, "actor_id": actor_id},
                    )
                )
                credential = run_path / "cccc-actor.json"
                write_json(
                    credential,
                    {
                        "schema_version": 1,
                        "agent_id": owner,
                        "endpoint": endpoint,
                        "group_id": group_id,
                        "actor_id": actor_id,
                        "actor_generation": grant["actor_generation"],
                        "token": grant["token"],
                    },
                )
                selection = run_path / "plugins.json"
                write_json(
                    selection,
                    {
                        "schema_version": 1,
                        "gateway": {
                            "plugins": {
                                "cccc": {
                                    "implementation": "cccc",
                                    "credential_ref": {"file": str(credential)},
                                    "config": {
                                        "endpoint": endpoint,
                                        "group_id": group_id,
                                        "actor_id": actor_id,
                                        "actor_generation": grant["actor_generation"],
                                    },
                                }
                            }
                        },
                    },
                )
                scope = ["agents", "single", "--agent-id", owner, "gateway"]
                env = run_environment(run)
                manager_root_call([*scope, "detach"], env=env)
                attached = manager_root_call(
                    [*scope, "attach", "--background", "--plugins-config", str(selection)], env=env
                )
                run["identity"].update(
                    gateway_host=attached["gateway_host"], gateway_port=attached["gateway_port"]
                )
                write_json(run_path / "run.json", run)
                base = f"http://{attached['gateway_host']}:{attached['gateway_port']}"
                gateways.append(base)

                def connected() -> dict[str, Any] | None:
                    """Inspect maintained plugin state without provider mutation."""

                    response = httpx.get(base + "/v1/plugins/cccc/binding", trust_env=False)
                    if response.status_code != 200:
                        return None
                    binding = response.json()
                    return binding if binding.get("connection") == "connected" else None

                bindings.append(_wait(connected, 60, "Real-agent receiver did not connect"))
                reports.append(
                    {
                        "agent_id": owner,
                        "actor_id": actor_id,
                        "client_version": run.get("client_version"),
                    }
                )
            _require(reports[0]["agent_id"] != reports[1]["agent_id"], "Owners must be distinct")
            report.update(
                _exchange(
                    arguments.mode,
                    cli,
                    gateways,
                    bindings,
                    run_paths,
                    marker,
                    arguments.timeout,
                    prompt_run,
                ),
                agents=reports,
            )
        finally:
            cleanup = []
            for run_path in reversed(run_paths):
                try:
                    cleanup.append(stop_run(run_path).get("cleanup"))
                except Exception:
                    cleanup.append("failed_requires_scoped_follow_up")
            if group_id is not None:
                deleted = provider.delete(f"/api/v1/groups/{group_id}")
                report["group_cleanup"] = deleted.status_code == 200
            report["agent_cleanup"] = cleanup
            write_json(work / "qualification.json", report)
    _require(all(c == "stopped_owned_identity" for c in cleanup), "Real-agent cleanup failed")
    _require(report.get("group_cleanup") is True, "Owned CCCC Group cleanup failed")
    return report


def main() -> None:
    """Run explicit installed-wheel qualification with secret-safe diagnostics."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--work-root", required=True, type=Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--case", choices=("cloud-api", "self-hosted"), default="cloud-api")
    parser.add_argument("--client", choices=("claude", "codex", "kimi"), default="claude")
    parser.add_argument("--model", required=True)
    parser.add_argument("--mode", choices=("chat", "mail"), default="chat")
    parser.add_argument("--timeout", type=float, default=300)
    arguments = parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(qualify(arguments), indent=2))
    except Exception as exc:
        # Native diagnostics may include provider input. Keep them in private run
        # artifacts; only the fixed error class is emitted by this driver.
        if arguments.work_root.is_dir():
            diagnostic = arguments.work_root / "driver-error.txt"
            diagnostic.write_text(traceback.format_exc())
            diagnostic.chmod(0o600)
        print(
            json.dumps(
                {
                    "result": "failed",
                    "error_type": type(exc).__name__,
                    "private_report": str(arguments.work_root / "qualification.json"),
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
