# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`Houmao` is a framework + CLI toolkit for building and running teams of loosely-coupled, CLI-based agents (codex, claude, gemini) as real tmux-backed processes — not in-process object graphs.

## Development Status

This system is under active and unstable development. Prioritize clarity and forward progress over backward compatibility.

Breaking changes are allowed. Do not spend effort preserving legacy interfaces, call patterns, or stored data formats unless the user explicitly asks for compatibility or migration support.

If a design or refactoring change breaks functionality, identify the breakage clearly and propose a direct fix in the updated design or implementation plan. Prefer repairing the repository around the new design over adding backward-compatibility shims.

## Development Commands

When invoking Python or Python-based tools, prefer `pixi run ...` so commands execute in the managed environment; do not rely on `pixi shell`, `python`, or other system-level interpreters being active.

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
- `src/houmao/srv_ctrl/cli.py` — `houmao-mgr` entrypoint for managed lifecycle, agent, and server control
- `src/houmao/server/cli.py` — `houmao-server` entrypoint
- `src/houmao/cli.py` and `src/houmao/cao_cli.py` — deprecated compatibility entrypoints; prefer `houmao-mgr` and `houmao-server`

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
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:` prefixes. Keep commits focused and imperative.
- Credential files (`api-creds/`, `*.env`, `auth.json`, `credentials.json`) must never be committed — excluded in `pyproject.toml` and `.gitignore`.
- Tests: `tests/unit/**/test_*.py`, `tests/integration/**/test_*.py`, `tests/manual/manual_*.py`. Add integration coverage when behavior spans subprocesses, tmux, or CAO paths.
- PRs should include: concise problem/solution summary, linked issue/spec (for behavior changes), test evidence (commands run + results), docs updates when CLI behavior or workflows change.

### Python Style

Follow [`magic-context/instructions/python-coding-guide.md`](magic-context/instructions/python-coding-guide.md) for Python implementation details:

- Prefer absolute imports; group imports as standard library, third-party, then local modules.
- Use NumPy-style docstrings for modules, classes, and functions; private helpers (`_name`) still require a brief docstring.
- Add module-level docstrings for non-trivial modules.
- For stateful service/helper/controller classes, prefix instance members with `m_`, declare them in `__init__`, and type them explicitly.
- Do not use `m_` on `pydantic` or `attrs` data model fields.
- Expose read-only data via `@property`; use explicit `set_xxx()` methods for mutation with validation.
- Prefer zero-arg constructors plus `@classmethod` factories like `from_config()` or `from_file()` for complex initialization.

### Markdown Style

Do not hard-wrap lines purely for width; keep paragraphs as natural long lines and only add line breaks for semantic structure (headings, lists, tables, quotes, or code blocks).
For UML-style diagrams in Markdown, prefer Mermaid fenced code blocks that render inline; avoid plain-text ASCII art and PlantUML unless the user explicitly requests a different format.

## Supporting Directories

- `openspec/` — spec-driven change tracking (proposals, designs, tasks)
- `context/` and `magic-context/` — agent context packages (roles, skills, instructions)
- `scripts/` — automation helpers and demo scripts
- `config/` — project configuration assets (e.g., CAO server launcher config)
- `tmp/` — generated runtime homes and artifacts (safe to delete/rebuild; gitignored)
