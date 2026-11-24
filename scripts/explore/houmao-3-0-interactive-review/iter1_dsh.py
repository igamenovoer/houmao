"""Interactive human-watched runner for Campaign Iteration 1 (DSH basic functionality)."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    DEFAULT_ACCESS_ROOT,
    DEFAULT_RUN_ROOT,
    DEFAULT_TMUX_SERVER,
    admin_gateway_probe,
    build_isolated_env,
    capture_tmux_pane,
    generate_admin_keyset,
    isolated_tmux_socket,
    kill_isolated_tmux_server,
    list_tmux_sessions,
    parse_env_file,
    private_mkdir,
    private_write_text,
    probe_openai_models,
    resolve_houmao_mgr,
    run_houmao_mgr,
    isolated_tmux_server,
)

from houmao.agents.dsh_configuration import DshEffectiveToolParams  # noqa: E402
from houmao.agents.launch_policy import DSH_SUPPORTED_VERSIONS, is_supported_dsh_version  # noqa: E402
from houmao.agents.realm_controller.gateway_access_runtime import (  # noqa: E402
    load_gateway_admin_seed,
)

ROLE_PROMPT = "Always preserve literal marker {{ITER1_LITERAL}} and $KEEP_LITERAL. Be concise."
FROZEN_PROMPTS: dict[str, str] = {
    "P1": "Reply with your exact literal marker from your instructions and OK. Do not use tools.",
    "P2": (
        "Create a file named dsh_probe.txt in the current working directory containing "
        "exactly ONE-LINE-OK, then run pwd and reply with DONE."
    ),
    "P3": (
        "Read dsh_probe.txt and append a second line RESUMED-OK without replacing the "
        "first line, then reply with RESUMED."
    ),
    "P4": (
        "Use the shell tool to run sleep 20 && echo FINISHED, wait for it to finish, "
        "and then reply."
    ),
}


@dataclass(frozen=True)
class ArmSpec:
    """Declarative specification for each predeclared Iteration 1 arm."""

    name: str
    mode: str
    lane: str
    headless: bool
    setup_name: str
    adapter: str
    protocol: str
    route: str
    base_url_env: str
    api_key_env: str
    default_context_window: int
    default_max_output_tokens: int


ARM_SPECS: dict[str, ArmSpec] = {
    "a1": ArmSpec(
        name="a1",
        mode="dsh_acp",
        lane="cloud-api",
        headless=True,
        setup_name="default",
        adapter="deepseek",
        protocol="messages",
        route="deepseek-official",
        base_url_env="DEEPSEEK_BASE_URL_ANTHROPIC",
        api_key_env="DEEPSEEK_API_KEY",
        default_context_window=128000,
        default_max_output_tokens=8192,
    ),
    "a2": ArmSpec(
        name="a2",
        mode="dsh_web",
        lane="cloud-api",
        headless=False,
        setup_name="default",
        adapter="deepseek",
        protocol="messages",
        route="deepseek-official",
        base_url_env="DEEPSEEK_BASE_URL_ANTHROPIC",
        api_key_env="DEEPSEEK_API_KEY",
        default_context_window=128000,
        default_max_output_tokens=8192,
    ),
    "b1": ArmSpec(
        name="b1",
        mode="dsh_acp",
        lane="self-hosted",
        headless=True,
        setup_name="openai-compatible",
        adapter="pi-ai",
        protocol="openai-completions",
        route="houmao-compatible",
        base_url_env="OPENAI_BASE_URL",
        api_key_env="OPENAI_API_KEY",
        default_context_window=262144,
        default_max_output_tokens=16384,
    ),
    "b2": ArmSpec(
        name="b2",
        mode="dsh_web",
        lane="self-hosted",
        headless=False,
        setup_name="openai-compatible",
        adapter="pi-ai",
        protocol="openai-completions",
        route="houmao-compatible",
        base_url_env="OPENAI_BASE_URL",
        api_key_env="OPENAI_API_KEY",
        default_context_window=262144,
        default_max_output_tokens=16384,
    ),
}


def _isolated_env(
    args: argparse.Namespace,
    *,
    project_dir: Path | None = None,
    path_prefix: Sequence[Path] = (),
    strip_default_dsh: bool = False,
) -> dict[str, str]:
    """Build an isolated Houmao env using repo `tmp/` for run state and home XDG for gateway access."""

    return build_isolated_env(
        Path(args.run_root).resolve(),
        server_name=args.tmux_server,
        access_root=Path(args.access_root).resolve(),
        project_dir=project_dir,
        path_prefix=path_prefix,
        strip_default_dsh=strip_default_dsh,
    )


def _arm_root(run_root: Path, arm: str) -> Path:
    """Return the external arm root directory outside the checkout."""

    return run_root / "arms" / arm


def _arm_state_path(run_root: Path, arm: str) -> Path:
    """Return the non-secret arm runtime state metadata path."""

    return _arm_root(run_root, arm) / "arm-state.json"


def _load_arm_state(run_root: Path, arm: str) -> dict[str, Any]:
    """Load persisted state metadata for one prepared or launched arm."""

    path = _arm_state_path(run_root, arm)
    if not path.is_file():
        raise FileNotFoundError(
            f"Arm `{arm}` is not prepared yet; run `setup-arm --arm {arm}` first"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid arm state payload at {path}")
    return data


def _save_arm_state(run_root: Path, arm: str, payload: Mapping[str, Any]) -> Path:
    """Persist updated non-secret arm state with `0600` permissions."""

    return private_write_text(
        _arm_state_path(run_root, arm),
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
    )


def _check_dsh_version_binary(executable: Path) -> dict[str, Any]:
    """Inspect a DSH binary `--version` and test it against `is_supported_dsh_version`."""

    if not executable.is_file():
        return {"path": str(executable), "present": False, "version": None, "supported": False}
    proc = subprocess.run(
        [str(executable), "--version"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10.0,
    )
    raw = (proc.stdout or proc.stderr).strip()
    token = raw.splitlines()[-1].split()[-1] if raw else ""
    return {
        "path": str(executable),
        "present": True,
        "returncode": proc.returncode,
        "raw_output": raw,
        "version": token,
        "supported": is_supported_dsh_version(token),
    }


def _create_fake_dsh(directory: Path, version_text: str) -> Path:
    """Write an executable synthetic `dsh` shim returning a fixed `--version` string."""

    script = f"#!/bin/sh\necho {json.dumps(version_text)}\n"
    return private_write_text(directory / "dsh", script, mode=0o700)


def _probe_isolated_tmux(run_root: Path) -> dict[str, Any]:
    """Verify isolated `-S <socket_path>` session creation without touching default server."""

    socket_path = isolated_tmux_socket(run_root)
    before_default = list_tmux_sessions()
    probe_session = "houmao-g0-smoke"
    server = isolated_tmux_server(socket_path)
    server.command(["kill-session", "-t", f"={probe_session}"])
    created = server.start(
        ["new-session", "-d", "-s", probe_session, "sleep", "5"],
        environment=server.native_environment(),
    )
    listed = list_tmux_sessions(socket_path=socket_path)
    server.command(["kill-session", "-t", f"={probe_session}"])
    after_default = list_tmux_sessions()
    return {
        "socket_path": str(socket_path),
        "smoke_created_rc": created.returncode,
        "smoke_seen": probe_session in listed,
        "default_before": before_default,
        "default_after": after_default,
        "default_untouched": before_default == after_default,
    }


def _parse_reasoning_option(raw: str) -> bool | dict[str, str | None]:
    """Read false or a native slot-to-wire mapping, including null for off."""

    stripped = raw.strip()
    if stripped.lower() == "false":
        return False
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("`--reasoning` must be `false` or a non-empty JSON mapping")
    if any(not isinstance(value, str) and value is not None for value in parsed.values()):
        raise ValueError("`--reasoning` values must be strings or null")
    return parsed


def _dsh_tool_params(
    *,
    spec: ArmSpec,
    model_id: str,
    context_window: int,
    max_output_tokens: int,
    reasoning: bool | dict[str, str | None],
    api_key_env: str | None,
    compat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose the exact DSH tool parameters for specialist authoring."""

    model: dict[str, Any] = {
        "id": model_id,
        "context_window": context_window,
        "max_output_tokens": max_output_tokens,
        "reasoning_efforts": reasoning,
    }
    if compat is not None:
        model["compat"] = compat
    return {
        "provider": {
            "adapter": spec.adapter,
            "protocol": spec.protocol,
            "route": spec.route,
            "base_url_env": spec.base_url_env,
            "api_key_env": api_key_env,
        },
        "models": [model],
    }


