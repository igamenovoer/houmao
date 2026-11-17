"""Qualify common observation and refresh against the owned native Web process."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import socket
import time
from typing import Any

import pytest
import httpx

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient, DshWebError
from tests.integration.agents.dsh.web.conftest import NativeWebGates, NativeWebHost
from tests.integration.agents.dsh.web.refresh_model import controlled_skill_model
from tests.integration.agents.dsh.web.test_native_control import native_prompt, wait_terminal


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


def _skill(root: Path, name: str, description: str) -> None:
    """Write only a synthetic skill below this fixture's selected root."""

    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nBody {description}.\n"
    )


def _configure_skills(host: NativeWebHost, *, watch: bool = False) -> Path:
    """Select an isolated watch-disabled provider through the actual home patch."""

    root = host.root / "selected-skills"
    root.mkdir()
    patch = host.root / "dsh-home/cordis.patch.yml"
    patch.write_text(
        json.dumps(
            [
                {
                    "insert": [
                        {
                            "id": "qualification-skills",
                            "name": str(
                                Path(os.environ["HOUMAO_DSH_EXECUTABLE"]).resolve().parents[2]
                                / "dsh-skill-filesystem/lib/index.js"
                            ),
                            "config": {
                                "includeDefaultRoots": False,
                                "providerName": "qualification-refresh",
                                "customSkillDirs": [str(root)],
                                "watch": watch,
                                "watchUsePolling": True,
                                "watchStabilityThresholdMs": 20,
                                "watchPollIntervalMs": 10,
                            },
                        }
                    ]
                }
            ]
        )
    )
    return root


def _observe(host: NativeWebHost) -> dict[str, Any]:
    """Read the native common state through its authenticated owner route."""

    return host.client.observe_common_plugins(host.identity)


def _refresh(host: NativeWebHost) -> dict[str, Any]:
    """Request bounded native refresh without creating another session or model turn."""

    return host.client.refresh_common_plugins(host.identity, timeout_seconds=5)


def _probe(mode: str, directory: Path) -> dict[str, Any]:
    """Select an explicit native-result shim for failure protocol qualification."""

    return {
        "id": "qualification-refresh-result",
        "name": str(Path(__file__).with_name("native-refresh-probe.mjs")),
        "config": {"mode": mode, "directory": str(directory)},
    }


def _wait_file(path: Path) -> None:
    """Wait for a bounded fixture-controlled native boundary."""

    deadline = time.monotonic() + 5
    while not path.exists():
        assert time.monotonic() < deadline, path
        time.sleep(0.01)


