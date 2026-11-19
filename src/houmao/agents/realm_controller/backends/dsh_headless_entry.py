"""Prepare and exec one native DSH CLI worker under the owned bridge."""

from __future__ import annotations

import argparse
import fcntl
from importlib.resources import files
import json
import os
from pathlib import Path
import sys
from typing import Any, NoReturn

from houmao.agents.dsh_configuration import (
    DshConfigurationError,
    DshEffectiveToolParams,
    load_dsh_home,
    read_dsh_mcp_environment,
)
from houmao.agents.realm_controller.backends.dispatch_control import (
    _dispatch_origin_birth_token,
    headless_dispatch_permission_allowed,
)
from houmao.agents.realm_controller.backends.dsh_acp_driver import _write_private_json
from houmao.agents.realm_controller.owner_admission import OwnerPromptClaim
from houmao.agents.realm_controller.usage_support import write_usage_json


def _check_permission(guard: Path, manifest_path: Path, generation: str, attempt: str) -> bool:
    """Require a still-current owner reservation at the actual native input boundary."""

    try:
        payload = json.loads(guard.read_text(encoding="utf-8"))
        return (
            isinstance(payload, dict)
            and payload.get("manifest_path") == str(manifest_path)
            and payload.get("registry_generation_id") == generation
            and payload.get("attempt_id") == attempt
            and headless_dispatch_permission_allowed(guard)
            and OwnerPromptClaim(manifest_path, generation, attempt, "headless").active()
        )
    except (OSError, ValueError, RuntimeError):
        return False


def _exec_native(input_path: Path) -> NoReturn:
    """Replace the bridge's child with the qualified native command, preserving its PID."""

    private: dict[str, Any] = json.loads(input_path.read_text(encoding="utf-8"))
    input_path.unlink()
    home = Path(private["home_path"])
    turn_dir = input_path.parent
    guard = turn_dir / ".dispatch-permission.json"
    manifest = Path(private["manifest_path"])
    generation = private["generation"]
    attempt = turn_dir.name
    if not _check_permission(guard, manifest, generation, attempt):
        raise DshConfigurationError("DSH headless prompt has no current dispatch permission")
    lock = os.open(home / "houmao-invocation.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DshConfigurationError("DSH already owns an active native attempt") from None

        params = DshEffectiveToolParams.from_file(Path(private["setup_path"]))
        prepared = load_dsh_home(
            home,
            params,
            os.environ,
            credential_environment=read_dsh_mcp_environment(
                params, private.get("credential_env_source")
            ),
            selected_model=private.get("model"),
            reasoning_level=private.get("reasoning_level"),
            native_profile="headless",
        )
        pid = os.getpid()
        birth = _dispatch_origin_birth_token(pid)
        if birth is None or os.getsid(pid) != pid:
            raise DshConfigurationError("DSH requires an isolated, verified worker process")
        binding = {
            "version": 1,
            "attempt_id": attempt,
            "runtime_session_id": private["runtime_session_id"],
            "generation": generation,
            "working_directory": private["working_directory"],
            "process_id": pid,
            "process_birth_token": birth,
            "evidence_path": str(turn_dir / "dsh-native-evidence.jsonl"),
            "persistence_root": str(prepared.persistence_root),
            "source_revision": "39163dd30f703a79079e2d2446545cff3c453738",
        }
        write_usage_json(home / "houmao-native-attempt.json", binding)
        control = turn_dir / "dsh-control.json"
        _write_private_json(
            control,
            {
                **binding,
                "expected_native_session_id": private["session_id"],
                "abandoned_message_ids": [],
                "one_shot": {
                    "manifest_path": str(manifest),
                    "guard_path": str(guard),
                    "python_executable": sys.executable,
                    "session_path": str(home / "houmao-native-session.json"),
                },
            },
        )
        companion = files("houmao.agents").joinpath("assets/dsh/managed-companion.mjs")
        patch = turn_dir / "dsh-companion.patch.json"
        descriptor = os.open(patch, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                [
                    *prepared.invocation_patch,
                    {
                        "insert": [
                            {
                                "id": "houmao-managed",
                                "name": str(companion),
                                "config": {
                                    "controlFile": str(control),
                                    "roleFile": str(prepared.role_path),
                                },
                            }
                        ]
                    },
                ],
                stream,
            )
        cli = [
            private["executable"],
            "--profile",
            "headless",
            "--patch",
            str(prepared.patch_path),
            "--patch",
            str(patch),
            "--json",
        ]
        if private["session_id"] is not None:
            cli.extend(["--session-id", private["session_id"]])
        if prepared.permission_preset is not None:
            cli.extend(["--permission-mode", prepared.permission_preset])

        task_path = turn_dir / ".dsh-task"
        descriptor = os.open(task_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            task_path.unlink()
            with os.fdopen(os.dup(descriptor), "wb") as stream:
                stream.write(private["prompt"].encode("utf-8"))
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.dup2(descriptor, 0)
        finally:
            os.close(descriptor)
        os.set_inheritable(lock, True)
        os.execvpe(cli[0], cli, prepared.environment)
    finally:
        os.close(lock)


def main() -> int:
    """Run the native worker or verify a companion's one-shot attempt permission."""

    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--input", type=Path)
    action.add_argument("--verify-dispatch", nargs=4)
    args = parser.parse_args()
    if args.verify_dispatch is not None:
        guard, manifest, generation, attempt = args.verify_dispatch
        return 0 if _check_permission(Path(guard), Path(manifest), generation, attempt) else 125
    try:
        _exec_native(args.input)
    except (OSError, TypeError, ValueError, DshConfigurationError) as exc:
        detail = (
            str(exc) if isinstance(exc, DshConfigurationError) else "Invalid native worker setup"
        )
        print(f"DSH headless: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
