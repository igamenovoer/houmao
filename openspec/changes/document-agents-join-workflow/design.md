## Context

The `houmao-mgr agents join` command is already fully implemented and tested (`src/houmao/srv_ctrl/commands/agents/core.py:226-330`, `src/houmao/srv_ctrl/commands/runtime_artifacts.py:101-275`, unit tests in `tests/unit/srv_ctrl/commands/test_runtime_artifacts_join.py`). Detailed operator documentation exists in `docs/reference/houmao_server_pair.md` (lines 118-176) and `docs/reference/cli/houmao-mgr.md`.

However, the project `README.md` — the first thing new users read — never shows the `join` workflow. It leads with the heaviest path (build-brain → start-session), then shows blueprint-driven launch, then server-backed launch. The README's "How Agents Join Your Workflow" paragraph (line 51) still claims that "today, the management commands assume the session was launched by `houmao-mgr`", which has been false since `agents join` was implemented.

There is no demo pack that exercises the join lifecycle, making it impossible for new users or CI to verify the simplest adoption path works end-to-end.

The existing demo packs under `scripts/demo/` follow a consistent pattern: a directory containing a `README.md`, shell scripts for each lifecycle step, and an `agents/` symlink pointing at the fixture agent definition directory.

## Goals / Non-Goals

**Goals:**

- Add a prominent "Quick Start: Adopt an Existing Session" section to `README.md` before the current "Basic Workflow", with Mermaid sequence diagrams showing the join pipeline.
- Fix the outdated "How Agents Join Your Workflow" paragraph to reflect current reality.
- Create a self-contained demo pack at `scripts/demo/agents-join-demo-pack/` that exercises the TUI join lifecycle end-to-end.
- Use Mermaid UML diagrams in both the README section and the demo README to explain the join workflow visually.

**Non-Goals:**

- Changing the `agents join` implementation in `src/houmao/`.
- Adding headless join coverage to the demo pack (TUI join is the primary user-facing path; headless join is documented in the reference docs).
- Rewriting the existing "Basic Workflow" or other README sections beyond the targeted additions.
- Adding CI automation for the demo pack (demo packs in this repo are not CI-collected).

## Decisions

### Place the join section before the build-based workflow in the README

The join workflow requires zero setup (no agent-def-dir, no recipes, no credential profiles) and represents the lowest-friction entry point. It belongs before the current Section 3 "Basic Workflow" which requires full agent-def-dir setup.

Why this over appending at the end: the README currently leads with the most complex workflow. A new user who just wants to try Houmao with their existing Claude/Codex/Gemini should find the simplest path first.

### Use Mermaid sequence diagrams to explain the join pipeline

The join pipeline has a clear actor→system→tmux flow that is best communicated visually. The repo conventions prefer Mermaid fenced code blocks for diagrams in Markdown.

Why this over text-only explanation: the join pipeline involves tmux process detection, manifest creation, gateway attachment, and registry publication — steps that are hard to follow as a paragraph but clear as a sequence diagram.

### Follow the established demo pack pattern

The demo pack will follow the same conventions as `scripts/demo/houmao-server-interactive-full-pipeline-demo/`: a `README.md`, individual shell scripts per lifecycle step, and a `run_demo.sh` orchestrator.

The demo pack will NOT carry its own agent definition directory or brain recipes because `agents join` does not need them. This is a key simplicity advantage to highlight.

Why this over a Python-based demo: shell scripts match the existing demo pack pattern and are directly runnable by operators learning the workflow.

### Demo exercises TUI join with Claude Code as the default provider

Claude Code is the default provider (`_DEFAULT_PROVIDER = "claude_code"` at `core.py:57`) and the most common user-facing tool. The demo will default to Claude but accept `--provider` to switch.

Why this over requiring a provider argument: defaulting to Claude matches the CLI default and reduces friction for the most common case.

## Risks / Trade-offs

- [Demo requires a working Claude/Codex CLI] → Document prerequisites clearly; demo scripts validate tool availability before starting.
- [README section may become stale if join CLI changes] → The section references stable CLI options documented in `docs/reference/cli/houmao-mgr.md`; demo scripts serve as living validation.
- [Mermaid diagrams may not render in all Markdown viewers] → GitHub, MkDocs, and VS Code all support Mermaid natively; this is consistent with all other diagrams in the repo.

## Open Questions

None — this is a documentation and demo scripting change with no design ambiguity.
