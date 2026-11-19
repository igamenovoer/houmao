"""Prove explicit Web generation replacement excludes stale publication and deletion."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading

import pytest

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.native_surface import WebNativeSurfaceV1
from houmao.agents.realm_controller.registry_models import RegistryIdentityV1, RegistryRuntimeV1
from houmao.agents.realm_controller import registry_storage as storage
from tests.unit.agents.realm_controller.test_registry_storage import _sample_record
from houmao.execution.context import observed_local_binding


@pytest.mark.parametrize("backend", ["dsh_web", "claude_headless"])
def test_runtime_generation_handoff_has_no_gap_and_excludes_stale_writer_and_remover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    """Concurrent stale work cannot restore or delete the new generation across atomic replacement."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    manifest = tmp_path / "manifest.json"
    binding = (
        observed_local_binding(
            working_directory=tmp_path,
            runtime_root=tmp_path,
            registry_root=tmp_path / "registry",
            tmux_socket=None,
        )
        if backend == "claude_headless"
        else None
    )
    old = _sample_record().model_copy(
        update={
            "identity": RegistryIdentityV1(
                backend=backend, tool="dsh" if backend == "dsh_web" else "claude"
            ),
            "mode": "web" if backend == "dsh_web" else "headless",
            "native_surface": WebNativeSurfaceV1(
                origin="http://127.0.0.1:45231", native_session_id="native"
            )
            if backend == "dsh_web"
            else None,
            "execution_binding": binding,
            "runtime": RegistryRuntimeV1(manifest_path=str(manifest)),
        }
    )

    def commit_generation(generation: str) -> None:
        """Commit the runtime authority before publishing its corresponding public generation."""

        manifest.write_text(
            json.dumps(
                {
                    "backend": backend,
                    "mode": old.mode,
                    "agent_id": old.agent_id,
                    "registry_generation_id": generation,
                    "runtime": {
                        "execution_binding": binding.model_dump(mode="json")
                        if binding is not None
                        else None
                    },
                    "backend_state": {
                        "web_identity": {"generation": generation, "agent_id": old.agent_id}
                    },
                }
            )
        )

    commit_generation(old.generation_id)
    storage.publish_live_agent_record(old)
    new = old.model_copy(update={"generation_id": "replacement-generation"})
    commit_generation(new.generation_id)
    # A stale teardown cannot remove the old pointer in the manifest-to-registry handoff window.
    assert storage.remove_live_agent_record(old.agent_id, generation_id=old.generation_id) is False
    entered = threading.Event()
    release = threading.Event()
    original_write = storage._write_json_atomically

    def held_write(path: Path, payload: dict[str, object]) -> None:
        """Hold the real atomic replacement while contenders reach the logical owner lock."""

        if payload["generation_id"] == new.generation_id:
            entered.set()
            assert release.wait(3)
        original_write(path, payload)

    monkeypatch.setattr(storage, "_write_json_atomically", held_write)
    with ThreadPoolExecutor(max_workers=3) as pool:
        replacement = pool.submit(
            storage.publish_live_agent_record, new, expected_generation_id=old.generation_id
        )
        assert entered.wait(2)
        stale_writer = pool.submit(storage.publish_live_agent_record, old)
        stale_remover = pool.submit(
            storage.remove_live_agent_record, old.agent_id, generation_id=old.generation_id
        )
        assert not stale_writer.done() and not stale_remover.done()
        # Readers retain the original record until the single atomic replacement.
        assert storage.load_managed_agent_record_by_agent_id(old.agent_id) == old
        release.set()
        assert replacement.result(timeout=3) == new
        with pytest.raises(SessionManifestError):
            stale_writer.result(timeout=3)
        assert stale_remover.result(timeout=3) is False
    assert storage.load_managed_agent_record_by_agent_id(old.agent_id) == new


@pytest.mark.parametrize("damage", ["generation", "runtime"])
def test_web_generation_handoff_rejects_another_captured_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    """An expected generation cannot transfer a different manifest's logical identity."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    old = _sample_record()
    storage.publish_live_agent_record(old)
    new = old.model_copy(update={"generation_id": "replacement-generation"})
    if damage == "runtime":
        new = new.model_copy(
            update={"runtime": RegistryRuntimeV1(manifest_path=str(tmp_path / "other.json"))}
        )
    with pytest.raises(SessionManifestError, match="captured owner"):
        storage.publish_live_agent_record(
            new,
            expected_generation_id="another-generation"
            if damage == "generation"
            else old.generation_id,
        )
    assert storage.load_managed_agent_record_by_agent_id(old.agent_id) == old
