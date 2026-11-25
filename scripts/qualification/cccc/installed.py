"""Qualify installed CCCC plugin wheels against an explicitly selected real service.

Preparation can download dependencies. Qualification installs from the selected
wheelhouse only and copies its utility runner outside the source checkout.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import hashlib
import http.client
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import sysconfig
import tempfile
import time
import traceback
from types import ModuleType
from typing import Any
from urllib.parse import urlencode
from urllib.parse import urlsplit
import uuid


class QualificationError(RuntimeError):
    """Describe a safe setup or observed-contract failure."""


def _support(path: Path) -> ModuleType:
    """Load an explicit qualification utility, never production source by import path."""

    spec = importlib.util.spec_from_file_location("cccc_installed_support", path)
    if spec is None or spec.loader is None:
        raise QualificationError("Qualification support utility is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require(value: bool, message: str) -> None:
    """Fail without printing service responses, credentials, or message bodies."""

    if not value:
        raise QualificationError(message)


def _root(path: Path, source: Path) -> Path:
    """Require credential-bearing environments and runs outside the checkout."""

    resolved = path.resolve()
    _require(
        not resolved.is_relative_to(source), "Qualification state must be outside the checkout"
    )
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    return resolved


def _wheels(wheelhouse: Path) -> list[Path]:
    """Require one wheel for each independently installed artifact."""

    result = []
    for pattern in (
        "houmao-*.whl",
        "houmao_cccc-*.whl",
        "houmao_gateway_qualification_fixtures-*.whl",
    ):
        selected = sorted(wheelhouse.glob(pattern))
        _require(len(selected) == 1, "Setup requires exactly one wheel matching " + pattern)
        result.append(selected[0])
    return result


def prepare(source: Path, wheelhouse: Path) -> dict[str, object]:
    """Build independently installable artifacts and prepare their dependency wheelhouse."""

    support = _support(source / "scripts/qualification/gateway-plugins/qualify.py")
    environment = support._clean_environment()
    log = wheelhouse / "prepare.log"
    for project in (
        source,
        source / "packages/houmao-cccc",
        source / "tests/fixtures/gateway-plugins/fixture-package",
    ):
        support._run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(wheelhouse), str(project)],
            cwd=wheelhouse,
            env=environment,
            log=log,
        )
    support._run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--dest",
            str(wheelhouse),
            *(str(wheel) for wheel in _wheels(wheelhouse)),
        ],
        cwd=wheelhouse,
        env=environment,
        log=log,
    )
    return {
        "result": "passed",
        "action": "prepare",
        "wheel_count": len(list(wheelhouse.glob("*.whl"))),
    }


def qualify(
    source: Path,
    wheelhouse: Path,
    work: Path,
    endpoint: str,
    *,
    mail_recovery: bool = False,
) -> dict[str, object]:
    """Install wheels offline and execute the copied runner with isolated import paths."""

    support_path = source / "scripts/qualification/gateway-plugins/qualify.py"
    support = _support(support_path)
    artifacts = [
        {"filename": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}
        for wheel in _wheels(wheelhouse)
    ]
    _require(not (work / "venv").exists(), "Setup requires a fresh external work root")
    real_tmux = shutil.which("tmux")
    _require(real_tmux is not None, "Setup requires a real tmux executable")
    environment = support._clean_environment()
    log = work / "operations.log"
    support._run(
        [sys.executable, "-m", "venv", str(work / "venv")], cwd=work, env=environment, log=log
    )
    python = work / "venv/bin/python"
    support._run(
        [
            str(python),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "Houmao",
            "houmao-cccc",
            "houmao-gateway-qualification-fixtures",
        ],
        cwd=work,
        env=environment,
        log=log,
    )
    runner = work / "installed_runner.py"
    shutil.copyfile(Path(__file__).resolve(), runner)
    shutil.copyfile(support_path, work / "gateway_support.py")
    environment["PATH"] = str(work / "venv/bin") + os.pathsep + environment.get("PATH", "")
    support._bind_fixture_tmux_executable(work, str(real_tmux))
    environment["HOUMAO_PLUGIN_FIXTURE_REAL_TMUX"] = str(real_tmux)
    environment["HOUMAO_GLOBAL_REGISTRY_DIR"] = str(work / "registry")
    environment["XDG_CONFIG_HOME"] = str(work / "config")
    with tempfile.TemporaryDirectory(prefix="hcc-", dir="/tmp") as socket_root:
        environment["TMUX_TMPDIR"] = socket_root
        support._prepare_isolated_socket(socket_root)
        try:
            support._run(
                [
                    str(python),
                    "-I",
                    str(runner),
                    "installed-mail-run" if mail_recovery else "installed-run",
                    "--source-root",
                    str(source),
                    "--work-root",
                    str(work),
                    "--endpoint",
                    endpoint,
                ],
                cwd=work,
                env=environment,
                log=log,
            )
        finally:
            support._cleanup_isolated_tmux(python, cwd=work, environment=environment)
    result = json.loads((work / "qualification.json").read_text())
    result["artifacts"] = artifacts
    result["environment"] = {
        "python": str(python),
        "cli": str(work / "venv/bin/houmao-cccc"),
        "retained": True,
    }
    (work / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    return dict(result)


def _provider_result(response: Any) -> dict[str, Any]:
    """Extract provider setup results without echoing private grant material."""

    _require(response.status_code == 200, "Provider setup request failed")
    document = response.json()
    _require(document.get("ok") is True, "Provider setup envelope failed")
    return dict(document["result"])


def _body_snapshot(support: ModuleType, controller: Any) -> tuple[str, object]:
    """Read the live owned pane PID and persisted native conversation identifier."""

    document = json.loads(controller.manifest_path.read_text())
    pane = document["agent_launch_authority"]["primary_pane_id"]
    process = support._tmux_server().checked_command(
        ["display-message", "-p", "-t", pane, "#{pane_pid}"],
    )
    return process.stdout.strip(), document["backend_state"]["session_id"]


def _invocations(root: Path) -> int:
    """Count native body launches without retaining the dispatched text."""

    path = root / "invocations"
    return int(path.read_text()) if path.exists() else 0


def _cleanup_runtime(support: ModuleType, controller: Any) -> None:
    """Clean only recorded owned test processes, including already-replaced bodies."""

    instance = controller.gateway_root / "run/current-instance.json"
    pid: int | None = None
    if instance.exists():
        document = json.loads(instance.read_text())
        if type(document.get("pid")) is int:
            pid = document["pid"]
    try:
        controller.stop(force_cleanup=True)
    except Exception:
        pass
    server = support._tmux_server()
    server.command(["kill-session", "-t", f"={controller.tmux_session_name}"])
    if pid is not None and support._process_alive(pid):
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        except FileNotFoundError:
            command = []
        _require(
            not support._process_alive(pid)
            or (
                b"houmao.agents.realm_controller.gateway_service" in command
                and os.fsencode(controller.gateway_root) in command
            ),
            "Cleanup refused a process outside the owned gateway identity",
        )
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 5
        while support._process_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        if support._process_alive(pid):
            os.kill(pid, signal.SIGKILL)
        support._wait(lambda: not support._process_alive(pid), "Owned gateway survived cleanup")
    _require(
        controller.tmux_session_name not in server.list_sessions(allow_missing_server=True),
        "Owned body session survived cleanup",
    )


def _record_live_gateway(
    support: ModuleType,
    controller: Any,
    gateway: dict[str, Any],
) -> None:
    """Bind fresh clients to the live listener and its current owner generation."""

    state = controller.gateway_status()
    _require(
        state.gateway_host == ("0.0.0.0" if gateway.get("seeded_admin") else "127.0.0.1")
        and state.gateway_port is not None,
        "Gateway did not publish the expected resolved listener",
    )
    gateway["url"] = f"http://127.0.0.1:{state.gateway_port}"
    support._bind_self(gateway["url"], controller, save=gateway["root"] / "self-binding.json")
    if gateway.get("seeded_admin"):
        support._bind_admin(gateway["url"], controller)


def _send(
    support: ModuleType, sender: dict[str, Any], text: str = "Synthetic admission qualification"
) -> dict[str, Any]:
    """Create one chat event under the current selected sender connection."""

    status, members = support._request(sender["url"], "/v1/plugins/cccc/members")
    _require(status == 200 and bool(members.get("connection_token")), "Member selection failed")
    code, document = support._request(
        sender["url"],
        "/v1/plugins/cccc/chat/send",
        {
            "connection_token": members["connection_token"],
            "operation_id": uuid.uuid4().hex,
            "to": ["receiver"],
            "text": text,
            "mode": "send",
        },
    )
    _require(code == 200 and document.get("stored") is True, "Fresh stored chat operation failed")
    return dict(document)


def _receipt(
    support: ModuleType,
    sender: dict[str, Any],
    event_ref: str,
    states: set[str],
    *,
    seconds: float = 25,
) -> dict[str, Any]:
    """Wait for one authoritative recipient attempt in an explicit terminal state."""

    result: dict[str, Any] = {}
    observed: list[str] = []

    def settled() -> bool:
        """Inspect receipts through the sender-scoped non-consuming route."""

        code, document = support._request(
            sender["url"],
            "/v1/plugins/cccc/chat/deliveries?" + urlencode({"event_ref": event_ref}),
        )
        observed.clear()
        observed.extend(
            str(row.get("state"))[:32]
            for row in document.get("deliveries", [])
            if isinstance(row, dict)
        )
        for row in document.get("deliveries", []) if code == 200 else []:
            if row.get("actor_id") == "receiver" and row.get("state") in states:
                result.update(row)
                return True
        return False

    try:
        support._wait(
            settled, "Authoritative recipient attempt did not settle as expected", seconds=seconds
        )
    except RuntimeError:
        safe_states = [
            state
            for state in observed
            if state
            in {
                "pending",
                "offered",
                "staged",
                "started",
                "accepted",
                "refused",
                "failed",
                "uncertain",
                "direct_read",
            }
        ]
        raise QualificationError(
            "Authoritative receipt outcome mismatch; expected="
            + ",".join(sorted(states))
            + "; observed="
            + ",".join(safe_states)
        ) from None
    return result


def _refuse_pending_chat(profile: Path, event_id: str) -> str:
    """Settle one exact offered attempt as refused without handing it to a body."""

    import httpx

    credential = json.loads(profile.read_text())
    with httpx.Client(
        base_url=credential["endpoint"],
        headers={"Authorization": "Bearer " + credential["token"]},
        trust_env=False,
    ) as recipient:

        def rpc(operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
            """Use the recipient's existing grant on the v2 compatibility interface."""

            return _provider_result(
                recipient.post(
                    "/api/v1/external-receiver/v2/rpc",
                    json={"operation": operation, "arguments": arguments},
                )
            )

        lease = rpc("lease.acquire", {"transport": "pull", "receiver": "gateway"})
        scope = {field: lease[field] for field in ("lease_id", "lease_generation")}
        try:
            offers = rpc("lease.next", {**scope, "limit": 1})["offers"]
            _require(
                len(offers) == 1 and offers[0]["event_id"] == event_id,
                "Refusal fixture did not select the expected pending event",
            )
            attempt_id = str(offers[0]["attempt_id"])
            dispatch_id = uuid.uuid4().hex
            started = rpc(
                "lease.start",
                {**scope, "dispatch_id": dispatch_id, "attempt_ids": [attempt_id]},
            )
            _require(started["outcome"] == "started", "Refusal fixture did not start")
            rpc(
                "lease.settle",
                {**scope, "dispatch_id": dispatch_id, "outcome": "refused", "retryable": True},
            )
            return attempt_id
        finally:
            rpc("lease.release", scope)