def _print_watch_banner(
    *,
    run_root: Path,
    session_name: str | None,
    capture_lines: int = 25,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """Display operator watch instructions and current tmux pane output."""

    socket_path = isolated_tmux_socket(run_root)
    print("\n=== HUMAN WATCH CHECKPOINT ===")
    if session_name:
        print(
            "Attach live tmux: "
            f"env -u TMUX -u TMUX_PANE tmux -S {socket_path} attach -t {session_name}"
        )
        print(f"--- tmux pane ({session_name}) ---")
        print(capture_tmux_pane(socket_path, session_name, lines=capture_lines).rstrip())
    else:
        print(
            f"Isolated tmux sessions ({socket_path}): {list_tmux_sessions(socket_path=socket_path)}"
        )
    if extra:
        print("--- checkpoint metadata ---")
        print(json.dumps(dict(extra), indent=2, sort_keys=True))


def cmd_g0(args: argparse.Namespace) -> int:
    """Run Gate G0 prerequisite, DSH version policy, tmux isolation, and endpoint probes."""

    run_root = Path(args.run_root).resolve()
    env_path = Path(args.env_file).resolve()
    env_vars = parse_env_file(env_path) if env_path.is_file() else {}
    required_keys = ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL_ANTHROPIC", "DEEPSEEK_BASE_URL_OPENAI")
    env_status = {
        key: {
            "present": bool(env_vars.get(key, "").strip()),
            "length": len(env_vars.get(key, "")),
        }
        for key in required_keys
    }

    host_dsh_raw = shutil.which("dsh")
    host_dsh = (
        _check_dsh_version_binary(Path(host_dsh_raw).resolve())
        if host_dsh_raw
        else {"present": False, "supported": False}
    )
    isolated_dsh = _check_dsh_version_binary(
        REPO_ROOT / "tmp/dsh/npm-runtime/node_modules/.bin/dsh"
    )
    policy_checks = {
        "floor_specifier": DSH_SUPPORTED_VERSIONS,
        "0.2.1": is_supported_dsh_version("0.2.1"),
        "0.2.2-alpha.3": is_supported_dsh_version("0.2.2-alpha.3"),
        "0.2.2-rc.1": is_supported_dsh_version("0.2.2-rc.1"),
        "0.2.2-rc.3": is_supported_dsh_version("0.2.2-rc.3"),
        "0.2.2": is_supported_dsh_version("0.2.2"),
        "0.3.0": is_supported_dsh_version("0.3.0"),
        "0.3.0-rc.1": is_supported_dsh_version("0.3.0-rc.1"),
    }

    env_smoke = _isolated_env(args)
    tmux_probe = _probe_isolated_tmux(run_root)
    qwen_probe: dict[str, Any] = {"status": "not_probed"}
    if not args.self_test and args.qwen_base_url:
        qwen_probe = probe_openai_models(args.qwen_base_url, api_key=args.qwen_api_key)

    report = {
        "gate": "G0",
        "self_test": bool(args.self_test),
        "run_root": str(run_root),
        "access_root": str(Path(args.access_root).resolve()),
        "isolated_env_vars_set": sorted(k for k in env_smoke if k.startswith("HOUMAO_GLOBAL_")),
        "tmux_probe": tmux_probe,
        "dsh_policy_checks": policy_checks,
        "host_dsh": host_dsh,
        "repo_isolated_dsh": isolated_dsh,
        "dotenv_file": {"path": str(env_path), "exists": env_path.is_file(), "keys": env_status},
        "qwen_probe": qwen_probe,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    ok = (
        tmux_probe["smoke_created_rc"] == 0
        and tmux_probe["smoke_seen"]
        and tmux_probe["default_untouched"]
        and host_dsh.get("supported", False)
        and policy_checks["0.2.2-rc.1"]
        and policy_checks["0.2.2"]
        and not policy_checks["0.2.2-alpha.3"]
        and not policy_checks["0.2.1"]
    )
    if args.self_test:
        print("G0 SELF-TEST PASSED" if ok else "G0 SELF-TEST FAILED")
    return 0 if ok else 1


def cmd_a0(args: argparse.Namespace) -> int:
    """Run Arm A0 cold project setup and DSH version/config diagnostic probes (no LLM calls)."""

    run_root = Path(args.run_root).resolve()
    proj = private_mkdir(run_root / "proj-a0")
    if (proj / ".houmao").exists():
        shutil.rmtree(proj / ".houmao")
    env = _isolated_env(args, project_dir=proj)

    init_res = run_houmao_mgr(["project", "init"], env=env, cwd=proj)
    setup_path = proj / ".houmao/agents/tools/dsh/setups/default/tool-params.yaml"
    starter_setup = setup_path.read_text(encoding="utf-8") if setup_path.is_file() else ""

    spec_res = run_houmao_mgr(
        [
            "project",
            "specialist",
            "create",
            "--name",
            "a0-probe",
            "--tool",
            "dsh",
            "--setup",
            "default",
            "--system-prompt",
            ROLE_PROMPT,
            "--no-system-skills",
        ],
        env=env,
        cwd=proj,
    )
    empty_models_launch = run_houmao_mgr(
        [
            "project",
            "agents",
            "launch",
            "--specialist",
            "a0-probe",
            "--name",
            "a0-empty-models",
            "--headless",
            "--no-gateway",
        ],
        env=env,
        cwd=proj,
    )

    sys.path.insert(0, str(REPO_ROOT))
    from tools.dsh.prepare import inspect_runtime as dsh_inspect_runtime  # noqa: E402

    shim_root = private_mkdir(run_root / "a0-shims")
    host_dsh_path = Path(shutil.which("dsh") or "")
    alpha_dir = private_mkdir(shim_root / "alpha")
    old_dir = private_mkdir(shim_root / "old")
    _create_fake_dsh(alpha_dir, "0.2.2-alpha.3")
    _create_fake_dsh(old_dir, "0.2.1")

    version_probes: list[dict[str, Any]] = []
    source_root = REPO_ROOT / "extern/orphan/deepseek-harness"
    if source_root.is_dir() and host_dsh_path.is_file():
        try:
            inspected = dsh_inspect_runtime(source_root, host_dsh_path)
            version_probes.append(
                {"label": "host-inspect-runtime", "ok": True, "runtime": inspected}
            )
        except Exception as exc:  # noqa: BLE001
            version_probes.append({"label": "host-inspect-runtime", "ok": False, "error": str(exc)})

    probe_params = _dsh_tool_params(
        spec=ARM_SPECS["a1"],
        model_id="deepseek-chat",
        context_window=128000,
        max_output_tokens=8192,
        reasoning=False,
        api_key_env=ARM_SPECS["a1"].api_key_env,
    )
    private_write_text(setup_path, yaml.safe_dump(probe_params, sort_keys=False))
    missing_cred_launch = run_houmao_mgr(
        [
            "project",
            "agents",
            "launch",
            "--specialist",
            "a0-probe",
            "--name",
            "a0-missing-cred",
            "--headless",
            "--no-gateway",
        ],
        env=env,
        cwd=proj,
    )

    for label, shim_dir in (("synthetic-alpha", alpha_dir), ("synthetic-old", old_dir)):
        shim_env = _isolated_env(
            args,
            project_dir=proj,
            path_prefix=(shim_dir,),
            strip_default_dsh=True,
        )
        probe_res = run_houmao_mgr(
            [
                "project",
                "agents",
                "launch",
                "--specialist",
                "a0-probe",
                "--name",
                f"a0-{label}",
                "--headless",
                "--no-gateway",
            ],
            env=shim_env,
            cwd=proj,
        )
        version_probes.append(
            {
                "label": label,
                "rc": probe_res.returncode,
                "stdout": probe_res.stdout.strip(),
                "stderr": probe_res.stderr.strip(),
            }
        )

    report = {
        "arm": "A0",
        "project_dir": str(proj),
        "project_init_rc": init_res.returncode,
        "starter_setup_yaml": starter_setup,
        "specialist_create_rc": spec_res.returncode,
        "specialist_create_err": spec_res.stderr.strip(),
        "empty_models_launch_rc": empty_models_launch.returncode,
        "empty_models_launch_out": empty_models_launch.stdout.strip(),
        "empty_models_launch_err": empty_models_launch.stderr.strip(),
        "missing_cred_launch_rc": missing_cred_launch.returncode,
        "missing_cred_launch_out": missing_cred_launch.stdout.strip(),
        "missing_cred_launch_err": missing_cred_launch.stderr.strip(),
        "version_probes": version_probes,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_gen_admin_keys(args: argparse.Namespace) -> int:
    """Generate Ed25519 admin keypairs and a validated `gateway-admin-seed.json`."""

    access_root = Path(args.access_root).resolve()
    keys_dir = Path(args.keys_dir).resolve() if args.keys_dir else (access_root / "keys")
    result = generate_admin_keyset(keys_dir, principals=args.principals)
    print(json.dumps(result, indent=2))
    return 0


def cmd_setup_arm(args: argparse.Namespace) -> int:
    """Prepare an isolated specialist, profile, credential bundle, and optional admin keys."""

    run_root = Path(args.run_root).resolve()
    spec = ARM_SPECS[args.arm]
    arm_dir = private_mkdir(_arm_root(run_root, args.arm))
    proj = private_mkdir(arm_dir / "workdir")
    env = _isolated_env(args, project_dir=proj)

    if args.lane_override == "cloud-api" or spec.lane == "cloud-api":
        if args.env_file is None:
            raise ValueError("Cloud arms require an explicitly selected external --env-file")
        credential_file = Path(args.env_file).resolve()
        if credential_file.is_relative_to(REPO_ROOT):
            raise ValueError("Cloud credential env files must remain outside the checkout")
        env_values = parse_env_file(credential_file)
        api_key = env_values.get(spec.api_key_env, "")
        base_url = args.base_url or env_values.get(spec.base_url_env, "")
        if not api_key or not base_url:
            raise ValueError(
                f"Missing required keys `{spec.api_key_env}` / `{spec.base_url_env}` in {args.env_file}"
            )
    else:
        base_url = args.base_url or ""
        api_key = args.api_key or ""
        if not base_url:
            raise ValueError(f"`--base-url` is required for self-hosted arm `{args.arm}`")

    context_window = args.context_window or spec.default_context_window
    max_output_tokens = args.max_output_tokens or spec.default_max_output_tokens
    qwen_38 = spec.adapter == "pi-ai" and args.model == "Qwen/Qwen3.8-27B-FP8"
    reasoning: bool | dict[str, str | None] = False
    compat = None
    if qwen_38:
        reasoning = {"off": "none", "low": "low", "medium": "medium", "high": "high"}
        compat = {"supports_developer_role": False}
    if args.reasoning is not None:
        reasoning = _parse_reasoning_option(args.reasoning)
    if args.compat is not None:
        compat = json.loads(args.compat)
        if not isinstance(compat, dict):
            raise ValueError("`--compat` must be a JSON mapping")
    tool_params = _dsh_tool_params(
        spec=spec,
        model_id=args.model,
        context_window=context_window,
        max_output_tokens=max_output_tokens,
        reasoning=reasoning,
        api_key_env=spec.api_key_env if api_key else None,
        compat=compat,
    )
    configured_model, _ = DshEffectiveToolParams.from_mapping(tool_params).select_model(args.model)

    steps: list[dict[str, Any]] = []
    init_res = run_houmao_mgr(["project", "init"], env=env, cwd=proj, print_json=True)
    steps.append(
        {"step": "project init", "rc": init_res.returncode, "err": init_res.stderr.strip()}
    )
    if init_res.returncode != 0:
        print(json.dumps({"steps": steps}, indent=2))
        return init_res.returncode

    cred_name = f"cred-{spec.name}"
    cred_op = "add"
    cred_args = [
        "--name",
        cred_name,
        "--adapter",
        spec.adapter,
        "--base-url",
        base_url,
        "--base-url-env",
        spec.base_url_env,
    ]
    if api_key:
        cred_args.extend(["--api-key", api_key, "--api-key-env", spec.api_key_env])
    cred_res = run_houmao_mgr(
        ["project", "credentials", "dsh", "add", *cred_args],
        env=env,
        cwd=proj,
        print_json=True,
    )
    if cred_res.returncode != 0 and "already exists" in cred_res.stderr:
        cred_op = "set"
        if not api_key:
            cred_args.append("--clear-api-key")
        cred_res = run_houmao_mgr(
            ["project", "credentials", "dsh", "set", *cred_args],
            env=env,
            cwd=proj,
            print_json=True,
        )
    steps.append(
        {
            "step": f"credentials dsh {cred_op}",
            "rc": cred_res.returncode,
            "err": cred_res.stderr.strip(),
        }
    )
    if cred_res.returncode != 0:
        print(json.dumps({"steps": steps}, indent=2))
        return cred_res.returncode

    tool_params_path = private_write_text(
        arm_dir / "tool-params.yaml", yaml.safe_dump(tool_params, sort_keys=False)
    )

    specialist_name = args.specialist_name or f"iter1-{spec.name}-dsh"
    spec_res = run_houmao_mgr(
        [
            "project",
            "specialist",
            "create",
            "--name",
            specialist_name,
            "--tool",
            "dsh",
            "--setup",
            spec.setup_name,
            "--credential",
            cred_name,
            "--model",
            args.model,
            "--tool-params",
            f"@{tool_params_path}",
            "--system-prompt",
            ROLE_PROMPT,
            "--no-system-skills",
            "--yes",
        ],
        env=env,
        cwd=proj,
        print_json=True,
    )
    steps.append(
        {"step": "specialist create", "rc": spec_res.returncode, "err": spec_res.stderr.strip()}
    )
    if spec_res.returncode != 0:
        print(json.dumps({"steps": steps}, indent=2))
        return spec_res.returncode

    profile_name = args.profile_name or f"iter1-{spec.name}"
    agent_name = args.agent_name or f"iter1-{spec.name}"
    profile_cmd = [
        "project",
        "profile",
        "create",
        "--name",
        profile_name,
        "--specialist",
        specialist_name,
        "--agent-name",
        agent_name,
        "--model",
        args.model,
        "--workdir",
        str(proj),
        "--yes",
    ]
    if spec.headless:
        profile_cmd.append("--headless")
    profile_res = run_houmao_mgr(profile_cmd, env=env, cwd=proj, print_json=True)
    steps.append(
        {"step": "profile create", "rc": profile_res.returncode, "err": profile_res.stderr.strip()}
    )
    if profile_res.returncode != 0:
        print(json.dumps({"steps": steps}, indent=2))
        return profile_res.returncode

    profile_get = run_houmao_mgr(
        ["project", "profile", "get", "--name", profile_name],
        env=env,
        cwd=proj,
        print_json=True,
    )
    steps.append(
        {"step": "profile get", "rc": profile_get.returncode, "err": profile_get.stderr.strip()}
    )

    admin_bundle: dict[str, Any] | None = None
    admin_seed_path: str | None = None
    if args.admin_seed:
        candidate = Path(args.admin_seed).resolve()
        validated_seed = load_gateway_admin_seed(candidate)
        admin_seed_path = str(candidate)
        resolved_keys: list[dict[str, str]] = []
        for entry in validated_seed.admin_keys:
            priv_candidate = candidate.parent / f"{entry.principal}_ed25519"
            pub_candidate = candidate.parent / f"{entry.principal}_ed25519.pub"
            resolved_keys.append(
                {
                    "principal": entry.principal,
                    "key_id": entry.key_id,
                    "private_key_path": str(priv_candidate) if priv_candidate.is_file() else "",
                    "public_key_path": str(pub_candidate) if pub_candidate.is_file() else "",
                    "public_key": entry.public_key,
                }
            )
        admin_bundle = {
            "seed_path": admin_seed_path,
            "enrolled_count": len(validated_seed.admin_keys),
            "key_ids": [entry.key_id for entry in validated_seed.admin_keys],
            "keys": resolved_keys,
        }
    elif args.with_admin_keys:
        keys_dir = (
            Path(args.keys_dir).resolve()
            if args.keys_dir
            else (Path(args.access_root).resolve() / "keys")
        )
        admin_bundle = generate_admin_keyset(keys_dir, principals=args.principals)
        admin_seed_path = admin_bundle["seed_path"]

    state: dict[str, Any] = {
        "arm": spec.name,
        "mode": spec.mode,
        "lane": spec.lane,
        "headless": spec.headless,
        "project_dir": str(proj),
        "tool_params_path": str(tool_params_path),
        "specialist_name": specialist_name,
        "agent_name": agent_name,
        "profile_name": profile_name,
        "profile": profile_get.parse_json_stdout(),
        "model": configured_model.id,
        "context_window": context_window,
        "max_output_tokens": max_output_tokens,
        "reasoning": reasoning,
        "compat": compat,
        "base_url": base_url,
        "tmux_server": args.tmux_server,
        "access_root": str(Path(args.access_root).resolve()),
        "admin_seed_path": admin_seed_path,
        "admin_keys": admin_bundle["keys"] if admin_bundle else [],
        "launched": False,
    }
    state_path = _save_arm_state(run_root, spec.name, state)
    print(
        json.dumps(
            {
                "steps": steps,
                "state_path": str(state_path),
                "admin_bundle": admin_bundle,
                "state": state,
            },
            indent=2,
        )
    )
    return profile_res.returncode


def cmd_launch(args: argparse.Namespace) -> int:
    """Launch a prepared arm and display live watch details without auto-advancing."""

    run_root = Path(args.run_root).resolve()
    state = _load_arm_state(run_root, args.arm)
    spec = ARM_SPECS[args.arm]
    proj = Path(state["project_dir"])
    env = _isolated_env(args, project_dir=proj)

    cmd_args = [
        "project",
        "agents",
        "launch",
        "--profile",
        state["profile_name"],
        "--gateway-background",
        "--headless" if spec.headless else "--no-headless",
    ]
    admin_seed = args.gateway_admin_seed or state.get("admin_seed_path")
    if admin_seed:
        seed_path = str(Path(admin_seed).resolve())
        load_gateway_admin_seed(Path(seed_path))
        cmd_args.extend(["--gateway-admin-seed", seed_path])
    if args.gateway_port is not None:
        cmd_args.extend(["--gateway-port", str(args.gateway_port)])
    if args.reasoning_level is not None:
        cmd_args.extend(["--reasoning-level", str(args.reasoning_level)])

    t0 = time.monotonic()
    res = run_houmao_mgr(cmd_args, env=env, cwd=proj, print_json=True)
    elapsed = round(time.monotonic() - t0, 3)
    payload = res.parse_json_stdout()
    if payload is None and res.returncode == 0:
        # Interactive launch in a captured subprocess also emits a terminal handoff record.
        try:
            stdout = res.stdout.lstrip()
            completion, end = json.JSONDecoder().raw_decode(stdout)
            handoff = json.loads(stdout[end:])
        except ValueError:
            pass
        else:
            if (
                isinstance(completion, dict)
                and isinstance(completion.get("agent_id"), str)
                and isinstance(handoff, dict)
                and handoff.get("terminal_handoff") == "skipped_non_interactive"
            ):
                payload = completion
    if res.returncode == 0 and isinstance(payload, dict):
        state["launched"] = True
        state["agent_id"] = payload.get("agent_id")
        state["session_name"] = payload.get("session_name") or payload.get("tmux_session_name")
        state["gateway_port"] = payload.get("gateway_port")
        state["launch_payload"] = payload
        _save_arm_state(run_root, args.arm, state)

    print(
        json.dumps(
            {
                "arm": args.arm,
                "rc": res.returncode,
                "elapsed_seconds": elapsed,
                "stdout_json": payload,
                "stderr": res.stderr.strip(),
            },
            indent=2,
        )
    )
    _print_watch_banner(
        run_root=run_root,
        session_name=state.get("session_name"),
        extra={"agent_id": state.get("agent_id"), "gateway_port": state.get("gateway_port")},
    )
    return res.returncode


def cmd_send(args: argparse.Namespace) -> int:
    """Submit a frozen or custom prompt to a launched arm cleanly."""

    run_root = Path(args.run_root).resolve()
    state = _load_arm_state(run_root, args.arm)
    proj = Path(state["project_dir"])
    env = _isolated_env(args, project_dir=proj)
    prompt_text = args.text if args.text is not None else FROZEN_PROMPTS[args.prompt_id]

    agent_name = state["agent_name"]
    if args.via == "turn":
        cmd_args = [
            "agents",
            "single",
            "--agent-name",
            agent_name,
            "turn",
            "submit",
            "--prompt",
            prompt_text,
        ]
    elif args.via == "gateway":
        cmd_args = [
            "agents",
            "single",
            "--agent-name",
            agent_name,
            "gateway",
            "prompt",
            "--admission-policy",
            args.admission_policy,
            "--prompt",
            prompt_text,
        ]
    else:
        cmd_args = [
            "agents",
            "single",
            "--agent-name",
            agent_name,
            "prompt",
            "--prompt",
            prompt_text,
        ]
    if args.reasoning_level is not None:
        cmd_args.extend(["--reasoning-level", str(args.reasoning_level)])

    if args.background:
        log_path = _arm_root(run_root, args.arm) / "last-send.log"
        private_write_text(log_path, "")
        with log_path.open("w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                [resolve_houmao_mgr(), "--print-json", *cmd_args],
                cwd=str(proj),
                env=dict(env),
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print(
            json.dumps(
                {
                    "arm": args.arm,
                    "via": args.via,
                    "prompt_id": args.prompt_id,
                    "background_pid": proc.pid,
                    "log_path": str(log_path),
                },
                indent=2,
            )
        )
        time.sleep(args.settle_wait)
        _print_watch_banner(run_root=run_root, session_name=state.get("session_name"))
        return 0

    t0 = time.monotonic()
    res = run_houmao_mgr(cmd_args, env=env, cwd=proj, print_json=True, timeout=args.timeout)
    elapsed = round(time.monotonic() - t0, 3)

    probe_file = proj / "dsh_probe.txt"
    probe_text = probe_file.read_text(encoding="utf-8") if probe_file.is_file() else None
    print(
        json.dumps(
            {
                "arm": args.arm,
                "via": args.via,
                "prompt_id": args.prompt_id,
                "rc": res.returncode,
                "elapsed_seconds": elapsed,
                "stdout_json": res.parse_json_stdout(),
                "raw_stdout": None if res.parse_json_stdout() is not None else res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "dsh_probe_txt": probe_text,
            },
            indent=2,
        )
    )
    _print_watch_banner(run_root=run_root, session_name=state.get("session_name"))
    return res.returncode


def cmd_interrupt(args: argparse.Namespace) -> int:
    """Interrupt an active turn on a launched arm via single or gateway CLI surface."""

    run_root = Path(args.run_root).resolve()
    state = _load_arm_state(run_root, args.arm)
    proj = Path(state["project_dir"])
    env = _isolated_env(args, project_dir=proj)
    agent_name = state["agent_name"]
    subcmd = (
        ["agents", "single", "--agent-name", agent_name, "gateway", "interrupt"]
        if args.via == "gateway"
        else ["agents", "single", "--agent-name", agent_name, "interrupt"]
    )
    res = run_houmao_mgr(subcmd, env=env, cwd=proj, print_json=True)
    print(
        json.dumps(
            {
                "arm": args.arm,
                "via": args.via,
                "rc": res.returncode,
                "stdout_json": res.parse_json_stdout(),
                "stderr": res.stderr.strip(),
            },
            indent=2,
        )
    )
    _print_watch_banner(run_root=run_root, session_name=state.get("session_name"))
    return res.returncode


def cmd_watch(args: argparse.Namespace) -> int:
    """Inspect managed agent state, gateway status, usage endpoint, and tmux pane."""

    run_root = Path(args.run_root).resolve()
    state = _load_arm_state(run_root, args.arm)
    proj = Path(state["project_dir"])
    env = _isolated_env(args, project_dir=proj)
    agent_name = state["agent_name"]

    agent_state = run_houmao_mgr(
        ["agents", "single", "--agent-name", agent_name, "state"],
        env=env,
        cwd=proj,
        print_json=True,
    )
    gw_status = run_houmao_mgr(
        ["agents", "single", "--agent-name", agent_name, "gateway", "status"],
        env=env,
        cwd=proj,
        print_json=True,
    )
    gw_payload = gw_status.parse_json_stdout()
    port = state.get("gateway_port")
    if isinstance(gw_payload, dict) and isinstance(gw_payload.get("gateway_port"), int):
        port = gw_payload["gateway_port"]

    gateway_probe: dict[str, Any] = {"probed": False}
    if isinstance(port, int) and port > 0:
        admin_key_path: Path | None = None
        if args.admin_key_path:
            admin_key_path = Path(args.admin_key_path).resolve()
        elif isinstance(state.get("admin_keys"), list) and state["admin_keys"]:
            candidate = state["admin_keys"][0].get("private_key_path")
            if isinstance(candidate, str) and candidate:
                admin_key_path = Path(candidate)
        gateway_probe = {
            "probed": True,
            "base_url": f"http://127.0.0.1:{port}",
            **admin_gateway_probe(
                f"http://127.0.0.1:{port}",
                admin_private_key_path=admin_key_path,
            ),
        }

    print(
        json.dumps(
            {
                "arm": args.arm,
                "state_rc": agent_state.returncode,
                "agent_state": agent_state.parse_json_stdout() or agent_state.stderr.strip(),
                "gateway_rc": gw_status.returncode,
                "gateway_status": gw_payload or gw_status.stderr.strip(),
                "gateway_probe": gateway_probe,
            },
            indent=2,
        )
    )
    _print_watch_banner(
        run_root=run_root,
        session_name=state.get("session_name"),
        capture_lines=args.lines,
    )
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    """Stop one arm cleanly and confirm its isolated tmux session closed."""

    run_root = Path(args.run_root).resolve()
    state = _load_arm_state(run_root, args.arm)
    proj = Path(state["project_dir"])
    env = _isolated_env(args, project_dir=proj)
    res = run_houmao_mgr(
        ["agents", "single", "--agent-name", state["agent_name"], "stop"],
        env=env,
        cwd=proj,
        print_json=True,
    )
    state["launched"] = False
    _save_arm_state(run_root, args.arm, state)
    print(
        json.dumps(
            {
                "arm": args.arm,
                "stop_rc": res.returncode,
                "stdout_json": res.parse_json_stdout(),
                "stderr": res.stderr.strip(),
                "remaining_isolated_sessions": list_tmux_sessions(
                    socket_path=isolated_tmux_socket(run_root)
                ),
                "default_sessions": list_tmux_sessions(),
            },
            indent=2,
        )
    )
    return res.returncode


def cmd_teardown(args: argparse.Namespace) -> int:
    """Run Gate G4 teardown: stop active arms, kill isolated tmux server if requested, verify default tmux."""

    run_root = Path(args.run_root).resolve()
    before_default = list_tmux_sessions()
    stopped: list[dict[str, Any]] = []
    arms_dir = run_root / "arms"
    if arms_dir.is_dir():
        for arm_path in sorted(arms_dir.iterdir()):
            if not (arm_path / "arm-state.json").is_file():
                continue
            arm = arm_path.name
            state = _load_arm_state(run_root, arm)
            if state.get("launched"):
                proj = Path(state["project_dir"])
                env = _isolated_env(args, project_dir=proj)
                res = run_houmao_mgr(
                    ["agents", "single", "--agent-name", state["agent_name"], "stop"],
                    env=env,
                    cwd=proj,
                    print_json=True,
                )
                state["launched"] = False
                _save_arm_state(run_root, arm, state)
                stopped.append({"arm": arm, "rc": res.returncode})

    kill_res = None
    socket_path = isolated_tmux_socket(run_root)
    if args.kill_server:
        res = kill_isolated_tmux_server(socket_path)
        kill_res = {"rc": res.returncode, "stderr": res.stderr.strip()}

    after_default = list_tmux_sessions()
    remaining_isolated = list_tmux_sessions(socket_path=socket_path)
    print(
        json.dumps(
            {
                "gate": "G4",
                "stopped_arms": stopped,
                "kill_isolated_server": kill_res,
                "remaining_isolated_sessions": remaining_isolated,
                "default_before": before_default,
                "default_after": after_default,
                "default_untouched": before_default == after_default,
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the Iteration 1 CLI parser."""

    parser = argparse.ArgumentParser(description="Houmao 3.0 Iteration 1 interactive DSH driver")
    parser.add_argument(
        "--run-root", default=str(DEFAULT_RUN_ROOT), help="Scratch run root under `<repo>/tmp`"
    )
    parser.add_argument(
        "--access-root",
        default=str(DEFAULT_ACCESS_ROOT),
        help="Non-checkout owner access root (keys and XDG config outside `.git`)",
    )
    parser.add_argument(
        "--tmux-server", default=DEFAULT_TMUX_SERVER, help="Isolated tmux `-L` name"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_g0 = sub.add_parser("g0", help="Run Gate G0 prerequisite and tmux isolation checks")
    p_g0.add_argument(
        "--self-test", action="store_true", help="Offline G0 check without Qwen HTTP probe"
    )
    p_g0.add_argument(
        "--env-file", default=str(REPO_ROOT / ".env"), help="Dotenv path to check keys"
    )
    p_g0.add_argument("--qwen-base-url", default=None, help="Optional Qwen OpenAI-compatible URL")
    p_g0.add_argument("--qwen-api-key", default=None, help="Optional Qwen API key for /models")

    sub.add_parser("a0", help="Run Arm A0 cold setup and DSH version guardrail probes")

    p_keys = sub.add_parser(
        "gen-admin-keys",
        help="Generate Ed25519 admin keypairs and validated gateway-admin-seed.json",
    )
    p_keys.add_argument("--keys-dir", default=None, help="External directory for generated keys")
    p_keys.add_argument(
        "--principals",
        nargs="+",
        default=["iter1-operator-admin", "iter1-reviewer-admin"],
        help="Admin principal names to generate and seed",
    )

    p_setup = sub.add_parser("setup-arm", help="Prepare an isolated Iteration 1 arm")
    p_setup.add_argument("--arm", choices=sorted(ARM_SPECS), required=True)
    p_setup.add_argument("--model", required=True, help="Exact model ID for tool-params.yaml")
    p_setup.add_argument("--env-file", help="Explicit external dotenv for cloud-api")
    p_setup.add_argument("--base-url", default=None, help="Explicit provider endpoint URL override")
    p_setup.add_argument("--api-key", default=None, help="Explicit self-hosted API key override")
    p_setup.add_argument("--context-window", type=int, default=None)
    p_setup.add_argument("--max-output-tokens", type=int, default=None)
    p_setup.add_argument(
        "--reasoning", help="DSH reasoning JSON: false or a native slot-to-wire mapping"
    )
    p_setup.add_argument("--compat", help="DSH model compatibility as a JSON mapping")
    p_setup.add_argument("--lane-override", choices=("cloud-api", "self-hosted"), default=None)
    p_setup.add_argument("--specialist-name", default=None, help="Custom specialist name override")
    p_setup.add_argument("--profile-name", default=None, help="Custom launch profile name override")
    p_setup.add_argument("--agent-name", default=None, help="Custom default agent name override")
    p_setup.add_argument(
        "--with-admin-keys",
        action="store_true",
        help="Generate Ed25519 admin keys and bind `gateway-admin-seed.json` to the arm",
    )
    p_setup.add_argument(
        "--keys-dir", default=None, help="Directory for generated admin keys when --with-admin-keys"
    )
    p_setup.add_argument(
        "--principals",
        nargs="+",
        default=["iter1-operator-admin", "iter1-reviewer-admin"],
        help="Admin key principals when --with-admin-keys is enabled",
    )
    p_setup.add_argument(
        "--admin-seed",
        default=None,
        help="Existing validated `gateway-admin-seed.json` path to reuse for launch",
    )

    p_launch = sub.add_parser("launch", help="Launch a prepared arm and print watch details")
    p_launch.add_argument("--arm", choices=sorted(ARM_SPECS), required=True)
    p_launch.add_argument("--gateway-port", type=int, default=None)
    p_launch.add_argument("--reasoning-level", type=int, default=None)
    p_launch.add_argument("--gateway-admin-seed", default=None, help="Explicit admin seed JSON")

    p_send = sub.add_parser("send", help="Submit a frozen or custom prompt to a launched arm")
    p_send.add_argument("--arm", choices=sorted(ARM_SPECS), required=True)
    p_send.add_argument("--prompt-id", choices=sorted(FROZEN_PROMPTS), default="P1")
    p_send.add_argument("--text", default=None, help="Custom prompt text overriding --prompt-id")
    p_send.add_argument("--via", choices=("prompt", "turn", "gateway"), default="prompt")
    p_send.add_argument(
        "--admission-policy",
        choices=("ready-only", "if-no-pending", "always"),
        default="ready-only",
    )
    p_send.add_argument("--reasoning-level", type=int, default=None)
    p_send.add_argument("--timeout", type=float, default=180.0)
    p_send.add_argument(
        "--background",
        action="store_true",
        help="Start prompt submission detached so operator can watch and interrupt mid-turn",
    )
    p_send.add_argument(
        "--settle-wait",
        type=float,
        default=1.5,
        help="Seconds to pause before capturing pane when `--background` is set",
    )

    p_int = sub.add_parser("interrupt", help="Interrupt an active turn on a launched arm")
    p_int.add_argument("--arm", choices=sorted(ARM_SPECS), required=True)
    p_int.add_argument("--via", choices=("single", "gateway"), default="single")

    p_watch = sub.add_parser("watch", help="Inspect agent state, gateway status, usage, and pane")
    p_watch.add_argument("--arm", choices=sorted(ARM_SPECS), required=True)
    p_watch.add_argument("--lines", type=int, default=40)
    p_watch.add_argument("--admin-key-path", default=None, help="Admin Ed25519 private key path")

    p_stop = sub.add_parser("stop", help="Stop a launched arm cleanly")
    p_stop.add_argument("--arm", choices=sorted(ARM_SPECS), required=True)

    p_td = sub.add_parser("teardown", help="Stop remaining arms and run Gate G4 check")
    p_td.add_argument("--kill-server", action="store_true", help="Kill only `-L <tmux_server>`")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for Iteration 1 campaign tooling."""

    args = build_parser().parse_args(argv)
    dispatch = {
        "g0": cmd_g0,
        "a0": cmd_a0,
        "gen-admin-keys": cmd_gen_admin_keys,
        "setup-arm": cmd_setup_arm,
        "launch": cmd_launch,
        "send": cmd_send,
        "interrupt": cmd_interrupt,
        "watch": cmd_watch,
        "stop": cmd_stop,
        "teardown": cmd_teardown,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
