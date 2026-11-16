"""Exercise the actual Web companion's validation and authorization boundaries."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize(
    "principal,protocol,operation,expected",
    [
        ("owner", 1, "describe", None),
        ("guest", 1, "describe", "forbidden"),
        ("owner", 99, "describe", "protocol_mismatch"),
        ("owner", 1, "prompt", "unavailable"),
        ("owner", 1, "unknown", "unsupported_operation"),
    ],
)
def test_native_web_companion_refuses_before_activation(
    tmp_path: Path, principal: str, protocol: int, operation: str, expected: str | None
) -> None:
    """Invoke the shipped native route against a minimal authenticated service boundary."""

    bun = shutil.which("bun")
    if bun is None:
        pytest.skip("Bun is required for packaged ECMAScript checks")
    asset = Path(__file__).resolve().parents[4] / "src/houmao/agents/assets/dsh/managed-web.mjs"
    control = {
        "version": 1,
        "mode": "web",
        "agent_id": "logical",
        "runtime_session_id": "runtime",
        "generation": "generation",
        "working_directory": str(tmp_path),
        "state_path": str(tmp_path / "state.json"),
        "evidence_path": str(tmp_path / "evidence.jsonl"),
        "bootstrap_path": str(tmp_path / "bootstrap.json"),
        "provider": "controlled",
        "model": "controlled",
    }
    control_path = tmp_path / "control.json"
    control_path.write_text(json.dumps(control))
    script = tmp_path / "invoke.mjs"
    script.write_text(r"""
