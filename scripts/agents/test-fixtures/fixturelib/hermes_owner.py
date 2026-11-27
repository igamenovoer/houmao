"""Bind managed Hermes fixtures to one private, already prepared test owner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import select
import signal
from typing import Any

from houmao.agents.hermes_installation import (
    HERMES_INSTALLATION_ROOT_ENV,
    PreparedHermesInstallation,
    load_prepared_hermes_installation,
)
from houmao.agents.realm_controller.backends.headless_runner import _libc_pidfd_call, _signal_worker
from houmao.agents.realm_controller.backends.hermes_native import HermesDaemon
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import BackendExecutionError

from fixturelib.auth import private_directory, write_json
from fixturelib.config import FixtureError, REPO_ROOT


HERMES_FIXTURE_OWNER_ENV = "HOUMAO_TEST_HERMES_OWNER_ROOT"


def selected_owner_root(path: Path | None = None) -> Path:
    """Require one explicitly selected, private Hermes installation inside repository scratch."""

    raw = path if path is not None else os.environ.get(HERMES_FIXTURE_OWNER_ENV)
    if not raw:
        raise FixtureError(f"Select --hermes-owner-root or {HERMES_FIXTURE_OWNER_ENV}")
    selected = Path(raw).expanduser().absolute()
    canonical = selected.resolve()
    scratch = REPO_ROOT / "tmp"
    if canonical == scratch or not canonical.is_relative_to(scratch) or selected != canonical:
        raise FixtureError(
            "Hermes fixture owner root must be a canonical directory under repo tmp/"
        )
    if not canonical.is_dir():
        raise FixtureError("Prepare the selected test-owned stock Hermes installation first")
    metadata = canonical.stat()
    if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
        raise FixtureError("Hermes fixture owner root must be owner-private")
    return canonical


def owner_environment(root: Path) -> dict[str, str]:
    """Restore the test owner's shared scope from an explicitly captured root."""

    owner = root / "fixture-owner"
    return {
        HERMES_INSTALLATION_ROOT_ENV: str(root),
        "HOUMAO_GLOBAL_REGISTRY_DIR": str(owner / "registry"),
        "HOUMAO_GLOBAL_RUNTIME_DIR": str(owner / "runtime"),
        "XDG_CONFIG_HOME": str(owner / "config"),
        "XDG_DATA_HOME": str(owner / "data"),
        "XDG_STATE_HOME": str(owner / "state"),
        "XDG_CACHE_HOME": str(owner / "cache"),
    }


def qualify_owner(root: Path) -> PreparedHermesInstallation:
    """Verify native readiness prerequisites without ambient owner selection."""

    from fixturelib.prepare import command_environment

    with command_environment(owner_environment(root)):
        try:
            return load_prepared_hermes_installation()
        except ValueError as exc:
            raise FixtureError(str(exc)) from None


def initialize_owner(root: Path) -> PreparedHermesInstallation:
    """Prepare private fixture registry and runtime anchors for the selected owner."""

    installed = qualify_owner(root)
    owner = root / "fixture-owner"
    if not owner.exists():
        try:
            existing = _root_daemon(installed).discover()
        except BackendExecutionError:
            raise FixtureError("Cannot verify that the test Hermes root is vacant") from None
        if existing is not None:
            raise FixtureError("Use a test-owned Hermes root with no preexisting gateway")
    for path in (
        owner,
        *(Path(path) for path in owner_environment(root).values() if path != str(root)),
    ):
        if path.resolve() != path:
            raise FixtureError("Hermes fixture owner state redirects outside its recorded scope")
        private_directory(path)
    return installed


def _root_daemon(installed: PreparedHermesInstallation) -> HermesDaemon:
    """Address the exact prepared root gateway without starting one."""

    return HermesDaemon.from_inputs(
        executable=installed.executable,
        home=installed.root,
        workspace=installed.root,
        env=installed.native_environment(installed.root),
        root=installed.root / "fixture-owner",
    )