def _qualify_receipt_discovery(
    support: ModuleType,
    work: Path,
    sender: dict[str, Any],
    receiver: dict[str, Any],
    direct: Callable[..., dict[str, Any]],
) -> int:
    """Exercise each installed receipt selector against the same two attempts."""

    root = receiver["root"]
    baseline = _invocations(root)
    print(json.dumps({"qualification_stage": "installed-receipt-discovery"}), flush=True)
    url = receiver["url"]
    admin = support._ADMIN_CLIENTS[url]
    selection = {"expected_binding_id": receiver["binding"]["binding_id"]}
    status, _ = support._request(
        url, "/v1/plugins/cccc/connection/disconnect", selection, client=admin
    )
    _require(status == 200, "Receipt setup did not release gateway intake")
    event = _send(support, sender, "Synthetic receipt retry")["event"]
    _receipt(support, sender, event["event_ref"], {"pending"})
    refused_id = _refuse_pending_chat(root / "actor-credential.json", event["id"])
    _gateway_cli(
        work,
        sender,
        [
            "chat",
            "retry",
            "--binding-id",
            sender["binding"]["binding_id"],
            "--event-ref",
            event["event_ref"],
            "--to",
            "receiver",
        ],
    )
    status, _ = support._request(
        url, "/v1/plugins/cccc/connection/connect", selection, client=admin
    )
    _require(status == 200, "Receipt setup did not reconnect gateway intake")
    accepted = _receipt(support, sender, event["event_ref"], {"accepted"}, seconds=60)
    via_handle = _gateway_cli(work, sender, ["chat", "deliveries", "--handle", event["handle"]])
    via_ref = _gateway_cli(work, sender, ["chat", "deliveries", "--event-ref", event["event_ref"]])
    via_id = direct("chat", "deliveries", "--event-id", event["id"])
    _require(
        via_handle == via_ref
        and via_id["event_id"] == via_handle["event_id"] == event["id"]
        and via_id["deliveries"] == via_handle["deliveries"],
        "Installed receipt selectors returned different results for one event",
    )
    attempts = via_handle["deliveries"]
    limited = _gateway_cli(
        work, sender, ["chat", "deliveries", "--handle", event["handle"], "--limit", "1"]
    )
    _require(
        [(row["attempt_id"], row["state"]) for row in attempts]
        == [(accepted["attempt_id"], "accepted"), (refused_id, "refused")]
        and via_handle["has_more"] is False
        and via_id["has_more"] is False
        and limited["deliveries"] == attempts[:1]
        and limited["has_more"] is True,
        "Installed receipts did not retain the newest attempts in order",
    )
    group_arguments = ["members", "--group", receiver["binding"]["group_id"]]
    _require(
        _gateway_cli(work, sender, group_arguments) == _gateway_cli(work, sender, ["members"])
        and direct(*group_arguments) == direct("members"),
        "Group assertion changed the selected member projection",
    )
    conflict = _gateway_cli(work, sender, ["members", "--group", "different-group"], success=False)
    _require(
        conflict.get("error_code") == "group_conflict" and conflict.get("status") == 409,
        "Gateway did not report a typed Group conflict",
    )
    direct_conflict = direct(
        "members", "--group", "different-group", expected_error="group_conflict"
    )
    _require(direct_conflict.get("status") == 409, "Direct Group conflict lost its status")
    support._wait(lambda: support._ready(receiver["url"]), "Receipt retry did not finish")
    _require(_invocations(root) == baseline + 1, "Receipt retry did not hand off exactly once")
    return baseline + 1


