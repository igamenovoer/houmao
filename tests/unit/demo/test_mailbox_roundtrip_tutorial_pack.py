"""Unit tests for the mailbox roundtrip tutorial-pack helpers."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _helper_module() -> ModuleType:
    """Load the pack-local helper module from disk."""

    helper_path = (
        _repo_root()
        / "scripts"
        / "demo"
        / "mailbox-roundtrip-tutorial-pack"
        / "scripts"
        / "tutorial_pack_helpers.py"
    )
    module_name = "mailbox_roundtrip_tutorial_pack_helpers"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _helper_module()
PACK_DIR = _repo_root() / "scripts" / "demo" / "mailbox-roundtrip-tutorial-pack"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_tracked_demo_parameters_parse_and_render_demo_output_mailbox_root() -> None:
    """The tracked parameter file should expose the documented schema."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    assert parameters.backend == "cao_rest"
    assert parameters.sender.blueprint == "blueprints/gpu-kernel-coder-claude.yaml"
    assert parameters.receiver.blueprint == "blueprints/gpu-kernel-coder-codex.yaml"
    assert parameters.message.initial_body_file == "inputs/initial_message.md"
    assert HELPERS.render_mailbox_root(
        parameters,
        demo_output_dir=Path("/tmp/tutorial-pack"),
    ) == Path("/tmp/tutorial-pack/shared-mailbox")
    assert parameters.shared_mailbox_root_template == "{demo_output_dir}/shared-mailbox"


def test_demo_layout_helpers_resolve_repo_relative_paths() -> None:
    """Demo-output-dir and nested project paths should derive from the repository root."""

    repo_root = Path("/repo-root")

    default_output = HELPERS.resolve_repo_relative_path(
        None,
        repo_root=repo_root,
        default_relative="tmp/demo/mailbox-roundtrip-tutorial-pack",
    )
    explicit_output = HELPERS.resolve_repo_relative_path(
        "demos/manual-mailbox-run",
        repo_root=repo_root,
    )
    layout = HELPERS.build_demo_layout(demo_output_dir=explicit_output)

    assert default_output == Path("/repo-root/tmp/demo/mailbox-roundtrip-tutorial-pack")
    assert explicit_output == Path("/repo-root/demos/manual-mailbox-run")
    assert layout.project_workdir == explicit_output / "project"
    assert layout.runtime_root == explicit_output / "runtime"
    assert layout.mailbox_root == explicit_output / "shared-mailbox"
    assert layout.report_path == explicit_output / "report.json"


