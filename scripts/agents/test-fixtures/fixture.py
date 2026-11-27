"""Prepare reproducible API/native-login test agents with private external state.

Native provider metadata and Houmao-owned launch configuration are separate inputs.
The option help below identifies which mechanism each flag controls. Run
`fixture.py prepare --help` for the managed source/profile configuration guide,
including how to select a reasoning preset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Literal

from houmao.agents.realm_controller.run_modes import RUN_MODES
from houmao.execution.tmux import TmuxCommandError

from fixturelib.auth import (
    bundle_path,
    candidate_from_source,
    discover_auth,
    external_root,
    import_auth,
    validate_native_bundle,
)
from fixturelib.config import (
    FixtureError,
    ResolvedConfig,
    fixture_run_mode,
    resolve_config,
    validate_reasoning_level,
)
from fixturelib.hermes_owner import qualify_owner, retire_owner, selected_owner_root
from fixturelib.launch import (
    check_run,
    interrupt_run,
    launch_run,
    probe_configuration,
    prompt_run,
    public_run,
    stop_run,
)
from fixturelib.pool import ModelPoolEntry, load_model_pool, select_pool_key
from fixturelib.prepare import ManagedCommandError, load_run, prepare_run


_MANAGED_CONFIGURATION_GUIDE = """Houmao managed configuration:
  Native metadata flags describe the provider and model. --dsh-reasoning
  declares the available DSH slots. --reasoning-effort sets a native default
  for Claude, Codex, Kimi, and Hermes. Raw Hermes uses --reasoning-effort or the
  selected pool entry's reasoning_effort field.

  Houmao --reasoning-level selects a tool/model-specific preset by index.
  Manager preparation accepts it from the command line or a selected model-pool
  entry and validates it against the supported presets. For Hermes, level 5
  selects xhigh and level 0 selects none. A level overrides the native default.

  Manager preparation creates a fixture-agent specialist and project profile.

  Manager runs default to --tmux-server houmao-default and store that selection
  on the profile. Do not edit generated YAML projections directly. For DSH slots
  off, low, medium, xhigh, levels 1/2/3 select low/medium/xhigh and level 0
  selects off. Use profile set for other launch defaults such as model, prompt
  mode, environment, tool parameters, and tmux. Use specialist set on the same
  project for reusable role, skill, setup, credential, and system-skill
  configuration. See the corresponding Houmao command's --help for its options.

  On supported headless agents, Houmao prompt and turn-submit commands accept
  request-scoped --model and --reasoning-level overrides for a single turn.
  For Hermes, set the effort at launch. Web and TUI defaults take effect when
  the agent launches.
