"""Prepare reproducible API/native-login test agents with private external state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Literal

from houmao.agents.realm_controller.run_modes import RUN_MODES

from fixturelib.auth import (
    bundle_path,
    candidate_from_source,
    discover_auth,
    external_root,
    import_auth,
)
from fixturelib.config import FixtureError, ResolvedConfig, fixture_run_mode, resolve_config
from fixturelib.prepare import load_run, prepare_run
from fixturelib.launch import check_run, interrupt_run, launch_run, prompt_run, public_run, stop_run


def add_case_arguments(parser: argparse.ArgumentParser) -> None:
    """Add explicit API case and client configuration selection."""

    parser.add_argument("--client", choices=("claude", "codex", "kimi", "dsh"))
    parser.add_argument("--case", choices=("self-hosted", "cloud-api"))
    parser.add_argument("--auth-method", choices=("api-key", "native-login"), default="api-key")
    parser.add_argument("--auth-bundle")
    parser.add_argument("--auth-root", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--descriptor", type=Path)
    parser.add_argument("--context-window", type=int)
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument(
        "--dsh-reasoning", help="DSH reasoning JSON: false or a native slot-to-wire mapping"
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
    parser.add_argument("--capabilities", help="Explicit comma-separated model capabilities")
    parser.add_argument("--reasoning-key")
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--mode", choices=RUN_MODES, help="Native run mode for the selected client")
    parser.add_argument("--prompt-mode", choices=("unattended", "as_is"), default="unattended")
    parser.add_argument(
        "--surface", choices=("raw", "manager", "passive-server"), default="manager"
    )
    parser.add_argument(
        "--no-system-skills",
        action="store_true",
        help="Disable the managed agent system-skill pack (manager surface only)",
    )


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse utility commands without accepting resolved secrets as arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
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
    check = commands.add_parser("check", help="Validate selected configuration offline")
    add_case_arguments(check)
    check.add_argument("--run-dir", type=Path)
    check.add_argument(
        "--live", action="store_true", help="Explicitly contact a prepared authority"
    )
    prepare = commands.add_parser(
        "prepare", help="Prepare private client/project inputs without launch"
    )
    add_case_arguments(prepare)
    prepare.add_argument("--run-root", type=Path)
    prepare.add_argument("--seed-root", type=Path)
    prepare.add_argument("--role", default="server-api-smoke")
    prepare.add_argument("--system-prompt-file", type=Path)
    prepare.add_argument("--executable")
    for name in ("launch", "prompt", "interrupt", "stop", "browser-connection"):
        command = commands.add_parser(name, help=f"{name.title()} one prepared external run")
        command.add_argument("--run-dir", type=Path, required=True)
        if name in {"launch", "prompt"}:
            command.add_argument("--prompt", required=name == "prompt")
            command.add_argument("--timeout", type=float, default=300)
        if name == "launch":
            command.add_argument("--passive-url")
    return parser.parse_args(argv)


def selected_configuration(args: argparse.Namespace) -> ResolvedConfig:
    """Resolve either an API case or a deliberately selected imported native bundle."""

    if args.client is None:
        raise FixtureError("Select --client for configuration preparation")
    if args.no_system_skills and args.surface != "manager":
        raise FixtureError("--no-system-skills requires --surface manager")
    system_skill_policy: Literal["default", "none"] = "none" if args.no_system_skills else "default"
    if args.auth_method == "native-login":
        if args.client == "dsh":
            raise FixtureError("DSH fixtures support explicitly selected API credentials only")
        if args.case is not None or args.env_file is not None or args.base_url is not None:
            raise FixtureError("Native login selection is independent of API case/env routing")
        if not args.auth_bundle:
            raise FixtureError("Native login requires an explicit imported --auth-bundle")
        return ResolvedConfig(
            client=args.client,
            mode=fixture_run_mode(args.client, args.mode, args.surface).mode,
            surface=args.surface,
            operator_prompt_mode=args.prompt_mode,
            system_skill_policy=system_skill_policy,
            auth_method="native-login",
            model=args.model,
            native_bundle=bundle_path(
                external_root("auth", override=args.auth_root), args.client, args.auth_bundle
            ),
        )
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
        descriptor_path=args.descriptor,
        context_window=args.context_window,
        max_output_tokens=args.max_output_tokens,
        dsh_reasoning=args.dsh_reasoning,
        dsh_compat=args.dsh_compat,
        dsh_protocol=args.dsh_protocol,
        capabilities=[item.strip() for item in args.capabilities.split(",")]
        if args.capabilities is not None
        else None,
        reasoning_key=args.reasoning_key,
        reasoning_effort=args.reasoning_effort,
    )


def main(argv: list[str] | None = None) -> int:
    """Run one utility command and report safe JSON results."""

    args = parse_arguments(argv)
    try:
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
        elif args.command == "check" and args.run_dir is not None:
            if args.no_system_skills:
                raise FixtureError("Omit --run-dir to select --no-system-skills")
            payload = check_run(args.run_dir, live=args.live)
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
            config = selected_configuration(args)
            if args.command == "prepare":
                run = prepare_run(
                    config,
                    run_root=args.run_root,
                    seed_root=args.seed_root,
                    role=args.role,
                    prompt_file=args.system_prompt_file,
                    executable=args.executable,
                )
                payload = public_run(run)
            else:
                if args.live:
                    raise FixtureError("Live check requires explicit --run-dir for a prepared run")
                payload = {
                    "status": "configuration_valid",
                    "configuration": config.summary(),
                    "backend": config.selection().backend,
                }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0
    except (FixtureError, OSError) as exc:
        message = (
            str(exc) if isinstance(exc, FixtureError) else "Fixture filesystem operation failed"
        )
        print(json.dumps({"error": message}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
