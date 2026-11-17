"""Render isolated homes and prepare projects through maintained Houmao commands."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import threading
from typing import Any

import tomli_w
import yaml

from fixturelib.auth import (
    allocate_run,
    private_directory,
    private_write,
    validate_external_path,
    write_json,
)
from fixturelib.config import FixtureError, HOME_VARIABLE, REPO_ROOT, ResolvedConfig, read_env_file

_COMMAND_LOCK = threading.RLock()
_PROVIDER_PREFIXES = (
    "ANTHROPIC_",
    "CLAUDE_CODE_",
    "OPENAI_",
    "KIMI_",
    "DEEPSEEK_",
    "QWEN_",
    "DSH_",
)
_CLEAR_BINDINGS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_ORG_ID",
    "KIMI_MODEL_NAME",
    "KIMI_MODEL_API_KEY",
    "KIMI_MODEL_BASE_URL",
    "KIMI_MODEL_PROVIDER_TYPE",
    "KIMI_CODE_BASE_URL",
    "KIMI_CODE_OAUTH_HOST",
    "KIMI_OAUTH_HOST",
)


def isolated_environment(
    selected: Mapping[str, str],
    *,
    run_dir: Path,
    process_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a selected-provider environment, including tmux-clearing empty bindings."""

    original = os.environ if process_env is None else process_env
    result = {
        key: value
        for key, value in original.items()
        if not key.startswith((*_PROVIDER_PREFIXES, "HOUMAO_")) and key not in {"TMUX", "TMUX_PANE"}
    }
    result.update(dict.fromkeys(_CLEAR_BINDINGS, ""))
    result.update(
        {
            "HOUMAO_GLOBAL_REGISTRY_DIR": str(run_dir / "registry"),
            "HOUMAO_GLOBAL_RUNTIME_DIR": str(run_dir / "runtime"),
            "HOUMAO_PROJECT_OVERLAY_DIR": str(run_dir / "workdir/.houmao"),
            "HOUMAO_CLI_PRINT_STYLE": "json",
        }
    )
    result.update(selected)
    tmux_shim = run_dir / "bin/tmux"
    if tmux_shim.is_file():
        result["PATH"] = str(tmux_shim.parent) + os.pathsep + result.get("PATH", os.defpath)
    return result


def _prepare_tmux_isolation(run_dir: Path) -> dict[str, str]:
    """Force all fixture/runtime tmux subprocesses onto this run's private server."""

    executable = shutil.which("tmux")
    if executable is None:
        return {}
    server = "houmao-fixture-" + run_dir.name
    shim = run_dir / "bin/tmux"
    private_write(
        shim,
        (
            "#!/bin/sh\nunset TMUX TMUX_PANE\nexec "
            + shlex.quote(str(Path(executable).resolve()))
            + " -L "
            + shlex.quote(server)
            + ' "$@"\n'
        ).encode(),
    )
    shim.chmod(0o700)
    return {"tmux_server": server, "tmux_executable": str(Path(executable).resolve())}


@contextmanager
def command_environment(env: Mapping[str, str]) -> Iterator[None]:
    """Serialize temporary process env changes around in-process CLI operations."""

    with _COMMAND_LOCK:
        original = dict(os.environ)
        original_umask = os.umask(0o077)
        try:
            os.environ.clear()
            os.environ.update(env)
            yield
        finally:
            os.environ.clear()
            os.environ.update(original)
            os.umask(original_umask)


def manager_call(project: Path, args: list[str], *, env: Mapping[str, str]) -> dict[str, Any]:
    """Invoke maintained commands in-process, keeping key values out of OS arguments."""

    return manager_root_call(["project", "--project-dir", str(project), *args], env=env)


