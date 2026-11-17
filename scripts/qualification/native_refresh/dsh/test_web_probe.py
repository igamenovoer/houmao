"""Qualify configuration-only reload on an explicitly selected controlled Web host.

This operational qualification utility reuses the credential-free native fixture.
It does not implement or advertise Houmao refresh support.
"""

from collections.abc import Callable
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any

from tests.integration.agents.dsh.conftest import (
    controlled_messages_server as controlled_messages_server,
    dsh_executable as dsh_executable,
)
from tests.integration.agents.dsh.web.conftest import (
    NativeWebHost,
    native_web_factory as native_web_factory,
)


MCP_SERVER = """const rl=require('node:readline').createInterface({input:process.stdin});
rl.on('line',line=>{
  const r=JSON.parse(line); if(r.id===undefined)return; let result;
  if(r.method==='initialize')result={protocolVersion:r.params.protocolVersion,
    capabilities:{tools:{}},serverInfo:{name:'controlled',version:'1'}};
  else if(r.method==='tools/list')result={tools:[{name:'marker_'+process.argv[2],
    description:'Controlled marker',inputSchema:{type:'object',properties:{}}}]};
  else if(r.method==='ping')result={};
  else {console.log(JSON.stringify({jsonrpc:'2.0',id:r.id,
    error:{code:-32601,message:'Method not found'}}));return;}
  console.log(JSON.stringify({jsonrpc:'2.0',id:r.id,result}));
});
"""


def _write_skill(root: Path, name: str, description: str) -> None:
    """Write only synthetic skills inside this fixture's private home."""

    directory = root / name
    directory.mkdir(exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nbody\n", encoding="utf-8"
    )


def _request(host: NativeWebHost, method: str) -> dict[str, Any]:
    """Read a qualification snapshot or explicitly reload through native maintenance."""

    assert host.client.m_http is not None
    response = host.client.m_http.request(method, "/qualification-refresh")
    assert response.status_code == 200, response.text
    payload: dict[str, Any] = response.json()
    return payload["after"] if method == "POST" else payload


def _wait_tools(host: NativeWebHost, expected: list[str]) -> dict[str, Any]:
    """Observe the actual scoped tool registry after asynchronous MCP reconciliation."""

    deadline = time.monotonic() + 5
    snapshot = _request(host, "GET")
    while snapshot["tools"] != expected and time.monotonic() < deadline:
        time.sleep(0.02)
        snapshot = _request(host, "GET")
    assert snapshot["tools"] == expected
    return snapshot


def test_same_session_configuration_only_reload(
    tmp_path: Path,
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Keep the bound agent and journal while reloading skills, MCP and configuration."""

    modules_value = os.environ.get("HOUMAO_DSH_NODE_MODULES")
    assert modules_value, "Select HOUMAO_DSH_NODE_MODULES explicitly"
    modules = Path(modules_value).resolve(strict=True)
    selected = Path(os.environ["HOUMAO_DSH_EXECUTABLE"]).resolve(strict=True)
    assert selected == (modules / "@deepseek-ai/dsh/lib/bin.js").resolve(strict=True)
    root = tmp_path / "selected"
    root.mkdir()
    skills = root / "skills"
    skills.mkdir()
    _write_skill(skills, "alpha", "initial")
    native = root / "native.mjs"
    native.write_text(
        "export const name='native-probe';"
        "export function apply(ctx,cfg){ctx.provide('probeNativeConfig',cfg.value)}\n",
        encoding="utf-8",
    )
    mcp_server = root / "server.cjs"
    mcp_server.write_text(MCP_SERVER, encoding="utf-8")
    host = native_web_factory(
        root=root,
        extra_plugins=[
            {
                "id": "probe",
                "name": str(Path(__file__).with_name("web-probe-plugin.mjs")),
                "config": {"cwd": str(root)},
            }
        ],
    )
    patch = root / "dsh-home" / "cordis.patch.yml"
    native_row: dict[str, Any] = {
        "id": "probe-native-config",
        "name": str(native),
        "config": {"value": "initial"},
    }
    rows: list[dict[str, Any]] = [
        {
            "insert": [
                native_row,
                {
                    "id": "probe-skill-filesystem",
                    "name": str(modules / "@deepseek-ai/dsh-skill-filesystem/lib/index.js"),
                    "config": {
                        "includeDefaultRoots": False,
                        "providerName": "probe-explicit",
                        "customSkillDirs": [str(skills)],
                        "watch": False,
                    },
                },
            ]
        }
    ]
    patch.write_text(json.dumps(rows), encoding="utf-8")
    initial = _request(host, "POST")
    identity = dict(host.identity)
    _write_skill(skills, "alpha", "edited")
    _write_skill(skills, "beta", "added")
    native_row["config"]["value"] = "edited"
    node = shutil.which("node")
    assert node is not None
    server_entry: dict[str, Any] = {
        "transport": "stdio",
        "command": node,
        "args": [str(mcp_server), "v1"],
        "startupTimeoutMs": 2000,
        "closeTimeoutMs": 1000,
        "reconnect": {"enabled": False},
    }
    manager_row = {"id": "mcp-manager", "config": {"servers": {"probe": server_entry}}}
    rows.append(manager_row)
    patch.write_text(json.dumps(rows), encoding="utf-8")
    time.sleep(0.4)
    before = _request(host, "GET")
    assert before["config"] == "initial"
    assert next(s for s in before["skills"] if s["name"] == "alpha")["description"] == "initial"
    materialized_bytes = patch.read_bytes()
    _request(host, "POST")
    updated = _wait_tools(host, ["mcp__probe__marker_v1"])
    assert patch.read_bytes() == materialized_bytes
    assert updated["config"] == "edited"
    assert next(s for s in updated["skills"] if s["name"] == "alpha")["description"] == "edited"
    assert any(s["name"] == "beta" for s in updated["skills"])

    shutil.rmtree(skills / "alpha")
    server_entry["args"] = [str(mcp_server), "v2"]
    patch.write_text(json.dumps(rows), encoding="utf-8")
    _request(host, "POST")
    replaced = _wait_tools(host, ["mcp__probe__marker_v2"])
    assert all(s["name"] != "alpha" for s in replaced["skills"])
    manager_row["config"]["servers"].clear()
    shutil.rmtree(skills / "beta")
    patch.write_text(json.dumps(rows), encoding="utf-8")
    _request(host, "POST")
    removed = _wait_tools(host, [])
    assert all(s["name"] not in {"alpha", "beta"} for s in removed["skills"])
    for snapshot in [before, updated, replaced, removed]:
        assert initial["pid"] == snapshot["pid"]
        assert initial["id"] == snapshot["id"]
        assert initial["cursor"] == snapshot["cursor"]
    assert host.client.describe()["identity"] == identity
    assert controlled_messages_server[1] == []
    report_path = os.environ.get("HOUMAO_NATIVE_REFRESH_REPORT")
    if report_path:
        Path(report_path).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "passed",
                    "model_requests": 0,
                    "tmux_used": False,
                    "ambient_auth": False,
                    "initial": initial,
                    "before": before,
                    "after": updated,
                    "replaced": replaced,
                    "removed": removed,
                    "identity_unchanged": True,
                    "provider_requests": 0,
                    "limitations": [
                        "Only the fixture-selected host skill provider is reloaded.",
                        "No universal protection for arbitrary preset or lifecycle edits is established.",
                        "MCP tool removal does not independently prove child-process closure.",
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
