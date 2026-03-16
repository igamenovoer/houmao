#!/usr/bin/env python3
"""Helper utilities for the mailbox roundtrip tutorial pack."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from typing import Any

_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
)
_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_FLOW = [
    "sender_build",
    "receiver_build",
    "sender_start",
    "receiver_start",
    "mail_send",
    "receiver_check",
    "mail_reply",
    "sender_check",
    "sender_stop",
    "receiver_stop",
]
_ARTIFACT_FILENAMES = {label: f"{label}.json" for label in _FLOW}
_PATH_PLACEHOLDERS = {
    "demo_output_dir": "<DEMO_OUTPUT_DIR>",
    "project_workdir": "<PROJECT_WORKDIR>",
    "runtime_root": "<RUNTIME_ROOT>",
    "mailbox_root": "<MAILBOX_ROOT>",
    "agent_def_dir": "<AGENT_DEF_DIR>",
    "session_manifest": "<SESSION_MANIFEST_PATH>",
    "manifest_path": "<BRAIN_MANIFEST_PATH>",
    "home_path": "<BRAIN_HOME_PATH>",
    "launch_helper_path": "<LAUNCH_HELPER_PATH>",
    "job_dir": "<JOB_DIR>",
    "filesystem_root": "<MAILBOX_FILESYSTEM_ROOT>",
}
_VALUE_PLACEHOLDERS = {
    "generated_at_utc": "<TIMESTAMP>",
    "bindings_version": "<BINDINGS_VERSION>",
    "message_id": "<MESSAGE_ID>",
    "thread_id": "<THREAD_ID>",
    "request_id": "<REQUEST_ID>",
    "reply_parent_message_id": "<MESSAGE_ID>",
    "agent_id": "<AGENT_ID>",
    "home_id": "<BRAIN_HOME_ID>",
}
_TIMESTAMP_KEYS = {
    "created_at",
    "generated_at_utc",
    "received_at",
    "sent_at",
    "started_at",
    "updated_at",
}
_DEFAULT_DEMO_OUTPUT_DIR = Path("tmp/demo/mailbox-roundtrip-tutorial-pack")


GitRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class DemoParticipant:
    """One tutorial participant definition."""

    blueprint: str
    agent_identity: str
    mailbox_principal_id: str
    mailbox_address: str


@dataclass(frozen=True)
class MessageConfig:
    """Tracked message content configuration."""

    subject: str
    initial_body_file: str
    reply_body_file: str


@dataclass(frozen=True)
class DemoParameters:
    """Validated tutorial input parameters."""

    schema_version: int
    demo_id: str
    agent_def_dir: str
    backend: str
    cao_base_url: str
    shared_mailbox_root_template: str
    sender: DemoParticipant
    receiver: DemoParticipant
    message: MessageConfig


@dataclass(frozen=True)
class DemoLayout:
    """Resolved demo-owned filesystem layout."""

    demo_output_dir: Path
    project_workdir: Path
    runtime_root: Path
    inputs_dir: Path
    mailbox_root: Path
    report_path: Path
    sanitized_report_path: Path


def _read_json(path: Path) -> Any:
    """Load one JSON value from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    """Write one JSON value to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one mapping value or raise a validation error."""

    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value


