# Spec Delta

## ADDED Requirements

### Requirement: Pro loop covers post-3.0.0 runtime modes, skills, executor, DSH, and platform routes
`houmao-agent-loop-pro` SHALL update `references/platform-boundaries.md` to add `houmao-agent-access`, `houmao-agent-files`, and `houmao-cccc`, update `commands/execution/prepare-agents.md` for `service`/`web` modes, `system_skills` pack policy, and `project skills`, and update `launch-agents.md` for `--mode`, `--tmux-server`, `--executor`, `dsh`, and `managed_prompt_header` v2.

#### Scenario: Pro execution preparation and platform delegation stay current
- **WHEN** an agent prepares or launches a `houmao-agent-loop-pro` run
- **THEN** `prepare-agents.md` and `launch-agents.md` cover `headless`, `service`, `tui`, and `web` modes, `dsh`, `--tmux-server`, `--executor`, `system_skills` pack policy, and `project skills`
- **AND THEN** `references/platform-boundaries.md` delegates access, file edits, and `houmao-cccc` to their owning routines

### Requirement: Pro loop removes non-runtime design docs, fixes broken reference paths, and consolidates SKILL.md
`houmao-agent-loop-pro` SHALL remove `dev/design/` (1,179 lines of non-runtime maintainer docs), fix all `../reference/` paths in `commands/` to `../../references/`, remove duplicate `## Upfront Planning Rule`, and merge `## Subcommands` and `## Routing` into one `Complex-procedure` three-split table.

#### Scenario: Non-runtime files and broken reference strings are resolved
- **WHEN** a reviewer audits `houmao-agent-loop-pro` against `imsight-agent-skill-handling`
- **THEN** `dev/design/` is absent from the runtime skill tree and all command pages reference `../../references/<file>.md`
- **AND THEN** `SKILL.md` presents a single `Complex-procedure` three-split `## Subcommands` table (`Procedural`, `Helper`, `Misc`) and concise command pages without duplicated `## Upfront Planning Rule` or wrapper prose

### Requirement: Pro loop preserves loop-dir boundary, upfront planning, and non-polling execution
`houmao-agent-loop-pro` SHALL preserve explicit-only activation, help before `<loop-dir>` or `init` default, native-tool upfront planning, actor frame and `as-agent` gate, `<loop-dir>/{intention,execplan,runs}` separation, `tree-loop`/`generic-loop` pipelines, and no in-chat polling.

#### Scenario: Missing loop directory blocks execution before file generation
- **WHEN** `houmao-agent-loop-pro` starts an operational command without an explicit `<loop-dir>`
- **THEN** it stops and asks for `<loop-dir>` rather than inventing a directory
- **AND THEN** runtime execution relies on notifier-driven turns without in-chat polling or sleeping
