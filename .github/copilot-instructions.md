# Copilot Instructions for Houmao

## Build, test, and lint

Use Pixi as the default workflow. Run Python entrypoints, scripts, and tooling with `pixi run ...`; do not rely on a system `python` or an already-activated shell.

```bash
pixi install
pixi run format
pixi run lint
pixi run typecheck
pixi run test
pixi run test-runtime
pixi run build-dist
pixi run check-dist
```

Run a single test file or a single test with pytest directly through Pixi:

```bash
pixi run python -m pytest tests/unit/agents/test_brain_builder.py
pixi run python -m pytest tests/unit/agents/test_brain_builder.py::test_name -v
```

Prefer the supported CLI entrypoints `houmao-mgr` and `houmao-server`. `houmao-cli` and `houmao-cao-server` are deprecated compatibility surfaces and should not be used for new workflows or documentation.

## High-level architecture

Houmao orchestrates agents as real CLI processes (Claude, Codex, Gemini, and related tooling) that keep their own disk state, memory, and native TUI, usually inside tmux-backed sessions. The system is built around a two-phase lifecycle:

1. **Build phase**: `src/houmao/agents/brain_builder.py` resolves a preset/tool adapter plus setup, auth, skills, and launch defaults, materializes a runtime home, and emits a `BrainManifest`.
2. **Run phase**: `src/houmao/agents/realm_controller/launch_plan.py` and the `realm_controller` backends turn that manifest plus a role package into a `LaunchPlan`, then launch and control the session through the runtime controller.

Project-aware workflows are centered on the repo-local `.houmao/` overlay managed by `src/houmao/project/overlay.py`. After `houmao-mgr project init`, the overlay becomes the home for project-local agents, projected content, mailbox state, memory roots, runtime artifacts, and the project catalog.

Shared runtime subsystems are reused across both local runtime and server control planes:

- `src/houmao/mailbox/` handles filesystem and Stalwart-backed mailbox transports.
- `src/houmao/lifecycle/` contains the ReactiveX-based readiness and completion timing kernel.
- `src/houmao/shared_tui_tracking/` provides the shared TUI tracker, detectors, and reducer.
- `src/houmao/server/` contains the managed `houmao-server` REST service.
- `src/houmao/passive_server/` is a registry-driven stateless server variant without child-process supervision.

## Key conventions

This repository is under active, unstable development. Prefer direct fixes and forward progress over backward-compatibility shims unless compatibility or migration support is explicitly requested.

The default agent-definition root is `.houmao/agents/` (override with `HOUMAO_AGENT_DEF_DIR`). The important layout is:

- `tools/<tool>/setups/<setup>/` for secret-free tool configuration
- `tools/<tool>/auth/<auth>/` for local-only credentials
- `roles/<role>/system-prompt.md` for role packages
- `roles/<role>/presets/<tool>/<setup>.yaml` for path-derived presets
- `skills/<name>/SKILL.md` for reusable skill packages

For Python implementation details, follow the repo’s existing patterns instead of introducing new ones:

- Use absolute imports.
- Use NumPy-style docstrings for public modules, classes, and functions; private helpers still get short docstrings.
- In stateful service/helper/controller classes, declare and type instance members in `__init__` and prefix them with `m_`.
- Do not use `m_` on `pydantic` or `attrs` model fields.
- Prefer zero-argument constructors plus `@classmethod` factories such as `from_config()` or `from_file()` for complex initialization.

When a task involves a dependency or integration that has a source checkout under `extern/orphan/`, inspect that local reference first before falling back to web docs. Current local references include projects such as RxPY, codex, filestash, asciinema, cypht, and stalwart.

Keep credentials out of version control. Local-only material includes `auth/` bundles, `*.env`, `auth.json`, and `credentials.json`.

Test layout matters:

- `tests/unit/**/test_*.py` for fast hermetic tests
- `tests/integration/**/test_*.py` for multi-component or external-dependency coverage
- `tests/manual/manual_*.py` for manual scripts

When testing agent flows with fixture credentials, prefer these defaults unless the task requires another lane:

- Claude: `tests/fixtures/auth-bundles/claude/kimi-coding/`
- Codex: `tests/fixtures/auth-bundles/codex/yunwu-openai/`
- Gemini: `tests/fixtures/auth-bundles/gemini/personal-a-default/` and prefer OAuth over API-key mode

For automated TUI agent tests, default to unattended mode unless the task explicitly needs interactive or `as_is` behavior.

For Markdown docs, do not hard-wrap paragraphs for width. Prefer Mermaid fenced blocks for UML-style diagrams instead of ASCII art or PlantUML unless a task explicitly asks for something else.