def test_native_common_refresh_updates_skill_catalog_and_then_noops(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """External catalog edits become visible in the same agent with no provider call."""

    host = native_web_factory()
    root = _configure_skills(host)
    _skill(root, "alpha", "initial")
    before = _observe(host)
    assert before["freshness"] == "pending", before
    identity = dict(host.identity)
    cursor = host.client.conversation(identity)["current_cursor"]
    result = _refresh(host)
    assert result["outcome"] == "refreshed", json.dumps(result, indent=2)
    assert result["observation"]["freshness"] == "current", result
    assert host.client.describe()["identity"] == identity
    assert host.client.conversation(identity)["current_cursor"] == cursor
    assert _refresh(host)["outcome"] == "already_current"
    _skill(root, "alpha", "changed")
    _skill(root, "beta", "added")
    assert _observe(host)["freshness"] == "pending"
    assert _refresh(host)["outcome"] == "refreshed"
    (root / "alpha/SKILL.md").unlink()
    assert _observe(host)["freshness"] == "pending"
    assert _refresh(host)["outcome"] == "refreshed"
    names = {
        item["name"]
        for resource in _observe(host)["resources"]
        if resource["kind"] == "skills" and resource["component"] == "catalog"
        for item in resource["inventory"]
    }
    assert "beta" in names and "alpha" not in names
    assert controlled_messages_server[1] == []


def test_native_mcp_declarations_and_connection_generations(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Native add, replacement and removal confirm tools while revisions stay unknown."""

    host = native_web_factory()
    identity = dict(host.identity)
    cursor = host.client.conversation(identity)["current_cursor"]
    server = host.root / "server.cjs"
    server.write_text(MCP_SERVER)
    node = shutil.which("node")
    assert node
    declaration = {
        "transport": "stdio",
        "command": node,
        "args": [str(server), "v1"],
        "startupTimeoutMs": 2000,
        "closeTimeoutMs": 1000,
        "reconnect": {"enabled": False},
    }
    row = {"id": "mcp-manager", "config": {"servers": {"probe": declaration}}}
    patch = host.root / "dsh-home/cordis.patch.yml"
    patch.write_text(json.dumps([row]))
    assert _observe(host)["freshness"] == "pending"
    first = _refresh(host)
    assert first["outcome"] == "refreshed", json.dumps(first, indent=2)
    resources = first["observation"]["resources"]
    tools = next(item for item in resources if item["component"] == "tools")
    assert tools["freshness"] == "current", tools
    assert tools["inventory"][0]["tools"] == ["mcp__probe__marker_v1"]
    implementation = next(item for item in resources if item["component"] == "implementation")
    assert implementation["freshness"] == "unknown" and implementation["required"] is False
    assert _refresh(host)["outcome"] == "already_current"
    declaration["args"] = [str(server), "v2"]
    patch.write_text(json.dumps([row]))
    assert _observe(host)["freshness"] == "pending"
    replaced = _refresh(host)
    assert replaced["outcome"] == "refreshed", replaced
    tools = next(
        item for item in replaced["observation"]["resources"] if item["component"] == "tools"
    )
    assert tools["inventory"][0]["tools"] == ["mcp__probe__marker_v2"]
    row["config"]["servers"].clear()
    patch.write_text(json.dumps([row]))
    assert _observe(host)["freshness"] == "pending"
    removed = _refresh(host)
    assert removed["outcome"] == "refreshed", removed
    tools = next(
        item for item in removed["observation"]["resources"] if item["component"] == "tools"
    )
    assert not any(item["tools"] for item in tools["inventory"])
    assert host.client.describe()["identity"] == identity
    assert host.client.conversation(identity)["current_cursor"] == cursor
    assert controlled_messages_server[1] == []


def test_native_watcher_update_needs_no_houmao_receipt(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A watcher can apply external metadata changes before the managed query."""

    host = native_web_factory()
    root = _configure_skills(host, watch=True)
    _skill(root, "alpha", "initial")
    assert _refresh(host)["outcome"] == "refreshed"
    time.sleep(0.2)
    _skill(root, "alpha", "watcher edit")
    _skill(root, "beta", "watcher add")
    deadline = time.monotonic() + 5
    observed = _observe(host)
    while observed["freshness"] != "current" and time.monotonic() < deadline:
        time.sleep(0.03)
        observed = _observe(host)
    assert observed["freshness"] == "current", observed
    assert _refresh(host)["outcome"] == "already_current"
    assert controlled_messages_server[1] == []


def test_native_refresh_keeps_distinct_homes_isolated(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """The authenticated host consumes only its own externally selected inputs."""

    first, second = native_web_factory(), native_web_factory()
    first_root, second_root = _configure_skills(first), _configure_skills(second)
    _skill(first_root, "only-first", "first")
    _skill(second_root, "only-second", "second")
    assert _refresh(first)["outcome"] == "refreshed"
    assert _observe(second)["freshness"] == "pending"
    first_names = {
        row["name"]
        for item in _observe(first)["resources"]
        if item["component"] == "catalog"
        for row in item["inventory"]
    }
    assert "only-first" in first_names and "only-second" not in first_names
    assert controlled_messages_server[1] == []


def test_invalid_native_input_reports_failure_without_repair(
    native_web_factory: Callable[..., NativeWebHost],
) -> None:
    """Malformed caller-owned patches remain unchanged and retain live identity."""

    host = native_web_factory()
    patch = host.root / "dsh-home/cordis.patch.yml"
    patch.write_text("not: [valid")
    assert _observe(host)["freshness"] == "unknown"
    result = _refresh(host)
    assert result["outcome"] == "failed", result
    assert result["effects"] == "absent"
    assert result["native_ready"] and result["native_settled"]
    assert patch.read_text() == "not: [valid"
    assert host.client.describe()["identity"] == host.identity


@pytest.mark.parametrize("mode", ["pending", "failed"])
def test_broader_native_result_preserves_confirmed_common_state(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost], mode: str
) -> None:
    """Controlled host pending/failure diagnostics do not erase actual common apply."""

    host = native_web_factory(extra_plugins=[_probe(mode, tmp_path)])
    root = _configure_skills(host)
    _skill(root, "alpha", "actual profile apply")
    result = _refresh(host)
    assert result["outcome"] == "refreshed", result
    assert result["observation"]["freshness"] == "current"
    assert result["native_ready"] and result["native_settled"]
    assert result["diagnostics"] == [
        {"reason": "host-module" if mode == "pending" else "native_activation_failed"}
    ]
    assert result["effects"] == ("confirmed" if mode == "pending" else "partial")
    if mode == "failed":
        assert result["native_outcome"] == "failed"
    assert host.client.describe()["identity"] == host.identity


def test_timed_out_refresh_remains_observable_and_settles_without_replay(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost]
) -> None:
    """A lost confirmation keeps native maintenance until the original work finishes."""

    host = native_web_factory(extra_plugins=[_probe("gate", tmp_path)])
    _configure_skills(host)
    separate = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            pending = executor.submit(
                separate.refresh_common_plugins, host.identity, timeout_seconds=0.2
            )
            _wait_file(tmp_path / "reload.entered")
            result = pending.result(timeout=2)
            assert result["outcome"] == "outcome_unknown", result
            assert not result["native_settled"]
            started = time.monotonic()
            assert host.client.state(host.identity)["available"]
            assert time.monotonic() - started < 0.5
            assert not _observe(host)["native_settled"]
            assert _refresh(host)["outcome"] == "busy"
        finally:
            (tmp_path / "reload.release").touch()
            separate.close()
    deadline = time.monotonic() + 5
    while not _observe(host)["native_settled"] and time.monotonic() < deadline:
        time.sleep(0.02)
    observed = _observe(host)
    assert observed["native_settled"] and observed["native_ready"]
    assert observed["freshness"] == "current", observed
    assert _refresh(host)["outcome"] == "already_current"


def test_refresh_refuses_host_shared_native_child(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost]
) -> None:
    """An additional live native agent prevents mutation of shared providers."""

    host = native_web_factory(extra_plugins=[_probe("child", tmp_path)])
    _configure_skills(host)
    (tmp_path / "child.request").touch()
    _wait_file(tmp_path / "child.entered")
    result = _refresh(host)
    assert result["outcome"] == "busy", result
    assert result["effects"] == "absent"
    assert not (tmp_path / "reload.entered").exists()