def manager_root_call(args: list[str], *, env: Mapping[str, str]) -> dict[str, Any]:
    """Invoke current commands without exposing secret-bearing arguments to a process."""

    from houmao.srv_ctrl.commands.main import main

    output, errors = io.StringIO(), io.StringIO()
    with command_environment(env), redirect_stdout(output), redirect_stderr(errors):
        code = main(["--print-json", *args])
    payload: dict[str, Any] = {}
    decoder = json.JSONDecoder()
    remaining = output.getvalue().strip()
    try:
        while remaining:
            item, end = decoder.raw_decode(remaining)
            if not isinstance(item, dict):
                raise ValueError("Expected an object")
            payload.update(item)
            remaining = remaining[end:].strip()
    except ValueError as exc:
        raise FixtureError("Managed project command did not return structured output") from exc
    if code != 0:
        # Command errors can repeat input values. Report only the operation, never
        # captured raw diagnostics or the secret-bearing in-memory argv list.
        operation = "/".join(args[:2])
        diagnostic = errors.getvalue()
        for key, value in env.items():
            if value and any(marker in key for marker in ("KEY", "TOKEN", "SECRET")):
                diagnostic = diagnostic.replace(value, "[REDACTED]")
        runtime = env.get("HOUMAO_GLOBAL_RUNTIME_DIR")
        if runtime:
            diagnostic_root = Path(runtime).parent
            destination = diagnostic_root / "manager-error.txt"
            index = 1
            while destination.exists():
                destination = diagnostic_root / f"manager-error-{index}.txt"
                index += 1
            private_write(destination, diagnostic.encode())
        raise ManagedCommandError(f"Managed project operation failed: {operation}", payload)
    if not payload:
        raise FixtureError("Managed project command returned an empty result")
    return payload


class ManagedCommandError(FixtureError):
    """Retain emitted identity after a partially successful managed launch."""

    def __init__(self, message: str, payload: dict[str, Any]) -> None:
        super().__init__(message)
        self.m_payload: dict[str, Any] = payload

    @property
    def payload(self) -> dict[str, Any]:
        """Return command output for identity-scoped cleanup."""

        return self.m_payload


def credential_values(config: ResolvedConfig) -> dict[str, str]:
    """Map only selected API values into existing tool credential channels."""

    if config.auth_method == "native-login":
        if config.native_bundle is None:
            raise FixtureError("Native login preparation requires an imported bundle")
        return read_env_file(config.native_bundle / "env/vars.env")
    key = config.api_key.get_secret_value()
    assert config.model is not None and config.base_url is not None
    if config.client == "dsh":
        if config.dsh is None:
            raise FixtureError("DSH fixtures require an explicit adapter and protocol")
        if config.dsh.adapter == "deepseek":
            return {"DEEPSEEK_API_KEY": key, "DEEPSEEK_BASE_URL_ANTHROPIC": config.base_url}
        return {"OPENAI_API_KEY": key, "OPENAI_BASE_URL": config.base_url}
    if config.client == "codex":
        return {"OPENAI_API_KEY": key, "OPENAI_BASE_URL": config.base_url}
    if config.client == "claude":
        result = {"ANTHROPIC_AUTH_TOKEN": key, "ANTHROPIC_BASE_URL": config.base_url}
        result.update(
            {
                name: config.model
                for name in (
                    "ANTHROPIC_MODEL",
                    "ANTHROPIC_SMALL_FAST_MODEL",
                    "CLAUDE_CODE_SUBAGENT_MODEL",
                    "ANTHROPIC_DEFAULT_OPUS_MODEL",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL",
                    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                )
            }
        )
        return result
    options = config.model_options
    result = {
        "KIMI_MODEL_API_KEY": key,
        "KIMI_MODEL_BASE_URL": config.base_url,
        "KIMI_MODEL_PROVIDER_TYPE": "openai",
        "KIMI_MODEL_NAME": config.model,
        "KIMI_MODEL_MAX_CONTEXT_SIZE": str(options.context_window),
        "KIMI_MODEL_CAPABILITIES": ",".join(options.capabilities),
    }
    if options.reasoning_key:
        result["KIMI_MODEL_REASONING_KEY"] = options.reasoning_key
    if options.reasoning_effort:
        result["KIMI_MODEL_THINKING_EFFORT"] = options.reasoning_effort
    return result


