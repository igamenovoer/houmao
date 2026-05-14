# Prepare Workspace

## Read First

- `../reference/generated-contract-defaults.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Generated execplan exists.
- Concrete agent/profile facts have been prepared or explicitly supplied.
- Operator wants workspace setup planned, executed, or verified after agent preparation.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`

Use when present:
- `<loop-dir>/execplan/specs/workspace/workspace.toml`;
- `<loop-dir>/execplan/agents/bindings.toml`;
- prepared concrete agent/profile facts from `prepare-agents`;
- generated participant specs;
- generated run artifact contracts;
- existing workspace-manager plan or workspace contract docs;
- operator-supplied manual workspace readiness evidence;
- operator approval for execution.

## Actions

1. Validate the execplan shape before workspace preparation.
2. Read `execplan/manifest.toml` first.
3. If the manifest and generated docs record that no managed workspace is required, report that no workspace setup is required and stop.
4. Read `execplan/specs/workspace/workspace.toml`, `execplan/agents/bindings.toml`, prepared agent/profile facts, and related participant or run contracts when workspace setup or verification is required.
5. Extract workspace-manager inputs:
   - operation: `plan` or `execute`;
   - workspace flavor, defaulting to `in-repo` when unspecified and supported;
   - task name, repo root, and workspace root policy;
   - concrete agent ids, workspace agent names, and easy profile or explicit raw launch profile names prepared by `prepare-agents`;
   - launch cwd policy;
   - per-agent work roots, knowledge paths, shared resources, and read/write rules;
   - loop bookkeeping directories, including durable task/agent artifact paths and ignored transient paths;
   - memo-seed and launch-profile adjustment posture.
6. Default to workspace-manager `plan` mode unless the user explicitly asks to execute or has approved a current plan.
7. Use `houmao-utils-workspace-mgr` for supported workspace planning or execution.
8. Do not duplicate workspace-manager mechanics such as worktree creation, branch creation, local-state symlinks, submodule materialization, shared repos, `.gitignore` updates, memo-seed writes, or launch-profile cwd edits.
9. If the execplan selects a custom operator-owned workspace or the user supplies manual workspace readiness evidence, do not translate it into a standard workspace. Verify and report the custom or manual facts described by the execplan.
10. After plan or execution, compare available workspace facts with generated workspace contracts, generated agent bindings, and prepared agent/profile facts.

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

## Tips

- When Git worktrees are required, read `../reference/git-worktree-readiness.md`.
- Treat Git worktree readiness as a multi-part contract: registered worktree, branch/cwd posture, project runtime, submodules, local-only state, project config parity, task tooling, and recorded evidence.
- Keep standard worktree creation and repair routed through `houmao-utils-workspace-mgr` when it can represent the layout.

## Report

Report:
- operation used: `plan`, `execute`, or custom verification;
- workspace flavor and root facts;
- no-workspace posture when the execplan records an intentional omission;
- manual workspace evidence accepted or rejected when supplied;
- prepared agent/profile facts used as workspace-manager inputs;
- ready facts;
- planned-but-not-executed facts;
- missing facts;
- inconsistencies against `workspace.toml` or `bindings.toml`;
- whether later execution stages may treat workspace readiness as complete.

## Constraints

- Do not install generated skills.
- Do not create or update specialists, profiles, mailboxes, gateways, memories, or live agents.
- Do not prepare mailbox, gateway, memory, inspection, or Houmao system-skill posture.
- Do not start loop work.
- Do not call or route to `prepare-agents`.
- Do not invent placeholder agent ids, workspace agent names, or profile names when they should come from `prepare-agents`.
- Do not create workspaces by hand when `houmao-utils-workspace-mgr` can represent the layout.
