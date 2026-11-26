# Spec Delta

## ADDED Requirements

### Requirement: Workspace manager documents executor workdir and DSH Web workspace binding
`houmao-utils-workspace-mgr` SHALL document how multi-agent workspace layouts interact with `--executor` target-context workdirs and DSH Web `--workdir` workspace binding in `SKILL-MAIN.md` and `references/workspace-contract.md`.

#### Scenario: Workspace setup accounts for remote executor or DSH Web workdirs
- **WHEN** an agent or operator prepares an `in-repo` or `out-of-repo` workspace for `--executor` or DSH Web (`--mode web`) sessions
- **THEN** `houmao-utils-workspace-mgr` clarifies workdir binding boundaries without taking over launch or definition-owned `private-workspace` configuration

### Requirement: Workspace manager consolidates redundant entrypoint lists and extracts shared Git rules
`houmao-utils-workspace-mgr` SHALL merge redundant `## Help`, `## Subcommands`, and `## Routing` lists plus Missing-Input boilerplate in `SKILL-MAIN.md` into a lean entrypoint (~95 lines) and tighten shared Git worktree/`common-kb`/`.gitignore` rules across `in-repo-workspace.md` and `out-of-repo-workspace.md` into `references/`.

#### Scenario: Entrypoint and flavor pages avoid repeated prose
- **WHEN** a reviewer checks `houmao-utils-workspace-mgr`
- **THEN** `SKILL-MAIN.md` lists `plan`, `create` (`execute` alias), `validate`, and `summarize` once in a `## Subcommands` table and shares common Git rules cleanly via `references/`

### Requirement: Workspace manager preserves topology-only boundary, read-only default, and Git safety
`houmao-utils-workspace-mgr` SHALL preserve `## Actor Frame Gate`, its topology-only boundary (never launch agents, never absorb `private-workspace`), defaulting unclear requests to read-only `plan`, Git worktree safety rules, and standard branch naming (`houmao/<task-name>/<agent-name>/main` or `houmao/<agent-name>/main`).

#### Scenario: Unclear workspace request defaults to read-only plan and enforces Git safety
- **WHEN** a caller invokes `houmao-utils-workspace-mgr` without specifying a mutating verb
- **THEN** it defaults to read-only `plan()`, enforces non-nested worktrees and single-checkout branch isolation, and uses canonical `houmao/.../main` branch names