def runtime_values(config: ResolvedConfig) -> dict[str, str]:
    """Return non-secret version-qualified launch settings separate from credentials."""

    result: dict[str, str] = {}
    if config.client == "claude" and config.auth_method == "api-key":
        result["CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"] = "1"
        result["API_TIMEOUT_MS"] = "300000"
        if config.model_options.context_window is not None:
            result["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] = str(config.model_options.context_window)
        if config.model_options.reasoning_effort:
            result["CLAUDE_CODE_EFFORT_LEVEL"] = config.model_options.reasoning_effort
    if config.client == "kimi":
        result["KIMI_CODE_TRUST_WORKSPACE"] = "1"
        result["KIMI_CODE_LEGACY_FLAG"] = "0"
    return result


def _copy_files(source: Path, destination: Path) -> None:
    """Copy only regular files from an explicitly selected private/secret-free tree."""

    for path in source.rglob("*"):
        if path.is_symlink():
            raise FixtureError("Selected input tree contains unsupported symlinked files")
        if path.is_file():
            private_write(destination / path.relative_to(source), path.read_bytes())


def _render_setup(config: ResolvedConfig, setup: Path, *, seed: Path) -> None:
    """Render selected provider routing without copying unrelated native configuration."""

    private_directory(setup)
    if config.client == "dsh":
        if config.auth_method != "api-key" or config.dsh is None:
            raise FixtureError("DSH fixtures require explicitly selected API credentials")
        from houmao.agents.dsh_configuration import DshSetup

        native = config.dsh.adapter == "deepseek"
        payload = {
            "version": 1,
            "provider": {
                "adapter": config.dsh.adapter,
                "protocol": "messages" if native else "openai-completions",
                "route": config.dsh.route,
                "base_url_env": "DEEPSEEK_BASE_URL_ANTHROPIC" if native else "OPENAI_BASE_URL",
                "api_key_env": "DEEPSEEK_API_KEY" if native else "OPENAI_API_KEY",
            },
            "models": [
                {
                    "id": config.model,
                    "context_window": config.model_options.context_window,
                    "max_output_tokens": config.model_options.max_output_tokens,
                    "reasoning": config.model_options.dsh_reasoning,
                }
            ],
            "selected_model": config.model,
            "hmr": False,
        }
        DshSetup.from_mapping(payload)
        private_write(setup / "dsh-setup.yaml", yaml.safe_dump(payload).encode())
        return
    if config.auth_method == "native-login":
        default = seed / "tools" / config.client / "setups/default"
        if default.exists():
            _copy_files(default, setup)
        return
    if config.client == "codex":
        payload: dict[str, Any] = {
            "model_provider": "api-compatible",
            "model": config.model,
            "model_providers": {
                "api-compatible": {
                    "name": "Selected compatible API",
                    "base_url": config.base_url,
                    "env_key": "OPENAI_API_KEY",
                    "requires_openai_auth": False,
                    "wire_api": "responses",
                }
            },
            "tui": {"show_tooltips": False},
        }
        if config.model_options.context_window is not None:
            payload["model_context_window"] = config.model_options.context_window
        if config.model_options.reasoning_effort:
            payload["model_reasoning_effort"] = config.model_options.reasoning_effort
        private_write(setup / "config.toml", tomli_w.dumps(payload).encode())


def _render_assets(
    config: ResolvedConfig,
    run_dir: Path,
    *,
    seed: Path,
    role: str,
    prompt_file: Path,
    executable: str,
) -> tuple[Path, dict[str, str]]:
    """Produce one isolated native input tree with run-owned credential copies."""

    root = run_dir / "assets"
    tool_root = root / "tools" / config.client
    adapter = yaml.safe_load((seed / "tools" / config.client / "adapter.yaml").read_text())
    adapter["launch"]["executable"] = executable
    private_write(tool_root / "adapter.yaml", yaml.safe_dump(adapter).encode())
    private_write(root / "roles" / role / "system-prompt.md", prompt_file.read_bytes())
    private_directory(root / "skills")
    _render_setup(config, tool_root / "setups/fixture", seed=seed)
    auth = tool_root / "auth/default"
    values = credential_values(config)
    if config.native_bundle is not None:
        _copy_files(config.native_bundle / "files", auth / "files")
    projected = dict.fromkeys(adapter["auth_projection"]["env"]["allowlist"], "")
    projected.update(values)
    private_write(
        auth / "env/vars.env",
        "".join(f"{key}={value}\n" for key, value in projected.items()).encode(),
    )
    private_directory(auth / "files")
    preset = {
        "role": role,
        "tool": config.client,
        "setup": "fixture",
        "auth": "default",
        "skills": [],
        "launch": {"prompt_mode": config.operator_prompt_mode},
    }
    private_write(
        root / "presets" / f"{role}-{config.client}-fixture.yaml", yaml.safe_dump(preset).encode()
    )
    return root, values


def _prepare_project(
    config: ResolvedConfig,
    run_dir: Path,
    assets: Path,
    values: dict[str, str],
    *,
    role: str,
    env: dict[str, str],
) -> dict[str, Any]:
    """Prepare the project through existing CLI and shared credential writer behavior."""

    project = run_dir / "workdir"
    if shutil.which("git") is None:
        raise FixtureError("Managed preparation requires git for its isolated project")
    subprocess.run(["git", "init", "--quiet", str(project)], check=True, capture_output=True)
    manager_call(project, ["init"], env=env)
    from houmao.project.overlay import (
        load_project_overlay,
        materialize_project_agent_catalog_projection,
    )

    with command_environment(env):
        materialize_project_agent_catalog_projection(
            load_project_overlay(project / ".houmao/houmao-config.toml")
        )
    tool = config.client
    private_write(
        project / ".houmao/agents/tools" / tool / "adapter.yaml",
        (assets / "tools" / tool / "adapter.yaml").read_bytes(),
    )
    setup_result = manager_root_call(
        [
            "internals",
            "native-agent",
            "tools",
            tool,
            "setups",
            "add",
            "--name",
            "fixture",
            "--native-agent-root",
            str(project / ".houmao/agents"),
        ],
        env=env,
    )
    _copy_files(assets / "tools" / tool / "setups/fixture", Path(setup_result["path"]))
    auth_files = assets / "tools" / tool / "auth/default/files"
    args = ["credentials", tool, "add", "--name", "default"]
    if config.auth_method == "native-login":
        if tool == "claude":
            args.extend(["--config-dir", str(auth_files)])
        elif tool == "codex":
            args.extend(["--auth-json", str(auth_files / "auth.json")])
        else:
            args.extend(["--code-home", str(auth_files)])
    elif tool == "claude":
        args.extend(
            ["--auth-token", values["ANTHROPIC_AUTH_TOKEN"], "--base-url", str(config.base_url)]
        )
    elif tool == "dsh":
        assert config.dsh is not None
        key_name = "DEEPSEEK_API_KEY" if config.dsh.adapter == "deepseek" else "OPENAI_API_KEY"
        args.extend(
            [
                "--adapter",
                config.dsh.adapter,
                "--api-key",
                values[key_name],
                "--base-url",
                str(config.base_url),
            ]
        )
    else:
        args.extend(
            [
                "--api-key",
                values["OPENAI_API_KEY" if tool == "codex" else "KIMI_MODEL_API_KEY"],
                "--base-url",
                str(config.base_url),
            ]
        )
        if tool == "kimi":
            args.extend(["--model-name", str(config.model), "--provider-type", "openai"])
    credential = manager_call(project, args, env=env)
    if values:
        # The same adapter-driven writer owns metadata env inputs not exposed as
        # dedicated CLI flags (notably Kimi context/capability fields).
        from houmao.srv_ctrl.commands.credentials import (
            _resolve_agent_def_dir_target,
            _write_credential_bundle,
        )

        with command_environment(env):
            _write_credential_bundle(
                target=_resolve_agent_def_dir_target(project / ".houmao/agents"),
                tool=tool,
                name="default",
                env_values=values,
                file_sources={},
                require_any_input=True,
                operation="set",
                clear_env_names=set(),
                clear_file_sources=set(),
            )
    args = [
        "specialist",
        "create",
        "--name",
        "fixture-agent",
        "--tool",
        tool,
        "--setup",
        "fixture",
        "--credential",
        "default",
        "--system-prompt-file",
        str(assets / "roles" / role / "system-prompt.md"),
        "--no-system-skills",
    ]
    if config.operator_prompt_mode == "as_is":
        args.append("--no-unattended")
    if config.model:
        args.extend(["--model", config.model])
    for key, value in runtime_values(config).items():
        args.extend(["--env-set", f"{key}={value}"])
    specialist = manager_call(project, args, env=env)
    return {"project_dir": str(project), "specialist": specialist, "credential": credential}


def prepare_run(
    config: ResolvedConfig,
    *,
    run_root: Path | None = None,
    seed_root: Path | None = None,
    role: str = "server-api-smoke",
    prompt_file: Path | None = None,
    executable: str | None = None,
) -> dict[str, Any]:
    """Prepare private native inputs and an optional managed project before launch."""

    if not role or Path(role).name != role or role in {".", ".."}:
        raise FixtureError("Role must be one directory identifier")
    if config.client == "dsh" and config.auth_method != "api-key":
        raise FixtureError("DSH fixtures require explicitly selected API credentials")
    seed = (seed_root or REPO_ROOT / "tests/fixtures/plain-agent-def").resolve()
    prompt = (prompt_file or seed / "roles" / role / "system-prompt.md").resolve()
    if not prompt.is_file():
        raise FixtureError("Selected role prompt file is missing")
    resolved_executable = shutil.which(executable or config.client)
    if resolved_executable is None:
        raise FixtureError(f"Client executable is unavailable: {config.client}")
    if config.native_bundle is not None:
        validate_external_path(config.native_bundle)
        if not (config.native_bundle / "import.json").is_file():
            raise FixtureError("Select an imported native bundle from the external local store")
        try:
            imported = json.loads((config.native_bundle / "import.json").read_text())
        except (OSError, ValueError) as exc:
            raise FixtureError("Cannot read native bundle identity") from exc
        if imported.get("client") != config.client or imported.get("schema_version") != 1:
            raise FixtureError("Imported native bundle belongs to another client or schema")
        primary = {
            "claude": ".credentials.json",
            "codex": "auth.json",
            "kimi": "credentials/kimi-code.json",
        }[config.client]
        if not (config.native_bundle / "files" / primary).is_file():
            raise FixtureError("Imported native bundle is missing its supported auth file")
    run_dir = allocate_run(config, run_root=run_root)
    project = run_dir / "workdir"
    private_directory(project)
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "status": "preparing",
        "run_dir": str(run_dir),
        "configuration": config.summary(),
        "role": role,
        "executable": str(Path(resolved_executable).resolve()),
        "workdir": str(project),
        "assets_root": str(run_dir / "assets"),
        "home_path": str(run_dir / "home"),
    }
    if config.surface != "raw" or config.mode == "tui":
        metadata.update(_prepare_tmux_isolation(run_dir))
    write_json(run_dir / "run.json", metadata)
    try:
        assets, values = _render_assets(
            config,
            run_dir,
            seed=seed,
            role=role,
            prompt_file=prompt,
            executable=resolved_executable,
        )
        home = run_dir / "home"
        private_directory(home)
        if config.client == "dsh":
            private_directory(home / "skills")
        _copy_files(assets / "tools" / config.client / "setups/fixture", home)
        _copy_files(assets / "tools" / config.client / "auth/default/files", home)
        if config.client == "codex":
            private_write(
                home / ".env", "".join(f"{key}={value}\n" for key, value in values.items()).encode()
            )
        selected_env = {**values, **runtime_values(config), HOME_VARIABLE[config.client]: str(home)}
        write_json(run_dir / "private-env.json", selected_env)
        env = isolated_environment(selected_env, run_dir=run_dir)
        if config.client == "dsh" and config.surface == "raw" and config.mode == "headless":
            from houmao.agents.dsh_configuration import DshSetup, prepare_dsh_home

            prepare_dsh_home(
                home,
                DshSetup.from_file(home / "dsh-setup.yaml"),
                env,
                (assets / "roles" / role / "system-prompt.md").read_text(),
                selected_model=config.model,
                skill_roots=(home / "skills",),
                operator_prompt_mode=config.operator_prompt_mode,
            )
        if config.surface != "raw":
            metadata.update(_prepare_project(config, run_dir, assets, values, role=role, env=env))
        metadata["status"] = "prepared"
        write_json(run_dir / "run.json", metadata)
    except BaseException:
        metadata["status"] = "preparation_failed"
        write_json(run_dir / "run.json", metadata)
        raise
    return metadata


def load_run(path: Path) -> dict[str, Any]:
    """Read a prepared external run while rejecting foreign path references."""

    root = validate_external_path(path)
    try:
        result = json.loads((root / "run.json").read_text())
    except (OSError, ValueError) as exc:
        raise FixtureError("Cannot read prepared run metadata") from exc
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != 1
        or result.get("run_dir") != str(root)
    ):
        raise FixtureError("Invalid prepared run identity or schema")
    for key in ("workdir", "assets_root", "home_path", "project_dir"):
        value = result.get(key)
        if value is not None and not Path(value).resolve().is_relative_to(root):
            raise FixtureError("Prepared run references state outside its private root")
    return result
