"""Exercise named-profile build cleanup and retry through its normal entrypoint."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from subprocess import CompletedProcess
from types import SimpleNamespace

import pytest

from houmao.agents import hermes_profile_cleanup
from houmao.agents.brain_builder import BuildResult
from houmao.agents.hermes_profile import HermesProfileBinding, write_hermes_profile_record
from houmao.agents.realm_controller.errors import RuntimeStartupRollbackError
from houmao.srv_ctrl.commands import runtime_cleanup
from houmao.srv_ctrl.commands.agents import core


@pytest.fixture
def owned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, HermesProfileBinding]:
    """Build one parked synthetic profile and an independently located project link."""

    runtime = tmp_path / "owner-runtime"
    root = tmp_path / "hermes"
    home = root / "profiles" / "owned-profile"
    link = tmp_path / "project" / "runtime" / "homes" / "home-id"
    binding = HermesProfileBinding(
        prepared_root=root,
        profile_home=home,
        profile_name=home.name,
        context_id="test-owner",
        gateway_lock_dir=root / "gateway-locks",
        project_home_link=link,
        installation_build="a" * 40,
        profile_owner_id="profile-1",
        executable=root / "bin" / "hermes",
        broker_socket=tmp_path / "proof.sock",
    )
    home.mkdir(mode=0o700, parents=True)
    link.parent.mkdir(mode=0o700, parents=True)
    link.symlink_to(home)
    (home / "gateway.parked").touch(mode=0o600)
    write_hermes_profile_record(home, binding)
    manifest = runtime / "manifests" / "home-id.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "credentials": {},
                "runtime": {
                    "runtime_root": str(runtime),
                    "home_id": "home-id",
                    "home_path": str(home),
                    "hermes_profile": binding.model_dump(mode="json"),
                },
            }
        )
    )
    monkeypatch.setattr(
        hermes_profile_cleanup,
        "_check_installation",
        lambda _: SimpleNamespace(native_environment=lambda __: {}),
    )

    def verify_release(*, require_parked: bool = True) -> None:
        """Represent separate route/reservation release from the native daemon."""

        if require_parked and home.exists():
            assert (home / "gateway.parked").is_file()

    monkeypatch.setattr(
        hermes_profile_cleanup,
        "_native_daemon",
        lambda _: SimpleNamespace(verify_profile_released=verify_release),
    )
    return runtime, manifest, binding


def _cleanup(runtime: Path, *, dry_run: bool = False) -> dict[str, object]:
    """Select build cleanup from its usual owner runtime."""

    return runtime_cleanup.cleanup_runtime_builds(
        runtime_root=runtime, older_than_seconds=0, dry_run=dry_run
    )


def _native_delete(binding: HermesProfileBinding) -> None:
    """Mirror stock tombstoning and physical removal in a fixture native command."""

    tombstone = binding.profile_home.parent / ".deleted" / binding.profile_name
    tombstone.parent.mkdir(mode=0o700, exist_ok=True)
    tombstone.write_bytes(b"deleted\n")
    tombstone.chmod(0o600)
    shutil.rmtree(binding.profile_home)


@pytest.mark.parametrize("incomplete_runtime", [False, True])
def test_failed_launch_releases_only_the_acquired_hermes_build(
    owned_profile: tuple[Path, Path, HermesProfileBinding],
    monkeypatch: pytest.MonkeyPatch,
    incomplete_runtime: bool,
) -> None:
    """Keep fresh build evidence whenever runtime rollback cannot prove quiescence."""

    _, manifest, profile = owned_profile
    home = profile.project_home_link
    result = BuildResult(home.name, home, manifest, home / "launch.sh", "", {}, profile)
    sibling = profile.profile_home.with_name("sibling")
    sibling.mkdir()

    def run(command: list[str], **_: object) -> CompletedProcess[str]:
        """Delete exactly the fixture's fresh profile through its native command."""

        assert command[-3:] == ["delete", profile.profile_name, "--yes"]
        _native_delete(profile)
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", run)
    startup_error = RuntimeError("fixture startup failed")
    failure = (
        RuntimeStartupRollbackError(startup_error, ("runtime publication uncertain",))
        if incomplete_runtime
        else startup_error
    )

    detail = core._settle_failed_hermes_build(result, failure)

    assert sibling.is_dir()
    assert (
        home.is_symlink()
        == manifest.exists()
        == profile.profile_home.exists()
        == incomplete_runtime
    )
    assert bool(detail) == incomplete_runtime


