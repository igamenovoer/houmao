# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`Houmao` is a framework + CLI toolkit for building and running teams of loosely-coupled, CLI-based agents (codex, claude, gemini) as real tmux-backed processes — not in-process object graphs.

## Development Commands

```bash
pixi install && pixi shell   # install deps and enter dev shell

pixi run format              # ruff format src tests docs scripts
pixi run lint                # ruff check
pixi run typecheck           # mypy src (strict mode)
pixi run test                # unit tests (tests/unit)
pixi run test-runtime        # runtime-focused suites (tests/unit/agents + tests/unit/cao)
pixi run build-dist          # build wheel + sdist → dist/
pixi run check-dist          # validate package metadata with twine
```

Run a single test file or function:

```bash
python -m pytest tests/unit/agents/test_brain_builder.py
python -m pytest tests/unit/agents/test_brain_builder.py::test_name -v
```

## Architecture

### Two-Phase Lifecycle

1. **Build phase** (`build-brain`): A `BrainRecipe` (tool + skills + config/credential profiles) is resolved against an **agent definition directory** via a `ToolAdapter`. The `BrainBuilder` materializes a **runtime home** on disk with projected configs, skills, and credentials, then emits a `BrainManifest`.

2. **Run phase** (`start-session` / `send-prompt` / `stop-session`): The session driver takes the manifest + a role (system prompt package), builds a `LaunchPlan`, and dispatches to the chosen backend.

### Source Layout

- `src/houmao/agents/brain_builder.py` — Build phase: `BuildRequest` → `BuildResult` (home + manifest)
- `src/houmao/agents/realm_controller/` — Run phase: `LaunchPlan`, `RuntimeSessionController`, backends
- `src/houmao/agents/realm_controller/backends/` — Per-tool/backend implementations
- `src/houmao/cao/` — CAO REST client, server launcher, no-proxy helpers
- `src/houmao/cli.py` — `houmao-cli` entrypoint (delegates to `realm_controller.cli`)
- `src/houmao/cao_cli.py` — `houmao-cao-server` entrypoint

### Backend Model

All backends implement a common `InteractiveSession` protocol (see `models.py`). Current backends:

- `codex_headless` / `codex_app_server` — OpenAI Codex CLI
- `claude_headless` — Anthropic Claude Code CLI
- `gemini_headless` — Google Gemini CLI
- `cao_rest` — delegates to an external CAO (CLI Agent Orchestrator) server
- `tmux_runtime` — shared tmux primitives used by local backends

The `BackendKind` literal type in `models.py` is the canonical list. New backends must be added there and wired through `launch_plan.py`.

### Agent Definition Directory

Default location: `.agentsys/agents/` (override with `AGENTSYS_AGENT_DEF_DIR`). Template to copy: `tests/fixtures/agents/`.

```
brains/
  tool-adapters/<tool>.yaml      # per-tool build & launch contract (REQUIRED)
  skills/<name>/SKILL.md         # reusable capability modules (REQUIRED per recipe)
  cli-configs/<tool>/<profile>/  # secret-free tool config files (REQUIRED per recipe)
  api-creds/<tool>/<profile>/    # local-only credentials — gitignored (REQUIRED per recipe)
  brain-recipes/<tool>/*.yaml    # declarative presets: tool + skills + profiles (recommended)
roles/<role>/system-prompt.md    # role prompt packages (REQUIRED)
blueprints/*.yaml                # recipe+role bindings (recommended)
```

## Key Conventions

- **Python ≥ 3.11**, type hints on all public APIs, `mypy --strict`.
- **Pydantic v2** for validated models; `@dataclass(frozen=True)` for internal value objects.
- **Ruff** for formatting and linting (line length 100). Run `pixi run format && pixi run lint` before committing.
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:` prefixes.
- Credential files (`api-creds/`, `*.env`, `auth.json`, `credentials.json`) must never be committed — excluded in `pyproject.toml` and `.gitignore`.
- Tests: `tests/unit/**/test_*.py`, `tests/integration/**/test_*.py`, `tests/manual/manual_*.py`.

## Supporting Directories

- `openspec/` — spec-driven change tracking (proposals, designs, tasks)
- `context/` and `magic-context/` — agent context packages (roles, skills, instructions)
- `scripts/` — automation helpers and demo scripts
- `config/` — project configuration assets (e.g., CAO server launcher config)
- `tmp/` — generated runtime homes and artifacts (safe to delete/rebuild; gitignored)
