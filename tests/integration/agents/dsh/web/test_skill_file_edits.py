"""Qualify isolated native skill publication on the selected DSH Web build."""

from collections.abc import Callable
import json
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.dsh_web import DshWebSession
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient, DshWebError
from houmao.agents.realm_controller.backends.dsh_web_skill_mount import QUALIFIED_BUILD
from houmao.agents.realm_controller.models import RelaunchChatSessionSelection
from houmao.gateway.file_edits.projection import FileProjection
from tests.integration.agents.dsh.web.conftest import NativeWebHost, call_native_request
from tests.integration.agents.dsh.web.refresh_model import controlled_skill_model
from tests.integration.agents.dsh.web.test_managed_lifecycle import _controller, _stop, _web_plan
from tests.integration.agents.dsh.web.test_native_control import wait_terminal
from tests.integration.agents.dsh.web.test_refresh import MCP_SERVER, _configure_skills, _skill


@pytest.fixture(autouse=True)
def qualified_dsh_web_skills(dsh_executable: Path) -> None:
    """Run the skill-mount suite only for the explicitly qualified native build."""

    version = subprocess.check_output([str(dsh_executable), "--version"], text=True).strip()
    if version != QUALIFIED_BUILD:
        pytest.skip(f"Versioned Web skills qualify DSH {QUALIFIED_BUILD}")


def _revision(projection: FileProjection, revision: str, name: str, text: str) -> None:
    """Prepare one immutable skill with distinct metadata, body, and asset bytes."""

    projection.prepare(
        revision,
        {
            f"{name}/SKILL.md": f"---\nname: {name}\ndescription: {text}\n---\nBody {text}\n".encode(),
            f"{name}/asset.txt": f"Asset {text}\n".encode(),
        },
    )


def _intent(
    host: NativeWebHost, operation_id: str, expected: str, candidate: str
) -> dict[str, Any]:
    """Build one exact owner-native publication request."""

    return {
        "identity": host.identity,
        "operation_id": operation_id,
        "expected": expected,
        "candidate": candidate,
        "deadline_epoch_ms": int(time.time() * 1000) + 10000,
    }


def _publish(projection: FileProjection, host: NativeWebHost, request: dict[str, Any]) -> None:
    """Confirm publication evidence remains distinct from maintenance settlement."""

    opened = host.client.call("skill_mount_open", request)
    assert projection.published_marker() == request["expected"]
    request["maintenance_token"] = opened["maintenance_token"]
    published = host.client.call("skill_mount_publish", request)
    assert published["effective_commit"] == request["candidate"], published
    assert published["native_settled"] is False
    assert projection.published_marker() == request["candidate"]
    settlement = host.client.call("skill_mount_close", request)
    assert settlement == host.client.call("skill_mount_status", request)
    assert settlement["native_settled"] and settlement["native_ready"]


def _catalog(host: NativeWebHost) -> dict[str, dict[str, Any]]:
    """Use the ordinary native user-facing catalog rather than a managed probe."""

    response = call_native_request(
        host.client,
        "skills/list",
        {"request": {"sessionId": host.identity["native_session_id"]}},
    )
    return {entry["name"]: entry for entry in response["skills"]}


