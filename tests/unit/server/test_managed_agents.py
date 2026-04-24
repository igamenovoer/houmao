from __future__ import annotations

from pathlib import Path

from houmao.server.config import HoumaoServerConfig
from houmao.server.managed_agents import ManagedHeadlessAuthorityRecord, ManagedHeadlessStore


def _authority_record(*, tracked_agent_id: str) -> ManagedHeadlessAuthorityRecord:
    """Build one minimal authority record for managed-agent store tests."""

    return ManagedHeadlessAuthorityRecord(
        tracked_agent_id=tracked_agent_id,
        backend="codex_headless",
        tool="codex",
        manifest_path="/tmp/runtime/session/manifest.json",
        session_root="/tmp/runtime/session",
        tmux_session_name="managed-agent",
        agent_def_dir="/tmp/agents",
        agent_name="managed-agent",
        agent_id="agent-1",
        created_at_utc="2026-04-24T00:00:00+00:00",
        updated_at_utc="2026-04-24T00:00:00+00:00",
    )


def test_managed_store_delete_agent_unlinks_symlinked_agent_root_without_touching_source(
    tmp_path: Path,
) -> None:
    config = HoumaoServerConfig(runtime_root=tmp_path / "runtime")
    store = ManagedHeadlessStore(config=config)
    external_root = (tmp_path / "external-agent").resolve()
    external_root.mkdir(parents=True, exist_ok=True)
    (external_root / "authority.json").write_text('{"external": true}\n', encoding="utf-8")
    agent_root = store.agent_root(tracked_agent_id="agent-1")
    agent_root.parent.mkdir(parents=True, exist_ok=True)
    agent_root.symlink_to(external_root, target_is_directory=True)

    store.delete_agent(tracked_agent_id="agent-1")

    assert not agent_root.exists()
    assert (external_root / "authority.json").is_file()


def test_managed_store_write_authority_record_replaces_symlinked_file_without_touching_source(
    tmp_path: Path,
) -> None:
    config = HoumaoServerConfig(runtime_root=tmp_path / "runtime")
    store = ManagedHeadlessStore(config=config)
    authority_path = store.authority_path(tracked_agent_id="agent-1")
    authority_path.parent.mkdir(parents=True, exist_ok=True)
    external_file = (tmp_path / "external-authority.json").resolve()
    external_file.write_text('{"external": true}\n', encoding="utf-8")
    authority_path.symlink_to(external_file)

    store.write_authority(_authority_record(tracked_agent_id="agent-1"))

    assert authority_path.is_file()
    assert not authority_path.is_symlink()
    assert '"tracked_agent_id": "agent-1"' in authority_path.read_text(encoding="utf-8")
    assert external_file.read_text(encoding="utf-8") == '{"external": true}\n'
