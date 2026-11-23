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


@pytest.mark.parametrize("case", ["invalid-workdir", "attach-rejected", "attach-committed"])
def test_native_web_workspace_failure_keeps_exact_candidate(tmp_path: Path, case: str) -> None:
    """Publish only verified membership and reconcile uncertain attach without a new ID."""

    bun = shutil.which("bun")
    if bun is None:
        pytest.skip("Bun is required for packaged ECMAScript checks")
    asset = Path(__file__).resolve().parents[4] / "src/houmao/agents/assets/dsh/managed-web.mjs"
    native_module = tmp_path / "node_modules" / "@deepseek-ai" / "dsh-agent"
    native_module.mkdir(parents=True)
    (native_module / "package.json").write_text('{"main":"index.mjs"}')
    (native_module / "index.mjs").write_text("export function installModelSelection() {}")

    control_path = tmp_path / "control.json"
    control_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "web",
                "agent_id": "logical",
                "runtime_session_id": "runtime",
                "generation": "generation",
                "working_directory": str(tmp_path),
                "expected_native_session_id": "retained",
                "state_path": str(tmp_path / "state.json"),
                "evidence_path": str(tmp_path / "evidence.jsonl"),
                "bootstrap_path": str(tmp_path / "bootstrap.json"),
                "provider": "controlled",
                "model": "controlled",
                "native_version": "0.2.2-rc.3",
            }
        )
    )
    script = tmp_path / "workspace.mjs"
    script.write_text(r"""
import { EventEmitter } from 'node:events';
import { readFileSync } from 'node:fs';
import { Readable } from 'node:stream';
import { pathToFileURL } from 'node:url';
const [asset, controlFile, scenario] = process.argv.slice(2);
const plugin = await import(pathToFileURL(asset));
const { working_directory: cwd } = JSON.parse(readFileSync(controlFile, 'utf8'));
const peer = {principal: {kind: 'owner'}, signal: new AbortController().signal};
const listeners = new Map();
const resumeIds = [];
const attachments = [];
let route;
let live;
let publications = 0;
const session = {id: 'retained', header: {cwd}, seq: 0};
const workspace = {
  id: 'workspace',
  path: cwd,
  sessionIds: ['other-member'],
  async attachSession(id) {
    attachments.push(id);
    const first = attachments.length === 1;
    if (first && scenario === 'attach-rejected') throw new Error('PRIVATE NATIVE ERROR');
    this.sessionIds.push(id);
    if (first && scenario === 'attach-committed') throw new Error('PRIVATE NATIVE ERROR');
  },
};
const ctx = {
  on(event, callback) { listeners.set(event, callback); },
  inject() {},
  effect(callback) { callback(); },
  webServer: {register(value) { route = value; }},
  connection: {admit() { return {peer}; }},
  workspaceRegistry: {
    get() { return workspace; },
    async create() {
      if (scenario === 'invalid-workdir') throw new Error('PRIVATE NATIVE ERROR');
      return workspace;
    },
  },
  agentPresets: { async resolve() { return {id: 'preset'}; }, async mount() {} },
  sessionQuery: { async observeSession() { return {header: session.header, [Symbol.dispose]() {}}; }},
  sessions: {get(id) { return live?.id === id ? live.session : undefined; }},
  agents: {
    get(id) { return live?.id === id ? live : undefined; },
    async resume({resumeSessionId, setup}) {
      resumeIds.push(resumeSessionId);
      const agent = {
        id: resumeSessionId,
        session,
        inbox: {nextTurn: [], nextStep: [], hasPending: false},
      };
      await setup({}, agent);
      live = agent;
      await listeners.get('agent/created')({agent});
      publications++;
      return {agent};
    },
  },
};
plugin.apply(ctx, {controlFile});
async function request(operation, payload = {}) {
  const endpoint = 'managed/v1/' + operation;
  const body = { type: 'client-request', rpcId: operation, method: endpoint,
    payload: {protocol_version: 1, ...payload} };
  const req = Readable.from([Buffer.from(JSON.stringify(body))]);
  Object.assign(req, {method: 'POST', url: '/houmao/' + endpoint,
    headers: {'content-type': 'application/json'}});
  const res = new EventEmitter();
  let result;
  res.writeHead = () => {};
  res.end = data => {
    result = JSON.parse(data).result;
    res.writableEnded = true;
  };
  await route.handler(req, res);
  return result;
}
const selection = {mode: 'exact', session_id: 'retained'};
const first = await request('start', selection);
const publishedAfterFirst = (await request('describe')).value.identity.native_session_id;
const retry = scenario === 'attach-rejected' ? await request('start', selection) : null;
console.log(JSON.stringify({first, publishedAfterFirst, retry, resumeIds, attachments,
  publications, members: workspace.sessionIds}));
""")
    result = subprocess.run(
        [bun, str(script), str(asset), str(control_path), case],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = json.loads(result.stdout)
    assert "PRIVATE NATIVE ERROR" not in result.stdout + result.stderr
    assert not (tmp_path / "state.json.diagnostics").exists()
    if case == "invalid-workdir":
        assert output["first"]["error"]["code"] == "workspace_unavailable"
        assert output["publishedAfterFirst"] is None
        assert output["resumeIds"] == output["attachments"] == []
        assert output["members"] == ["other-member"]
        assert output["publications"] == 0
    elif case == "attach-rejected":
        assert output["first"]["error"]["code"] == "workspace_membership_unavailable"
        assert output["publishedAfterFirst"] is None
        assert output["retry"]["value"]["native_session_id"] == "retained"
        assert output["attachments"] == output["resumeIds"] == ["retained", "retained"]
        assert output["members"] == ["other-member", "retained"]
        assert output["publications"] == 1
    else:
        assert output["first"]["ok"] is True
        assert output["publishedAfterFirst"] == "retained"
        assert output["attachments"] == output["resumeIds"] == ["retained"]
        assert output["members"] == ["other-member", "retained"]
        assert output["publications"] == 1


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