def _require_non_empty_string(value: Any, *, context: str) -> str:
    """Return one non-empty string or raise a validation error."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _participant_from_payload(payload: Any, *, context: str) -> DemoParticipant:
    """Parse one participant block."""

    mapping = _require_mapping(payload, context=context)
    return DemoParticipant(
        blueprint=_require_non_empty_string(mapping.get("blueprint"), context=f"{context}.blueprint"),
        agent_identity=_require_non_empty_string(
            mapping.get("agent_identity"), context=f"{context}.agent_identity"
        ),
        mailbox_principal_id=_require_non_empty_string(
            mapping.get("mailbox_principal_id"),
            context=f"{context}.mailbox_principal_id",
        ),
        mailbox_address=_require_non_empty_string(
            mapping.get("mailbox_address"), context=f"{context}.mailbox_address"
        ),
    )


def _message_from_payload(payload: Any) -> MessageConfig:
    """Parse one message block."""

    mapping = _require_mapping(payload, context="message")
    return MessageConfig(
        subject=_require_non_empty_string(mapping.get("subject"), context="message.subject"),
        initial_body_file=_require_non_empty_string(
            mapping.get("initial_body_file"), context="message.initial_body_file"
        ),
        reply_body_file=_require_non_empty_string(
            mapping.get("reply_body_file"), context="message.reply_body_file"
        ),
    )


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load and validate the tracked tutorial parameters."""

    payload = _require_mapping(_read_json(path), context=str(path))
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise ValueError("demo parameters must use schema_version=1")

    parameters = DemoParameters(
        schema_version=int(schema_version),
        demo_id=_require_non_empty_string(payload.get("demo_id"), context="demo_id"),
        agent_def_dir=_require_non_empty_string(payload.get("agent_def_dir"), context="agent_def_dir"),
        backend=_require_non_empty_string(payload.get("backend"), context="backend"),
        cao_base_url=_require_non_empty_string(payload.get("cao_base_url"), context="cao_base_url"),
        shared_mailbox_root_template=_require_non_empty_string(
            payload.get("shared_mailbox_root_template"),
            context="shared_mailbox_root_template",
        ),
        sender=_participant_from_payload(payload.get("sender"), context="sender"),
        receiver=_participant_from_payload(payload.get("receiver"), context="receiver"),
        message=_message_from_payload(payload.get("message")),
    )
    if parameters.backend != "cao_rest":
        raise ValueError("demo parameters backend must be cao_rest")
    if "{demo_output_dir}" not in parameters.shared_mailbox_root_template and (
        "{workspace_dir}" not in parameters.shared_mailbox_root_template
    ):
        raise ValueError(
            "shared_mailbox_root_template must contain {demo_output_dir} or {workspace_dir}"
        )
    return parameters


def parameters_to_payload(parameters: DemoParameters) -> dict[str, Any]:
    """Convert parameters into one JSON-serializable payload."""

    return asdict(parameters)


def resolve_repo_relative_path(
    raw_path: str | None,
    *,
    repo_root: Path,
    default_relative: str | Path | None = None,
) -> Path:
    """Resolve one optional path relative to the repository root."""

    if raw_path is None or not raw_path.strip():
        if default_relative is None:
            raise ValueError("path is required when no default_relative is provided")
        candidate = Path(default_relative)
    else:
        candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root.resolve() / candidate).resolve()


def build_demo_layout(*, demo_output_dir: Path) -> DemoLayout:
    """Build the demo-owned output layout for one run."""

    resolved_output_dir = demo_output_dir.resolve()
    return DemoLayout(
        demo_output_dir=resolved_output_dir,
        project_workdir=resolved_output_dir / "project",
        runtime_root=resolved_output_dir / "runtime",
        inputs_dir=resolved_output_dir / "inputs",
        mailbox_root=resolved_output_dir / "shared-mailbox",
        report_path=resolved_output_dir / "report.json",
        sanitized_report_path=resolved_output_dir / "report.sanitized.json",
    )


def render_mailbox_root(parameters: DemoParameters, *, demo_output_dir: Path) -> Path:
    """Render the shared mailbox root from the demo-output-dir template."""

    rendered = parameters.shared_mailbox_root_template.replace(
        "{demo_output_dir}", str(demo_output_dir.resolve())
    ).replace("{workspace_dir}", str(demo_output_dir.resolve()))
    return Path(rendered).expanduser().resolve()


def extract_json_value(path: Path, dotted_path: str) -> Any:
    """Extract one dotted-path value from a JSON document."""

    value: Any = _read_json(path)
    for segment in dotted_path.split("."):
        if isinstance(value, dict) and segment in value:
            value = value[segment]
            continue
        raise ValueError(f"{path}: missing field `{dotted_path}`")
    return value


def extract_message_id(path: Path) -> str:
    """Extract one non-empty message_id from a mail-send payload."""

    payload = _require_mapping(_read_json(path), context=str(path))
    return _require_non_empty_string(payload.get("message_id"), context="message_id")


