## Why

`houmao-utils-workspace-mgr/SKILL.md` has grown into a long mixed policy document, making routing harder and hiding the core operations behind detail that belongs in routed pages. The workspace manager also needs to treat workspace creation and workspace validation as separate operations so a prepared worktree can be checked against project-scope tools before agents rely on it.

## What Changes

- **BREAKING**: Replace the top-level `plan`/`execute` operation model with a concise independent operation set: `help`, `plan`, `create`, `validate`, and `summarize`.
- Keep `houmao-utils-workspace-mgr` independent of loop-specific concepts; it prepares and validates workspaces for humans, scripts, or any upstream planner without naming loop plans as its own contract.
- Refactor the top-level `SKILL.md` into a short router modeled after `houmao-agent-loop-pro`: activation, help, operation table, routing table, references, and constraints.
- Move detailed policies into operation, flavor, and reference pages:
  - operation pages for `plan`, `create`, `validate`, and `summarize`
  - flavor pages for `in-repo` and `out-of-repo`
  - reference pages for local-state links, submodules, memo seeds, workspace contracts, and validation checks
- Define `create` as the operation that creates or updates workspace topology, worktrees, local-state links, workspace maps, optional memo seeds, and launch-profile cwd settings.
- Define `validate` as the operation that checks prepared worktrees for project-scope command readiness and verifies required local-state links/materialization were not missed.
- Allow `execute` only as a compatibility alias for `create` if retained in guidance, but make `create` the standard operation name.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-utils-workspace-mgr-skill`: Revise the packaged skill operation contract, entrypoint structure, and workspace validation requirements.

## Impact

- Packaged skill assets under `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/`.
- Tests that assert workspace-manager asset shape, operation names, routing guidance, or long-form entrypoint text.
- Documentation that describes workspace-manager operations as `plan`/`execute`.
- Downstream skills or docs that call `execute` may need to call `create` or treat `execute` as a compatibility alias.