def test_refresh_rejects_lifecycle_profile_changes_before_apply(
    native_web_factory: Callable[..., NativeWebHost],
) -> None:
    """Removing the active loop cannot dispose the agent through resource refresh."""

    host = native_web_factory()
    root = _configure_skills(host)
    _skill(root, "alpha", "pending")
    patch = host.root / "dsh-home/cordis.patch.yml"
    rows = json.loads(patch.read_text())
    rows.append({"id": "agent-loop", "disabled": True})
    patch.write_text(json.dumps(rows))
    result = _refresh(host)
    assert result["outcome"] == "restart_required", result
    assert result["effects"] == "absent"
    assert host.client.describe()["identity"] == host.identity


def test_failed_native_replacement_retains_applied_common_effects(
    native_web_factory: Callable[..., NativeWebHost],
) -> None:
    """A real failing Loader entry leaves successful skill activation observable."""

    host = native_web_factory()
    root = _configure_skills(host)
    _skill(root, "alpha", "initial")
    initial_plugin = host.root / "initial.mjs"
    initial_plugin.write_text(
        "export function apply(ctx,config){if(config.fail)throw new Error('synthetic activation failure')}\n"
    )
    patch = host.root / "dsh-home/cordis.patch.yml"
    rows = json.loads(patch.read_text())
    rows.append(
        {
            "insert": [
                {
                    "id": "qualification-failing",
                    "name": str(initial_plugin),
                    "config": {"fail": False},
                }
            ]
        }
    )
    patch.write_text(json.dumps(rows))
    assert _refresh(host)["outcome"] == "refreshed"
    _skill(root, "alpha", "applied before failure")
    rows[0]["insert"][0]["config"]["providerName"] = "qualification-replacement"
    rows[1]["insert"][0]["config"]["fail"] = True
    patch.write_text(json.dumps(rows))
    result = _refresh(host)
    assert result.get("native_outcome") == "failed", json.dumps(result, indent=2)
    assert result["effects"] == "partial"
    assert result["native_settled"] and result["native_ready"]
    assert result["observation"]["freshness"] == "current", result
    assert host.client.describe()["identity"] == host.identity


