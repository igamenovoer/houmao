"""Owner-side launch-time socket selection and default record storage."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier
from tempfile import TemporaryDirectory

import pytest

from houmao.agents.realm_controller.registry_storage import cleanup_stale_managed_agent_records
from houmao.execution import owner, tmux_selection
from houmao.execution.context import execution_read_only_scope, observed_local_binding
from houmao.execution.tmux import (
    TmuxObservationUnavailable,
    TmuxServer,
    native_default_tmux_socket_path,
    tmux_server_scope,
)
from houmao.execution.tmux_selection import (
    ResolvedTmuxServer,
    TmuxServerSelector,
    resolve_tmux_server,
)
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR


@pytest.fixture
def managed_namespace(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Use a short socket namespace reserved exclusively for these tests."""

    with TemporaryDirectory(prefix="houmao-tmx-") as directory:
        namespace = Path(directory) / "socket-owner"
        monkeypatch.setattr(tmux_selection, "_managed_socket_directory", lambda uid: namespace)
        yield namespace


def test_native_default_ignores_enclosing_and_scoped_selectors(tmp_path: Path) -> None:
    """An explicit native default chooses the owner environment's default address."""

    native = tmp_path.resolve() / f"tmux-{os.getuid()}" / "default"
    enclosing = str(tmp_path / "enclosing.sock")
    scoped = str(tmp_path / "scoped.sock")
    environment = {"TMUX": f"{enclosing},12,0", "TMUX_TMPDIR": str(tmp_path)}

    assert resolve_tmux_server(None, environment={}) == ResolvedTmuxServer(
        f"/tmp/tmux-{os.getuid()}/default", True
    )
    assert resolve_tmux_server(None, environment=environment) == ResolvedTmuxServer(enclosing, True)
    with tmux_server_scope(scoped, allow_start=False):
        assert resolve_tmux_server(None, environment=environment) == ResolvedTmuxServer(
            scoped, False
        )
        assert resolve_tmux_server(
            TmuxServerSelector(server="user-default"), environment=environment
        ) == ResolvedTmuxServer(str(native), True)
    assert not native.parent.exists()


def test_native_default_uses_real_socket_root_and_skips_missing_config(tmp_path: Path) -> None:
    """Native defaults use tmux's resolved root and fallback for a missing override."""

    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    leaf = Path(f"tmux-{os.getuid()}") / "default"
    assert native_default_tmux_socket_path({"TMUX_TMPDIR": str(alias)}) == str(
        tmp_path.resolve() / leaf
    )
    missing = tmp_path / "missing"
    env = {"TMUX_TMPDIR": str(missing)}
    assert native_default_tmux_socket_path(env) == str(Path("/tmp").resolve() / leaf)
    assert resolve_tmux_server(None, environment=env) == ResolvedTmuxServer(
        str(missing / leaf), True
    )


@pytest.mark.parametrize("unsafe", ["symlink", "world-accessible"])
def test_native_default_refuses_unsafe_leaf_during_preflight(tmp_path: Path, unsafe: str) -> None:
    """Native server selection rejects the same unsafe leaf shapes as tmux."""

    leaf = tmp_path / f"tmux-{os.getuid()}"
    if unsafe == "symlink":
        leaf.symlink_to(tmp_path, target_is_directory=True)
    else:
        leaf.mkdir(mode=0o700)
        leaf.chmod(0o701)
    with pytest.raises(ValueError, match="Unsafe native tmux socket directory"):
        resolve_tmux_server(
            TmuxServerSelector(server="user-default"),
            environment={"TMUX_TMPDIR": str(tmp_path)},
        )
    assert not (leaf / "default").exists()


def test_new_selection_allocates_distinct_private_addresses(managed_namespace: Path) -> None:
    """Each birth gets a different cold address under a private owner namespace."""

    selector = TmuxServerSelector(server="new")
    first, second = resolve_tmux_server(selector), resolve_tmux_server(selector)
    first_path, second_path = Path(first.socket_path), Path(second.socket_path)
    assert first.allow_start and second.allow_start
    assert first_path != second_path
    assert first_path.parent == second_path.parent
    assert first_path.parent.parent == managed_namespace
    assert first_path.parent.stat().st_mode & 0o777 == 0o700
    assert managed_namespace.stat().st_mode & 0o777 == 0o700
    assert not first_path.exists()
    assert not second_path.exists()


