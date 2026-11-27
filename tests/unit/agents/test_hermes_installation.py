"""Check read-only selection of the execution owner's prepared Hermes runtime."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any

import pytest

from houmao.agents import hermes_installation as installation
from houmao.execution.context import execution_binding_scope
from houmao.execution.models import ControllerScopeV1, ExecutionBindingV1


@pytest.fixture
def prepared_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal stock-shaped selection without downloading dependencies."""

    root = tmp_path.resolve() / "hermes"
    root.mkdir(mode=0o700)
    source = root / "hermes-agent"
    source.mkdir(mode=0o700)
    tools = root / "tools"
    tools.mkdir(mode=0o700)
    (root / "gateway-locks").mkdir(mode=0o700)
    launcher = source / ".hermes" / "bin" / "hermes"
    launcher.parent.mkdir(parents=True)
    store_python = tools / "python3"
    store_python.write_text("#!/bin/sh\nexit 99\n")
    store_python.chmod(0o700)
    script = "import sys\n" + f"sys.path.insert(0, {str(source)!r})\n"
    launcher.write_text(
        f'#!/bin/sh\nexec {shlex.join([str(store_python), "-I", "-c", script])} "$@"\n'
    )
    launcher.chmod(0o700)
    state = root / "installs" / hashlib.sha256(str(source).encode()).hexdigest()[:16]
    pm = state / "pm-runtime"
    pm_python = pm / "generations" / "prepared" / "bin" / "python"
    pm_python.parent.mkdir(parents=True)
    pm_python.symlink_to(store_python)
    (pm / "selected.json").write_text('{"generation":"generations/prepared"}')
    (state / "environments" / "prepared" / "venv").mkdir(parents=True)
    monkeypatch.setenv(installation.HERMES_INSTALLATION_ROOT_ENV, str(root))
    monkeypatch.delenv(installation.HERMES_EXECUTABLE_ENV, raising=False)
    return root