def test_native_watcher_can_race_managed_reconciliation(
    tmp_path: Path,
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """An autonomous watcher remains enabled while managed native work is held."""

    release = tmp_path / "reload.release"
    release.touch()
    host = native_web_factory(extra_plugins=[_probe("gate", tmp_path)])
    root = _configure_skills(host, watch=True)
    _skill(root, "alpha", "initial")
    assert _refresh(host)["outcome"] == "refreshed"
    time.sleep(0.2)
    release.unlink()
    (tmp_path / "reload.entered").unlink()
    patch = host.root / "dsh-home/cordis.patch.yml"
    rows = json.loads(patch.read_text())
    rows[0]["insert"][0]["config"]["watchStabilityThresholdMs"] = 30
    patch.write_text(json.dumps(rows))
    separate = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            pending = executor.submit(
                separate.refresh_common_plugins, host.identity, timeout_seconds=5
            )
            _wait_file(tmp_path / "reload.entered")
            _skill(root, "beta", "autonomous during maintenance")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                resources = _observe(host)["resources"]
                catalog = next(item for item in resources if item["component"] == "catalog")
                if any(row["name"] == "beta" for row in catalog["inventory"]):
                    break
                time.sleep(0.02)
            assert any(row["name"] == "beta" for row in catalog["inventory"])
            assert not _observe(host)["native_settled"]
            release.touch()
            assert pending.result(timeout=5)["outcome"] == "refreshed"
        finally:
            release.touch()
            separate.close()
    assert _observe(host)["freshness"] == "current"
    assert controlled_messages_server[1] == []


def test_invalid_readiness_retains_maintenance_until_explicit_disposal(
    tmp_path: Path,
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """The native finally path cannot wake queued work after failed readiness."""

    host = native_web_factory(extra_plugins=[_probe("unready", tmp_path)])
    _configure_skills(host)
    result = _refresh(host)
    assert result["outcome"] == "failed", result
    assert not result["native_ready"] and not result["native_settled"]
    assert result["effects"] == "partial"
    receipt = host.client.prompt(
        host.identity,
        "must remain queued",
        operation_id="after-unready",
        deadline_epoch_ms=int(time.time() * 1000) + 5000,
        admission_policy="always",
        operator=True,
    )
    assert receipt["status"] == "admitted"
    time.sleep(0.1)
    assert host.client.state(host.identity)["pending_inbox"]
    assert not _observe(host)["native_ready"]
    assert controlled_messages_server[1] == []
    assert host.client.stop(host.identity)["stopped"]
    assert controlled_messages_server[1] == []


def test_busy_native_serializer_leaves_no_deferred_mutation(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost]
) -> None:
    """A queued serializer callback is abandoned before it can change resources."""

    host = native_web_factory(extra_plugins=[_probe("lockbusy", tmp_path)])
    _configure_skills(host)
    result = _refresh(host)
    assert result["outcome"] == "busy", result
    assert result["effects"] == "absent"
    (tmp_path / "reload.release").touch()
    time.sleep(0.1)
    assert not (tmp_path / "reload.entered").exists()
    assert _observe(host)["freshness"] == "pending"


def test_actual_native_http_response_loss_does_not_replay_refresh(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost]
) -> None:
    """A real wire timeout leaves the original native job available for observation."""

    host = native_web_factory(extra_plugins=[_probe("gate", tmp_path)])
    _configure_skills(host)
    separate = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    assert separate.m_http is not None
    separate.m_http.timeout = httpx.Timeout(0.1)
    try:
        with pytest.raises(DshWebError) as lost:
            separate.refresh_common_plugins(host.identity, timeout_seconds=5)
        assert lost.value.code == "outcome_uncertain"
        assert "inspect common state" in str(lost.value)
        _wait_file(tmp_path / "reload.entered")
        assert not _observe(host)["native_settled"]
        assert _refresh(host)["outcome"] == "busy"
    finally:
        (tmp_path / "reload.release").touch()
        separate.close()
    deadline = time.monotonic() + 5
    while not _observe(host)["native_settled"] and time.monotonic() < deadline:
        time.sleep(0.02)
    assert _observe(host)["freshness"] == "current"
    assert _refresh(host)["outcome"] == "already_current"


