# Git Worktree Readiness

## Purpose

Use this page when a generated loop requires Git worktree readiness evidence, or when manual workspace evidence claims a Git worktree is ready.

For standard Houmao managed workspaces, this page is evidence guidance only. Route worktree creation, local-state linking, submodule materialization, launch cwd posture, memo-seed posture, project-scope command checks, and compact summaries through `prepare-workspace` and `houmao-utils-workspace-mgr` `create`, `validate`, or `summarize`.

## Core Rules

- Treat generated workspace contracts and prepared agent/profile facts as the authority for expected path, branch, cwd, memo, validation command, and read/write posture.
- For standard in-repo workspaces, use workspace-manager evidence for `<task-root>/<agent-name>/repo/` worktrees, `<task-root>/<agent-name>/states/`, `<task-root>/shared-kb/`, and `<task-root>/owner-states/<subdir>/...`.
- Do not create worktrees, repair local-only state, add symlinks, materialize submodules, or run project-scope validation commands directly from this reference page.
- Do not blindly reuse generic worktree symlink defaults. Local-state completeness belongs to workspace-manager `validate` evidence or explicit manual evidence.
- Do not invent broad build, test, package-manager, or smoke commands. Use explicit workspace-manager validation inputs from `workspace.toml`, operator-provided commands, or documented safe project commands.
- A workspace-manager `plan` report alone is not launch-ready evidence when managed workspace readiness is required.
- Record exact evidence so `validate-loop` can distinguish planned, created, validated, summarized, missing, inconsistent, and custom/manual workspace facts.

## Worktree Identity Evidence

For each managed or manually supplied agent worktree, evidence should identify:

```bash
cd "$WT"
git rev-parse --show-toplevel
git status --short
git branch --show-current
git worktree list
```

Ready evidence shows:
- `$WT` is registered as a Git worktree of the intended source repo;
- the worktree path matches the workspace contract, normally `<task-root>/<agent-name>/repo/` for standard in-repo workspaces;
- current branch matches the generated workspace contract or accepted operator plan;
- dirty state is understandable and expected for the current stage;
- no two agents share the same mutable worktree target unless the generated contract explicitly allows it.

## Local State And Submodules

For standard Houmao workspaces, rely on workspace-manager `validate` output for local-state links, skipped link candidates, protected local state, submodule posture, memo seeds, launch cwd posture, and mutable-path isolation.

Manual evidence should name:
- required local-only paths and whether they are present from inside the worktree;
- linked or mounted paths and why each is safe;
- skipped local-state candidates and skip reasons;
- required submodule paths, status, and whether each is materialized from inside the worktree;
- missing local-state or submodule facts that block launch.

If required local state or submodules are missing for a standard workspace, report the gap and route follow-up through workspace-manager `create` or `validate`; do not repair it here.

## Project-Scope Validation Commands

Project command readiness belongs in workspace-manager validation inputs. Accept commands from:
- explicit operator instructions;
- `execplan/specs/workspace/workspace.toml`;
- documented safe project commands, such as Pixi tasks, Python virtual environment checks, C or C++ build commands, package scripts, or in-project scripts.

When evidence comes from workspace-manager `validate`, preserve:
- checks considered;
- commands run;
- commands skipped and why;
- pass/fail status;
- cwd used for each command;
- follow-up actions for failures.

When evidence is manual, require the same facts. If no safe command is known, record missing validation input instead of manufacturing a heavy build or test command.

## Readiness Report

For each worktree, report:
- source repo root and worktree path;
- branch name and `git status --short` posture;
- launch cwd that profiles will use;
- task root and workspace-manager surfaces checked;
- submodule posture from workspace-manager validation or explicit manual evidence;
- local-state link posture from workspace-manager validation or explicit manual evidence;
- project runtime/tool validation commands, pass/fail/skipped posture, and cwd;
- writable and read-only path boundaries;
- workspace summary/report timestamp or source when available;
- unresolved blockers and warnings.

`validate-loop` should treat missing, stale, inconsistent, or plan-only managed-workspace evidence as a blocker before `launch-agents`.
