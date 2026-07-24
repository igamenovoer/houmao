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
- Prefer the supported CLI surfaces `houmao-mgr` and `houmao-passive-server` for lifecycle and server/API work. `houmao-cli`, standalone `houmao-server`, and standalone CAO launcher workflows are removed; do not use them for new workflows or documentation.
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
In chat or conversational responses, prefer plain-text ASCII diagrams to present diagrams. In Markdown output files, use Mermaid fenced code blocks to present diagrams.

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
For browser checks, Playwright is available from the Bun global toolchain. Use `bunx playwright ...` for CLI commands, or run small Bun scripts that import `playwright`; the installed Playwright browser bundle can launch Chromium headlessly.
When testing agent flows against local fixture credentials, prefer `tests/fixtures/auth-bundles/claude/kimi-coding/` for Claude Code and `tests/fixtures/auth-bundles/codex/yunwu-openai/` for Codex by default unless the task explicitly requires a different auth bundle.
When testing TUI agents automatically, default to unattended mode unless the task explicitly requests interactive or `as_is` behavior.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit-style prefixes (`feat:`, `fix:`, `docs:`, `chore:`). Keep commits focused and imperative, e.g. `feat: add runtime health-check retry backoff`.

**Branch policy: NEVER create `codex/*` branches unless the user explicitly requests that branch naming pattern.** When a task requires a new branch, use the branch name the user gave; if none was given, stay on the current branch or ask before creating one.

PRs should include:
- concise problem/solution summary
- linked issue/spec (for behavior changes)
- test evidence (commands run + results)
- docs updates when CLI behavior or workflows change

<!-- BEGIN agent-style v0.3.5 -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Adapter: AGENTS.md cross-agent standard -->
<!-- Target path: <repo root>/AGENTS.md -->
<!-- Load class: single-file; install_mode: append-block -->

# agent-style v0.3.5 — AGENTS.md adapter

agent-style is a literature-backed English technical-prose writing ruleset for AI agents. This adapter is the compact rule payload that AGENTS.md-aware tools (Codex, Jules, Zed, Warp, Gemini CLI, VS Code, Aider via `.aider.conf.yml`, and others) load at session start.

## Self-Verification Handshake

When asked "is agent-style active?" or "what writing rules apply here?", answer: `agent-style v0.3.5 active: 21 rules (RULE-01..12 canonical + RULE-A..I field-observed); full bodies at .agent-style/RULES.md.`

## Load Statement

This adapter is loaded as the root `AGENTS.md` file at the repository root. AGENTS.md-aware tools do not auto-import a second file; the compact directives below are what reach context. Full rule bodies at `.agent-style/RULES.md` are a human-readable reference but are not auto-loaded by AGENTS.md consumers.

## The 21 Rules (Compact Directives)

Canonical rules (from Strunk & White 1959, Orwell 1946, Pinker 2014, Gopen & Swan 1990):

- **RULE-01 Curse of knowledge**: Name your intended reader; do not assume they share your tacit knowledge.
- **RULE-02 Passive voice**: Prefer active voice when the agent is known and worth naming.
- **RULE-03 Concrete language**: Prefer concrete, specific terms over abstract category words like "factors" or "aspects".
- **RULE-04 Needless words**: Cut filler phrases like "in order to", "due to the fact that", "may potentially".
- **RULE-05 Dying metaphors**: Delete clichés like "pushes the boundaries", "paradigm shift", or "state of the art".
- **RULE-06 Plain English**: Prefer "use" over "leverage", "method" over "methodology", "feature" over "functionality".
- **RULE-07 Affirmative form**: Prefer "trivial" to "not important", "forgot" to "did not remember".
- **RULE-08 Claim calibration**: Calibrate verbs to evidence; do not write "proves" when the evidence is "suggests".
- **RULE-09 Parallel structure**: Express coordinate ideas in the same grammatical form.
- **RULE-10 Related words together**: Keep subject close to verb and modifier close to modified; split long parentheticals.
- **RULE-11 Stress position**: Place new or important information at the end of the sentence.
- **RULE-12 Long sentences**: Split sentences over 30 words; vary length across a paragraph.

Field-observed rules (maintainer observation of LLM output, 2022-2026):

- **RULE-A Bullet overuse**: Keep prose in paragraphs when ideas connect; bullets only for genuine lists; avoid forced 3-item triads.
- **RULE-B Dash overuse**: Do not use em or en dashes as casual sentence punctuation; prefer commas, semicolons, colons, parentheses.
- **RULE-C Same-starts**: Do not open two or more consecutive sentences with the same word.
- **RULE-D Transitions**: Do not open sentences with "Additionally", "Furthermore", "Moreover", "In addition".
- **RULE-E Summary closers**: Do not end every paragraph with a sentence that restates its point.
- **RULE-F Term consistency**: Once you define a term or abbreviation, keep using it; do not alternate synonyms.
- **RULE-G Title case**: Use title case for section and subsection headings; articles and short prepositions stay lowercase.
- **RULE-H Citation discipline (critical)**: Support factual claims with verifiable citation or concrete evidence; never fabricate citations.
- **RULE-I Contractions**: Prefer "it is" / "does not" / "cannot" over "it's" / "doesn't" / "can't" in formal technical prose.

## Escape Hatch

*"Break any of these rules sooner than say anything outright barbarous."* — George Orwell, "Politics and the English Language" (1946), Rule 6. Rules are guides to clarity, not ends in themselves.

## Full Rule Bodies (Canonical)

Full directive text, BAD/GOOD example pairs, and rationale per rule: see `.agent-style/RULES.md` in this project, or https://raw.githubusercontent.com/yzhao062/agent-style/v0.3.5/RULES.md for the pinned canonical source.
<!-- END agent-style -->