def test_socket_selection_checks_only_the_requested_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing-only selection validates only its owner-local server."""

    path = str(tmp_path / "requested.sock")
    selector = TmuxServerSelector(server="socket", socket_path=path)
    calls: list[str] = []

    def list_sessions(server: TmuxServer) -> set[str]:
        """Capture the exact socket without opening a real server."""

        calls.append(server.socket_path)
        if len(calls) > 1:
            raise TmuxObservationUnavailable("test refusal")
        return {"test"}

    monkeypatch.setattr(TmuxServer, "list_sessions", list_sessions)
    with tmux_server_scope(tmp_path / "enclosing.sock"):
        assert resolve_tmux_server(selector) == ResolvedTmuxServer(path, False)
        with pytest.raises(ValueError, match="unavailable.*requested.sock"):
            resolve_tmux_server(selector)
    assert calls == [path, path]


def test_admitted_pin_is_checked_before_default_bootstrap(
    managed_namespace: Path, tmp_path: Path
) -> None:
    """An incompatible selector cannot publish or allocate an owner default."""

    registry = tmp_path / "registry"
    pinned = str(tmp_path / "pinned.sock")
    binding = observed_local_binding(
        working_directory=tmp_path,
        registry_root=registry,
        runtime_root=tmp_path / "runtime",
        tmux_socket=pinned,
    )
    with tmux_server_scope(tmp_path / "scoped.sock", allow_start=False):
        assert resolve_tmux_server(None, execution_binding=binding) == ResolvedTmuxServer(
            pinned, True
        )
        with pytest.raises(ValueError, match="differs from admitted owner socket"):
            resolve_tmux_server(
                TmuxServerSelector(server="houmao-default"), execution_binding=binding
            )
        with pytest.raises(ValueError, match="pinned.*cannot select"):
            resolve_tmux_server(TmuxServerSelector(server="new"), execution_binding=binding)
    assert not registry.exists()
    assert not managed_namespace.exists()


def test_default_bootstrap_is_atomic_and_independent_of_projects_and_registries(
    managed_namespace: Path, tmp_path: Path
) -> None:
    """Concurrent projects and separate empty registries select one owner address."""

    selector = TmuxServerSelector(server="houmao-default")
    registry = tmp_path / "shared"
    other_registry = tmp_path / "other"
    project_bindings = [
        observed_local_binding(
            working_directory=tmp_path / f"project-{index}",
            registry_root=registry,
            runtime_root=tmp_path / f"project-{index}" / "runtime",
            tmux_socket=None,
        )
        for index in range(2)
    ]
    assert project_bindings[0].context_id != project_bindings[1].context_id
    barrier = Barrier(2, timeout=10)

    def resolve(index: int) -> ResolvedTmuxServer:
        """Initialize the same effective registry from independent project contexts."""

        barrier.wait()
        return resolve_tmux_server(selector, execution_binding=project_bindings[index])

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(resolve, range(2))
    assert first == second
    assert resolve_tmux_server(selector, registry_root=other_registry) == first
    assert first.allow_start
    assert not Path(first.socket_path).exists()
    assert Path(first.socket_path).parent.parent == managed_namespace
    (first_record,) = registry.glob("*/record.json")
    (second_record,) = other_registry.glob("*/record.json")
    assert first_record.read_bytes() == second_record.read_bytes()
    assert first_record.stat().st_mode & 0o777 == 0o600
    assert first_record.parent.stat().st_mode & 0o777 == 0o700
    assert list(first_record.parent.glob(".record-*")) == []


def test_default_bootstrap_scope_distinguishes_host_and_container(
    managed_namespace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shared registry metadata for a second socket domain uses independent paths."""

    selector = TmuxServerSelector(server="houmao-default")
    registry = tmp_path / "registry"
    binding = observed_local_binding(
        working_directory=tmp_path,
        registry_root=registry,
        runtime_root=tmp_path / "runtime",
        tmux_socket=None,
    )
    normal = resolve_tmux_server(selector, execution_binding=binding)
    separate_container = resolve_tmux_server(
        selector, execution_binding=binding.model_copy(update={"container_id": "c" * 64})
    )
    monkeypatch.setattr(owner, "_host_identity", lambda: "b" * 64)
    separate_host = resolve_tmux_server(selector, registry_root=registry)
    assert len({normal.socket_path, separate_container.socket_path, separate_host.socket_path}) == 3
    assert len(list(registry.glob("*/record.json"))) == 3
    first_owner = tmux_selection._OwnerScope(uid=os.geteuid(), host_id="a" * 64)
    second_owner = first_owner.model_copy(update={"uid": os.geteuid() + 1})
    assert first_owner.key != second_owner.key
    assert first_owner.socket_directory != second_owner.socket_directory