def observe_profile(
    root: Path, manifest: SessionManifestPayloadV4, installed: PreparedHermesInstallation
) -> dict[str, Any]:
    """Check the reported profile against native ticket, session, and process evidence."""

    profile = manifest.launch_plan.hermes_profile
    if (
        profile is None
        or profile.prepared_root != root
        or not profile.project_home_link.is_symlink()
    ):
        raise FixtureError("Managed Hermes fixture did not capture its named profile and link")
    if (
        profile.project_home_link.resolve() != profile.profile_home
        or profile.installation_build != installed.evidence.build
    ):
        raise FixtureError("Managed Hermes fixture profile differs from its prepared owner")
    daemon = HermesDaemon.from_inputs(
        executable=installed.executable,
        home=profile.profile_home,
        workspace=Path(manifest.working_directory),
        env=installed.native_environment(profile.profile_home),
        root=root / "fixture-owner",
        profile=profile,
    )
    try:
        identity = daemon.discover()
        if identity is None or identity.profile_id != str(profile.profile_home):
            raise FixtureError("The exact managed Hermes profile is not served")
        session_key = "session_id" if manifest.mode == "headless" else "native_session_id"
        logical = manifest.backend_state.get(session_key)
        if not isinstance(logical, str) or not logical:
            raise FixtureError("Managed Hermes fixture did not capture its logical session")
        native = daemon.resolve_session(logical)
        host = _root_daemon(installed).discover()
    except BackendExecutionError:
        raise FixtureError("Native Hermes fixture profile/session could not be verified") from None
    if (
        host is None
        or host.pid != identity.pid
        or host.instance_id != identity.instance_id
        or host.birth_token != identity.birth_token
        or native.daemon_instance_id != identity.instance_id
    ):
        raise FixtureError("Hermes fixture profile does not use the selected native host")
    host_record = {
        "pid": host.pid,
        "birth_token": host.birth_token,
        "instance_id": host.instance_id,
    }
    host_file = root / "fixture-owner/host.json"
    if host_file.is_file() and json.loads(host_file.read_bytes()) != host_record:
        raise FixtureError("The fixture owner reached a different gateway incarnation")
    write_json(host_file, host_record)
    return {
        "prepared_root": str(root),
        "context_id": profile.context_id,
        "profile_id": identity.profile_id,
        "profile_name": profile.profile_name,
        "project_home_link": str(profile.project_home_link),
        "workspace": manifest.working_directory,
        "session_id": native.session_id,
        "generation_id": manifest.registry_generation_id,
        "authority_epoch": identity.authority_epoch,
        "build": installed.evidence.build,
        "version": installed.evidence.version,
        "dependency_environment": str(installed.evidence.dependency_environment),
        "dependency_stamp": installed.evidence.dependency_stamp,
        "host": host_record,
    }


def retire_owner(root: Path) -> dict[str, Any]:
    """Retire only the observed stock test host after all named profiles are removed."""

    installed = qualify_owner(root)
    profiles = root / "profiles"
    if profiles.is_symlink() or (
        profiles.is_dir()
        and any(
            path.is_symlink() or (path.is_dir() and path.name != ".deleted")
            for path in profiles.iterdir()
        )
    ):
        raise FixtureError("Remove every named fixture profile before retiring its test host")
    daemon = _root_daemon(installed)
    try:
        record = json.loads((root / "fixture-owner/host.json").read_bytes())
        current = daemon.discover()
        if current is None:
            raise FixtureError("Cannot verify the fixture's saved host for retirement")
        if record != {
            "pid": current.pid,
            "birth_token": current.birth_token,
            "instance_id": current.instance_id,
        }:
            raise FixtureError("Fixture host changed since its last native observation")
        descriptor = (
            os.pidfd_open(current.pid)
            if hasattr(os, "pidfd_open")
            else _libc_pidfd_call("pidfd_open", current.pid, 0)
        )
        try:
            if daemon.discover() != current:
                raise FixtureError("Fixture host changed before retirement")
            _signal_worker(descriptor, signal.SIGTERM)
            observer = select.poll()
            observer.register(descriptor, select.POLLIN)
            if not observer.poll(15_000):
                raise FixtureError("Fixture host has not exited after its scoped shutdown")
        finally:
            os.close(descriptor)
        if daemon.discover() is not None:
            raise FixtureError("A different host appeared during fixture teardown")
    except (AttributeError, OSError, ValueError, BackendExecutionError):
        raise FixtureError("Could not verify exact fixture host retirement") from None
    evidence = {"prepared_root": str(root), "retired_host": record, "host_exited": True}
    write_json(root / "fixture-owner/retired-host.json", evidence)
    (root / "fixture-owner/host.json").unlink()
    return evidence