def _failure_cases(
    support: ModuleType,
    work: Path,
    sender: dict[str, Any],
    receiver: dict[str, Any],
    controller: Any,
) -> dict[str, bool]:
    """Qualify scheduled pull, live push policies, direct intake, and recovery."""

    from houmao.agents.realm_controller.errors import GatewayHttpError
    from houmao.agents.realm_controller.gateway_client import GatewayClient

    prefix = "/v1/plugins/cccc"
    root = receiver["root"]
    control_path = root / "control.json"
    control = json.loads(control_path.read_text())
    support._wait(lambda: support._ready(receiver["url"]), "Recipient did not become ready")
    print(json.dumps({"qualification_stage": "busy-queue"}), flush=True)
    baseline = _invocations(root)
    control["turn_seconds"] = 4.0
    control_path.write_text(json.dumps(control))
    first = _send(support, sender)
    _receipt(support, sender, first["event"]["event_ref"], {"accepted"})
    support._wait(lambda: _invocations(root) == baseline + 1, "Busy fixture never started")
    waiting = _send(support, sender)
    _receipt(support, sender, waiting["event"]["event_ref"], {"staged", "offered", "pending"})
    _require(_invocations(root) == baseline + 1, "Busy body received competing work")
    control["turn_seconds"] = 0.25
    control_path.write_text(json.dumps(control))
    _receipt(support, sender, waiting["event"]["event_ref"], {"accepted"})
    support._wait(lambda: support._ready(receiver["url"]), "Waiting batch did not finish")
    _require(_invocations(root) == baseline + 2, "Waiting chat handoff count differs")

    print(json.dumps({"qualification_stage": "live-push"}), flush=True)
    url = receiver["url"]
    route = prefix + "/delivery"
    admin = support._ADMIN_CLIENTS[url]
    _, initial = support._request(url, route)
    _require(initial["effective"]["transport"] == "pull", "Receiver did not default to pull")
    try:
        GatewayClient(base_url=url).request_plugin_json(
            "PUT", route, body={"revision": initial["revision"], "settings": initial["desired"]}
        )
    except GatewayHttpError as error:
        _require(error.status_code == 401, "Delivery update authorization changed")
    else:
        raise QualificationError("Unauthorized delivery update passed")

    def update(settings: dict[str, object], revision: int) -> None:
        """Change transport or policy through the exact signed management action."""

        result = admin.request_plugin_json(
            "PUT", route, body={"revision": revision, "settings": settings}
        )
        _require(result["revision"] == revision + 1, "Delivery revision did not advance")
        support._wait(
            lambda: (
                (state := support._request(url, route)[1]).get("transition") == "active"
                and state["effective"]["transport"] == settings["transport"]
                and state["effective"]["push_policy"] == settings.get("push_policy")
            ),
            "Delivery settings did not become effective",
        )

    update({"transport": "push", "push_policy": "asap"}, initial["revision"])
    asap_baseline = _invocations(root)
    asap = [_send(support, sender, f"ASAP delivery {index}") for index in range(2)]
    for stored in asap:
        _receipt(support, sender, stored["event"]["event_ref"], {"accepted"})
    support._wait(lambda: support._ready(url), "ASAP deliveries did not finish")
    _require(_invocations(root) == asap_baseline + 2, "ASAP coalesced distinct offers")

    update(
        {"transport": "push", "push_policy": "batch", "quiet_interval": 2.0, "max_wait": 6.0},
        initial["revision"] + 1,
    )
    batch_baseline = _invocations(root)
    batch = [_send(support, sender, f"Timed push delivery {index}") for index in range(2)]
    for stored in batch:
        _receipt(support, sender, stored["event"]["event_ref"], {"accepted"})
    support._wait(lambda: support._ready(url), "Timed push batch did not finish")
    _require(_invocations(root) == batch_baseline + 1, "Timed push did not group the burst")

    print(json.dumps({"qualification_stage": "direct-and-reconnect"}), flush=True)
    _require(controller.detach_gateway().status == "ok", "Gateway absence setup failed")
    absent = [_send(support, sender, f"Direct pull order {index}") for index in range(2)]
    profile = root / "actor-credential.json"

    def direct(*arguments: str, expected_error: str | None = None) -> dict[str, Any]:
        """Use an independent CLI invocation and the explicit selected Actor profile."""

        deadline = time.monotonic() + 50.0
        while True:
            result = subprocess.run(
                [
                    str(work / "venv/bin/houmao-cccc"),
                    "--direct-profile",
                    str(profile),
                    "--agent-id",
                    receiver["binding"]["agent_id"],
                    *arguments,
                ],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=40,
                check=False,
            )
            if result.returncode == 0:
                _require(expected_error is None, "Expected direct CCCC operation to fail")
                return dict(json.loads(result.stdout))
            try:
                failure = json.loads(result.stderr)
                code = failure.get("error_code", "unexpected_result")
            except (ValueError, AttributeError):
                failure = {}
                code = "unexpected_result"
            if expected_error is not None and code == expected_error:
                return dict(failure)
            if (
                arguments[:2] == ("chat", "pull")
                and code == "receiver_lease_conflict"
                and time.monotonic() < deadline
            ):
                time.sleep(0.5)
                continue
            if not isinstance(code, str) or not code.replace("_", "").isalnum():
                code = "unexpected_result"
            raise QualificationError(
                f"Installed direct CCCC {' '.join(arguments[:2])} failed: {code[:128]}"
            )

    pulled = direct("chat", "pull")
    _require(
        [row["text"] for row in pulled["messages"]]
        == ["Direct pull order 0", "Direct pull order 1"],
        "Direct CLI pull did not preserve the ordered snapshot",
    )
    acknowledged = direct("chat", "ack", "--receipt", pulled["receipt"])
    _require(acknowledged["acknowledged"] is True, "Direct receipt was not acknowledged")
    for stored in absent:
        _receipt(support, sender, stored["event"]["event_ref"], {"direct_read"})
    reply = direct(
        "chat",
        "reply",
        "--event-ref",
        pulled["messages"][0]["event_ref"],
        "--operation-id",
        uuid.uuid4().hex,
        "--text",
        "Direct exact reply",
    )
    _require(
        reply["event"]["data"]["reply_to"] == absent[0]["event"]["id"],
        "Direct reply parent changed",
    )
    sent_mail = _gateway_cli(
        work,
        sender,
        [
            "mail",
            "send",
            "--binding-id",
            sender["binding"]["binding_id"],
            "--operation-id",
            uuid.uuid4().hex,
            "--to",
            "receiver",
            "--text",
            "Direct deferred Mail",
        ],
    )
    cursor = direct("mail", "cursor")["cursor"]["event_id"]
    read_id = uuid.uuid4().hex
    read_arguments = (
        "mail",
        "read",
        "--expected-cursor",
        cursor,
        "--operation-id",
        read_id,
        "--limit",
        "1",
    )
    mail = direct(*read_arguments)
    repeated = direct(*read_arguments)
    receipt = direct("mail", "reads", "--operation-id", read_id)
    _require(
        mail["messages"][0]["id"] == sent_mail["event"]["id"]
        and receipt["receipt"] == repeated["receipt"] == mail["receipt"]
        and not repeated["messages"],
        "Direct Mail receipt did not reconcile the exact read",
    )

    recovering = _send(support, sender, "Pending while gateway absent")
    _receipt(support, sender, recovering["event"]["event_ref"], {"pending"})
    _require(controller.attach_gateway().status == "ok", "Absent gateway did not restart")
    _record_live_gateway(support, controller, receiver)
    support._wait(
        lambda: (
            support._request(receiver["url"], prefix + "/binding")[1].get("connection")
            == "connected"
        ),
        "Absent gateway did not reacquire its lease",
        seconds=60,
    )
    _receipt(support, sender, recovering["event"]["event_ref"], {"accepted"})
    support._wait(lambda: support._ready(receiver["url"]), "Recovered batch did not finish")
    baseline = _invocations(root)
    _require(baseline == batch_baseline + 2, "Recovery did not deliver exactly the pending chat")

    baseline = _qualify_receipt_discovery(support, work, sender, receiver, direct)

    replaced = root.parent.name == "detached_process"
    scenario = "generation_replaced" if replaced else "body_window_died"
    print(json.dumps({"qualification_stage": scenario}), flush=True)
    support._arm_handoff_barrier(root, control, control_path)
    blocked = _send(support, sender)
    support._wait(lambda: (root / "paused").exists(), "Actual receiver missed the native barrier")
    original = controller.manifest_path.read_text()
    if replaced:
        manifest = json.loads(original)
        manifest["registry_generation_id"] = uuid.uuid4().hex
        controller.manifest_path.write_text(json.dumps(manifest))
    else:
        support._tmux_server().checked_command(
            ["kill-window", "-t", f"={controller.tmux_session_name}:0"]
        )
    try:
        (root / "released").touch()
        _receipt(
            support,
            sender,
            blocked["event"]["event_ref"],
            {"failed", "refused", "uncertain"},
            seconds=65,
        )
    finally:
        if replaced:
            controller.manifest_path.write_text(original)
    time.sleep(0.4)
    _require(_invocations(root) == baseline, "Retired native handoff reached a body later")
    return {
        "busy_chat_waits": True,
        "live_push_asap": True,
        "live_push_batch": True,
        "gateway_absence_pending_recovery": True,
        "direct_cli_with_mail": True,
        "installed_receipt_targets": True,
        "limited_receipt_history": True,
        "group_assertions": True,
        ("body_replacement_fenced" if replaced else "body_death_fenced"): True,
    }


