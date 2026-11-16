"""Qualify installed CCCC plugin wheels against an explicitly selected real service.

Preparation can download dependencies. Qualification installs from the selected
wheelhouse only and copies its utility runner outside the source checkout.
"""

from __future__ import annotations

import argparse
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
    previous_plugin_wheel: Path | None = None,
) -> dict[str, object]:
    """Install wheels offline and execute the copied runner with isolated import paths."""

    support_path = source / "scripts/qualification/gateway-plugins/qualify.py"
    support = _support(support_path)
    artifacts = [
        {"filename": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}
        for wheel in _wheels(wheelhouse)
    ]
    previous: Path | None = None
    if previous_plugin_wheel is not None:
        _require(previous_plugin_wheel.is_file(), "Setup requires the frozen previous plugin wheel")
        previous = work / "previous-wheel" / previous_plugin_wheel.name
        previous.parent.mkdir(mode=0o700)
        shutil.copyfile(previous_plugin_wheel, previous)
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
            str(previous) if previous is not None else "houmao-cccc",
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
    environment["HOUMAO_PLUGIN_FIXTURE_REAL_TMUX"] = str(real_tmux)
    environment["HOUMAO_GLOBAL_REGISTRY_DIR"] = str(work / "registry")
    with tempfile.TemporaryDirectory(prefix="hcc-", dir="/tmp") as socket_root:
        environment["TMUX_TMPDIR"] = socket_root
        try:
            support._run(
                [
                    str(python),
                    "-I",
                    str(runner),
                    "installed-mail-run" if previous is not None else "installed-run",
                    "--source-root",
                    str(source),
                    "--work-root",
                    str(work),
                    "--endpoint",
                    endpoint,
                    *(
                        [
                            "--previous-plugin-wheel",
                            str(previous),
                            "--upgrade-plugin-wheel",
                            str(_wheels(wheelhouse)[1]),
                        ]
                        if previous is not None
                        else []
                    ),
                ],
                cwd=work,
                env=environment,
                log=log,
            )
        finally:
            subprocess.run(
                [str(real_tmux), "kill-server"],
                cwd=work,
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    result = json.loads((work / "qualification.json").read_text())
    result["artifacts"] = artifacts
    result["environment"] = {
        "python": str(python),
        "cli": str(work / "venv/bin/houmao-cccc"),
        "retained": True,
    }
    if previous is not None:
        result["previous_plugin_artifact"] = {
            "filename": previous.name,
            "sha256": hashlib.sha256(previous.read_bytes()).hexdigest(),
        }
    (work / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    return dict(result)


def _provider_result(response: Any) -> dict[str, Any]:
    """Extract provider setup results without echoing private grant material."""

    _require(response.status_code == 200, "Provider setup request failed")
    document = response.json()
    _require(document.get("ok") is True, "Provider setup envelope failed")
    return dict(document["result"])


def _body_snapshot(controller: Any) -> tuple[str, object]:
    """Read the live owned pane PID and persisted native conversation identifier."""

    document = json.loads(controller.manifest_path.read_text())
    pane = document["agent_launch_authority"]["primary_pane_id"]
    process = subprocess.run(
        [
            os.environ["HOUMAO_PLUGIN_FIXTURE_REAL_TMUX"],
            "display-message",
            "-p",
            "-t",
            pane,
            "#{pane_pid}",
        ],
        capture_output=True,
        text=True,
        check=True,
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
    real_tmux = os.environ["HOUMAO_PLUGIN_FIXTURE_REAL_TMUX"]
    subprocess.run(
        [real_tmux, "kill-session", "-t", controller.tmux_session_name],
        capture_output=True,
        check=False,
    )
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
    remaining = subprocess.run(
        [real_tmux, "has-session", "-t", controller.tmux_session_name],
        capture_output=True,
        check=False,
    )
    _require(remaining.returncode != 0, "Owned body session survived cleanup")


def _send(support: ModuleType, sender: dict[str, Any]) -> dict[str, Any]:
    """Create a fresh explicit sender operation using its maintained binding."""

    code, document = support._request(
        sender["url"],
        "/v1/plugins/cccc/chat/send",
        {
            "expected_binding_id": sender["binding"]["binding_id"],
            "operation_id": uuid.uuid4().hex,
            "to": ["receiver"],
            "text": "Synthetic admission qualification",
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
            if state in {"pending", "offered", "accepted", "refused", "failed", "uncertain"}
        ]
        raise QualificationError(
            "Authoritative receipt outcome mismatch; expected="
            + ",".join(sorted(states))
            + "; observed="
            + ",".join(safe_states)
        ) from None
    return result


def _failure_cases(
    support: ModuleType,
    sender: dict[str, Any],
    receiver: dict[str, Any],
    controller: Any,
) -> dict[str, bool]:
    """Qualify immediate refusals and native handoff races against actual CCCC."""

    prefix = "/v1/plugins/cccc"
    root = receiver["root"]
    control_path = root / "control.json"
    control = json.loads(control_path.read_text())
    support._wait(lambda: support._ready(receiver["url"]), "Recipient did not become ready")
    print(json.dumps({"qualification_stage": "busy-and-explicit-retry"}), flush=True)
    baseline = _invocations(root)
    control["turn_seconds"] = 4.0
    control_path.write_text(json.dumps(control))
    first = _send(support, sender)
    _receipt(support, sender, first["event"]["event_ref"], {"accepted"})
    support._wait(lambda: _invocations(root) == baseline + 1, "Busy fixture never started")
    refused = _send(support, sender)
    failed = _receipt(support, sender, refused["event"]["event_ref"], {"refused"})
    _require(failed.get("retryable") is True, "Busy refusal did not permit a fresh sender retry")
    support._wait(lambda: support._ready(receiver["url"]), "Busy body did not finish")
    time.sleep(0.4)
    _require(_invocations(root) == baseline + 1, "Busy refusal was automatically replayed")
    control["turn_seconds"] = 0.25
    control_path.write_text(json.dumps(control))
    code, _ = support._request(
        sender["url"],
        prefix + "/chat/retry",
        {
            "expected_binding_id": sender["binding"]["binding_id"],
            "event_ref": refused["event"]["event_ref"],
            "actor_ids": ["receiver"],
            "allow_uncertain_retry": False,
        },
    )
    _require(code == 200, "Explicit delivery retry failed")
    _receipt(support, sender, refused["event"]["event_ref"], {"accepted"})
    support._wait(lambda: support._ready(receiver["url"]), "Explicit retry did not finish")
    _require(
        _invocations(root) == baseline + 2, "Explicit retry did not produce exactly one new launch"
    )

    print(json.dumps({"qualification_stage": "gateway-absence"}), flush=True)
    _require(controller.detach_gateway().status == "ok", "Gateway absence setup failed")
    absent = _send(support, sender)
    _receipt(support, sender, absent["event"]["event_ref"], {"refused", "failed"})
    _require(controller.attach_gateway().status == "ok", "Absent gateway did not restart")
    status = controller.gateway_status()
    receiver["url"] = f"http://{status.gateway_host}:{status.gateway_port}"
    support._wait(
        lambda: (
            support._request(receiver["url"], prefix + "/binding")[1].get("connection")
            == "connected"
        ),
        "Absent gateway did not reacquire its lease",
        seconds=60,
    )
    time.sleep(0.4)
    _require(_invocations(root) == baseline + 2, "Gateway recovery replayed unavailable work")

    for scenario in ("generation_replaced", "body_window_died"):
        print(json.dumps({"qualification_stage": scenario}), flush=True)
        support._wait(lambda: support._ready(receiver["url"]), "Race fixture was not ready")
        support._arm_handoff_barrier(root, control, control_path)
        blocked = _send(support, sender)
        support._wait(
            lambda: (root / "paused").exists(), "Actual receiver missed the native barrier"
        )
        original = controller.manifest_path.read_text()
        if scenario == "generation_replaced":
            manifest = json.loads(original)
            manifest["registry_generation_id"] = uuid.uuid4().hex
            controller.manifest_path.write_text(json.dumps(manifest))
        else:
            subprocess.run(
                [
                    os.environ["HOUMAO_PLUGIN_FIXTURE_REAL_TMUX"],
                    "kill-window",
                    "-t",
                    f"{controller.tmux_session_name}:0",
                ],
                check=True,
                capture_output=True,
            )
        (root / "released").touch()
        _receipt(
            support,
            sender,
            blocked["event"]["event_ref"],
            {"failed", "refused", "uncertain"},
            seconds=65,
        )
        control["pause_handoff"] = False
        control_path.write_text(json.dumps(control))
        if scenario == "generation_replaced":
            controller.manifest_path.write_text(original)
            _require(
                controller.detach_gateway().status == "ok", "Replacement gateway cleanup failed"
            )
            _require(
                controller.attach_gateway().status == "ok", "Replacement gateway recovery failed"
            )
            status = controller.gateway_status()
            receiver["url"] = f"http://{status.gateway_host}:{status.gateway_port}"
            support._wait(
                lambda: (
                    support._request(receiver["url"], prefix + "/binding")[1].get("connection")
                    == "connected"
                ),
                "Replacement gateway did not recover its receiver",
                seconds=60,
            )
            support._wait(
                lambda: support._ready(receiver["url"]), "Restored body did not become ready"
            )
        time.sleep(0.4)
        _require(_invocations(root) == baseline + 2, "Retired native handoff reached a body later")
    return {
        "busy_refusal": True,
        "explicit_retry": True,
        "gateway_absence_no_replay": True,
        "body_replacement_fenced": True,
        "body_death_fenced": True,
    }


def _mail_cli(
    work: Path,
    gateway: dict[str, Any],
    arguments: list[str],
    *,
    success: bool = True,
) -> dict[str, Any]:
    """Call the independently installed CLI and retain no message bodies in evidence."""

    result = subprocess.run(
        [str(work / "venv/bin/houmao-cccc"), "--gateway-url", gateway["url"], *arguments],
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
        raise QualificationError("Installed Mail CLI operation failed: " + code[:128])
    return document


def _mail_upgrade_cases(
    support: ModuleType,
    work: Path,
    gateways: list[dict[str, Any]],
    controllers: list[Any],
    upgrade_wheel: Path,
) -> dict[str, bool]:
    """Upgrade only installed gateway code and exercise explicit bounded Mail decisions."""

    from houmao.gateway.plugins import GatewayPluginConfiguration

    print(json.dumps({"qualification_stage": "mail-package-upgrade"}), flush=True)
    for gateway in gateways:
        support._wait(
            lambda: support._ready(gateway["url"]), "Body was not ready before package upgrade"
        )
    snapshots = [_body_snapshot(controller) for controller in controllers]
    _require(
        any(
            getattr(controller.backend_session.state, "session_id", None) != snapshot[1]
            for controller, snapshot in zip(controllers, snapshots, strict=True)
        ),
        "Upgrade fixture did not retain a controller older than its gateway-authored conversation",
    )
    counts = [_invocations(item["root"]) for item in gateways]
    for controller in controllers:
        _require(controller.detach_gateway().status == "ok", "Pre-upgrade gateway detach failed")
    support._run(
        [
            str(work / "venv/bin/python"),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--no-index",
            "--no-deps",
            "--force-reinstall",
            str(upgrade_wheel),
        ],
        cwd=work,
        env=support._clean_environment(),
        log=work / "operations.log",
    )
    _require(importlib.metadata.version("houmao-cccc") == "0.2.0", "Plugin wheel upgrade failed")
    for controller, gateway, snapshot in zip(controllers, gateways, snapshots, strict=True):
        os.environ["HOUMAO_PLUGIN_FIXTURE_CONTROL"] = str(gateway["root"] / "control.json")
        selected = gateway["selection"].model_dump(mode="json")
        selected["plugins"]["cccc"]["config"]["mail_max_bytes"] = 1048576
        _require(
            controller.attach_gateway(
                plugin_config=GatewayPluginConfiguration.model_validate(selected)
            ).status
            == "ok",
            "Mail upgrade gateway restart failed",
        )
        status = controller.gateway_status()
        gateway["url"] = f"http://{status.gateway_host}:{status.gateway_port}"
        support._wait(
            lambda: (
                support._request(gateway["url"], "/v1/plugins/cccc/binding")[1].get("connection")
                == "connected"
            ),
            "Upgraded gateway did not recover its existing Actor lease",
            seconds=65,
        )
        current = support._request(gateway["url"], "/v1/plugins/cccc/binding")[1]
        _require(
            current["binding_id"] == gateway["binding"]["binding_id"],
            "Upgrade changed the owner binding",
        )
        _require(
            _body_snapshot(controller) == snapshot,
            "Package upgrade changed body PID or conversation",
        )
        code, _ = support._request(
            gateway["url"],
            "/v1/plugins/cccc/connection/refresh-credentials",
            {"expected_binding_id": current["binding_id"]},
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
            _body_snapshot(controller) == snapshot,
            "Credential refresh changed the body or conversation",
        )
    sender, receiver = gateways
    print(json.dumps({"qualification_stage": "mail-inspection-and-send"}), flush=True)
    preserved = _mail_cli(
        work, sender, ["chat", "history", "--event-ref", sender["existing_chat_ref"]]
    )
    _require(
        preserved["messages"][0]["id"] == sender["existing_chat_id"],
        "Upgrade invalidated an existing chat reference",
    )
    binding = ["--binding-id", receiver["binding"]["binding_id"]]

    def send_mail(text: str = "Synthetic deferred Mail") -> dict[str, Any]:
        """Send one explicit deferred operation through the installed CLI."""

        return _mail_cli(
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

        return _mail_cli(
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

    caps = _mail_cli(work, receiver, ["capabilities"])
    _require(
        isinstance(caps.get("mail"), dict) and caps["mail"].get("qualified") is True,
        "Upgraded provider did not negotiate the complete Mail contract",
    )
    first = send_mail()
    second = send_mail("Synthetic following Mail")
    _require(
        first.get("consumed") is False and first["event"]["data"]["message_mode"] == "mail",
        "Mail send did not remain deferred",
    )
    cursor = _mail_cli(work, receiver, ["mail", "cursor"])
    before = cursor["cursor_ref"]
    peek = _mail_cli(work, receiver, ["mail", "peek", "--limit", "1", "--max-bytes", "1048576"])
    repeated_peek = _mail_cli(work, receiver, ["mail", "peek", "--limit", "1"])
    _require(
        peek["messages"][0]["id"] == repeated_peek["messages"][0]["id"] == first["event"]["id"],
        "Mail peek changed the ordered pending batch",
    )
    _require(
        _mail_cli(work, receiver, ["mail", "cursor"])["cursor_ref"] == before,
        "Non-consuming Mail inspection advanced the cursor",
    )
    reply = _mail_cli(
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
        _mail_cli(work, receiver, ["mail", "cursor"])["cursor_ref"] == before,
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
    receipt = _mail_cli(work, receiver, ["mail", "reads", "--operation-id", operation_id])
    _require(
        receipt.get("found") is True and receipt["receipt"]["event_ids"] == [first["event"]["id"]],
        "Read receipt did not preserve the exact consumed prefix",
    )
    wrong_receipt = _mail_cli(
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
    following = _mail_cli(work, receiver, ["mail", "peek", "--limit", "1"])
    _require(
        following["messages"][0]["id"] == second["event"]["id"],
        "Receipt reconciliation consumed the following batch",
    )
    stale = read_mail(uuid.uuid4().hex, before, success=False)
    _require(stale.get("error_code") == "cursor_conflict", "Stale Mail cursor did not conflict")
    wrong_owner = _mail_cli(
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
    recovered = _mail_cli(
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
        connection.request(
            "POST",
            "/v1/plugins/cccc/mail/read",
            body=json.dumps(
                {
                    "expected_binding_id": receiver["binding"]["binding_id"],
                    "operation_id": lost_operation,
                    "expected_cursor": following["cursor_ref"],
                    "limit": 1,
                    "max_bytes": 262144,
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        saved: dict[str, Any] = {}

        def read_committed() -> bool:
            """Reconcile only the known operation without accepting its lost response."""

            result = _mail_cli(work, receiver, ["mail", "reads", "--operation-id", lost_operation])
            saved.update(result)
            return result.get("found") is True

        support._wait(read_committed, "Discarded read response had no authoritative receipt")
    finally:
        connection.close()
    _require(
        saved["receipt"]["event_ids"] == [second["event"]["id"]],
        "Lost response reconciliation changed the consumed batch",
    )
    _require(len(saved["receipt"]["event_refs"]) == 1, "Receipt omitted scoped recovery references")
    lost_content = _mail_cli(
        work, receiver, ["chat", "history", "--event-ref", saved["receipt"]["event_refs"][0]]
    )
    _require(
        lost_content["messages"][0]["id"] == second["event"]["id"],
        "Receipt reference did not recover lost content",
    )
    after_loss = _mail_cli(work, receiver, ["mail", "peek", "--limit", "1"])
    _require(
        after_loss["messages"][0]["id"] == after_lost_batch["event"]["id"],
        "Lost-response recovery consumed the following batch",
    )
    read_mail(uuid.uuid4().hex, after_loss["cursor_ref"])
    empty_cursor = _mail_cli(work, receiver, ["mail", "cursor"])["cursor_ref"]
    empty_id = uuid.uuid4().hex
    _require(
        read_mail(empty_id, empty_cursor)["outcome"] == "empty", "Empty Mail read was not recorded"
    )
    third = send_mail("Synthetic post-empty Mail")
    _require(
        read_mail(empty_id, empty_cursor)["outcome"] == "already_completed",
        "Empty read identity was reused as new consumption",
    )
    pending = _mail_cli(work, receiver, ["mail", "peek", "--limit", "200"])
    _require(
        pending["messages"][0]["id"] == third["event"]["id"],
        "Repeating an empty read consumed later Mail",
    )
    read_mail(uuid.uuid4().hex, pending["cursor_ref"])
    send_mail("Synthetic oversized first Mail " + "x" * 5000)
    print(json.dumps({"qualification_stage": "mail-precommit-byte-bound"}), flush=True)
    large_cursor = _mail_cli(work, receiver, ["mail", "cursor"])["cursor_ref"]
    too_large = read_mail(uuid.uuid4().hex, large_cursor, max_bytes=4096, success=False)
    _require(
        too_large.get("error_code") == "content_limit",
        "Oversized head Mail did not fail before commit",
    )
    _require(
        _mail_cli(work, receiver, ["mail", "cursor"])["cursor_ref"] == large_cursor,
        "Oversized read advanced the cursor",
    )
    unknown = _mail_cli(work, receiver, ["mail", "reads", "--operation-id", uuid.uuid4().hex])
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
    support._wait(lambda: support._ready(receiver["url"]), "Upgraded chat handoff did not finish")
    _require(
        _invocations(receiver["root"]) == counts[1] + 1,
        "Upgraded Mail package broke ordinary chat admission",
    )
    return {
        "mail_upgrade_preserved_body": True,
        "stale_controller_upgrade_preserved": True,
        "mail_cli": True,
        "mail_deferred": True,
        "mail_non_consuming_inspection": True,
        "mail_ordered_read": True,
        "mail_receipt_recovery": True,
        "mail_lost_response": True,
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
    previous_plugin_wheel: Path | None = None,
    upgrade_plugin_wheel: Path | None = None,
) -> dict[str, object]:
    """Run real installed gateways with synthetic body executables and actual CCCC."""

    import httpx
    import houmao
    import houmao_cccc
    import houmao_gateway_fixtures
    from houmao.agents.realm_controller.runtime import start_runtime_session
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
    results: list[dict[str, object]] = []
    with httpx.Client(
        base_url=endpoint,
        headers={"Origin": endpoint, "Referer": endpoint + "/"},
        trust_env=False,
        follow_redirects=False,
        timeout=25,
    ) as administrator:
        for mode in ("detached_process", "tmux_auxiliary_window"):
            if previous_plugin_wheel is not None:
                support._run(
                    [
                        str(work / "venv/bin/python"),
                        "-m",
                        "pip",
                        "--isolated",
                        "install",
                        "--no-index",
                        "--no-deps",
                        "--force-reinstall",
                        str(previous_plugin_wheel),
                    ],
                    cwd=work,
                    env=support._clean_environment(),
                    log=work / "operations.log",
                )
                _require(
                    importlib.metadata.version("houmao-cccc") == "0.1.0",
                    "Upgrade requires the qualified 0.1.0 package",
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
                            "/api/v1/external-receiver/v1/grants",
                            json={"group_id": group_id, "actor_id": actor_id},
                        )
                    )
                    owner = uuid.uuid4().hex
                    credentials = root / "actor-credential.json"
                    credentials.write_text(
                        json.dumps(
                            {
                                "agent_id": owner,
                                "endpoint": endpoint,
                                "group_id": group_id,
                                "actor_id": actor_id,
                                "actor_generation": grant["actor_generation"],
                                "token": grant["token"],
                            }
                        )
                    )
                    credentials.chmod(0o600)
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
                    controller = start_runtime_session(
                        agent_def_dir=root / "agent-def",
                        brain_manifest_path=brain,
                        role_name="qualification",
                        runtime_root=root / "runtime",
                        backend="codex_headless",
                        working_directory=workspace,
                        agent_name="cccc-installed-" + uuid.uuid4().hex[:10],
                        agent_id=owner,
                    )
                    controllers.append(controller)
                    controller.send_prompt("Synthetic conversation before plugin attachment")
                    before_attach = _body_snapshot(controller)
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
                                    },
                                }
                            }
                        }
                    )
                    if actor_id == "sender":
                        broad = controller.attach_gateway(
                            host_override="0.0.0.0",
                            port_override=0,
                            execution_mode_override=mode,
                            plugin_config=selection,
                        )
                        _require(broad.status == "ok", "Broad-listener core gateway did not start")
                        broad_status = controller.gateway_status()
                        broad_url = f"http://127.0.0.1:{broad_status.gateway_port}"
                        code, _ = support._request(broad_url, "/v1/plugins/cccc/binding")
                        _require(code == 503, "Broad listener activated CCCC credentials or routes")
                        _require(
                            controller.detach_gateway().status == "ok",
                            "Broad gateway cleanup failed",
                        )
                    attached = controller.attach_gateway(
                        host_override="127.0.0.1",
                        port_override=0,
                        execution_mode_override=mode,
                        plugin_config=selection,
                    )
                    _require(attached.status == "ok", "Normal installed gateway attach failed")
                    status = controller.gateway_status()
                    url = f"http://{status.gateway_host}:{status.gateway_port}"
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
                        _body_snapshot(controller) == before_attach,
                        "Plugin attachment changed the live body PID or native conversation",
                    )
                    gateways.append(
                        {"url": url, "binding": binding, "root": root, "selection": selection}
                    )
                sender, receiver = gateways
                prefix = "/v1/plugins/cccc"
                status, stored = support._request(
                    sender["url"],
                    prefix + "/chat/send",
                    {
                        "expected_binding_id": sender["binding"]["binding_id"],
                        "operation_id": uuid.uuid4().hex,
                        "to": ["receiver"],
                        "text": "Synthetic installed chat",
                        "mode": "send",
                    },
                )
                _require(
                    status == 200 and stored.get("stored") is True, "Installed chat send failed"
                )
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
                        "expected_binding_id": receiver["binding"]["binding_id"],
                        "operation_id": uuid.uuid4().hex,
                        "event_ref": event_ref,
                        "text": "Synthetic invalid owner ref",
                    },
                )
                _require(code == 422, "Another owner reused a targeting reference")
                code, reply = support._request(
                    receiver["url"],
                    prefix + "/chat/reply",
                    {
                        "expected_binding_id": receiver["binding"]["binding_id"],
                        "operation_id": uuid.uuid4().hex,
                        "event_ref": receiver_ref,
                        "text": "Synthetic installed reply",
                    },
                )
                _require(
                    code == 200 and reply["event"]["data"]["reply_to"] == event_id,
                    "Installed reply ancestry failed",
                )
                support._wait(
                    lambda: (receiver["root"] / "invocations").exists(),
                    "Fixture receiver never ran",
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
                gateway_status = controllers[1].gateway_status()
                new_url = f"http://{gateway_status.gateway_host}:{gateway_status.gateway_port}"
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
                receiver["url"] = new_url
                if upgrade_plugin_wheel is not None:
                    sender.update(existing_chat_ref=event_ref, existing_chat_id=event_id)
                    failures = _mail_upgrade_cases(
                        support, work, gateways, controllers, upgrade_plugin_wheel
                    )
                else:
                    failures = _failure_cases(support, sender, receiver, controllers[1])
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
                        "broad_listener_disabled": True,
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
        "action": "run-mail" if upgrade_plugin_wheel is not None else "run",
        "checkout_imports": False,
        "offline_install": True,
        "actual_cccc": True,
        "stand_in_bodies": True,
        "real_agent_smoke": "separate_required_qualification",
        "cleanup": "completed",
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("Houmao", "houmao-cccc", "houmao-gateway-qualification-fixtures")
        },
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
    parser.add_argument("--previous-plugin-wheel", type=Path)
    parser.add_argument("--upgrade-plugin-wheel", type=Path)
    arguments = parser.parse_args()
    source = (arguments.source_root or Path(__file__).resolve().parents[3]).resolve()
    try:
        if arguments.action in {"installed-run", "installed-mail-run"}:
            _require(arguments.work_root is not None, "Setup requires an external work root")
            _require(
                arguments.endpoint is not None,
                "Setup requires an explicit compatible CCCC endpoint",
            )
            if arguments.action == "installed-mail-run":
                _require(
                    arguments.previous_plugin_wheel is not None
                    and arguments.upgrade_plugin_wheel is not None,
                    "Mail qualification requires previous and upgraded package wheels",
                )
            report = _installed(
                source,
                arguments.work_root.resolve(),
                arguments.endpoint,
                previous_plugin_wheel=arguments.previous_plugin_wheel,
                upgrade_plugin_wheel=arguments.upgrade_plugin_wheel,
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
                _require(
                    arguments.action != "run-mail" or arguments.previous_plugin_wheel is not None,
                    "Mail upgrade qualification requires the frozen previous plugin wheel",
                )
                report = qualify(
                    source,
                    wheelhouse,
                    _root(arguments.work_root, source),
                    arguments.endpoint,
                    previous_plugin_wheel=(
                        arguments.previous_plugin_wheel if arguments.action == "run-mail" else None
                    ),
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
