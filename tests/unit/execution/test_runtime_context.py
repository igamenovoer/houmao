"""Persisted controller authority stays independent across runtime operations."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.models import InteractiveSession, LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.execution.context import current_execution_binding, observed_local_binding
from houmao.execution.models import ExecutionBindingV1
from houmao.execution.tmux import current_tmux_socket_path


def _controller(root: Path) -> RuntimeSessionController:
    """Construct an owner-bound controller without starting any native process."""

    binding = observed_local_binding(
        working_directory=root,
        runtime_root=root / "runtime",
        registry_root=root / "registry",
        tmux_socket=str(root / "tmux.sock"),
    )
    return RuntimeSessionController(
        launch_plan=LaunchPlan(
            backend="claude_headless",
            tool="claude",
            executable="unused",
            args=[],
            working_directory=root,
            home_env_var="CLAUDE_CONFIG_DIR",
            home_path=root / "native-home",
            env={},
            env_var_names=[],
            role_injection=RoleInjectionPlan(
                method="native_append_system_prompt", role_name="r", prompt=""
            ),
            metadata={"tmux_socket_path": binding.tmux_socket},
            execution_binding=binding,
        ),
        role_name="r",
        brain_manifest_path=root / "brain.yaml",
        manifest_path=root / "manifest.json",
        backend_session=cast(InteractiveSession, object()),
    )


def test_concurrent_controllers_restore_their_own_owner_and_socket(tmp_path: Path) -> None:
    """Worker threads use each saved context rather than a process-global selector."""

    controllers = [_controller(tmp_path / "first"), _controller(tmp_path / "second")]

    def observed(
        controller: RuntimeSessionController,
    ) -> tuple[ExecutionBindingV1 | None, str | None]:
        """Read the complete authority visible inside one controller operation."""

        with controller.execution_scope():
            return current_execution_binding(), current_tmux_socket_path()

    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(observed, controllers))
    assert values == [(c.execution_binding, c.tmux_socket_path) for c in controllers]
    assert values[0][0] != values[1][0]
    assert current_execution_binding() is None
    assert current_tmux_socket_path() is None


def test_nested_operation_cannot_replace_admitted_owner(tmp_path: Path) -> None:
    """Another controller cannot turn an admitted request into a different context."""

    first = _controller(tmp_path / "first")
    second = _controller(tmp_path / "second")
    with first.execution_scope():
        with pytest.raises(SessionManifestError, match="binding differs"):
            with second.execution_scope():
                pytest.fail("A mismatched owner context must not be admitted")
        assert current_execution_binding() == first.execution_binding
        assert current_tmux_socket_path() == first.tmux_socket_path
    assert current_execution_binding() is None


def test_controller_refuses_wrong_actual_os_owner(tmp_path: Path) -> None:
    """Persisted identity fields cannot authorize control as a different UID."""

    controller = _controller(tmp_path)
    binding = controller.execution_binding
    assert binding is not None
    controller.launch_plan = replace(
        controller.launch_plan,
        execution_binding=binding.model_copy(update={"uid": binding.uid + 1}),
    )
    with pytest.raises(SessionManifestError, match="UID/GID"):
        with controller.execution_scope():
            pytest.fail("Control must verify actual UID/GID")


def test_local_controller_refuses_replaced_context_without_repair(tmp_path: Path) -> None:
    """A recreated owner context cannot adopt a persisted agent by UID alone."""

    controller = _controller(tmp_path)
    binding = controller.execution_binding
    assert binding is not None
    context_path = Path(binding.runtime_root) / "execution-context.json"
    replacement = json.loads(context_path.read_text())
    replacement["context_id"] = str(uuid4())
    context_path.write_text(json.dumps(replacement))
    before = context_path.read_bytes()
    with pytest.raises(SessionManifestError, match="context differs"):
        with controller.execution_scope():
            pytest.fail("A replacement owner context must be rejected")
    assert context_path.read_bytes() == before