def test_native_child_activation_cannot_race_shared_refresh(
    tmp_path: Path,
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A new native Agent is rolled back before it can execute shared resources."""

    host = native_web_factory(extra_plugins=[_probe("gate-child", tmp_path)])
    _configure_skills(host)
    separate = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            pending = executor.submit(
                separate.refresh_common_plugins, host.identity, timeout_seconds=5
            )
            _wait_file(tmp_path / "reload.entered")
            (tmp_path / "child.request").touch()
            _wait_file(tmp_path / "child.refused")
            assert not (tmp_path / "child.entered").exists()
            (tmp_path / "reload.release").touch()
            result = pending.result(timeout=5)
            assert result["outcome"] == "refreshed", result
        finally:
            (tmp_path / "reload.release").touch()
            separate.close()
    assert host.client.describe()["identity"] == host.identity
    assert controlled_messages_server[1] == []


def test_native_office_provider_cache_is_compared_with_current_assets(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Bundled extension skills remain common resources with independent disk proof."""

    host = native_web_factory()
    assets = host.root / "dsh-home/office-assets"
    assets.mkdir()
    for name in ["office", "office-docx", "office-pptx", "office-xlsx"]:
        _skill(assets, name, "initial")
    patch = host.root / "dsh-home/cordis.patch.yml"
    patch.write_text(json.dumps([{"id": "skill-office", "config": {"assetRoot": str(assets)}}]))
    assert _observe(host)["freshness"] == "pending"
    assert _refresh(host)["outcome"] == "refreshed"
    _skill(assets, "office", "externally edited")
    assert _observe(host)["freshness"] == "pending"
    assert _observe(host)["freshness"] == "pending"
    assert _refresh(host)["outcome"] == "refreshed"
    (assets / "office/SKILL.md").unlink()
    assert _observe(host)["freshness"] == "pending"
    assert _refresh(host)["outcome"] == "refreshed"
    assert not any(
        row["name"] == "office"
        for item in _observe(host)["resources"]
        if item["component"] == "catalog"
        for row in item["inventory"]
    )
    assert controlled_messages_server[1] == []


@pytest.mark.parametrize("empty", [False, True])
def test_opaque_native_provider_cannot_establish_complete_current_scope(
    native_web_factory: Callable[..., NativeWebHost], empty: bool
) -> None:
    """Even cached empty inventories need source coverage for registered providers."""

    host = native_web_factory(
        extra_plugins=[
            {
                "id": "qualification-opaque-skills",
                "name": str(Path(__file__).with_name("opaque-skill-provider.mjs")),
                "config": {"empty": empty},
            }
        ]
    )
    observed = _observe(host)
    assert observed["freshness"] == "unknown", observed
    assert not observed["coverage_complete"]
    result = _refresh(host)
    assert result["outcome"] == "partial", result
    assert result["native_ready"] and result["native_settled"]
    assert "Private body" not in json.dumps(result)


def test_browser_turn_wins_before_native_refresh_admission(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A browser-equivalent native turn after observation refuses managed mutation."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    _configure_skills(host)
    assert _observe(host)["freshness"] == "pending"
    native_web_gates.hold("step", "browser wins refresh race")
    try:
        native_prompt(host, "browser wins refresh race")
        native_web_gates.wait("step")
        result = _refresh(host)
        assert result["outcome"] == "busy" and result["effects"] == "absent", result
        assert host.client.state(host.identity)["active_turn"] is not None
        assert _observe(host)["freshness"] == "pending"
        assert controlled_messages_server[1] == []
    finally:
        native_web_gates.release("step")
    deadline = time.monotonic() + 10
    while (
        host.client.state(host.identity)["active_turn"] is not None and time.monotonic() < deadline
    ):
        time.sleep(0.02)
    assert host.client.state(host.identity)["last_turn"]["result"] == "completed"
    assert len(controlled_messages_server[1]) == 1
    assert "browser wins refresh race" in json.dumps(controlled_messages_server[1][0])


def test_loaded_skill_history_survives_refresh_and_next_load_reads_new_body(
    native_web_factory: Callable[..., NativeWebHost],
) -> None:
    """Actual native skill tool results retain old text while later loads use edits."""

    with controlled_skill_model() as model:
        host = native_web_factory(endpoint=model.endpoint)
        root = _configure_skills(host)
        _skill(root, "alpha", "stable discovery metadata")
        skill = root / "alpha/SKILL.md"
        skill.write_text(skill.read_text() + "\nOLD_NATIVE_BODY\n")
        assert _refresh(host)["outcome"] == "refreshed"
        host.client.prompt(
            host.identity,
            "load original alpha",
            operation_id="old-skill",
            deadline_epoch_ms=int(time.time() * 1000) + 10000,
        )
        assert wait_terminal(host, "old-skill")["result"] == "completed"
        before = host.client.conversation(host.identity, limit=500)
        assert "OLD_NATIVE_BODY" in json.dumps(before)
        assert len(model.requests) == 2
        skill.write_text(skill.read_text().replace("OLD_NATIVE_BODY", "NEW_NATIVE_BODY"))
        count = len(model.requests)
        refresh = _refresh(host)
        assert refresh["outcome"] == "already_current", refresh
        assert len(model.requests) == count
        retained = host.client.conversation(host.identity, limit=500)
        assert retained["current_cursor"] == before["current_cursor"]
        assert "OLD_NATIVE_BODY" in json.dumps(retained) and "NEW_NATIVE_BODY" not in json.dumps(
            retained
        )
        host.client.prompt(
            host.identity,
            "load revised alpha",
            operation_id="new-skill",
            deadline_epoch_ms=int(time.time() * 1000) + 10000,
        )
        assert wait_terminal(host, "new-skill")["result"] == "completed"
        after = json.dumps(host.client.conversation(host.identity, limit=500))
        assert "OLD_NATIVE_BODY" in after and "NEW_NATIVE_BODY" in after
        assert len(model.requests) == 4
        assert "NEW_NATIVE_BODY" in json.dumps(model.requests[-1])


def test_applied_unreachable_mcp_keeps_declaration_freshness_separate_from_health(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A refused local connection does not make the applied declaration stale."""

    host = native_web_factory()
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        # This bound socket intentionally never listens, so the selected port
        # remains unavailable without reaching any external MCP service.
        port = reserved.getsockname()[1]
        patch = host.root / "dsh-home/cordis.patch.yml"
        patch.write_text(
            json.dumps(
                [
                    {
                        "id": "mcp-manager",
                        "config": {
                            "servers": {
                                "unreachable": {
                                    "transport": "streamable-http",
                                    "url": f"http://127.0.0.1:{port}/mcp",
                                    "startupTimeoutMs": 200,
                                    "reconnect": {"enabled": False},
                                }
                            }
                        },
                    }
                ]
            )
        )
        result = _refresh(host)
        assert result["outcome"] == "partial", result
        resources = result["observation"]["resources"]
        declaration = next(
            row for row in resources if row["kind"] == "mcp" and row["component"] == "declarations"
        )
        tools = next(
            row for row in resources if row["kind"] == "mcp" and row["component"] == "tools"
        )
        assert declaration["freshness"] == "current"
        assert tools["freshness"] == "unknown" and tools["health"] == "degraded"
        assert tools["inventory"][0]["health"] == "failed"
        assert result["native_ready"] and result["native_settled"]
        assert controlled_messages_server[1] == []


def test_native_observation_cannot_reset_expired_refresh_deadline(
    tmp_path: Path,
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A blocked initial native read cannot later enter configuration application."""

    host = native_web_factory(extra_plugins=[_probe("observation-gate", tmp_path)])
    _configure_skills(host)
    assert _observe(host)["freshness"] == "pending"
    (tmp_path / "observation.request").touch()
    separate = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            pending = executor.submit(
                separate.refresh_common_plugins, host.identity, timeout_seconds=0.2
            )
            _wait_file(tmp_path / "observation.entered")
            time.sleep(0.25)
            (tmp_path / "observation.release").touch()
            with pytest.raises(DshWebError) as expired:
                pending.result(timeout=5)
            assert expired.value.code == "expired"
        finally:
            (tmp_path / "observation.release").touch()
            separate.close()
    observed = _observe(host)
    assert observed["freshness"] == "pending", observed
    assert observed["native_settled"] and observed["native_ready"]
    assert not (tmp_path / "reload.entered").exists()
    assert controlled_messages_server[1] == []


def test_expired_native_apply_does_not_start_later_resource_restarts(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost]
) -> None:
    """An admitted native apply may settle late without starting the next mutation."""

    release = tmp_path / "reload.release"
    release.touch()
    host = native_web_factory(extra_plugins=[_probe("gate", tmp_path)])
    root = _configure_skills(host)
    _skill(root, "alpha", "initial")
    assert _refresh(host)["outcome"] == "refreshed"
    release.unlink()
    (tmp_path / "reload.entered").unlink()
    _skill(root, "alpha", "must wait for another explicit refresh")
    assert _observe(host)["freshness"] == "pending"
    separate = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            pending = executor.submit(
                separate.refresh_common_plugins, host.identity, timeout_seconds=0.2
            )
            _wait_file(tmp_path / "reload.entered")
            assert pending.result(timeout=5)["outcome"] == "outcome_unknown"
        finally:
            release.touch()
            separate.close()
    deadline = time.monotonic() + 5
    observed = _observe(host)
    while not observed["native_settled"] and time.monotonic() < deadline:
        time.sleep(0.02)
        observed = _observe(host)
    assert observed["native_settled"] and observed["native_ready"]
    assert observed["freshness"] == "pending", observed
    assert _refresh(host)["outcome"] == "refreshed"


def test_native_refresh_refuses_existing_maintenance_without_waiting(
    native_web_factory: Callable[..., NativeWebHost], native_web_gates: NativeWebGates
) -> None:
    """A pending common edit does not let managed reload overlap native work."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    _configure_skills(host)
    native_web_gates.hold("maintenance")
    native_web_gates.wait("maintenance")
    try:
        result = _refresh(host)
        assert result["outcome"] == "busy", result
        assert result["effects"] == "absent"
        assert _observe(host)["native_ready"] is True
    finally:
        native_web_gates.release("maintenance")


def test_native_read_does_not_apply_edited_profile(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """The check route reports pending evidence without invalidating native caches."""

    host = native_web_factory()
    root = _configure_skills(host)
    _skill(root, "alpha", "read only")
    patch = host.root / "dsh-home/cordis.patch.yml"
    contents = patch.read_bytes()
    for _ in range(2):
        observed = _observe(host)
        assert observed["freshness"] == "pending", observed
        assert not any(
            item["name"] == "alpha"
            for resource in observed["resources"]
            if resource["kind"] == "skills"
            for item in resource["inventory"]
        )
    assert patch.read_bytes() == contents
    assert controlled_messages_server[1] == []