import { pathToFileURL } from 'node:url';
import { Readable } from 'node:stream';
import { EventEmitter } from 'node:events';
const [asset, controlFile, principal, version, operation] = process.argv.slice(2);
const plugin = await import(pathToFileURL(asset));
const cleanup = [];
let route;
let activations = 0;
const ctx = {
  on() {},
  inject(keys, callback) { callback(ctx); },
  effect(callback) { const release = callback(); if (typeof release === 'function') cleanup.push(release); return () => {}; },
  webServer: {port: undefined, register(value) { route = value; return () => {}; }},
  connection: {admit() { return {peer: {principal: {kind: principal}, signal: new AbortController().signal}}; }},
  agents: {get() { return undefined; }, create() { activations++; }, resume() { activations++; }},
  sessions: {get() { return undefined; }},
};
plugin.apply(ctx, {controlFile});
const endpoint = `managed/v1/${operation}`;
const input = {type: 'client-request', rpcId: 'operation', method: endpoint, payload: {protocol_version: Number(version), identity: {}, text: 'PRIVATE INPUT', operation_id: 'input', deadline_epoch_ms: Date.now() + 1000}};
const req = Readable.from([Buffer.from(JSON.stringify(input))]);
Object.assign(req, {method: 'POST', url: `/houmao/${endpoint}`, headers: {'content-type': 'application/json'}});
const res = new EventEmitter();
let body;
res.writeHead = () => {};
res.end = data => { body = JSON.parse(data); res.writableEnded = true; };
try {
  await route.handler(req, res);
  console.log(JSON.stringify({body, activations}));
} finally { for (const release of cleanup.reverse()) await release(); }
""")
    result = subprocess.run(
        [bun, str(script), str(asset), str(control_path), principal, str(protocol), operation],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = json.loads(result.stdout)
    assert output["activations"] == 0
    assert "PRIVATE INPUT" not in result.stdout
    assert "PRIVATE INPUT" not in (tmp_path / "state.json").read_text()
    response = output["body"]["result"]
    if expected is None:
        assert response["ok"] is True
        assert response["value"]["protocol_version"] == 1
        assert response["value"]["identity"]["native_session_id"] is None
    else:
        assert response["ok"] is False
        assert response["error"]["code"] == expected


@pytest.mark.parametrize(
    "case",
    [
        "verified",
        "wrong-sequence",
        "wrong-message",
        "wrong-route",
        "wrong-session",
        "wrong-runtime",
        "open-turn",
    ],
)
def test_restored_receipt_requires_exact_native_claim_and_terminal(
    tmp_path: Path, case: str
) -> None:
    """Read-only recovery retains original identity and refuses incomplete ownership proof."""

    bun = shutil.which("bun")
    if bun is None:
        pytest.skip("Bun is required for packaged ECMAScript checks")
    asset = Path(__file__).resolve().parents[4] / "src/houmao/agents/assets/dsh/managed-web.mjs"
    receipt = {
        "operation_id": "operation",
        "message_id": "managed-input",
        "status": "claimed",
        "turns": [1],
        "claims": [{"turn": 1, "native_sequence": 2}],
        "identity": {
            "agent_id": "logical",
            "runtime_session_id": "runtime",
            "generation": "original-generation",
            "native_session_id": "native",
            "host_incarnation": "original-host",
            "agent_incarnation": "original-agent",
        },
    }
    events = [
        {
            "seq": 0,
            "type": "agent/inbox/spliced",
            "data": {
                "target": "next-turn",
                "start": 0,
                "removedCount": 0,
                "inserted": [
                    {
                        "id": "managed-input",
                        "source": {"kind": "user", "rpcId": "houmao:operation"},
                        "content": "PRIVATE INPUT",
                    }
                ],
            },
        },
        {"seq": 1, "type": "turn/start", "data": {"turn": 1}},
        {
            "seq": 2,
            "type": "agent/inbox/spliced",
            "data": {"target": "next-turn", "start": 0, "removedCount": 1, "inserted": []},
        },
        {"seq": 3, "type": "step/start", "data": {"turn": 1, "step": 1}},
        {"seq": 4, "type": "step/end", "data": {"turn": 1, "step": 1}},
        {"seq": 5, "type": "turn/end", "data": {"turn": 1, "reason": {"kind": "interrupted"}}},
    ]
    if case == "wrong-sequence":
        receipt["claims"][0]["native_sequence"] = 1
    elif case == "wrong-message":
        receipt["message_id"] = "another-input"
    elif case == "wrong-route":
        events[0]["data"]["inserted"][0]["source"]["rpcId"] = "houmao:another-operation"
    elif case == "wrong-session":
        receipt["identity"]["native_session_id"] = "another-native"
    elif case == "wrong-runtime":
        receipt["identity"]["runtime_session_id"] = "another-runtime"
    elif case == "open-turn":
        events.pop()
    original_identity = dict(receipt["identity"])
    payload = tmp_path / "input.json"
    payload.write_text(json.dumps({"receipt": receipt, "events": events}))
    script = tmp_path / "reconcile.mjs"
    script.write_text(r"""
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const [asset, payload] = process.argv.slice(2);
const {reconcileNativeReceipts} = await import(pathToFileURL(asset));
const {receipt, events} = JSON.parse(readFileSync(payload, 'utf8'));
const before = JSON.stringify(events);
const settled = reconcileNativeReceipts({id: 'native', seq: events.length, eventAt: seq => events[seq]}, [receipt], {agent_id: 'logical', runtime_session_id: 'runtime'});
console.log(JSON.stringify({count: settled.length, receipt, unchanged: before === JSON.stringify(events)}));
""")
    result = subprocess.run(
        [bun, str(script), str(asset), str(payload)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = json.loads(result.stdout)
    assert output["unchanged"] is True
    assert "PRIVATE INPUT" not in result.stdout
    assert output["receipt"]["identity"] == original_identity
    if case == "verified":
        assert output["count"] == 1
        assert output["receipt"]["status"] == "terminal"
        assert output["receipt"]["result"] == "interrupted"
        assert output["receipt"]["end_sequence"] == 5
        assert output["receipt"]["mixed_input"] == "unknown"
    else:
        assert output["count"] == 0
        assert output["receipt"]["status"] == "claimed"