def _artifact_paths(demo_output_dir: Path) -> dict[str, Path]:
    """Return the expected demo-output-dir-local artifact paths."""

    return {
        label: demo_output_dir / filename for label, filename in _ARTIFACT_FILENAMES.items()
    }


def _load_artifacts(demo_output_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all required JSON artifacts from the demo output directory."""

    artifacts: dict[str, dict[str, Any]] = {}
    for label, path in _artifact_paths(demo_output_dir).items():
        artifacts[label] = _require_mapping(_read_json(path), context=str(path))
    return artifacts


def _default_git_runner(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one git command for demo worktree management."""

    return subprocess.run(
        args,
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )


def _resolved_git_reported_path(raw_path: str, *, cwd: Path) -> Path:
    """Resolve one git-reported path relative to the command cwd when needed."""

    candidate = Path(raw_path.strip())
    if candidate.is_absolute():
        return candidate.resolve()
    return (cwd.resolve() / candidate).resolve()


def _git_output(
    *,
    args: list[str],
    cwd: Path,
    run_git: GitRunner,
) -> str | None:
    """Run one git command and return stripped stdout on success."""

    result = run_git(args, cwd)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_repo_project_worktree(
    *,
    repo_root: Path,
    project_workdir: Path,
    run_git: GitRunner = _default_git_runner,
) -> bool:
    """Return whether the path is a git worktree attached to the main repository."""

    if not project_workdir.exists():
        return False

    inside = _git_output(
        args=["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_workdir,
        run_git=run_git,
    )
    if inside != "true":
        return False

    project_top = _git_output(
        args=["git", "rev-parse", "--show-toplevel"],
        cwd=project_workdir,
        run_git=run_git,
    )
    repo_common = _git_output(
        args=["git", "rev-parse", "--git-common-dir"],
        cwd=repo_root,
        run_git=run_git,
    )
    project_common = _git_output(
        args=["git", "rev-parse", "--git-common-dir"],
        cwd=project_workdir,
        run_git=run_git,
    )
    if project_top is None or repo_common is None or project_common is None:
        return False

    return (
        _resolved_git_reported_path(project_top, cwd=project_workdir) == project_workdir.resolve()
        and _resolved_git_reported_path(project_common, cwd=project_workdir)
        == _resolved_git_reported_path(repo_common, cwd=repo_root)
    )


def ensure_project_worktree(
    *,
    repo_root: Path,
    project_workdir: Path,
    run_git: GitRunner = _default_git_runner,
) -> Path:
    """Ensure the demo project workdir exists as a git worktree of the repository."""

    resolved_repo_root = repo_root.resolve()
    resolved_project_workdir = project_workdir.resolve()

    if is_repo_project_worktree(
        repo_root=resolved_repo_root,
        project_workdir=resolved_project_workdir,
        run_git=run_git,
    ):
        return resolved_project_workdir

    if resolved_project_workdir.exists():
        raise ValueError(
            "demo project directory exists but is not a git worktree of the repository: "
            f"{resolved_project_workdir}"
        )

    resolved_project_workdir.parent.mkdir(parents=True, exist_ok=True)
    result = run_git(
        ["git", "worktree", "add", "--detach", str(resolved_project_workdir), "HEAD"],
        resolved_repo_root,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git worktree add failed"
        raise RuntimeError(f"failed to provision demo project worktree: {detail}")

    if not is_repo_project_worktree(
        repo_root=resolved_repo_root,
        project_workdir=resolved_project_workdir,
        run_git=run_git,
    ):
        raise RuntimeError(
            "git worktree provisioning finished but the resulting project directory did not "
            f"validate as a repository worktree: {resolved_project_workdir}"
        )
    return resolved_project_workdir


def build_report(
    *,
    output_path: Path,
    parameters_path: Path,
    demo_output_dir: Path,
    project_workdir: Path,
    runtime_root: Path,
    mailbox_root: Path,
    agent_def_dir: Path,
    reply_parent_message_id: str,
) -> dict[str, Any]:
    """Build one raw tutorial report from captured command artifacts."""

    parameters = load_demo_parameters(parameters_path)
    artifacts = _load_artifacts(demo_output_dir)
    send_message_id = extract_message_id(demo_output_dir / _ARTIFACT_FILENAMES["mail_send"])
    sender_start = artifacts["sender_start"]
    receiver_start = artifacts["receiver_start"]
    sender_mailbox = _require_mapping(sender_start.get("mailbox"), context="sender_start.mailbox")
    receiver_mailbox = _require_mapping(
        receiver_start.get("mailbox"), context="receiver_start.mailbox"
    )

    report = {
        "demo": parameters.demo_id,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "demo_output_dir": str(demo_output_dir.resolve()),
        "project_workdir": str(project_workdir.resolve()),
        "runtime_root": str(runtime_root.resolve()),
        "mailbox_root": str(mailbox_root.resolve()),
        "agent_def_dir": str(agent_def_dir.resolve()),
        "parameters": parameters_to_payload(parameters),
        "artifacts": {
            label: str(path.resolve()) for label, path in _artifact_paths(demo_output_dir).items()
        },
        "flow": list(_FLOW),
        "reply_parent_message_id": reply_parent_message_id,
        "steps": artifacts,
        "checks": {
            "sender_build_manifest_present": bool(artifacts["sender_build"].get("manifest_path")),
            "receiver_build_manifest_present": bool(
                artifacts["receiver_build"].get("manifest_path")
            ),
            "sender_start_mailbox_enabled": sender_mailbox.get("transport") == "filesystem",
            "receiver_start_mailbox_enabled": receiver_mailbox.get("transport") == "filesystem",
            "shared_mailbox_root": sender_mailbox.get("filesystem_root")
            == receiver_mailbox.get("filesystem_root")
            == str(mailbox_root.resolve()),
            "send_message_id_present": bool(send_message_id),
            "reply_parent_matches_send_message_id": reply_parent_message_id == send_message_id,
            "sender_stop_ok": artifacts["sender_stop"].get("status") == "ok",
            "receiver_stop_ok": artifacts["receiver_stop"].get("status") == "ok",
        },
    }
    _write_json(output_path, report)
    return report


def _sanitize_string(value: str, *, key: str | None, parent_key: str | None) -> str:
    """Sanitize one string value using field-aware placeholders."""

    if key in _VALUE_PLACEHOLDERS:
        return _VALUE_PLACEHOLDERS[key]
    if key in _PATH_PLACEHOLDERS:
        return _PATH_PLACEHOLDERS[key]
    if parent_key == "artifacts" and key is not None:
        return f"<ARTIFACT_PATH:{key}>"
    if key in _TIMESTAMP_KEYS or _TIMESTAMP_PATTERN.match(value):
        return "<TIMESTAMP>"
    if _ABSOLUTE_PATH_PATTERN.match(value):
        return "<ABSOLUTE_PATH>"
    return value


def sanitize_report(payload: Any, *, key: str | None = None, parent_key: str | None = None) -> Any:
    """Recursively sanitize one raw tutorial report payload."""

    if isinstance(payload, dict):
        return {
            child_key: sanitize_report(child_value, key=child_key, parent_key=key)
            for child_key, child_value in payload.items()
        }
    if isinstance(payload, list):
        return [sanitize_report(item, key=None, parent_key=key) for item in payload]
    if isinstance(payload, str):
        return _sanitize_string(payload, key=key, parent_key=parent_key)
    return payload


def verify_sanitized_report(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Validate that sanitized actual output matches the expected contract."""

    if actual != expected:
        raise ValueError(
            "sanitized report mismatch\n"
            f"expected:\n{json.dumps(expected, indent=2, sort_keys=True)}\n"
            f"actual:\n{json.dumps(actual, indent=2, sort_keys=True)}"
        )


def _cmd_validate_parameters(args: argparse.Namespace) -> int:
    """Validate the tracked parameter file."""

    load_demo_parameters(args.parameters)
    print("parameters valid")
    return 0


def _cmd_json_value(args: argparse.Namespace) -> int:
    """Print one JSON field value."""

    value = extract_json_value(args.json_path, args.dotted_path)
    if isinstance(value, (dict, list)):
        print(json.dumps(value, separators=(",", ":"), sort_keys=True))
    else:
        print(value)
    return 0


def _cmd_render_mailbox_root(args: argparse.Namespace) -> int:
    """Render the demo-local mailbox root path."""

    parameters = load_demo_parameters(args.parameters)
    print(render_mailbox_root(parameters, demo_output_dir=args.demo_output_dir))
    return 0


def _cmd_resolve_path(args: argparse.Namespace) -> int:
    """Resolve one optional path from the repository root."""

    default_relative = args.default_relative if args.default_relative is not None else None
    print(
        resolve_repo_relative_path(
            args.raw_path,
            repo_root=args.repo_root,
            default_relative=default_relative,
        )
    )
    return 0


def _cmd_ensure_project_worktree(args: argparse.Namespace) -> int:
    """Provision or validate the demo project worktree."""

    print(ensure_project_worktree(repo_root=args.repo_root, project_workdir=args.project_workdir))
    return 0


def _cmd_message_id(args: argparse.Namespace) -> int:
    """Print one validated message_id."""

    print(extract_message_id(args.payload))
    return 0


def _cmd_build_report(args: argparse.Namespace) -> int:
    """Build one raw report from workspace artifacts."""

    build_report(
        output_path=args.output,
        parameters_path=args.parameters,
        demo_output_dir=args.demo_output_dir,
        project_workdir=args.project_workdir,
        runtime_root=args.runtime_root,
        mailbox_root=args.mailbox_root,
        agent_def_dir=args.agent_def_dir,
        reply_parent_message_id=args.reply_parent_message_id,
    )
    print(args.output)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the helper CLI parser."""

    parser = argparse.ArgumentParser(description="Mailbox roundtrip tutorial helper utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-parameters")
    validate_parser.add_argument("parameters", type=Path)
    validate_parser.set_defaults(func=_cmd_validate_parameters)

    json_value_parser = subparsers.add_parser("json-value")
    json_value_parser.add_argument("json_path", type=Path)
    json_value_parser.add_argument("dotted_path")
    json_value_parser.set_defaults(func=_cmd_json_value)

    resolve_path_parser = subparsers.add_parser("resolve-path")
    resolve_path_parser.add_argument("--repo-root", type=Path, required=True)
    resolve_path_parser.add_argument("--default-relative")
    resolve_path_parser.add_argument("raw_path", nargs="?")
    resolve_path_parser.set_defaults(func=_cmd_resolve_path)

    mailbox_root_parser = subparsers.add_parser("render-mailbox-root")
    mailbox_root_parser.add_argument("parameters", type=Path)
    mailbox_root_parser.add_argument("demo_output_dir", type=Path)
    mailbox_root_parser.set_defaults(func=_cmd_render_mailbox_root)

    worktree_parser = subparsers.add_parser("ensure-project-worktree")
    worktree_parser.add_argument("--repo-root", type=Path, required=True)
    worktree_parser.add_argument("--project-workdir", type=Path, required=True)
    worktree_parser.set_defaults(func=_cmd_ensure_project_worktree)

    message_id_parser = subparsers.add_parser("message-id")
    message_id_parser.add_argument("payload", type=Path)
    message_id_parser.set_defaults(func=_cmd_message_id)

    build_report_parser = subparsers.add_parser("build-report")
    build_report_parser.add_argument("--output", type=Path, required=True)
    build_report_parser.add_argument("--parameters", type=Path, required=True)
    build_report_parser.add_argument("--demo-output-dir", type=Path, required=True)
    build_report_parser.add_argument("--project-workdir", type=Path, required=True)
    build_report_parser.add_argument("--runtime-root", type=Path, required=True)
    build_report_parser.add_argument("--mailbox-root", type=Path, required=True)
    build_report_parser.add_argument("--agent-def-dir", type=Path, required=True)
    build_report_parser.add_argument("--reply-parent-message-id", required=True)
    build_report_parser.set_defaults(func=_cmd_build_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the helper CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
