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
pixi run lint                # ruff check src tests docs scripts
pixi run typecheck           # mypy src (strict mode)
pixi run test                # unit tests (tests/unit)
pixi run test-runtime        # runtime-focused suites (tests/unit/agents + tests/unit/cao)
pixi run build-dist          # build wheel + sdist → dist/
pixi run check-dist          # validate package metadata with twine
pixi run docs-build          # mkdocs build --strict
pixi run docs-serve          # mkdocs serve on 127.0.0.1:8000
pixi run install-global-tool # install this checkout as a global editable uv tool
```

Run a single test file or function through Pixi:

```bash
pixi run python -m pytest tests/unit/agents/test_brain_builder.py
pixi run python -m pytest tests/unit/agents/test_brain_builder.py::test_name -v
```

Supported CLI entrypoints are `houmao-mgr` (lifecycle, agents, server control) and `houmao-passive-server` (stateless registry-driven server). Legacy `houmao-cli` and the standalone `houmao-server` launcher have been removed; do not re-introduce them in code or docs.

Optional Pixi environments: `pg-hosting` (local Postgres + pgvector under `tmp/pg-hosting/`, tasks `pg-init`/`pg-start`/`pg-stop`/...) and `gui` (Go + tmux + `webtmux-build`/`webtmux-run`). Activate with `pixi run -e <env> <task>`.

## Architecture

### Two-Phase Lifecycle

1. **Build phase** (`brains build`): A **recipe** (role + tool + skills + setup/auth bundles) is resolved against an **agent definition directory** via a `ToolAdapter`, optionally composed with a **launch profile** that carries reusable birth-time defaults (managed-agent identity, workdir, auth override, prompt mode, durable env records, mailbox config, gateway posture, managed-header policy). The `BrainBuilder` materializes a **runtime home** on disk with projected configs, skills, and credentials, then emits a `BrainManifest` that records the resolved recipe plus any launch-profile provenance.

2. **Run phase** (`agents launch` / `agents prompt` / `agents stop`): The session driver takes the manifest + a role package, composes a `LaunchPlan` via `build_launch_plan()`, and dispatches to the chosen backend through `RuntimeSessionController`.

### Source Layout

- `src/houmao/agents/brain_builder.py` — Build phase: `BuildRequest` → `BuildResult` (home + manifest)
- `src/houmao/agents/realm_controller/` — Run phase: `LaunchPlan`, `RuntimeSessionController`, backends
- `src/houmao/agents/realm_controller/backends/` — Per-tool/backend implementations
- `src/houmao/project/` — Project overlay: catalog, easy specialists/profiles, launch profiles, and `.houmao/` resolution helpers
- `src/houmao/server/` — Internal modules retained from the retired standalone server surface (REST app, client, managed-agent supervision, TUI tracking, `/houmao/*` routes); imported by `houmao-mgr` rather than launched directly
- `src/houmao/passive_server/` — Registry-driven stateless `houmao-passive-server` (no CAO compatibility layer, no child process supervision); CLI entrypoint at `passive_server/cli.py`
- `src/houmao/mailbox/` — Unified mailbox subsystem: filesystem + Stalwart JMAP transports, managed helpers, operator-origin send
- `src/houmao/lifecycle/` — Shared ReactiveX readiness / anchored-completion timing kernel reused by the runtime and server modules
- `src/houmao/terminal_record/` — Tmux session recording service and replay models
- `src/houmao/shared_tui_tracking/` — Shared TUI state tracker, detectors, and reducer used by runtime and server watch-planes
- `src/houmao/srv_ctrl/cli.py` — `houmao-mgr` entrypoint; subcommands live under `srv_ctrl/commands/` (agents, brains, mailbox, project, managed_agents, native_agent, ...)
- `src/houmao/cao/` — Retained CAO REST client used only by the deprecated `cao_rest` backend escape hatch

### Backend Model

All backends implement a common `InteractiveSession` protocol (see `models.py`). Current backends:

- `codex_headless` / `codex_app_server` — OpenAI Codex CLI
- `claude_headless` — Anthropic Claude Code CLI
- `gemini_headless` — Google Gemini CLI
- `cao_rest` — delegates to an external CAO (CLI Agent Orchestrator) server
- `tmux_runtime` — shared tmux primitives used by local backends

The `BackendKind` literal type in `models.py` is the canonical list. New backends must be added there and wired through `launch_plan.py`.

### Agent Definition Directory

Default location: `.houmao/agents/` (override with `HOUMAO_AGENT_DEF_DIR`). Template to copy: `tests/fixtures/plain-agent-def/`.

```
tools/
  <tool>/
    adapter.yaml                   # per-tool build & launch contract (REQUIRED)
    setups/<setup>/                # secret-free tool config files (REQUIRED per preset)
    auth/<auth>/                   # local-only credentials — gitignored (REQUIRED per preset)
roles/
  <role>/
    system-prompt.md               # role prompt packages (REQUIRED)
    presets/<tool>/<setup>.yaml    # path-derived presets: skills + auth + launch (recommended)
skills/
  <name>/SKILL.md                  # reusable capability modules (REQUIRED per preset)
```

## Key Conventions

- **Python ≥ 3.11**, type hints on all public APIs, `mypy --strict`.
- **Pydantic v2** for validated models; `@dataclass(frozen=True)` for internal value objects.
- **Ruff** for formatting and linting (line length 100). Run `pixi run format && pixi run lint` before committing.
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:` prefixes. Keep commits focused and imperative.
- Credential files (`auth/`, `*.env`, `auth.json`, `credentials.json`) must never be committed — excluded in `pyproject.toml` and `.gitignore`.
- Tests: `tests/unit/**/test_*.py`, `tests/integration/**/test_*.py`, `tests/manual/manual_*.py`. Add integration coverage when behavior spans subprocesses, tmux, or CAO paths.
- When testing agent flows against fixture credentials, default to: Claude → `tests/fixtures/auth-bundles/claude/kimi-coding/`; Codex → `tests/fixtures/auth-bundles/codex/yunwu-openai/`; Gemini → `tests/fixtures/auth-bundles/gemini/personal-a-default/` (prefer OAuth over API-key mode). Override only when the task requires a different lane.
- For automated TUI agent tests, default to unattended mode unless the task explicitly needs interactive or `as_is` behavior.
- When a task touches a library/tool/integration that has a source checkout under `extern/orphan/` (e.g., RxPY, codex, filestash, asciinema, cypht, stalwart), inspect that local reference first; only fall back to web docs when the local checkout is missing or out of date.
- **Branch policy**: never create `codex/*` branches unless the user explicitly asks for that name. If a task needs a new branch, use the name the user gave; otherwise stay on the current branch or ask first.
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
- `config/` — legacy configuration assets retained for historical reference; not used by current Houmao workflows
- `tmp/` — generated runtime homes and artifacts (safe to delete/rebuild; gitignored)
