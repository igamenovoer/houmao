# Copilot Instructions for houmao

## Build, Test, and Lint

This project uses [Pixi](https://pixi.sh) as its task runner. Enter the dev shell first:

```bash
pixi install && pixi shell
```

Common commands:

```bash
pixi run format        # ruff format src tests docs scripts
pixi run lint          # ruff check
pixi run typecheck     # mypy src (strict mode)
pixi run test          # unit tests only (tests/unit)
pixi run test-runtime  # runtime-focused suites (tests/unit/agents + tests/unit/cao)
pixi run build-dist    # build wheel + sdist → dist/
pixi run check-dist    # validate package metadata with twine
```

Run a single test file or test function:

```bash
python -m pytest tests/unit/agents/test_brain_builder.py
python -m pytest tests/unit/agents/test_brain_builder.py::test_name -v
```

## Architecture

`Houmao` is a framework + CLI for building **teams of CLI-based agents** (codex, claude, gemini) that run as real tmux-backed processes.

### Two-phase lifecycle

1. **Build phase** (`build-brain`): A `BrainRecipe` (tool + skills + config/credential profiles) is resolved against an **agent definition directory** and a `ToolAdapter`. The `BrainBuilder` materializes a **runtime home** on disk — a self-contained directory with projected configs, skills, and credentials — and emits a `BrainManifest`.

2. **Run phase** (`start-session` / `send-prompt` / `stop-session`): The `SessionDriver` takes the manifest + a role (system prompt package) and launches the tool CLI via one of several backends. A `LaunchPlan` is built from the manifest + role injection strategy, then dispatched to the chosen backend.

### Backend model

All backends implement a common `InteractiveSession` protocol (`models.py`). Current backends in `src/houmao/agents/realm_controller/backends/`:

- `codex_headless` / `codex_app_server` — OpenAI Codex CLI (headless JSON‑stream or app-server HTTP)
- `claude_headless` — Anthropic Claude Code CLI
- `gemini_headless` — Google Gemini CLI
- `cao_rest` — delegates to an external CAO (CLI Agent Orchestrator) server
- `tmux_runtime` — shared tmux session/window primitives used by local backends

### Agent definition directory

The directory (default `.agentsys/agents/`, overridable via `AGENTSYS_AGENT_DEF_DIR`) holds all declarative inputs:

```
brains/
  tool-adapters/<tool>.yaml      # per-tool build & launch contract
  skills/<name>/SKILL.md         # reusable capability modules
  cli-configs/<tool>/<profile>/  # secret-free tool config files
  api-creds/<tool>/<profile>/    # local-only credentials (gitignored)
  brain-recipes/<tool>/*.yaml    # declarative presets (tool + skills + profiles)
roles/<role>/system-prompt.md    # role prompt packages
blueprints/*.yaml                # optional recipe+role bindings
```

### CLI entry points

- `houmao-cli` → `src/houmao/cli.py` → delegates to `agents.realm_controller.cli`
- `houmao-cao-server` → `src/houmao/cao_cli.py` → CAO server lifecycle management

### Supporting directories

- `openspec/` — spec-driven change tracking (proposals, designs, tasks)
- `context/` and `magic-context/` — agent context packages (roles, skills, instructions, knowledge bases)
- `scripts/` — automation helpers and demo scripts

## Key Conventions

- **Python ≥ 3.11**, type hints on all public APIs, `mypy --strict`.
- **Ruff** for formatting and linting (line length 100). Run `pixi run format && pixi run lint` before committing.
- **Pydantic v2** for validated models; plain `@dataclass(frozen=True)` for internal value objects.
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:` prefixes.
- Test files follow `tests/unit/**/test_*.py` and `tests/integration/**/test_*.py`. Manual scripts use `tests/manual/manual_*.py`.
- Credential files (`api-creds/`, `*.env`, `auth.json`, `credentials.json`) must never be committed — they are excluded in `pyproject.toml` build config and `.gitignore`.
- The `BackendKind` literal type in `models.py` is the canonical list of supported launch backends. New backends must be added there and wired through `launch_plan.py`.
