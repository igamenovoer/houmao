# Repository Guidelines

## Project Structure & Module Organization
Core runtime code lives in `src/houmao/` (CLI entrypoints, launch/runtime logic, and CAO integration). Tests are under `tests/` and split by intent:
- `tests/unit/` for fast hermetic tests
- `tests/integration/` for multi-component or external dependency tests
- `tests/manual/` for non-CI manual scripts

Supporting material is organized as: `docs/` (reference and migration docs), `scripts/` (automation and helper CLIs), `openspec/` (spec-driven change artifacts), and `config/` (project configuration assets).
External code lives under `extern/`: use `extern/tracked/` for tracked dependencies and `extern/orphan/` for local reference-only checkouts. The RxPY source reference cloned for this workspace is at `extern/orphan/RxPY/`.
When a task involves a library, tool, or integration that has a source reference under `extern/orphan/`, inspect that local source checkout first and use it as the primary reference for behavior, APIs, config, and implementation details. Only fall back to online documentation or web search after checking the in-repo source, or when you need newer upstream context that is not present in the local checkout. Current examples under `extern/orphan/` include `RxPY`, `filestash`, `codex`, `asciinema`, `cypht`, and `stalwart`.

## Build, Test, and Development Commands
Use Pixi as the default workflow:
- `pixi install && pixi shell` installs dependencies and opens the dev shell.
- When invoking Python or Python-based tools, prefer `pixi run ...` so commands execute in the managed environment; do not rely on `pixi shell`, `python`, or other system-level interpreters being active.
- `pixi run format` runs `ruff format` on `src tests docs scripts`.
- `pixi run lint` runs Ruff static checks.
- `pixi run typecheck` runs strict `mypy` on `src`.
- `pixi run test` runs unit tests (`tests/unit`).
- `pixi run test-runtime` runs runtime-focused suites.
- `pixi run build-dist` builds wheel + sdist to `dist/`.
- `pixi run check-dist` validates package metadata with Twine.

## Development Status
This system is under active and unstable development. When designing new features or refactoring existing behavior, prioritize clarity and forward progress over backward compatibility.

Breaking changes are allowed. Do not spend effort preserving legacy interfaces, call patterns, or stored data formats unless the user explicitly asks for compatibility or migration support.

If a design or refactoring change breaks functionality in this repository, identify the breakage clearly and propose a direct fix in the updated design or implementation plan. Prefer repairing the repository around the new design over adding backward-compatibility shims.

## Coding Style & Naming Conventions
Target Python 3.11+ with 4-space indentation and type hints for public logic. Ruff enforces formatting/linting (line length 100), and mypy runs in `strict = true` mode. Use `snake_case` for modules/functions/variables, `PascalCase` for classes, and keep CLI-facing names explicit (for example, `houmao_cli`-style semantics in scripts and commands).

For Markdown documentation, do not hard-wrap lines purely for width; keep paragraphs as natural long lines and only add line breaks for semantic structure (headings, lists, tables, quotes, or code blocks).
For UML-style diagrams in Markdown, prefer Mermaid fenced code blocks that render inline; avoid plain-text ASCII art and PlantUML unless the user explicitly requests a different format.

### Python Style (magic-context)
Follow [`magic-context/instructions/python-coding-guide.md`](magic-context/instructions/python-coding-guide.md) for Python implementation details:
- Run Python entrypoints, scripts, and tooling via `pixi run` rather than the system `python` executable.
- Prefer absolute imports; group imports as standard library, third-party, then local modules.
- Use NumPy-style docstrings for modules, classes, and functions; private helpers (`_name`) still require a brief docstring.
- Add module-level docstrings for non-trivial modules.
- For stateful service/helper/controller classes, prefix instance members with `m_`, declare them in `__init__`, and type them explicitly.
- Do not use `m_` on `pydantic` or `attrs` data model fields.
- Expose read-only data via `@property`; use explicit `set_xxx()` methods for mutation with validation.
- Prefer zero-arg constructors plus `@classmethod` factories like `from_config()` or `from_file()` for complex initialization.

## Testing Guidelines
Framework: `pytest` (with some `unittest` compatibility). Follow file naming from `tests/README.md`:
- `tests/unit/**/test_*.py`
- `tests/integration/**/test_*.py`
- `tests/manual/manual_*.py`

Keep unit tests deterministic and isolated; prefer fixtures over network access. Run `pixi run test` before opening a PR, and add integration coverage when behavior spans subprocesses, tmux, or CAO paths.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit-style prefixes (`feat:`, `fix:`, `docs:`, `chore:`). Keep commits focused and imperative, e.g. `feat: add runtime health-check retry backoff`.

PRs should include:
- concise problem/solution summary
- linked issue/spec (for behavior changes)
- test evidence (commands run + results)
- docs updates when CLI behavior or workflows change