def test_detect_cao_profile_store_prefers_launcher_ownership_home_dir(tmp_path: Path) -> None:
    """Profile-store detection should prefer the launcher ownership artifact when present."""

    repo_root = tmp_path / "repo"
    config_dir = repo_root / "config" / "cao-server-launcher"
    runtime_root = repo_root / "tmp" / "agents-runtime"
    launcher_home = tmp_path / "launcher-home-from-ownership"
    ownership_path = runtime_root / "cao_servers" / "127.0.0.1-9991" / "launcher" / "ownership.json"
    config_dir.mkdir(parents=True)
    ownership_path.parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "local.toml").write_text(
        '\n'.join(
            [
                'base_url = "http://localhost:9889"',
                f'runtime_root = "{runtime_root}"',
                f'home_dir = "{tmp_path / "launcher-home-from-config"}"',
                'proxy_policy = "clear"',
                "startup_timeout_seconds = 15",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ownership_path.write_text(
        json.dumps(
            {
                "managed_by": "houmao.cao.server_launcher",
                "launch_mode": "detached",
                "base_url": "http://127.0.0.1:9991",
                "runtime_root": str(runtime_root),
                "artifact_dir": str(ownership_path.parent),
                "home_dir": str(launcher_home),
                "config_path": str(config_dir / "local.toml"),
                "proxy_policy": "clear",
                "pid": 1234,
                "process_group_id": 1234,
                "executable_path": str(tmp_path / "bin" / "cao-server"),
                "started_at_utc": "2026-03-16T09:00:00+00:00",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    detected = HELPERS.detect_cao_profile_store(
        repo_root=repo_root,
        cao_base_url="http://127.0.0.1:9991",
    )

    assert detected == launcher_home / ".aws" / "cli-agent-orchestrator" / "agent-store"


def test_detect_cao_profile_store_falls_back_to_matching_launcher_config_home_dir(
    tmp_path: Path,
) -> None:
    """Profile-store detection should fall back to launcher config when ownership is absent."""

    repo_root = tmp_path / "repo"
    config_dir = repo_root / "config" / "cao-server-launcher"
    launcher_home = tmp_path / "launcher-home"
    config_dir.mkdir(parents=True)
    (config_dir / "local.toml").write_text(
        '\n'.join(
            [
                'base_url = "http://localhost:9889"',
                f'runtime_root = "{repo_root / "tmp" / "agents-runtime"}"',
                f'home_dir = "{launcher_home}"',
                'proxy_policy = "clear"',
                "startup_timeout_seconds = 15",
                "",
            ]
        ),
        encoding="utf-8",
    )

    detected = HELPERS.detect_cao_profile_store(
        repo_root=repo_root,
        cao_base_url="http://localhost:9889",
    )

    assert detected == launcher_home / ".aws" / "cli-agent-orchestrator" / "agent-store"


def test_detect_cao_profile_store_returns_none_for_unrelated_base_url_without_ownership(
    tmp_path: Path,
) -> None:
    """Profile-store detection should not guess when only an unrelated config base URL is present."""

    repo_root = tmp_path / "repo"
    config_dir = repo_root / "config" / "cao-server-launcher"
    config_dir.mkdir(parents=True)
    (config_dir / "local.toml").write_text(
        '\n'.join(
            [
                'base_url = "http://localhost:9889"',
                f'runtime_root = "{repo_root / "tmp" / "agents-runtime"}"',
                f'home_dir = "{tmp_path / "launcher-home"}"',
                'proxy_policy = "clear"',
                "startup_timeout_seconds = 15",
                "",
            ]
        ),
        encoding="utf-8",
    )

    detected = HELPERS.detect_cao_profile_store(
        repo_root=repo_root,
        cao_base_url="http://127.0.0.1:9991",
    )

    assert detected is None


def test_ensure_project_worktree_provisions_missing_project_directory(tmp_path: Path) -> None:
    """Missing project directories should be provisioned through git worktree add."""

    repo_root = tmp_path / "repo"
    project_workdir = tmp_path / "demo-output" / "project"
    calls: list[tuple[list[str], Path]] = []

    def fake_run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((args, cwd))
        if args == ["git", "worktree", "add", "--detach", str(project_workdir.resolve()), "HEAD"]:
            project_workdir.mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if cwd == repo_root and args == ["git", "rev-parse", "--git-common-dir"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=str((repo_root / ".git").resolve()) + "\n",
                stderr="",
            )
        if cwd == project_workdir and args == ["git", "rev-parse", "--is-inside-work-tree"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="true\n", stderr="")
        if cwd == project_workdir and args == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=str(project_workdir.resolve()) + "\n",
                stderr="",
            )
        if cwd == project_workdir and args == ["git", "rev-parse", "--git-common-dir"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=str((repo_root / ".git").resolve()) + "\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="unexpected")

    resolved = HELPERS.ensure_project_worktree(
        repo_root=repo_root,
        project_workdir=project_workdir,
        run_git=fake_run_git,
    )

    assert resolved == project_workdir.resolve()
    assert any(call[0][:4] == ["git", "worktree", "add", "--detach"] for call in calls)


def test_ensure_project_worktree_rejects_incompatible_existing_directory(tmp_path: Path) -> None:
    """Existing non-worktree project directories should fail clearly."""

    repo_root = tmp_path / "repo"
    project_workdir = tmp_path / "demo-output" / "project"
    project_workdir.mkdir(parents=True)

    def fake_run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="not a worktree")

    with pytest.raises(ValueError, match="not a git worktree"):
        HELPERS.ensure_project_worktree(
            repo_root=repo_root,
            project_workdir=project_workdir,
            run_git=fake_run_git,
        )


def test_extract_json_value_and_message_id_require_present_non_empty_fields(tmp_path: Path) -> None:
    """Generic JSON extraction and message-id parsing should fail clearly on bad input."""

    payload_path = tmp_path / "mail_send.json"
    _write_json(
        payload_path,
        {
            "message_id": "msg-20260316T120000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "nested": {"value": "ok"},
        },
    )

    assert HELPERS.extract_json_value(payload_path, "nested.value") == "ok"
    assert (
        HELPERS.extract_message_id(payload_path)
        == "msg-20260316T120000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )

    _write_json(payload_path, {"message_id": "   "})
    with pytest.raises(ValueError, match="message_id"):
        HELPERS.extract_message_id(payload_path)


def test_build_report_and_sanitize_report_mask_nondeterministic_fields(tmp_path: Path) -> None:
    """The raw report should capture checks, and sanitization should mask unstable values."""

    demo_output_dir = tmp_path / "demo-output"
    project_workdir = demo_output_dir / "project"
    runtime_root = demo_output_dir / "runtime"
    mailbox_root = demo_output_dir / "shared-mailbox"
    agent_def_dir = tmp_path / "repo" / "tests" / "fixtures" / "agents"
    report_path = demo_output_dir / "report.json"
    parameters_path = PACK_DIR / "inputs" / "demo_parameters.json"
    message_id = "msg-20260316T120000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    artifacts = {
        "sender_build": {
            "home_id": "home-sender",
            "home_path": str(runtime_root / "homes" / "claude" / "home-sender"),
            "manifest_path": str(runtime_root / "manifests" / "sender.yaml"),
            "launch_helper_path": str(runtime_root / "homes" / "claude" / "home-sender" / "launch.sh"),
        },
        "receiver_build": {
            "home_id": "home-receiver",
            "home_path": str(runtime_root / "homes" / "codex" / "home-receiver"),
            "manifest_path": str(runtime_root / "manifests" / "receiver.yaml"),
            "launch_helper_path": str(runtime_root / "homes" / "codex" / "home-receiver" / "launch.sh"),
        },
        "sender_start": {
            "session_manifest": str(runtime_root / "sessions" / "sender.json"),
            "backend": "cao_rest",
            "tool": "claude",
            "agent_identity": "AGENTSYS-mailbox-sender",
            "tmux_session_name": "AGENTSYS-mailbox-sender",
            "job_dir": str(project_workdir / ".houmao" / "jobs" / "sender"),
            "mailbox": {
                "transport": "filesystem",
                "principal_id": "AGENTSYS-mailbox-sender",
                "address": "AGENTSYS-mailbox-sender@agents.localhost",
                "filesystem_root": str(mailbox_root),
                "bindings_version": "2026-03-16T12:00:01Z",
            },
        },
        "receiver_start": {
            "session_manifest": str(runtime_root / "sessions" / "receiver.json"),
            "backend": "cao_rest",
            "tool": "codex",
            "agent_identity": "AGENTSYS-mailbox-receiver",
            "tmux_session_name": "AGENTSYS-mailbox-receiver",
            "job_dir": str(project_workdir / ".houmao" / "jobs" / "receiver"),
            "mailbox": {
                "transport": "filesystem",
                "principal_id": "AGENTSYS-mailbox-receiver",
                "address": "AGENTSYS-mailbox-receiver@agents.localhost",
                "filesystem_root": str(mailbox_root),
                "bindings_version": "2026-03-16T12:00:02Z",
            },
        },
        "mail_send": {
            "ok": True,
            "operation": "send",
            "request_id": "req-send",
            "message_id": message_id,
            "thread_id": message_id,
            "subject": "Mailbox tutorial roundtrip",
        },
        "receiver_check": {
            "ok": True,
            "operation": "check",
            "request_id": "req-check-receiver",
            "unread_count": 1,
        },
        "mail_reply": {
            "ok": True,
            "operation": "reply",
            "request_id": "req-reply",
            "message_id": "msg-20260316T120500Z-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "thread_id": message_id,
        },
        "sender_check": {
            "ok": True,
            "operation": "check",
            "request_id": "req-check-sender",
            "unread_count": 1,
        },
        "sender_stop": {"status": "ok", "action": "terminate", "detail": "stopped"},
        "receiver_stop": {"status": "ok", "action": "terminate", "detail": "stopped"},
    }

    for label, payload in artifacts.items():
        _write_json(demo_output_dir / f"{label}.json", payload)

    report = HELPERS.build_report(
        output_path=report_path,
        parameters_path=parameters_path,
        demo_output_dir=demo_output_dir,
        project_workdir=project_workdir,
        runtime_root=runtime_root,
        mailbox_root=mailbox_root,
        agent_def_dir=agent_def_dir,
        reply_parent_message_id=message_id,
    )

    assert report["checks"]["shared_mailbox_root"] is True
    assert report["checks"]["reply_parent_matches_send_message_id"] is True

    sanitized = HELPERS.sanitize_report(report)

    assert sanitized["generated_at_utc"] == "<TIMESTAMP>"
    assert sanitized["demo_output_dir"] == "<DEMO_OUTPUT_DIR>"
    assert sanitized["project_workdir"] == "<PROJECT_WORKDIR>"
    assert sanitized["runtime_root"] == "<RUNTIME_ROOT>"
    assert sanitized["agent_def_dir"] == "<AGENT_DEF_DIR>"
    assert sanitized["reply_parent_message_id"] == "<MESSAGE_ID>"
    assert sanitized["artifacts"]["mail_send"] == "<ARTIFACT_PATH:mail_send>"
    assert sanitized["steps"]["sender_build"]["home_id"] == "<BRAIN_HOME_ID>"
    assert sanitized["steps"]["sender_start"]["session_manifest"] == "<SESSION_MANIFEST_PATH>"
    assert sanitized["steps"]["sender_start"]["mailbox"]["filesystem_root"] == "<MAILBOX_FILESYSTEM_ROOT>"
    assert sanitized["steps"]["sender_start"]["job_dir"] == "<JOB_DIR>"
    assert sanitized["steps"]["mail_send"]["message_id"] == "<MESSAGE_ID>"
    assert sanitized["steps"]["mail_send"]["thread_id"] == "<THREAD_ID>"
    assert sanitized["steps"]["mail_reply"]["request_id"] == "<REQUEST_ID>"


def test_verify_sanitized_report_detects_mismatch() -> None:
    """Sanitized verification should pass on equality and fail on drift."""

    actual = {"demo": "mailbox-roundtrip-tutorial-pack", "checks": {"sender_stop_ok": True}}
    HELPERS.verify_sanitized_report(actual, dict(actual))

    with pytest.raises(ValueError, match="sanitized report mismatch"):
        HELPERS.verify_sanitized_report(actual, {"demo": "mailbox-roundtrip-tutorial-pack"})
