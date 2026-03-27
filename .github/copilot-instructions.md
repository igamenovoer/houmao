# Copilot Instructions for houmao

## Build, test, and lint

Use Pixi as the default workflow. Even for one-off Python or pytest commands, prefer `pixi run ...` instead of relying on an activated shell or the system interpreter.

```bash
pixi install && pixi shell

pixi run format        # ruff format src tests docs scripts
pixi run lint          # ruff check src tests docs scripts
pixi run typecheck     # mypy src (strict mode)
pixi run test          # tests/unit
pixi run test-runtime  # tests/unit/agents + tests/unit/cao
pixi run build-dist    # build wheel + sdist into dist/
pixi run check-dist    # twine check dist/*
```

Run a single test file or function with Pixi as well:

```bash
pixi run python -m pytest tests/unit/agents/test_brain_builder.py
pixi run python -m pytest tests/unit/agents/test_brain_builder.py::test_name -v
```

## High-level architecture

`Houmao` is a framework and CLI toolkit for orchestrating teams of CLI-based agents as real tmux-backed processes, not in-process agent objects.

### Two-phase lifecycle

1. **Build phase** (`build-brain`): `src/houmao/agents/brain_builder.py` resolves a recipe or explicit `{tool, skills, config_profile, credential_profile}` request against an agent definition directory. It projects secret-free config, selected skills, and local credentials into a disposable runtime home and emits a secret-free brain manifest plus launch helper.
2. **Run phase** (`start-session` / `send-prompt` / `stop-session`): `houmao.agents.realm_controller` combines the built manifest with a role package, turns that into a backend-specific `LaunchPlan`, and launches or resumes the live session.

### Agent definition model

The canonical inputs live in an agent definition directory (default `.agentsys/agents`, override with `AGENTSYS_AGENT_DEF_DIR`). The best in-repo template/reference is `tests/fixtures/agents/`.

Committed inputs are split by responsibility:

- `brains/tool-adapters/` for per-tool build and launch contracts
- `brains/skills/` for reusable capability packages
- `brains/cli-configs/` for secret-free tool config profiles
- `brains/brain-recipes/` for declarative presets
- `roles/<role>/system-prompt.md` for role packages
- `blueprints/` for optional recipe + role bindings

Local-only credentials live under `brains/api-creds/<tool>/<profile>/` and must stay uncommitted.

### Runtime control surfaces

- `houmao-cli` is only a thin entrypoint to `houmao.agents.realm_controller.cli`.
- `houmao-cao-server` manages local CAO server lifecycle.
- `houmao-server` and `houmao-mgr` are the newer paired server/manager surface. `src/houmao/agents/realm_controller/cli.py` already marks standalone operator use of `backend='cao_rest'` as retired in favor of that pair.

### Where the cross-cutting runtime logic lives

- `src/houmao/agents/brain_builder.py` owns build-time projection of configs, skills, credentials, manifest writing, and launch helper generation.
- `src/houmao/agents/realm_controller/launch_plan.py` is the bridge between build-time and run-time. It resolves allowlisted env vars, launch overrides, mailbox bindings, launch policy, and backend-specific role injection.
- `src/houmao/agents/realm_controller/models.py` defines the canonical backend and session contracts. The current `BackendKind` list is `codex_headless`, `codex_app_server`, `claude_headless`, `gemini_headless`, `cao_rest`, and `houmao_server_rest`.
- Gateway attach/detach, mailbox-enabled sessions, and the shared agent registry are runtime-owned layers on top of the same session model rather than separate one-off tools.

### Backend behavior that matters when editing runtime code

Role injection is backend-specific in `launch_plan.py`:

- Codex backends use native developer instructions.
- Claude headless uses native appended system prompt plus a bootstrap message.
- Gemini headless uses a bootstrap message.
- CAO-backed and Houmao-server-backed sessions use a profile-based role injection path.

For concrete end-to-end workflows, the most useful examples live under `scripts/demo/`. The current README-recommended proof of concept is `scripts/demo/mail-ping-pong-gateway-demo-pack/`.

## Key conventions

- Prefer `pixi run ...` for Python entrypoints, scripts, and tests, even when a plain `python -m ...` command would work.
- This repository is intentionally breaking-change friendly. Unless a task explicitly asks for compatibility, prefer repairing callers around the new design instead of adding backward-compatibility shims.
- Keep the secret-free and local-only split intact: config profiles, skills, recipes, roles, and blueprints are repository assets; credential profiles under `brains/api-creds/` are local-only. Generated manifests intentionally persist env var names and local paths, not secret values.
- For stateful service, helper, and controller classes, prefix instance members with `m_` and declare them in `__init__`. Do not use `m_` on `pydantic` or `attrs` model fields.
- Follow the repo Python style from `magic-context/instructions/python-coding-guide.md`: absolute imports, NumPy-style docstrings, module docstrings for non-trivial modules, and explicit `set_xxx()` mutators for validated state changes.
- `BackendKind` in `src/houmao/agents/realm_controller/models.py` is the authoritative backend list. Adding a backend requires wiring `launch_plan.py` and the related runtime/control surfaces, not just dropping in a backend implementation.
- Launch overrides are intentionally limited: recipes and direct builds can request secret-free `launch_overrides`, but protocol-required args such as `claude -p`, `gemini -p`, `codex exec --json`, `resume`, and `app-server` stay backend-owned.
- Unattended startup is a versioned launch policy resolved at launch time against the installed CLI version; unsupported versions fail closed instead of guessing a bootstrap strategy.
- Tests are organized by intent: `tests/unit/` for hermetic tests, `tests/integration/` for multi-component or external-service coverage, and `tests/manual/` for scripts that are not CI-collected. The runtime-focused unit suites live in `tests/unit/agents/` and `tests/unit/cao/`.
- When work touches a third-party integration that has a local source checkout under `extern/orphan/`, inspect that checkout first before falling back to external docs.
- Markdown docs in this repository should not be hard-wrapped for width. Use Mermaid when a diagram is needed unless the task explicitly asks for another format.
