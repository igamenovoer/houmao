#!/usr/bin/env python3
"""Qualify live online controls and reminders with an isolated fake agent body.

This development utility intentionally uses the repository's deterministic gateway
fixture. Stalwart and its normal-account requests are real; the agent body is a
small subprocess, not an LLM CLI. All generated runtime state stays outside Git.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import resource
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.gateway_storage import read_gateway_notifier_audit_records
from houmao.mailbox.stalwart import StalwartJmapClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tests.unit.agents.realm_controller.test_gateway_dual_mail import _runtime  # noqa: E402
from tests.unit.agents.realm_controller.test_gateway_support import _FakeCaoRestClient  # noqa: E402


def _wait(predicate: Callable[[], bool]) -> None:
    """Yield a finite fake-body dispatch deadline."""
    deadline = monotonic() + 5
    while monotonic() < deadline:
        if predicate():
            return
        sleep(0.02)
    raise RuntimeError("fake-body qualification dispatch deadline exceeded")


def qualify(args: argparse.Namespace) -> dict[str, object]:
    """Exercise real normal-account activation without management access."""
    root = args.work_dir.resolve()
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    transcript = root / "fake-body-transcript.jsonl"
    body_program = (
        "import json,sys\nfrom pathlib import Path\n"
        "path=Path(sys.argv[1])\n"
        "for line in sys.stdin:\n"
        " with path.open('a') as stream: stream.write(json.dumps({'conversation':'fixed','prompt_received':True})+'\\n')\n"
    )
    body = subprocess.Popen(
        [sys.executable, "-u", "-c", body_program, str(transcript)],
        stdin=subprocess.PIPE,
        text=True,
    )
    original_pid = body.pid
    runtime = None
    client = StalwartJmapClient(
        jmap_url=args.discovery_url,
        login_identity=args.login,
        credential_file=args.credential_file,
        sender_address=args.address,
    )
    fixture_id = None
    try:
        client.validate_binding()
        # Explicit provider test setup: self-delivery can deduplicate against Sent.
        # Moving this unique owned test message into Inbox establishes eligible work.
        fixture = client.send(
            sender_address=args.address,
            to_addresses=[args.address],
            cc_addresses=[],
            subject="Houmao runtime qualification " + uuid4().hex,
            body_content="Disposable local qualification work.",
            attachments=[],
        )
        fixture_id = str(fixture["id"])
        client.move(message_ref=fixture_id, destination_box="inbox")
        with pytest.MonkeyPatch.context() as patch:
            runtime = _runtime(root, patch, dual=False, enabled=False)

            class BodyClient(_FakeCaoRestClient):
                """Dispatch through the test transport into the stable fake-body process."""

                def send_terminal_input(self, terminal_id: str, message: str):
                    assert body.poll() is None and body.stdin is not None
                    body.stdin.write(message.replace("\n", " ") + "\n")
                    body.stdin.flush()
                    return super().send_terminal_input(terminal_id, message)

            transport = BodyClient(base_url="http://127.0.0.1:9889")
            patch.setattr(
                "houmao.agents.realm_controller.gateway_service.CaoRestClient",
                lambda *a, **k: transport,
            )
            patch.setattr(
                GatewayServiceRuntime, "_tui_prompt_not_ready_reasons_locked", lambda self: []
            )
            # Build again after selecting the body transport, preserving seeded runtime.
            runtime = GatewayServiceRuntime.from_gateway_root(
                gateway_root=runtime.m_paths.gateway_root, host="127.0.0.1", port=43123
            )
            original = runtime._load_manifest_payload_for_mailbox_support().model_dump(mode="json")
            http = TestClient(create_app(runtime=runtime))
            status = http.get("/v1/mail/online/binding").json()
            attached = http.put(
                "/v1/mail/online/binding",
                json={
                    "expected_revision": status["revision"],
                    "jmap_url": args.discovery_url,
                    "address": args.address,
                    "login_identity": args.login,
                    "credential_source_ref": str(args.credential_file.resolve()),
                },
            )
            assert attached.status_code == 200, "normal-account attachment failed"
            active = attached.json()
            binding_id = active["binding_id"]
            page = http.post(
                "/v1/mail/online/list", json={"expected_binding_id": binding_id, "limit": 2}
            )
            assert page.status_code == 200 and all(
                m["body_text"] is None for m in page.json()["messages"]
            )
            runtime.start()
            patch.setattr(runtime, "_notifier_block_detail_locked", lambda **kwargs: None)
            clock = [datetime.now(UTC).replace(microsecond=0)]
            patch.setattr(
                "houmao.agents.realm_controller.gateway_service.now_utc_iso",
                lambda: clock[0].isoformat(),
            )
            assert (
                http.put("/v1/mail-notifier/online", json={"interval_seconds": 3600}).status_code
                == 200
            )
            runtime._run_notifier_cycle(channel="online")
            _wait(lambda: transcript.exists())
            _wait(lambda: runtime.status().queue_depth == 0)
            runtime._run_notifier_cycle(channel="online")
            clock[0] += timedelta(hours=1)
            runtime._run_notifier_cycle(channel="online")
            _wait(lambda: len(transcript.read_text().splitlines()) >= 2)
            _wait(lambda: runtime.status().queue_depth == 0)
            audit = read_gateway_notifier_audit_records(runtime.m_paths.queue_path)
            enqueued = sum(row.outcome == "enqueued" for row in audit)
            assert enqueued == 2 and any(row.outcome == "dedup_skip" for row in audit)
            refreshed = http.post(
                "/v1/mail/online/binding/refresh", json={"expected_revision": active["revision"]}
            )
            assert refreshed.status_code == 200
            fresh = refreshed.json()
            assert fresh["binding_id"] == binding_id and fresh["revision"] != active["revision"]
            reconnected = http.post(
                "/v1/mail/online/binding/reconnect", json={"expected_revision": fresh["revision"]}
            )
            assert (
                reconnected.status_code == 200
                and reconnected.json()["epoch_id"] != fresh["epoch_id"]
            )
            runtime.shutdown()
            runtime = GatewayServiceRuntime.from_gateway_root(
                gateway_root=runtime.m_paths.gateway_root, host="127.0.0.1", port=43123
            )
            http = TestClient(create_app(runtime=runtime))
            after_restart = http.get("/v1/mail-notifier/online").json()
            assert after_restart["sync"]["available"]
            detached = http.request(
                "DELETE", "/v1/mail/online/binding", json={"expected_revision": fresh["revision"]}
            )
            assert detached.status_code == 200 and detached.json()["state"] == "absent"
            final = runtime._load_manifest_payload_for_mailbox_support().model_dump(mode="json")
            assert (
                final["runtime"] == original["runtime"]
                and final["agent_id"] == original["agent_id"]
            )
            assert body.poll() is None and body.pid == original_pid
            return {
                "success": True,
                "service_release": args.service_release,
                "accounts_bound": 1,
                "body": "fake subprocess",
                "body_pid_stable": True,
                "conversation_marker_stable": True,
                "gateway": "in-process HTTP ASGI fixture",
                "attachment_requires_management": False,
                "metadata_body_free": True,
                "refresh_binding_preserved": True,
                "reconnect_epoch_changed": True,
                "restart_sync_recovered": True,
                "detached": True,
                "unchanged_work_reminders": enqueued,
                "same_cycle_duplicates_suppressed": True,
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "scale": "one account, two reminder cycles; no target-scale capacity claim",
            }
    finally:
        if runtime is not None:
            runtime.shutdown()
        body.terminate()
        body.wait(timeout=5)
        if fixture_id is not None:
            client.archive(message_ref=fixture_id)


def main() -> int:
    """Require protected explicit input and write only a sanitized external report."""
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("discovery-url", "login", "address", "service-release"):
        parser.add_argument("--" + flag, required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    if args.work_dir.resolve().is_relative_to(repo_root):
        parser.error("--work-dir must be a new directory outside the checkout")
    report = qualify(args)
    path = args.work_dir / "runtime-report.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    path.chmod(0o600)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