def _gateway_cli(
    work: Path,
    gateway: dict[str, Any],
    arguments: list[str],
    *,
    success: bool = True,
) -> dict[str, Any]:
    """Call the independently installed CLI and retain no message bodies in evidence."""

    result = subprocess.run(
        [
            str(work / "venv/bin/houmao-cccc"),
            "--gateway-url",
            gateway["url"],
            "--signer-binding",
            str(gateway["root"] / "self-binding.json"),
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )
    document = dict(json.loads(result.stdout or result.stderr))
    if (result.returncode == 0) is not success:
        raw_code = document.get("error_code")
        code = (
            raw_code
            if isinstance(raw_code, str) and raw_code.replace("_", "").isalnum()
            else "unexpected_result"
        )
        raise QualificationError("Installed gateway CCCC operation failed: " + code[:128])
    return document


def _qualify_current_mail(
    support: ModuleType,
    work: Path,
    sender: dict[str, Any],
    receiver: dict[str, Any],
) -> None:
    """Use the installed signed CLI for actual deferred Mail and scoped inspection."""

    sender_binding = sender["binding"]["binding_id"]
    receiver_binding = receiver["binding"]["binding_id"]
    prefix = "/v1/plugins/cccc"
    sent = _gateway_cli(
        work,
        sender,
        [
            "mail",
            "send",
            "--binding-id",
            sender_binding,
            "--operation-id",
            uuid.uuid4().hex,
            "--to",
            "receiver",
            "--text",
            "Synthetic signed deferred Mail",
        ],
    )
    _require(sent.get("stored") is True, "Signed Mail was not stored by CCCC")
    _require(
        support._request(receiver["url"], prefix + "/mail/peek?limit=1", signed=False)[0] == 401,
        "Unsigned Mail inspection passed",
    )

    def pending() -> bool:
        """Wait for the actual provider to expose this Actor's deferred Mail."""

        code, result = support._request(receiver["url"], prefix + "/mail/peek?limit=1")
        return code == 200 and any(
            item.get("id") == sent["event"]["id"] for item in result.get("messages", [])
        )

    support._wait(pending, "Signed recipient did not see the CCCC Mail")
    _, cursor = support._request(receiver["url"], prefix + "/mail/cursor")
    consumed = _gateway_cli(
        work,
        receiver,
        [
            "mail",
            "read",
            "--binding-id",
            receiver_binding,
            "--operation-id",
            uuid.uuid4().hex,
            "--expected-cursor",
            cursor["cursor_ref"],
            "--limit",
            "1",
        ],
    )
    _require(
        consumed.get("consumed") is True and consumed["messages"][0]["id"] == sent["event"]["id"],
        "Signed bounded Mail read did not return the provider's deferred event",
    )


def _reconnect_mail_gateway(
    support: ModuleType,
    gateway: dict[str, Any],
    controller: Any,
    snapshot: tuple[str, object],
) -> None:
    """Restart the same installed gateway while preserving its body and Actor binding."""

    _require(controller.detach_gateway().status == "ok", "Mail gateway detach failed")
    os.environ["HOUMAO_PLUGIN_FIXTURE_CONTROL"] = str(gateway["root"] / "control.json")
    _require(
        controller.attach_gateway(plugin_config=gateway["selection"]).status == "ok",
        "Mail gateway reconnect failed",
    )
    _record_live_gateway(support, controller, gateway)
    support._wait(
        lambda: (
            support._request(gateway["url"], "/v1/plugins/cccc/binding")[1].get("connection")
            == "connected"
        ),
        "Reconnected gateway did not recover its existing Actor lease",
        seconds=65,
    )
    current = support._request(gateway["url"], "/v1/plugins/cccc/binding")[1]
    _require(
        current["binding_id"] == gateway["binding"]["binding_id"],
        "Gateway reconnect changed the owner binding",
    )
    _require(
        _body_snapshot(support, controller) == snapshot,
        "Gateway reconnect changed body PID or conversation",
    )


def _mail_recovery_cases(
    support: ModuleType,
    work: Path,
    gateways: list[dict[str, Any]],
    controllers: list[Any],
) -> dict[str, bool]:
    """Exercise bounded Mail decisions across same-wheel gateway restarts."""

    def body_ready(gateway: dict[str, Any]) -> bool:
        """Use the explicit open-admin fixture for this runtime control read."""

        code, state = support._request(gateway["url"], "/v1/control/headless/state", signed=False)
        _require(code == 200, f"Mail fixture readiness inspection failed with HTTP {code}")
        return state.get("can_accept_prompt_now") is True

    print(json.dumps({"qualification_stage": "mail-gateway-reconnect"}), flush=True)
    for gateway in gateways:
        support._wait(lambda: body_ready(gateway), "Body was not ready before gateway reconnect")
    snapshots = [_body_snapshot(support, controller) for controller in controllers]
    _require(
        any(
            getattr(controller.backend_session.state, "session_id", None) != snapshot[1]
            for controller, snapshot in zip(controllers, snapshots, strict=True)
        ),
        "Reconnect fixture did not retain a controller older than its gateway-authored conversation",
    )
    counts = [_invocations(item["root"]) for item in gateways]
    for controller, gateway, snapshot in zip(controllers, gateways, snapshots, strict=True):
        _reconnect_mail_gateway(support, gateway, controller, snapshot)
        code, _ = support._request(
            gateway["url"],
            "/v1/plugins/cccc/connection/refresh-credentials",
            {"expected_binding_id": gateway["binding"]["binding_id"]},
            signed=False,
        )
        _require(code == 200, "Installed credential refresh failed")
        support._wait(
            lambda: (
                support._request(gateway["url"], "/v1/plugins/cccc/binding")[1].get("connection")
                == "connected"
            ),
            "Credential refresh lost the existing binding",
            seconds=65,
        )
        _require(
            _body_snapshot(support, controller) == snapshot,
            "Credential refresh changed the body or conversation",
        )
    sender, receiver = gateways
    print(json.dumps({"qualification_stage": "mail-inspection-and-send"}), flush=True)
    preserved = _gateway_cli(
        work, sender, ["chat", "history", "--event-ref", sender["existing_chat_ref"]]
    )
    _require(
        preserved["messages"][0]["id"] == sender["existing_chat_id"],
        "Gateway reconnect invalidated an existing chat reference",
    )
    binding = ["--binding-id", receiver["binding"]["binding_id"]]

    def send_mail(text: str = "Synthetic deferred Mail") -> dict[str, Any]:
        """Send one explicit deferred operation through the installed CLI."""

        return _gateway_cli(
            work,
            sender,
            [
                "mail",
                "send",
                "--binding-id",
                sender["binding"]["binding_id"],
                "--operation-id",
                uuid.uuid4().hex,
                "--to",
                "receiver",
                "--text",
                text,
            ],
        )

    def read_mail(
        operation_id: str,
        cursor: str,
        *,
        limit: int = 1,
        max_bytes: int = 262144,
        success: bool = True,
    ) -> dict[str, Any]:
        """Read exactly one caller-authorized bounded next batch."""

        return _gateway_cli(
            work,
            receiver,
            [
                "mail",
                "read",
                *binding,
                "--operation-id",
                operation_id,
                "--expected-cursor",
                cursor,
                "--limit",
                str(limit),
                "--max-bytes",
                str(max_bytes),
            ],
            success=success,
        )

    caps = _gateway_cli(work, receiver, ["capabilities"])
    _require(
        isinstance(caps.get("mail"), dict) and caps["mail"].get("qualified") is True,
        "Reconnected gateway did not negotiate the complete Mail contract",
    )
    first = send_mail()
    second = send_mail("Synthetic following Mail")
    _require(
        first.get("consumed") is False and first["event"]["data"]["message_mode"] == "mail",
        "Mail send did not remain deferred",
    )
    cursor = _gateway_cli(work, receiver, ["mail", "cursor"])
    before = cursor["cursor_ref"]
    peek = _gateway_cli(work, receiver, ["mail", "peek", "--limit", "1", "--max-bytes", "1048576"])
    repeated_peek = _gateway_cli(work, receiver, ["mail", "peek", "--limit", "1"])
    _require(
        peek["messages"][0]["id"] == repeated_peek["messages"][0]["id"] == first["event"]["id"],
        "Mail peek changed the ordered pending batch",
    )
    _require(
        _gateway_cli(work, receiver, ["mail", "cursor"])["cursor_ref"] == before,
        "Non-consuming Mail inspection advanced the cursor",
    )
    reply = _gateway_cli(
        work,
        receiver,
        [
            "mail",
            "reply",
            *binding,
            "--operation-id",
            uuid.uuid4().hex,
            "--event-ref",
            peek["messages"][0]["event_ref"],
            "--text",
            "Synthetic deferred reply",
        ],
    )
    _require(
        reply["event"]["data"]["reply_to"] == first["event"]["id"]
        and reply["event"]["data"]["message_mode"] == "mail",
        "Mail reply lost deferred ancestry",
    )
    _require(
        _gateway_cli(work, receiver, ["mail", "cursor"])["cursor_ref"] == before,
        "Reply without read consumed the incoming batch",
    )
    operation_id = uuid.uuid4().hex
    print(json.dumps({"qualification_stage": "mail-ordered-consumption"}), flush=True)
    consumed = read_mail(operation_id, before)
    _require(
        consumed["outcome"] == "consumed"
        and len(consumed["messages"]) == 1
        and consumed["messages"][0]["id"] == first["event"]["id"],
        "Bounded Mail read lost append order",
    )
    receipt = _gateway_cli(work, receiver, ["mail", "reads", "--operation-id", operation_id])
    _require(
        receipt.get("found") is True and receipt["receipt"]["event_ids"] == [first["event"]["id"]],
        "Read receipt did not preserve the exact consumed prefix",
    )
    wrong_receipt = _gateway_cli(
        work,
        sender,
        ["mail", "reads", "--operation-id", operation_id, "--read-ref", receipt["read_ref"]],
        success=False,
    )
    _require(
        wrong_receipt.get("error_code") == "reference_scope_error",
        "Another owner reused a read receipt reference",
    )
    repeated = read_mail(operation_id, before)
    _require(
        repeated["outcome"] == "already_completed" and repeated["messages"] == [],
        "Matching Mail read repeated consumption",
    )
    following = _gateway_cli(work, receiver, ["mail", "peek", "--limit", "1"])
    _require(
        following["messages"][0]["id"] == second["event"]["id"],
        "Receipt reconciliation consumed the following batch",
    )
    stale = read_mail(uuid.uuid4().hex, before, success=False)
    _require(stale.get("error_code") == "cursor_conflict", "Stale Mail cursor did not conflict")
    wrong_owner = _gateway_cli(
        work,
        sender,
        [
            "mail",
            "read",
            "--binding-id",
            sender["binding"]["binding_id"],
            "--operation-id",
            uuid.uuid4().hex,
            "--expected-cursor",
            before,
        ],
        success=False,
    )
    _require(
        wrong_owner.get("error_code") == "reference_scope_error",
        "Another owner reused a Mail cursor",
    )
    recovered = _gateway_cli(
        work, receiver, ["chat", "history", "--event-ref", consumed["messages"][0]["event_ref"]]
    )
    _require(
        recovered["messages"][0]["id"] == first["event"]["id"],
        "Exact history could not recover consumed Mail",
    )
    after_lost_batch = send_mail("Synthetic following a lost read response")

    # The sender application deliberately discards a successfully committed read reply.
    lost_operation = uuid.uuid4().hex
    print(json.dumps({"qualification_stage": "mail-lost-read-response"}), flush=True)
    listener = urlsplit(receiver["url"])
    connection = http.client.HTTPConnection(listener.hostname, listener.port, timeout=25)
    try:
        request = support._prepare_request(
            receiver["url"],
            "/v1/plugins/cccc/mail/read",
            {
                "expected_binding_id": receiver["binding"]["binding_id"],
                "operation_id": lost_operation,
                "expected_cursor": following["cursor_ref"],
                "limit": 1,
                "max_bytes": 262144,
            },
        )
        connection.request(
            request.get_method(),
            urlsplit(request.full_url).path,
            body=request.data,
            headers=dict(request.header_items()),
        )
        saved: dict[str, Any] = {}

        def read_committed() -> bool:
            """Reconcile only the known operation without accepting its lost response."""

            result = _gateway_cli(
                work, receiver, ["mail", "reads", "--operation-id", lost_operation]
            )
            saved.update(result)
            return result.get("found") is True

        support._wait(read_committed, "Discarded read response had no authoritative receipt")
    finally:
        connection.close()
    print(json.dumps({"qualification_stage": "mail-receipt-after-reconnect"}), flush=True)
    _reconnect_mail_gateway(support, receiver, controllers[1], snapshots[1])
    recovered_receipt = _gateway_cli(
        work, receiver, ["mail", "reads", "--operation-id", lost_operation]
    )
    _require(
        recovered_receipt.get("found") is True and recovered_receipt["receipt"] == saved["receipt"],
        "Gateway reconnect changed the authoritative read receipt",
    )
    _require(
        saved["receipt"]["event_ids"] == [second["event"]["id"]],
        "Lost response reconciliation changed the consumed batch",
    )
    _require(len(saved["receipt"]["event_refs"]) == 1, "Receipt omitted scoped recovery references")
    lost_content = _gateway_cli(
        work, receiver, ["chat", "history", "--event-ref", saved["receipt"]["event_refs"][0]]
    )
    _require(
        lost_content["messages"][0]["id"] == second["event"]["id"],
        "Receipt reference did not recover lost content",
    )
    after_loss = _gateway_cli(work, receiver, ["mail", "peek", "--limit", "1"])
    _require(
        after_loss["messages"][0]["id"] == after_lost_batch["event"]["id"],
        "Lost-response recovery consumed the following batch",
    )
    read_mail(uuid.uuid4().hex, after_loss["cursor_ref"])
    empty_cursor = _gateway_cli(work, receiver, ["mail", "cursor"])["cursor_ref"]
    empty_id = uuid.uuid4().hex
    _require(
        read_mail(empty_id, empty_cursor)["outcome"] == "empty", "Empty Mail read was not recorded"
    )
    third = send_mail("Synthetic post-empty Mail")
    _require(
        read_mail(empty_id, empty_cursor)["outcome"] == "already_completed",
        "Empty read identity was reused as new consumption",
    )
    pending = _gateway_cli(work, receiver, ["mail", "peek", "--limit", "200"])
    _require(
        pending["messages"][0]["id"] == third["event"]["id"],
        "Repeating an empty read consumed later Mail",
    )
    read_mail(uuid.uuid4().hex, pending["cursor_ref"])
    send_mail("Synthetic oversized first Mail " + "x" * 5000)
    print(json.dumps({"qualification_stage": "mail-precommit-byte-bound"}), flush=True)
    large_cursor = _gateway_cli(work, receiver, ["mail", "cursor"])["cursor_ref"]
    too_large = read_mail(uuid.uuid4().hex, large_cursor, max_bytes=4096, success=False)
    _require(
        too_large.get("error_code") == "content_limit",
        "Oversized head Mail did not fail before commit",
    )
    _require(
        _gateway_cli(work, receiver, ["mail", "cursor"])["cursor_ref"] == large_cursor,
        "Oversized read advanced the cursor",
    )
    unknown = _gateway_cli(work, receiver, ["mail", "reads", "--operation-id", uuid.uuid4().hex])
    _require(
        unknown.get("found") is False and unknown.get("outcome") == "unknown",
        "Missing receipt was misreported as a failed read",
    )
    _require(
        [_invocations(item["root"]) for item in gateways] == counts,
        "Explicit Mail operations directly launched a body",
    )
    maintained = _send(support, sender)
    _receipt(support, sender, maintained["event"]["event_ref"], {"accepted"})
    support._wait(lambda: body_ready(receiver), "Recovered chat handoff did not finish")
    _require(
        _invocations(receiver["root"]) == counts[1] + 1,
        "Mail recovery broke ordinary chat admission",
    )
    return {
        "mail_reconnect_preserved_body": True,
        "stale_controller_reconnect_preserved": True,
        "mail_cli": True,
        "mail_deferred": True,
        "mail_non_consuming_inspection": True,
        "mail_ordered_read": True,
        "mail_receipt_recovery": True,
        "mail_lost_response": True,
        "mail_receipt_gateway_restart": True,
        "mail_empty_reuse": True,
        "mail_precommit_size": True,
        "mail_reference_isolation": True,
        "mail_credential_refresh": True,
        "maintained_chat": True,
    }


def _installed(
    source: Path,
    work: Path,
    endpoint: str,
    *,
    mail_recovery: bool = False,
) -> dict[str, object]:
    """Run real installed gateways with synthetic body executables and actual CCCC."""

    import httpx
    import houmao
    import houmao_cccc
    import houmao_gateway_fixtures
    from houmao.agents.realm_controller.runtime import start_runtime_session
    from houmao.gateway.access import GatewayLaunchSeed
    from houmao.gateway.deployment import GatewayDeployment
    from houmao.gateway.plugins import GatewayPluginConfiguration

    support = _support(work / "gateway_support.py")
    for module in (houmao, houmao_cccc, houmao_gateway_fixtures):
        origin = Path(module.__file__ or "").resolve()
        _require(
            origin.is_relative_to(work / "venv"), "Installed module escaped the fresh environment"
        )
        _require(not origin.is_relative_to(source), "Qualification imported product checkout code")
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    allowed = {
        stdlib,
        stdlib / "lib-dynload",
        (
            Path(sys.base_prefix)
            / "lib"
            / f"python{sys.version_info.major}{sys.version_info.minor}.zip"
        ).resolve(),
    }
    for item in sys.path:
        if item:
            resolved = Path(item).resolve()
            _require(
                not resolved.is_relative_to(source) or resolved in allowed,
                "Checkout path entered the installed import search path",
            )
    versions = {
        name: importlib.metadata.version(name)
        for name in ("Houmao", "houmao-cccc", "houmao-gateway-qualification-fixtures")
    }
    if not mail_recovery:
        cli_version = subprocess.run(
            [str(work / "venv/bin/houmao-cccc"), "--version"],
            cwd=work,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        _require(
            cli_version.returncode == 0
            and cli_version.stdout.strip() == f"houmao-cccc {versions['houmao-cccc']}"
            and not cli_version.stderr,
            "Installed CLI version did not match wheel distribution metadata",
        )
    results: list[dict[str, object]] = []
    with httpx.Client(
        base_url=endpoint,
        headers={"Origin": endpoint, "Referer": endpoint + "/"},
        trust_env=False,
        follow_redirects=False,
        timeout=25,
    ) as administrator:
        for mode in ("detached_process", "tmux_auxiliary_window"):
            if mail_recovery:
                print(
                    json.dumps({"qualification_stage": "mail-mode", "execution_mode": mode}),
                    flush=True,
                )
            group = _provider_result(
                administrator.post(
                    "/api/v1/groups", json={"title": "installed-" + uuid.uuid4().hex}
                )
            )
            group_id = group["group_id"]
            controllers: list[Any] = []
            gateways: list[dict[str, Any]] = []
            try:
                for actor_id in ("sender", "receiver"):
                    root = work / mode / actor_id
                    root.mkdir(parents=True, mode=0o700)
                    workspace = root / "workspace"
                    workspace.mkdir(mode=0o700)
                    _provider_result(
                        administrator.post(
                            f"/api/v1/groups/{group_id}/actors",
                            json={
                                "actor_id": actor_id,
                                "runtime": "custom",
                                "command": ["/bin/true"],
                            },
                        )
                    )
                    grant = _provider_result(
                        administrator.post(
                            "/api/v1/external-receiver/v2/grants",
                            json={"group_id": group_id, "actor_id": actor_id},
                        )
                    )
                    _require(
                        grant.get("protocol_version") == 2, "Provider did not issue a v2 grant"
                    )
                    owner = uuid.uuid4().hex
                    credentials = root / "actor-credential.json"
                    descriptor = os.open(credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(descriptor, "w", encoding="utf-8") as credential_file:
                        json.dump(
                            {
                                "schema_version": 1,
                                "agent_id": owner,
                                "endpoint": endpoint,
                                "group_id": group_id,
                                "actor_id": actor_id,
                                "actor_generation": grant["actor_generation"],
                                "token": grant["token"],
                            },
                            credential_file,
                        )
                    control = root / "control.json"
                    control.write_text(
                        json.dumps(
                            {
                                "count_file": str(root / "invocations"),
                                "turn_seconds": 0.25,
                                "paused_file": str(root / "paused"),
                                "release_file": str(root / "released"),
                            }
                        )
                    )
                    os.environ["HOUMAO_PLUGIN_FIXTURE_CONTROL"] = str(control)
                    brain = support._seed_brain(root, work / "venv/bin/houmao-fixture-codex")
                    broader_receiver = actor_id == "receiver" and not mail_recovery
                    signer = root / "broad-fixture-admin.key"
                    seed = (
                        GatewayLaunchSeed(admin_keys=(support._fixture_admin(signer),))
                        if broader_receiver
                        else GatewayLaunchSeed()
                    )
                    controller = start_runtime_session(
                        agent_def_dir=root / "agent-def",
                        brain_manifest_path=brain,
                        role_name="qualification",
                        runtime_root=root / "runtime",
                        backend="codex_headless",
                        working_directory=workspace,
                        agent_name="cccc-installed-" + uuid.uuid4().hex[:10],
                        agent_id=owner,
                        gateway_admin_seed=seed,
                    )
                    controllers.append(controller)
                    controller.send_prompt("Synthetic conversation before plugin attachment")
                    before_attach = _body_snapshot(support, controller)
                    _require(bool(before_attach[1]), "Fixture did not seed its native conversation")
                    selection = GatewayPluginConfiguration.model_validate(
                        {
                            "plugins": {
                                "cccc": {
                                    "implementation": "cccc",
                                    "credential_ref": {"file": str(credentials)},
                                    "config": {
                                        "endpoint": endpoint,
                                        "group_id": group_id,
                                        "actor_id": actor_id,
                                        "actor_generation": grant["actor_generation"],
                                        **({"mail_max_bytes": 1048576} if mail_recovery else {}),
                                    },
                                }
                            }
                        }
                    )
                    if broader_receiver:
                        broad = controller.attach_gateway(
                            host_override="0.0.0.0",
                            port_override=0,
                            execution_mode_override=mode,
                            plugin_config=selection,
                        )
                        _require(
                            broad.status == "error",
                            "Broad-listener gateway started without an explicit access deployment",
                        )
                    attached = controller.attach_gateway(
                        host_override=None if broader_receiver else "127.0.0.1",
                        port_override=None if broader_receiver else 0,
                        execution_mode_override=mode,
                        plugin_config=selection,
                        access_config=(
                            GatewayDeployment(bind_host="0.0.0.0", admin_signer_path=str(signer))
                            if broader_receiver
                            else None
                        ),
                    )
                    _require(attached.status == "ok", "Normal installed gateway attach failed")
                    observation = {
                        "root": root,
                        "selection": selection,
                        "seeded_admin": broader_receiver,
                    }
                    _record_live_gateway(support, controller, observation)
                    url = observation["url"]
                    support._wait(
                        lambda: (
                            support._request(url, "/v1/plugins/cccc/binding")[1].get("connection")
                            == "connected"
                        ),
                        "Installed CCCC plugin did not establish its Actor lease",
                        seconds=60,
                    )
                    binding = support._request(url, "/v1/plugins/cccc/binding")[1]
                    _require(
                        _body_snapshot(support, controller) == before_attach,
                        "Plugin attachment changed the live body PID or native conversation",
                    )
                    observation["binding"] = binding
                    gateways.append(observation)
                sender, receiver = gateways
                prefix = "/v1/plugins/cccc"
                if not mail_recovery:
                    print(
                        json.dumps({"qualification_stage": "authenticated-chat-and-mail"}),
                        flush=True,
                    )
                    support._verify_plugin_access(
                        sender["url"],
                        root=sender["root"],
                        private_paths=(
                            prefix + "/binding",
                            prefix + "/chat/history?limit=1",
                            prefix + "/mail/peek?limit=1",
                        ),
                        admin_path=prefix + "/connection/connect",
                        admin_payload={"expected_binding_id": sender["binding"]["binding_id"]},
                    )
                    _qualify_current_mail(support, work, sender, receiver)
                stored = _send(support, sender, "Synthetic installed chat")
                event_id = stored["event"]["id"]
                event_ref = stored["event"]["event_ref"]
                query = urlencode({"event_ref": event_ref})

                def received() -> bool:
                    """Check the authoritative recipient handoff receipt."""

                    code, document = support._request(
                        sender["url"], prefix + "/chat/deliveries?" + query
                    )
                    return code == 200 and any(
                        row.get("state") == "accepted" for row in document.get("deliveries", [])
                    )

                support._wait(
                    received, "Installed receiver did not confirm actual body handoff", seconds=25
                )
                code, history = support._request(receiver["url"], prefix + "/chat/history?limit=1")
                _require(
                    code == 200 and history["messages"][0]["id"] == event_id,
                    "Installed Actor-visible history failed",
                )
                receiver_ref = history["messages"][0]["event_ref"]
                code, _ = support._request(
                    receiver["url"],
                    prefix + "/chat/reply",
                    {
                        "operation_id": uuid.uuid4().hex,
                        "handle": stored["event"]["handle"],
                        "text": "Synthetic invalid owner ref",
                    },
                )
                _require(code == 409, "Another owner reused a targeting handle")
                code, reply = support._request(
                    receiver["url"],
                    prefix + "/chat/reply",
                    {
                        "operation_id": uuid.uuid4().hex,
                        "handle": history["messages"][0]["handle"],
                        "text": "Synthetic installed reply",
                    },
                )
                _require(
                    code == 200 and reply["event"]["data"]["reply_to"] == event_id,
                    "Installed reply ancestry failed",
                )
                support._wait(
                    lambda: support._ready(receiver["url"]) and support._ready(sender["url"]),
                    "Fixture chat and reply did not finish before gateway restart",
                    seconds=35,
                )
                count = (receiver["root"] / "invocations").read_text()
                _require(
                    controllers[1].detach_gateway().status == "ok",
                    "Installed gateway detach failed",
                )
                _require(
                    controllers[1].attach_gateway().status == "ok",
                    "Installed gateway restart failed",
                )
                _record_live_gateway(support, controllers[1], receiver)
                new_url = receiver["url"]
                support._wait(
                    lambda: (
                        support._request(new_url, prefix + "/binding")[1].get("connection")
                        == "connected"
                    ),
                    "Restarted plugin did not recover",
                    seconds=60,
                )
                new_binding = support._request(new_url, prefix + "/binding")[1]
                _require(
                    new_binding["binding_id"] == receiver["binding"]["binding_id"],
                    "Gateway restart changed Actor binding",
                )
                code, exact = support._request(
                    new_url, prefix + "/chat/history?" + urlencode({"event_ref": receiver_ref})
                )
                _require(
                    code == 200 and exact["messages"][0]["id"] == event_id,
                    "Reference did not survive gateway restart",
                )
                _require(
                    (receiver["root"] / "invocations").read_text() == count,
                    "Gateway restart replayed delivered chat",
                )
                if mail_recovery:
                    sender.update(existing_chat_ref=event_ref, existing_chat_id=event_id)
                    failures = _mail_recovery_cases(support, work, gateways, controllers)
                else:
                    failures = _failure_cases(support, work, sender, receiver, controllers[1])
                results.append(
                    {
                        "execution_mode": mode,
                        "result": "passed",
                        "owner_isolation": True,
                        "chat_handoff": True,
                        "reply_ancestry": True,
                        "reference_continuity": True,
                        "restart_no_replay": True,
                        "attach_preserved_body": True,
                        "validated_broad_listener": not mail_recovery,
                        "open_and_key_required_controls": not mail_recovery,
                        "verified_private_callers": not mail_recovery,
                        "signed_deferred_mail": not mail_recovery,
                        **failures,
                    }
                )
            finally:
                cleanup_failed = False
                try:
                    for controller in reversed(controllers):
                        try:
                            _cleanup_runtime(support, controller)
                        except Exception:
                            cleanup_failed = True
                finally:
                    _provider_result(administrator.delete(f"/api/v1/groups/{group_id}"))
                _require(not cleanup_failed, "Installed runtime cleanup failed")
    report: dict[str, object] = {
        "result": "passed",
        "action": "run-mail" if mail_recovery else "run",
        "checkout_imports": False,
        "offline_install": True,
        "actual_cccc": True,
        "receiver_protocol_version": 2,
        "stand_in_bodies": True,
        "real_agent_smoke": "separate_required_qualification",
        "cleanup": "completed",
        "versions": versions,
        **({"cli_version_matches_metadata": True} if not mail_recovery else {}),
        "modes": results,
    }
    (work / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    """Expose preparation, offline installation, and copied-runner actions."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("prepare", "run", "run-mail", "installed-run", "installed-mail-run")
    )
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--endpoint")
    arguments = parser.parse_args()
    source = (arguments.source_root or Path(__file__).resolve().parents[3]).resolve()
    try:
        if arguments.action in {"installed-run", "installed-mail-run"}:
            _require(arguments.work_root is not None, "Setup requires an external work root")
            _require(
                arguments.endpoint is not None,
                "Setup requires an explicit compatible CCCC endpoint",
            )
            report = _installed(
                source,
                arguments.work_root.resolve(),
                arguments.endpoint,
                mail_recovery=arguments.action == "installed-mail-run",
            )
        else:
            _require(arguments.wheelhouse is not None, "Setup requires an explicit wheelhouse")
            wheelhouse = _root(arguments.wheelhouse, source)
            if arguments.action == "prepare":
                report = prepare(source, wheelhouse)
            else:
                _wheels(wheelhouse)
                _require(
                    arguments.endpoint is not None
                    and arguments.endpoint.startswith("http://127.0.0.1:"),
                    "Setup requires an explicitly selected dedicated loopback CCCC endpoint",
                )
                _require(arguments.work_root is not None, "Setup requires an external work root")
                report = qualify(
                    source,
                    wheelhouse,
                    _root(arguments.work_root, source),
                    arguments.endpoint,
                    mail_recovery=arguments.action == "run-mail",
                )
    except (QualificationError, OSError, ValueError) as exc:
        print(json.dumps({"result": "failed", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
    except RuntimeError as exc:
        if arguments.action in {"installed-run", "installed-mail-run"}:
            print(
                json.dumps(
                    {
                        "exception_type": type(exc).__name__,
                        "frames": [
                            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
                            for frame in traceback.extract_tb(exc.__traceback__)
                        ],
                    }
                ),
                file=sys.stderr,
            )
        reason = (
            str(exc)
            if type(exc).__module__ == "cccc_installed_support"
            else "Qualification failed; inspect the operation log"
        )
        print(
            json.dumps({"result": "failed", "error": reason}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
