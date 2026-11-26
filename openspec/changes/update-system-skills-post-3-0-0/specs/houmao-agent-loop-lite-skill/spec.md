# Spec Delta

## ADDED Requirements

### Requirement: Lite loop covers post-3.0.0 platform routines, run modes, and tmux server selection
`houmao-agent-loop-lite` SHALL update `references/platform-boundaries.md` to include `houmao-agent-access`, `houmao-agent-files`, `houmao-mailbox-mgr`, and `houmao-memory-mgr`, and update `commands/execution/prepare-agents.md` and `launch-agents.md` for `service`/`web` run modes and `--tmux-server`.

#### Scenario: Lite loop platform delegation and launch modes match current runtime
- **WHEN** a caller prepares or launches agents under `houmao-agent-loop-lite`
- **THEN** `references/platform-boundaries.md` lists all applicable sibling routines including `agent-access`, `agent-files`, `mailbox-mgr`, and `memory-mgr`
- **AND THEN** `prepare-agents.md` and `launch-agents.md` support `headless`, `service`, `tui`, and `web` modes plus `--tmux-server`

### Requirement: Lite loop fixes broken reference paths and consolidates SKILL.md routing
`houmao-agent-loop-lite` SHALL fix all `../reference/` paths in `commands/*/*.md` to `../../references/`, remove the duplicate `## Upfront Planning Rule` section, and merge `## Subcommands`, `Aliases:`, and `## Routing` into a clean `Complex-procedure` three-split `## Subcommands` table.

#### Scenario: Lite loop SKILL.md and command links conform to layout rules
- **WHEN** a reviewer inspects `houmao-agent-loop-lite`
- **THEN** every `## Read First` path in `commands/{authoring,execution}/*.md` resolves to `../../references/<file>.md`
- **AND THEN** `SKILL.md` uses a single `Complex-procedure` three-split `## Subcommands` table with clean alias notes and no duplicate `## Upfront Planning Rule`

### Requirement: Lite loop preserves lightweight Markdown and direct-SQLite boundaries
`houmao-agent-loop-lite` SHALL preserve explicit-only activation, help before `<loop-dir>` or `init`, strict `<loop-dir>` gating, Markdown contracts with typed headers (`Loop-Template-Type`, `Loop-Template-Version`), direct `state.sqlite3` execution without JSON schemas or Jinja2, and no polling.

#### Scenario: Lite loop rejects Pro-only harness complexity
- **WHEN** `houmao-agent-loop-lite` generates or runs a loop under `<loop-dir>`
- **THEN** it uses Markdown contracts, generated skills, and direct `runs/<run-id>/state.sqlite3` state without introducing Pro JSON schemas, Jinja2, or TOML registries
- **AND THEN** runtime execution remains notifier-driven with no in-chat waiting or polling