@pytest.mark.parametrize("bad_record", ["malformed", "symlink", "public", "foreign", "outside"])
def test_default_refuses_unsafe_records(
    bad_record: str, managed_namespace: Path, tmp_path: Path
) -> None:
    """A bad record stays available for diagnosis and cannot redirect startup."""

    selector = TmuxServerSelector(server="houmao-default")
    registry = tmp_path / "registry"
    selected = resolve_tmux_server(selector, registry_root=registry)
    (record,) = registry.glob("*/record.json")
    payload = json.loads(record.read_text())
    message = "record is malformed or unsafe"
    if bad_record == "malformed":
        record.write_text("{")
    elif bad_record == "symlink":
        moved = record.with_suffix(".other")
        record.rename(moved)
        record.symlink_to(moved)
    elif bad_record == "public":
        record.chmod(0o644)
    elif bad_record == "foreign":
        payload["owner"]["uid"] += 1
        record.write_text(json.dumps(payload))
        message = "different execution owner"
    else:
        payload["socket_path"] = str(tmp_path / "unrelated.sock")
        record.write_text(json.dumps(payload))
        message = "outside the owner-private namespace"
    new_contents = record.read_bytes()
    with pytest.raises(ValueError, match=message):
        resolve_tmux_server(selector, registry_root=registry)
    assert record.read_bytes() == new_contents
    assert not Path(selected.socket_path).exists()


def test_default_refuses_conflicting_socket_files(managed_namespace: Path, tmp_path: Path) -> None:
    """An existing regular file at the recorded address is preserved."""

    selector = TmuxServerSelector(server="houmao-default")
    registry = tmp_path / "registry"
    selected = Path(resolve_tmux_server(selector, registry_root=registry).socket_path)
    selected.write_text("not a socket")
    with pytest.raises(ValueError, match="Unsafe object.*default.sock"):
        resolve_tmux_server(selector, registry_root=registry)
    assert selected.read_text() == "not a socket"


def test_read_only_and_agent_cleanup_leave_default_state_untouched(
    managed_namespace: Path, tmp_path: Path
) -> None:
    """Read-only inspection and cleanup never initialize or remove the default."""

    selector = TmuxServerSelector(server="houmao-default")
    registry = tmp_path / "registry"
    with execution_read_only_scope():
        with pytest.raises(ValueError, match="uninitialized"):
            resolve_tmux_server(selector, registry_root=registry)
        with pytest.raises(ValueError, match="requires a launch"):
            resolve_tmux_server(TmuxServerSelector(server="new"), registry_root=registry)
    assert not registry.exists()
    assert not managed_namespace.exists()

    selected = resolve_tmux_server(selector, registry_root=registry)
    (record,) = registry.glob("*/record.json")
    old_content = record.read_bytes()
    socket_dir = Path(selected.socket_path).parent
    socket_dir.rmdir()
    managed_namespace.rmdir()
    with execution_read_only_scope():
        assert resolve_tmux_server(selector, registry_root=registry) == selected
    assert not managed_namespace.exists()

    stale = registry / "live_agents" / "stale-agent"
    stale.mkdir(parents=True)
    cleanup = cleanup_stale_managed_agent_records(
        env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: str(registry)}, probe_local_tmux=False
    )
    assert cleanup.removed_agent_ids == ("stale-agent",)
    assert record.read_bytes() == old_content
    assert not managed_namespace.exists()
