# Prepare Workspace

## Read First

- `../reference/generated-contract-defaults.md`
- `../reference/platform-boundaries.md`

## Preconditions

- Generated execplan exists.
- Operator wants workspace setup planned, executed, or verified before agent preparation.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`

Use when present:
- `<loop-dir>/execplan/specs/workspace/workspace.toml`;
- `<loop-dir>/execplan/agents/bindings.toml`;
- generated participant specs;
- generated run artifact contracts;
- existing workspace-manager plan or workspace contract docs;
- operator approval for execution.

## Actions

1. Validate the execplan shape before workspace preparation.
2. Read `execplan/manifest.toml` first.
3. If the manifest and generated docs record that no managed workspace is required, report that no workspace setup is required and stop.
4. Read `execplan/specs/workspace/workspace.toml`, `execplan/agents/bindings.toml`, and related participant or run contracts when workspace setup or verification is required.
5. Extract workspace-manager inputs:
   - operation: `plan` or `execute`;
   - workspace flavor, defaulting to `in-repo` when unspecified and supported;
   - task name, repo root, and workspace root policy;
   - concrete agent workspace names and launch profile names;
   - launch cwd policy;
   - per-agent work roots, knowledge paths, shared resources, and read/write rules;
   - loop bookkeeping directories, including durable task/agent artifact paths and ignored transient paths;
   - memo-seed and launch-profile adjustment posture.
6. Default to workspace-manager `plan` mode unless the user explicitly asks to execute or has approved a current plan.
7. Use `houmao-utils-workspace-mgr` for supported workspace planning or execution.
8. Do not duplicate workspace-manager mechanics such as worktree creation, branch creation, local-state symlinks, submodule materialization, shared repos, `.gitignore` updates, memo-seed writes, or launch-profile cwd edits.
9. If the execplan selects a custom operator-owned workspace that the workspace manager cannot represent, do not translate it into a standard workspace. Verify and report the custom facts described by the execplan.
10. After plan or execution, compare available workspace facts with generated workspace contracts and agent bindings.

## Postconditions To Check

For standard executed workspaces, check applicable facts:
- workspace contract docs exist;
- per-agent worktrees exist;
- per-agent knowledge paths exist;
- shared knowledge paths or repos exist;
- loop-requested bookkeeping directories exist;
- ignored transient paths are covered by ignore rules;
- launch-profile cwd posture matches the selected workspace flavor when profile adjustment was requested;
- memo-seed files exist when requested;
- no two agents share the same mutable worktree or private knowledge directory.

## Report

Report:
- operation used: `plan`, `execute`, or custom verification;
- workspace flavor and root facts;
- no-workspace posture when the execplan records an intentional omission;
- ready facts;
- planned-but-not-executed facts;
- missing facts;
- inconsistencies against `workspace.toml` or `bindings.toml`;
- whether later execution stages may treat workspace readiness as complete.

## Constraints

- Do not install generated skills.
- Do not create or update specialists, profiles, mailboxes, gateways, memories, or live agents.
- Do not bind maintained mail support skills.
- Do not start loop work.
- Do not call or route to `prepare-agents`.
- Do not create workspaces by hand when `houmao-utils-workspace-mgr` can represent the layout.