def test_preview_and_apply_clean_two_owned_artifacts(
    owned_profile: tuple[Path, Path, HermesProfileBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, manifest, binding = owned_profile
    sibling = binding.profile_home.with_name("sibling")
    sibling.mkdir()
    calls = []

    def run(command: list[str], **options: object) -> CompletedProcess[str]:
        """Run only the exact stock operation for the owned profile."""

        assert options["cwd"] == binding.prepared_root
        calls.append(command)
        _native_delete(binding)
        return CompletedProcess(command, 0)

    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", run)
    preview = _cleanup(runtime, dry_run=True)
    assert [item["artifact_kind"] for item in preview["planned_actions"]] == [
        "runtime_hermes_profile",
        "runtime_home_link",
        "runtime_build_manifest",
    ]
    assert calls == [] and manifest.exists() and binding.project_home_link.is_symlink()
    assert not (binding.prepared_root / ".houmao-host").exists()
    applied = _cleanup(runtime)
    assert not applied["blocked_actions"]
    assert calls == [[str(binding.executable), "profile", "delete", binding.profile_name, "--yes"]]
    assert sibling.is_dir() and not manifest.exists()
    assert not os.path.lexists(binding.project_home_link)


def test_retry_settles_identity_then_unlinks_dangling_entry(
    owned_profile: tuple[Path, Path, HermesProfileBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, manifest, binding = owned_profile
    verbs = []

    def run(command: list[str], **_: object) -> CompletedProcess[str]:
        """Physically remove once, then settle the exact retired routing identity."""

        verbs.append(command[2])
        if command[2] == "delete":
            _native_delete(binding)
            return CompletedProcess(command, 1)
        return CompletedProcess(command, 0)

    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", run)
    failure = _cleanup(runtime)
    assert len(failure["blocked_actions"]) == 2
    assert "routing identity settlement is pending" in failure["blocked_actions"][0]["reason"]
    assert manifest.exists() and binding.project_home_link.is_symlink()
    assert not binding.profile_home.exists()
    with pytest.raises(hermes_profile_cleanup.HermesProfileCleanupError, match="deletion evidence"):
        hermes_profile_cleanup.require_unused_hermes_profile_name(binding)
    retry = _cleanup(runtime)
    assert not retry["blocked_actions"], [item["reason"] for item in retry["blocked_actions"]]
    assert verbs == ["delete", "purge-identity"]
    assert not manifest.exists() and not os.path.lexists(binding.project_home_link)


def test_retry_refuses_a_replacement_profile_in_the_same_slot(
    owned_profile: tuple[Path, Path, HermesProfileBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, manifest, binding = owned_profile

    def fail_after_delete(command: list[str], **_: object) -> CompletedProcess[str]:
        """Remove the old home while leaving its native identity pending."""

        _native_delete(binding)
        return CompletedProcess(command, 1)

    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", fail_after_delete)
    assert _cleanup(runtime)["blocked_actions"]
    binding.profile_home.mkdir(mode=0o700)
    write_hermes_profile_record(
        binding.profile_home, binding.model_copy(update={"profile_owner_id": "replacement"})
    )
    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", pytest.fail)
    assert _cleanup(runtime)["blocked_actions"]
    assert (
        manifest.exists()
        and binding.profile_home.is_dir()
        and binding.project_home_link.is_symlink()
    )


def test_native_reservation_keeps_profile_and_project_link(
    owned_profile: tuple[Path, Path, HermesProfileBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, manifest, binding = owned_profile

    def reservation_held() -> None:
        """Represent a parked route that still has a native writer."""

        raise hermes_profile_cleanup.HermesProfileCleanupError("Native reservation is held.")

    monkeypatch.setattr(
        hermes_profile_cleanup,
        "_native_daemon",
        lambda _: SimpleNamespace(verify_profile_released=reservation_held),
    )
    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", pytest.fail)
    assert len(_cleanup(runtime, dry_run=True)["blocked_actions"]) == 2
    assert len(_cleanup(runtime)["blocked_actions"]) == 2
    assert (
        manifest.exists()
        and binding.profile_home.is_dir()
        and binding.project_home_link.is_symlink()
    )


def test_changed_link_and_preexisting_absence_preserve_unrelated_artifacts(
    owned_profile: tuple[Path, Path, HermesProfileBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, manifest, binding = owned_profile
    _native_delete(binding)
    unrelated = runtime / "unrelated"
    unrelated.write_text("keep")
    binding.project_home_link.unlink()
    binding.project_home_link.symlink_to(unrelated)
    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", pytest.fail)
    report = _cleanup(runtime)
    assert [item["artifact_kind"] for item in report["blocked_actions"]] == ["runtime_home_link"]
    assert manifest.exists() and unrelated.read_text() == "keep"
    binding.project_home_link.unlink()
    binding.project_home_link.symlink_to(binding.profile_home)
    assert not _cleanup(runtime)["blocked_actions"]
    assert not os.path.lexists(binding.project_home_link) and unrelated.exists()


def test_preserved_runtime_reference_blocks_both_named_artifacts(
    owned_profile: tuple[Path, Path, HermesProfileBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, manifest, binding = owned_profile
    retained = SimpleNamespace(
        payload=SimpleNamespace(
            brain_manifest_path=str(manifest), launch_plan=SimpleNamespace(hermes_profile=binding)
        ),
        session_root=runtime / "retained-session",
        retirement=None,
        live=False,
        parse_error=None,
    )
    retained.session_root.mkdir()
    monkeypatch.setattr(
        runtime_cleanup, "discover_runtime_session_envelopes", lambda _: (retained,)
    )
    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", pytest.fail)
    report = _cleanup(runtime)
    assert not report["applied_actions"]
    assert len(report["preserved_actions"]) == 3
    assert binding.project_home_link.is_symlink() and binding.profile_home.is_dir()


def test_force_clean_retry_finishes_a_stopped_predecessor_once(
    owned_profile: tuple[Path, Path, HermesProfileBinding], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, manifest, binding = owned_profile
    session = runtime / "sessions" / "hermes_headless" / "predecessor"
    session.mkdir(parents=True)
    record = SimpleNamespace(
        identity=SimpleNamespace(tool="hermes"), lifecycle=SimpleNamespace(state="active")
    )
    context = core._ManagedPredecessorHomeContext(
        agent_name="worker",
        agent_id="worker",
        record=record,
        home_id=binding.project_home_link.name,
        home_path=binding.profile_home,
        runtime_root=runtime,
        last_tmux_session_name=None,
        force_mode="clean",
        target=SimpleNamespace(mode="local"),
        session_root=session,
        mailbox_cleanup_paths=(),
        brain_manifest_path=manifest,
        hermes_profile=binding,
    )
    operations = []

    def stop(_: object) -> SimpleNamespace:
        """Record the single confirmed transition away from the live worker."""

        operations.append("stop")
        record.lifecycle.state = "stopped"
        return SimpleNamespace(success=True)

    def run(command: list[str], **_: object) -> CompletedProcess[str]:
        """Confirm physical cleanup before reporting an unresolved native identity."""

        verb = command[2]
        operations.append(verb)
        if verb == "delete":
            _native_delete(binding)
            return CompletedProcess(command, 1)
        return CompletedProcess(command, 0)

    monkeypatch.setattr(core, "stop_managed_agent", stop)
    monkeypatch.setattr(core, "resolve_live_agent_record_by_agent_id", lambda _: None)
    monkeypatch.setattr(hermes_profile_cleanup.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="predecessor stopped.*cleanup is incomplete"):
        core._perform_managed_force_takeover(context)
    assert manifest.exists() and session.exists() and binding.project_home_link.is_symlink()
    core._perform_managed_force_takeover(context)
    assert operations == ["stop", "delete", "purge-identity"]
    assert not manifest.exists() and not session.exists()
    assert not os.path.lexists(binding.project_home_link)