def test_prepared_selection_runs_only_read_only_probes(
    prepared_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep ambient launch values out of probes and use the stock prepared paths."""

    root = prepared_root
    source = root / "hermes-agent"
    apps = next((root / "installs").glob("*/environments/prepared/venv"))
    calls: list[list[str]] = []
    monkeypatch.setenv("HERMES_HOME", "/wrong/home")
    monkeypatch.setenv("HERMES_MANAGED_API_KEY", "test-secret")
    monkeypatch.setenv("HERMES_TUI_FORCE_BUILD", "1")

    def native_probe(argv: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        """Return the non-secret native observations expected by the preflight."""

        calls.append(argv)
        assert options["cwd"] == source
        assert options["env"]["HERMES_HOME"] == str(root)
        assert options["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        assert options["env"]["HERMES_DISABLE_LAZY_INSTALLS"] == "1"
        assert "HERMES_MANAGED_API_KEY" not in options["env"]
        assert "HERMES_TUI_FORCE_BUILD" not in options["env"]
        if argv[:1] == ["git"]:
            output = installation.QUALIFIED_HERMES_BUILD if argv[-1] == "HEAD" else ""
        else:
            assert Path(argv[0]).name == "python"
            assert argv[1:4] == ["-I", "-B", "-c"]
            output = json.dumps(
                {
                    "build": installation.QUALIFIED_HERMES_BUILD,
                    "version": "0.23.4",
                    "dependency_environment": str(apps),
                    "dependency_stamp": "generation-inputs",
                    "node": str(root / "tools" / "python3"),
                }
            )
        return subprocess.CompletedProcess(argv, 0, output, "")

    monkeypatch.setattr(installation.subprocess, "run", native_probe)
    selected = installation.load_prepared_hermes_installation()
    assert selected.root == root
    assert selected.executable == str(source / ".hermes" / "bin" / "hermes")
    assert selected.evidence.dependency_environment == apps
    assert selected.lock_dir == root / "gateway-locks"
    assert len(calls) == 3
    first = selected.native_environment(root / "profiles" / "first")
    second = selected.native_environment(root / "profiles" / "second")
    assert first.pop("HERMES_HOME") != second.pop("HERMES_HOME")
    assert first == second
    assert first["HERMES_TUI_DIR"] == str(source / "ui-tui")
    assert first["HERMES_DISABLE_LAZY_INSTALLS"] == "1"
    assert not (root / "profiles").exists()


def test_missing_selection_returns_owner_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing owner configuration cannot fall back to a native default home."""

    monkeypatch.delenv(installation.HERMES_INSTALLATION_ROOT_ENV, raising=False)
    with pytest.raises(
        installation.PreparedHermesInstallationError,
        match="execution context.*HOUMAO_HERMES_INSTALLATION_ROOT.*owner",
    ):
        installation.load_prepared_hermes_installation()


def test_recorded_root_and_expected_executable_cannot_rebind(
    prepared_root: Path, tmp_path: Path
) -> None:
    """A recorded worker cannot change installation during recovery."""

    with pytest.raises(
        installation.PreparedHermesInstallationError, match="recorded owner binding"
    ):
        installation.load_prepared_hermes_installation(expected_root=tmp_path / "different")
    with pytest.raises(installation.PreparedHermesInstallationError, match="outside the prepared"):
        installation.load_prepared_hermes_installation(tmp_path / "other-hermes")
    assert not (prepared_root / "profiles").exists()


def test_caller_cannot_replace_an_admitted_owner(prepared_root: Path) -> None:
    """Use the operation's admitted target identity in preparation diagnostics."""

    owner = ExecutionBindingV1(
        context_id="prepared-context",
        host_id="fixture-host",
        account="fixture-owner",
        uid=os.geteuid(),
        gid=os.getegid(),
        registry_root=str(prepared_root),
        runtime_root=str(prepared_root),
        project_root=str(prepared_root.parent),
        profile_name="fixture-owner",
        transport="ssh",
        controller=ControllerScopeV1(
            controller_id="fixture-controller",
            authority="ssh_account",
            operations=("launch",),
        ),
        route_fingerprint="1" * 64,
    )
    other = owner.model_copy(update={"context_id": "different-context"})
    with (
        execution_binding_scope(owner),
        pytest.raises(
            installation.PreparedHermesInstallationError,
            match="prepared-context.*admitted execution owner",
        ),
    ):
        installation.load_prepared_hermes_installation(owner=other)
    assert not (prepared_root / "profiles").exists()


@pytest.mark.parametrize(
    "reason", ["maintenance", "pm-runtime", "dependencies", "tui", "capabilities"]
)
def test_failed_native_preflight_preserves_prepared_state(
    prepared_root: Path, reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unprepared or unsupported stock dependencies fail before creating a profile."""

    def native_probe(argv: list[str], **_options: Any) -> subprocess.CompletedProcess[str]:
        """Simulate the owner-local probe refusing broken preparation."""

        if argv[:1] == ["git"]:
            output = installation.QUALIFIED_HERMES_BUILD if argv[-1] == "HEAD" else ""
            return subprocess.CompletedProcess(argv, 0, output, "")
        return subprocess.CompletedProcess(argv, 1, "", reason)

    monkeypatch.setattr(installation.subprocess, "run", native_probe)
    expected = set(prepared_root.rglob("*"))
    with pytest.raises(installation.PreparedHermesInstallationError, match="hermes pm install"):
        installation.load_prepared_hermes_installation()
    assert set(prepared_root.rglob("*")) == expected


def test_wrong_build_is_rejected_before_runtime_imports(
    prepared_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unrelated stock version cannot reach the native Python probe."""

    def native_probe(argv: list[str], **_options: Any) -> subprocess.CompletedProcess[str]:
        """Identify an unqualified source revision."""

        assert argv[:1] == ["git"]
        return subprocess.CompletedProcess(argv, 0, "0" * 40, "")

    monkeypatch.setattr(installation.subprocess, "run", native_probe)
    with pytest.raises(installation.PreparedHermesInstallationError, match="different build"):
        installation.load_prepared_hermes_installation()
    assert not (prepared_root / "profiles").exists()