"""

_POOL_ROUTING_FIELDS = (
    "client",
    "case",
    "auth_method",
    "auth_bundle",
    "model",
    "base_url",
    "env_file",
    "descriptor",
    "context_window",
    "max_output_tokens",
    "dsh_reasoning",
    "dsh_compat",
    "dsh_protocol",
    "capabilities",
    "reasoning_key",
    "reasoning_effort",
    "support_effort",
)


def add_case_arguments(parser: argparse.ArgumentParser) -> None:
    """Add explicit API case, native metadata, and Houmao launch selection options."""

    parser.add_argument("--client", choices=("claude", "codex", "kimi", "dsh", "hermes"))
    parser.add_argument("--case", choices=("self-hosted", "cloud-api"))
    parser.add_argument("--auth-method", choices=("api-key", "native-login"))
    parser.add_argument("--auth-bundle")
    parser.add_argument("--auth-root", type=Path)
    parser.add_argument(
        "--model", help="Select the model; manager preparation stores it as a launch default"
    )
    parser.add_argument("--base-url")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--descriptor", type=Path)
    parser.add_argument(
        "--hermes-owner-root",
        type=Path,
        help="Select the prepared test-owned Hermes root under repository tmp/",
    )
    parser.add_argument(
        "--context-window",
        type=int,
        help="Native model context metadata; required for Kimi and DSH API cases",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Native model output-limit metadata; required for DSH API cases",
    )
    parser.add_argument(
        "--dsh-reasoning",
        help=(
            "Declare DSH reasoning slots as false or a native slot-to-wire JSON mapping; "
            "select a default through Houmao specialist/profile --reasoning-level"
        ),
    )
    parser.add_argument("--dsh-compat", help="DSH model compatibility as a JSON mapping")
    parser.add_argument(
        "--dsh-protocol",
        choices=(
            "messages",
            "openai-completions",
            "openai-responses",
            "anthropic-messages",
            "google-generative-ai",
        ),
        help="Choose the DSH wire protocol for the selected case adapter",
    )
    parser.add_argument(
        "--capabilities",
        help="Declare comma-separated native model capabilities, not a reasoning selection",
    )
    parser.add_argument("--reasoning-key", help="Kimi native reasoning_key model metadata")
    parser.add_argument(
        "--reasoning-effort",
        help="Native default effort for Claude, Codex, Kimi, or Hermes. Example for Hermes is xhigh.",
    )
    parser.add_argument(
        "--support-effort",
        action="append",
        help="Declare one Kimi native effort label; repeat in catalog order",
    )
    parser.add_argument(
        "--reasoning-level",
        type=int,
        help="Set the manager launch profile's reasoning preset index. Hermes level 5 selects xhigh.",
    )
    parser.add_argument("--mode", choices=RUN_MODES, help="Houmao run mode for the selected client")
    parser.add_argument(
        "--prompt-mode",
        choices=("unattended", "as_is"),
        default="unattended",
        help="Managed operator prompt mode stored on the fixture-agent specialist",
    )
    parser.add_argument(
        "--surface",
        choices=("raw", "manager", "passive-server"),
        default="manager",
        help="Choose native raw, Houmao-managed project, or passive-server preparation",
    )
    parser.add_argument(
        "--no-system-skills",
        action="store_true",
        help="Disable the managed agent system-skill pack (manager surface only)",
    )
    pool_selection = parser.add_mutually_exclusive_group()
    pool_selection.add_argument("--pool-key", help="Select a named entry from the model pool")
    pool_selection.add_argument(
        "--pool-slot", help="Resolve a logical agent slot through HOUMAO_TEST_MODEL variables"
    )
    parser.add_argument(
        "--model-pool", type=Path, help="Override the external model-pool.toml path"
    )


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse utility commands without accepting resolved secrets as arguments."""

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_MANAGED_CONFIGURATION_GUIDE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    peer = commands.add_parser("chat-peer", help="Serve a controlled local Chat Completions peer")
    peer.add_argument("--state-dir", type=Path, required=True)
    retire_hermes = commands.add_parser(
        "retire-hermes-owner", help="Retire the exact test Hermes host after profile cleanup"
    )
    retire_hermes.add_argument("--hermes-owner-root", type=Path)
    discover = commands.add_parser("discover-auth", help="Read-only bounded native auth discovery")
    importer = commands.add_parser(
        "import-auth", help="Copy an explicitly selected native auth source"
    )
    for command in (discover, importer):
        command.add_argument("--client", choices=("claude", "codex", "kimi"), required=True)
        command.add_argument("--search-root", type=Path, action="append", default=[])
        command.add_argument("--no-defaults", action="store_true")
    importer.add_argument("--source", type=Path)
    importer.add_argument("--candidate")
    importer.add_argument("--name", required=True)
    importer.add_argument("--auth-root", type=Path)
    importer.add_argument("--replace", action="store_true")
    listing = commands.add_parser("list-models", help="List configured model-pool entries")
    listing.add_argument(
        "--model-pool", type=Path, help="Override the external model-pool.toml path"
    )
    check = commands.add_parser("check", help="Validate selected configuration or a prepared run")
    add_case_arguments(check)
    check.add_argument("--run-dir", type=Path)
    check.add_argument(
        "--live", action="store_true", help="Probe a selected pool endpoint or launched authority"
    )
    prepare = commands.add_parser(
        "prepare",
        help="Prepare private client/project inputs without launch",
        description=(
            "Prepare private client/project inputs without launch. For manager runs, "
            "apply Houmao source/profile changes before launch."
        ),
        epilog=_MANAGED_CONFIGURATION_GUIDE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_case_arguments(prepare)
    prepare.add_argument("--run-root", type=Path)
    prepare.add_argument("--seed-root", type=Path)
    prepare.add_argument(
        "--role",
        default="server-api-smoke",
        help="Select the fixture role for the agent definition",
    )
    prepare.add_argument(
        "--system-prompt-file",
        type=Path,
        help="Override the role prompt; manager preparation stores it on the specialist",
    )
    prepare.add_argument("--executable")
    prepare.add_argument(
        "--tmux-server",
        choices=("houmao-default", "new"),
        help=(
            "Use the shared Houmao or a private tmux server; manager preparation "
            "stores this on the fixture-agent project profile"
        ),
    )
    for name in ("launch", "prompt", "interrupt", "stop", "browser-connection"):
        command = commands.add_parser(name, help=f"{name.title()} one prepared external run")
        command.add_argument("--run-dir", type=Path, required=True)
        if name in {"launch", "prompt"}:
            command.add_argument("--prompt", required=name == "prompt")
            command.add_argument("--timeout", type=float, default=300)
        if name == "launch":
            command.add_argument("--passive-url")
    return parser.parse_args(argv)


def selected_pool_entry(args: argparse.Namespace) -> tuple[str, ModelPoolEntry] | None:
    """Select one pool entry and check its fixture surface and mode."""

    if args.pool_key is None and args.pool_slot is None:
        if args.model_pool is not None:
            raise FixtureError("--model-pool requires --pool-key or --pool-slot")
        return None
    conflicts = [
        "--" + field.replace("_", "-")
        for field in _POOL_ROUTING_FIELDS
        if getattr(args, field) is not None
    ]
    if conflicts:
        raise FixtureError("Pool selection conflicts with " + ", ".join(conflicts))
    pool = load_model_pool(args.model_pool)
    key = select_pool_key(pool, key=args.pool_key, slot=args.pool_slot)
    entry = pool.models[key]
    mode = fixture_run_mode(entry.client, args.mode, args.surface).mode
    if entry.supported_modes is not None and mode not in entry.supported_modes:
        raise FixtureError(
            f"Model pool key {key!r} does not support mode {mode!r}; "
            f"select one of: {', '.join(entry.supported_modes)}"
        )
    return key, entry


def list_models(path: Path | None) -> dict[str, object]:
    """List pool keys and manager-compatible modes without private inputs."""

    models = []
    for key, entry in sorted(load_model_pool(path).models.items()):
        supported = []
        for mode in RUN_MODES if entry.supported_modes is None else entry.supported_modes:
            try:
                fixture_run_mode(entry.client, mode, "manager")
            except FixtureError:
                continue
            supported.append(mode)
        models.append(
            {
                "key": key,
                "client": entry.client,
                "case": entry.case,
                "auth_method": entry.auth_method or "api-key",
                "model": entry.model,
                "supported_modes": supported,
            }
        )
    return {"models": models}


def selected_configuration(
    args: argparse.Namespace, *, entry: ModelPoolEntry | None = None
) -> ResolvedConfig:
    """Resolve either an API case or a deliberately selected imported native bundle."""

    if entry is not None:
        values = entry.model_dump(exclude_unset=True)
        projected = {field: values[field] for field in _POOL_ROUTING_FIELDS if field in values}
        for field in ("dsh_reasoning", "dsh_compat"):
            if field in projected:
                projected[field] = json.dumps(projected[field])
        projected.pop("capabilities", None)
        projected["support_effort"] = values.get("support_efforts")
        if args.reasoning_level is None:
            projected["reasoning_level"] = entry.reasoning_level
        args = argparse.Namespace(**{**vars(args), **projected})
    if args.client is None:
        raise FixtureError("Select --client for configuration preparation")
    if args.no_system_skills and args.surface != "manager":
        raise FixtureError("--no-system-skills requires --surface manager")
    system_skill_policy: Literal["default", "none"] = "none" if args.no_system_skills else "default"
    if args.auth_method == "native-login":
        if args.client == "dsh":
            raise FixtureError("DSH fixtures support explicitly selected API credentials only")
        if args.client == "hermes":
            raise FixtureError("Hermes fixtures require explicitly selected API credentials")
        if args.case is not None or args.env_file is not None or args.base_url is not None:
            raise FixtureError("Native login selection is independent of API case/env routing")
        if not args.auth_bundle:
            raise FixtureError("Native login requires an explicit imported --auth-bundle")
        if args.support_effort is not None:
            raise FixtureError("--support-effort requires a selected Kimi API case")
        if args.reasoning_level is not None and args.reasoning_level < 0:
            raise FixtureError("--reasoning-level must be nonnegative")
        config = ResolvedConfig(
            client=args.client,
            mode=fixture_run_mode(args.client, args.mode, args.surface).mode,
            surface=args.surface,
            operator_prompt_mode=args.prompt_mode,
            system_skill_policy=system_skill_policy,
            auth_method="native-login",
            model=args.model,
            reasoning_level=args.reasoning_level,
            native_bundle=bundle_path(
                external_root("auth", override=args.auth_root), args.client, args.auth_bundle
            ),
        )
        if config.client == "kimi" and config.reasoning_level is not None:
            validate_native_bundle(config)
        validate_reasoning_level(config)
        return config
    if args.auth_bundle is not None:
        raise FixtureError("API cases do not consume a native auth bundle")
    return resolve_config(
        case=args.case,
        client=args.client,
        mode=args.mode,
        surface=args.surface,
        operator_prompt_mode=args.prompt_mode,
        system_skill_policy=system_skill_policy,
        model=args.model,
        base_url=args.base_url,
        env_file=args.env_file,
        process_env={} if entry is not None else None,
        descriptor_path=args.descriptor,
        context_window=args.context_window,
        max_output_tokens=args.max_output_tokens,
        dsh_reasoning=args.dsh_reasoning,
        dsh_compat=args.dsh_compat,
        dsh_protocol=args.dsh_protocol,
        capabilities=(
            entry.capabilities
            if entry is not None and "capabilities" in entry.model_fields_set
            else [item.strip() for item in args.capabilities.split(",")]
            if args.capabilities is not None
            else None
        ),
        reasoning_key=args.reasoning_key,
        reasoning_effort=args.reasoning_effort,
        support_efforts=args.support_effort,
        reasoning_level=args.reasoning_level,
    )


def main(argv: list[str] | None = None) -> int:
    """Run one utility command and report safe JSON results."""

    args = parse_arguments(argv)
    try:
        if args.command == "chat-peer":
            from fixturelib.chat_peer import serve_chat_peer

            serve_chat_peer(args.state_dir)
            return 0
        if args.command in {"discover-auth", "import-auth"}:
            if args.command == "import-auth" and args.source is not None:
                if args.candidate is not None:
                    raise FixtureError("Select either --source or --candidate")
                candidates = [candidate_from_source(args.client, args.source)]
            else:
                candidates = discover_auth(
                    args.client,
                    search_roots=args.search_root,
                    include_defaults=not args.no_defaults,
                )
            if args.command == "discover-auth":
                payload = {"candidates": [item.summary() for item in candidates]}
            else:
                selected = next(
                    (item for item in candidates if item.candidate_id == args.candidate), None
                )
                if args.source is not None:
                    selected = candidates[0]
                if selected is None:
                    print(
                        json.dumps(
                            {
                                "error": "Import requires explicit --source or a discovered --candidate",
                                "candidates": [item.summary() for item in candidates],
                            }
                        ),
                        file=sys.stderr,
                    )
                    return 2
                destination = import_auth(
                    selected, name=args.name, auth_root=args.auth_root, replace=args.replace
                )
                payload = {
                    "client": args.client,
                    "name": args.name,
                    "bundle_path": str(destination),
                }
        elif args.command == "list-models":
            payload = list_models(args.model_pool)
        elif args.command == "check" and args.run_dir is not None:
            if any(value is not None for value in (args.pool_key, args.pool_slot, args.model_pool)):
                raise FixtureError("--run-dir conflicts with model pool selection")
            if args.no_system_skills:
                raise FixtureError("Omit --run-dir to select --no-system-skills")
            if args.hermes_owner_root is not None:
                raise FixtureError("Prepared runs use their captured Hermes test owner")
            payload = check_run(args.run_dir, live=args.live)
        elif args.command == "retire-hermes-owner":
            payload = retire_owner(selected_owner_root(args.hermes_owner_root))
        elif args.command == "launch":
            payload = launch_run(
                args.run_dir, prompt=args.prompt, passive_url=args.passive_url, timeout=args.timeout
            )
        elif args.command == "prompt":
            payload = prompt_run(args.run_dir, prompt=args.prompt, timeout=args.timeout)
        elif args.command == "stop":
            payload = stop_run(args.run_dir)
        elif args.command == "interrupt":
            payload = interrupt_run(args.run_dir)
        elif args.command == "browser-connection":
            from fixturelib.web import browser_connection_file

            run = load_run(args.run_dir)
            connection = browser_connection_file(run)
            payload = {"connection_file": str(connection), "identity": run["identity"]}
        else:
            selection = selected_pool_entry(args)
            pool_key, entry = selection if selection is not None else (None, None)
            config = selected_configuration(args, entry=entry)
            if args.hermes_owner_root is not None and (config.client, config.surface) != (
                "hermes",
                "manager",
            ):
                raise FixtureError("--hermes-owner-root requires a managed Hermes fixture")
            if args.command == "prepare":
                run = prepare_run(
                    config,
                    run_root=args.run_root,
                    seed_root=args.seed_root,
                    role=args.role,
                    prompt_file=args.system_prompt_file,
                    executable=args.executable
                    if args.executable is not None
                    else (entry.executable if entry is not None else None),
                    tmux_server=args.tmux_server,
                    pool_key=pool_key,
                    pool_slot=args.pool_slot,
                    hermes_owner_root=args.hermes_owner_root,
                )
                payload = public_run(run)
            else:
                payload = {
                    "status": "configuration_valid",
                    "configuration": config.summary(),
                    "backend": config.selection().backend,
                }
                if pool_key is not None:
                    payload["pool_key"] = pool_key
                if args.pool_slot is not None:
                    payload["pool_slot"] = args.pool_slot
                if args.live:
                    if entry is None:
                        raise FixtureError("Live check requires --run-dir or model pool selection")
                    if config.client == "hermes" and config.surface == "manager":
                        prepared = qualify_owner(selected_owner_root(args.hermes_owner_root))
                        payload["hermes_owner_root"] = str(prepared.root)
                        payload["client_version"] = prepared.evidence.version
                    payload["live"] = probe_configuration(config)
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0
    except (FixtureError, OSError, TmuxCommandError) as exc:
        message = (
            str(exc) if isinstance(exc, FixtureError) else "Fixture filesystem operation failed"
        )
        diagnostic = exc.diagnostic_reference() if isinstance(exc, ManagedCommandError) else {}
        print(json.dumps({"error": message, **diagnostic}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
