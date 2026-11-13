"""Read prepared fixture data and invoke credential commands without secret OS arguments."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import shutil
from pathlib import Path
import threading
from typing import Any, Literal, Mapping, Sequence

FixtureTool = Literal["claude", "codex", "kimi"]
_COMMAND_LOCK = threading.RLock()


def managed_subprocess_command(command: Sequence[str], *, cwd: Path) -> list[str]:
    """Reuse the parent's managed CLI without changing an external child's cwd."""

    del cwd
    result = list(command)
    if result[:3] == ["pixi", "run", "houmao-mgr"]:
        executable = shutil.which("houmao-mgr") or "houmao-mgr"
        return [executable, *result[3:]]
    return result


def prepared_root_from_auth(*, auth_dir: Path, repo_root: Path, tool: FixtureTool) -> Path | None:
    """Recognize explicitly selected run-owned auth without searching personal homes."""

    source = auth_dir.resolve()
    if len(source.parents) < 5:
        return None
    root = source.parents[4]
    if not (root / "run.json").is_file():
        return None
    metadata = read_prepared_run(prepared_run=root, repo_root=repo_root, tool=tool)
    expected = Path(str(metadata["assets_root"])) / "tools" / tool / "auth/default"
    if source != expected.resolve():
        raise RuntimeError("Selected credentials do not belong to the prepared fixture")
    return root


def invoke_private_credential_command(
    *,
    args: list[str],
    project: Path,
    env: Mapping[str, str],
    stdout_path: Path,
    stderr_path: Path,
    extra_env_values: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Execute the existing credential CLI in-process and persist redacted diagnostics."""

    from houmao.srv_ctrl.commands.main import main

    argv = list(args)
    output, errors = io.StringIO(), io.StringIO()
    with _COMMAND_LOCK:
        original = dict(os.environ)
        original_cwd = Path.cwd()
        mask = os.umask(0o077)
        try:
            os.chdir(project)
            os.environ.clear()
            os.environ.update(env)
            with redirect_stdout(output), redirect_stderr(errors):
                code = main(argv)
                if code == 0 and extra_env_values:
                    from houmao.srv_ctrl.commands.credentials import (
                        _resolve_agent_def_dir_target,
                        _write_credential_bundle,
                    )

                    overlay = Path(env.get("HOUMAO_PROJECT_OVERLAY_DIR", str(project / ".houmao")))
                    _write_credential_bundle(
                        target=_resolve_agent_def_dir_target(overlay / "agents"),
                        tool=args[args.index("credentials") + 1],
                        name=args[args.index("--name") + 1],
                        env_values=dict(extra_env_values),
                        file_sources={},
                        require_any_input=True,
                        operation="set",
                        clear_env_names=set(),
                        clear_file_sources=set(),
                    )
        finally:
            os.chdir(original_cwd)
            os.environ.clear()
            os.environ.update(original)
            os.umask(mask)
    secrets = [
        args[i + 1]
        for i, arg in enumerate(args[:-1])
        if arg in {"--api-key", "--auth-token", "--oauth-token"}
    ]
    texts = [output.getvalue(), errors.getvalue()]
    for secret in secrets:
        if secret:
            texts = [text.replace(secret, "[REDACTED]") for text in texts]
    for path, text in zip((stdout_path, stderr_path), texts, strict=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        path.chmod(0o600)
    if code != 0:
        raise RuntimeError(
            "Selected credential import failed; inspect private redacted diagnostics"
        )
    result = json.loads(texts[0])
    if not isinstance(result, dict):
        raise RuntimeError("Selected credential import returned unexpected output")
    return result


def read_prepared_run(
    *, prepared_run: Path, repo_root: Path, tool: FixtureTool
) -> dict[str, object]:
    """Validate explicit external fixture inputs without importing utility code."""

    root = prepared_run.expanduser().resolve()
    if root.is_relative_to(repo_root.resolve()):
        raise RuntimeError("Prepared credentials must be outside the checkout")
    try:
        payload = json.loads((root / "run.json").read_text())
    except (OSError, ValueError) as exc:
        raise RuntimeError("Cannot read selected --prepared-run metadata") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("Unsupported prepared-run schema")
    config = payload.get("configuration")
    if not isinstance(config, dict) or config.get("client") != tool:
        raise RuntimeError("Prepared run belongs to another tool")
    if payload.get("run_dir") != str(root):
        raise RuntimeError("Prepared run identity does not match its directory")
    assets = Path(str(payload.get("assets_root", ""))).resolve()
    if not assets.is_relative_to(root) or not assets.is_dir():
        raise RuntimeError("Prepared assets must stay inside their private run")
    return payload


def prepared_runtime_env(
    *, prepared_run: Path, repo_root: Path, tool: FixtureTool
) -> dict[str, str]:
    """Read only non-secret runtime settings for the demo's existing builder."""

    read_prepared_run(prepared_run=prepared_run, repo_root=repo_root, tool=tool)
    try:
        values = json.loads((prepared_run / "private-env.json").read_text())
    except (OSError, ValueError) as exc:
        raise RuntimeError("Cannot read prepared runtime settings") from exc
    allowlist = {
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS",
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
        "CLAUDE_CODE_EFFORT_LEVEL",
        "API_TIMEOUT_MS",
        "KIMI_CODE_TRUST_WORKSPACE",
        "KIMI_CODE_LEGACY_FLAG",
    }
    return {key: str(value) for key, value in values.items() if key in allowlist}


def private_demo_root(*, path: Path, repo_root: Path) -> Path:
    """Reject checkout-local live state and make its ancestor private."""

    result = path.expanduser().resolve()
    if result.is_relative_to(repo_root.resolve()):
        raise RuntimeError("Live output root must be outside the checkout")
    result.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return result