def test_skill_mount_switches_only_complete_revisions(
    tmp_path: Path,
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Qualify add, update and remove with a pending native MCP/profile change."""

    empty, initial, revised, removed = (digit * 40 for digit in "1234")
    mount_id = "9" * 32
    projection = FileProjection(tmp_path / "projection")
    projection.initialize(mount_id, empty, {})
    _revision(projection, initial, "only-managed", "initial definition")
    _revision(projection, revised, "only-managed", "revised definition")
    projection.prepare(removed, {})
    host = native_web_factory(skill_projection=projection.root)
    identity = dict(host.identity)
    details = host.client.call("skill_mount", {"identity": identity})
    assert details == {"mount_id": mount_id, "preset": "standard", "build": "0.2.2-rc.3"}
    before = host.client.conversation(identity)["current_cursor"]
    patch = host.root / "dsh-home/cordis.patch.yml"
    server = host.root / "server.cjs"
    starts = host.root / "mcp-starts"
    server.write_text(
        "require('node:fs').appendFileSync(process.argv[3], process.argv[2] + '\\n');\n"
        + MCP_SERVER
    )
    node = shutil.which("node")
    assert node
    declaration: dict[str, Any] = {
        "transport": "stdio",
        "command": node,
        "args": [str(server), "initial", str(starts)],
        "startupTimeoutMs": 2000,
        "closeTimeoutMs": 1000,
        "reconnect": {"enabled": False},
    }
    rows = [{"id": "mcp-manager", "config": {"servers": {"probe": declaration}}}]
    patch.write_text(json.dumps(rows))
    assert host.client.refresh_common_plugins(identity, timeout_seconds=5)["outcome"] == "refreshed"
    initial_starts = starts.read_text()
    assert set(initial_starts.splitlines()) == {"initial"}
    declaration["args"][1] = "pending"
    patch.write_text(json.dumps(rows))
    mcp = host.client.observe_common_plugins(identity)["resources"][2:]
    assert any(row["kind"] == "mcp" and row["freshness"] == "pending" for row in mcp)
    unrelated = {key: value for key, value in _catalog(host).items() if key != "only-managed"}
    _publish(projection, host, _intent(host, "add", empty, initial))
    old = _catalog(host)["only-managed"]
    assert old["description"] == "initial definition"
    _publish(projection, host, _intent(host, "update", initial, revised))
    new = _catalog(host)["only-managed"]
    assert new["description"] == "revised definition"
    assert initial in old["path"] and revised in new["path"]
    assert Path(old["path"]).with_name("asset.txt").read_text() == "Asset initial definition\n"
    assert Path(new["path"]).with_name("asset.txt").read_text() == "Asset revised definition\n"
    observation = host.client.observe_common_plugins(identity)
    catalog = next(row for row in observation["resources"] if row["component"] == "catalog")
    assert catalog["freshness"] == "current"
    assert any(item["provider"] == "houmao-versioned-skills" for item in catalog["inventory"])
    assert mcp == observation["resources"][2:]
    _publish(projection, host, _intent(host, "remove", revised, removed))
    assert starts.read_text() == initial_starts
    assert _catalog(host) == unrelated
    assert host.client.describe()["identity"] == identity
    assert host.client.conversation(identity)["current_cursor"] == before
    assert controlled_messages_server[1] == []


def test_standard_skill_tool_loads_revisions_and_relaunch_retains_them(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost]
) -> None:
    """Load pinned revisions through the real tool and exact same-home continuation."""

    empty, initial, revised = (digit * 40 for digit in "123")
    projection = FileProjection(tmp_path / "projection")
    projection.initialize("9" * 32, empty, {})
    _revision(projection, initial, "alpha", "OLD_NATIVE_BODY")
    _revision(projection, revised, "alpha", "NEW_NATIVE_BODY")
    with controlled_skill_model(read_asset=True) as model:
        host = native_web_factory(endpoint=model.endpoint, skill_projection=projection.root)
        _publish(projection, host, _intent(host, "add", empty, initial))
        for revision, marker in [(initial, "OLD_NATIVE_BODY"), (revised, "NEW_NATIVE_BODY")]:
            if revision == revised:
                cursor = host.client.conversation(host.identity)["current_cursor"]
                _publish(projection, host, _intent(host, "update", initial, revised))
                assert host.client.conversation(host.identity)["current_cursor"] == cursor
                assert len(model.requests) == 3
            host.client.prompt(
                host.identity,
                "load alpha",
                operation_id=marker,
                deadline_epoch_ms=int(time.time() * 1000) + 10000,
            )
            assert wait_terminal(host, marker)["result"] == "completed"
            result = json.dumps(model.requests[-1])
            assert f"Body {marker}" in result and revision in result
            assert f"Asset {marker}" in result
        assert len(model.requests) == 6
        history = json.dumps(host.client.conversation(host.identity, limit=500))
        assert "Body OLD_NATIVE_BODY" in history and "Body NEW_NATIVE_BODY" in history
        identity = dict(host.identity)
        host.close()
        live = native_web_factory(
            root=host.root,
            endpoint=model.endpoint,
            skill_projection=projection.root,
            mode="exact",
            session_id=identity["native_session_id"],
        )
        assert live.identity["native_session_id"] == identity["native_session_id"]
        assert live.identity["host_incarnation"] != identity["host_incarnation"]
        assert _catalog(live)["alpha"]["description"] == "NEW_NATIVE_BODY"
        assert len(model.requests) == 6


def test_publication_refuses_collision_pending_foreign_skills_and_competing_peer(
    tmp_path: Path, native_web_factory: Callable[..., NativeWebHost]
) -> None:
    """Keep native maintenance exclusive and reject broader unqualified effects."""

    empty, candidate, collision, unsafe = (digit * 40 for digit in "1234")
    projection = FileProjection(tmp_path / "projection")
    projection.initialize("9" * 32, empty, {})
    _revision(projection, candidate, "alpha", "owned definition")
    _revision(projection, collision, "dsh-doc", "cannot shadow native skill")
    _revision(projection, unsafe, "alpha", "unsafe asset")
    asset = projection.root / "revisions" / unsafe / "alpha/asset.txt"
    asset.unlink()
    asset.symlink_to(projection.root / "revisions" / candidate / "alpha/asset.txt")
    host = native_web_factory(skill_projection=projection.root)
    expired = _intent(host, "expired", empty, candidate)
    expired["deadline_epoch_ms"] = int(time.time() * 1000) - 1
    with pytest.raises(DshWebError, match="invalid_request"):
        host.client.call("skill_mount_open", expired)
    marker_file = projection.root / "published"
    original_marker = marker_file.read_bytes()
    try:
        marker_file.write_bytes(original_marker + b"\n")
        with pytest.raises(DshWebError):
            host.client.call("skill_mount_open", _intent(host, "foreign-marker", empty, candidate))
    finally:
        marker_file.write_bytes(original_marker)
    with pytest.raises(DshWebError):
        host.client.call("skill_mount_open", _intent(host, "unsafe", empty, unsafe))
    assert projection.published_marker() == empty
    conflict = _intent(host, "conflict", empty, collision)
    with pytest.raises(DshWebError, match="conflict"):
        host.client.call("skill_mount_open", conflict)
    request = _intent(host, "hold", empty, candidate)
    opened = host.client.call("skill_mount_open", request)
    request.update(opened)
    second = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    try:
        with pytest.raises(DshWebError, match="busy"):
            second.call("skill_mount_open", _intent(host, "second", empty, candidate))
        with pytest.raises(DshWebError, match="stale_operation"):
            second.call("skill_mount_publish", request)
        with pytest.raises(DshWebError, match="not_ready"):
            second.prompt(
                host.identity,
                "must stay out of the native inbox",
                operation_id="blocked-prompt",
                deadline_epoch_ms=int(time.time() * 1000) + 10000,
            )
    finally:
        second.close()
    closed = host.client.call("skill_mount_close", request)
    assert closed["outcome"] == "unchanged"
    assert closed["native_settled"] and closed["native_ready"]
    disconnected = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    abandoned = _intent(host, "lost-peer", empty, candidate)
    try:
        disconnected.call("skill_mount_open", abandoned)
    finally:
        disconnected.close()
    deadline = time.monotonic() + 5
    lost = host.client.call("skill_mount_status", abandoned)
    while not lost["native_ready"] and time.monotonic() < deadline:
        time.sleep(0.02)
        lost = host.client.call("skill_mount_status", abandoned)
    assert lost["operation_id"] == "lost-peer"
    assert lost["native_settled"] and lost["native_ready"] and lost["outcome"] == "unchanged"
    assert projection.published_marker() == empty
    root = _configure_skills(host)
    _skill(root, "unrelated", "initial")
    assert (
        host.client.refresh_common_plugins(host.identity, timeout_seconds=5)["outcome"]
        == "refreshed"
    )
    assert _catalog(host)["unrelated"]["description"] == "initial"
    _skill(root, "unrelated", "pending edit")
    with pytest.raises(DshWebError, match="unavailable"):
        host.client.call("skill_mount_open", _intent(host, "foreign", empty, candidate))
    assert _catalog(host)["unrelated"]["description"] == "initial"
    assert projection.published_marker() == empty


def test_backend_owner_opt_in_retains_mount_identity_on_same_home_relaunch(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provision from the selected launch config and recover the exact retained mount."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint, tmux_socket=isolated_tmux)
    setup = Path(plan.metadata["dsh"]["setup_path"])
    setup.write_text(json.dumps({**json.loads(setup.read_text()), "managed_web_skills": True}))
    session = DshWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=manifest,
        role_name="controlled",
        provider_start=True,
    )
    try:
        _controller(plan, manifest, session)
        identity = dict(session.state.web_identity)
        mount = session.skill_file_mount()
        assert mount is not None
        details = mount.storage.describe()
        assert mount.projection.published_marker() == details.published_commit
        assert session.state.managed_skill_lineage
        result = session.relaunch(
            chat_session=RelaunchChatSessionSelection(
                mode="exact", session_id=identity["native_session_id"]
            )
        )
        assert result.status == "ok", result.detail
        retained = session.skill_file_mount()
        assert retained is not None and retained.storage.describe() == details
        assert session.state.web_identity["native_session_id"] == identity["native_session_id"]
        assert session.state.web_identity["host_incarnation"] != identity["host_incarnation"]
        assert requests == []
    finally:
        _stop(session)
