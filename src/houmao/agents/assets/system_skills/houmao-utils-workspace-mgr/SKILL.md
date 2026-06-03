---
name: houmao-utils-workspace-mgr
description: Use Houmao's independent workspace manager skill to plan, create, validate, or summarize multi-agent workspaces, including untracked in-repo task workspaces, out-of-repo workspaces, Git worktrees, local-state links, tracked submodule materialization, launch-profile cwd updates, and optional memo-seed workspace rules. Use when the user asks to prepare, organize, inspect, dry-run, validate, or summarize a Houmao-standard workspace before launching agents.
---

# Houmao Workspace Manager

## Activation

- Use this Houmao skill when the user asks for Houmao-standard workspace planning, creation, validation, or summaries.
- This skill is independent workspace infrastructure. Upstream plans may request workspaces, but this skill's own contract is workspace preparation only.
- If the user invokes explicit help intent, answer from `## Help` before defaulting to `plan`.
- If the operation is unclear, default to `plan`.
- Do not launch agents from this skill. Use `houmao-agent-instance` or `houmao-agent-definition` after workspace preparation when launch is requested.

## Help

When the user asks `$houmao-utils-workspace-mgr help`, `help for houmao-utils-workspace-mgr`, `usage for houmao-utils-workspace-mgr`, `available functionality for houmao-utils-workspace-mgr`, or what this skill can do, answer from this section before choosing an operation, inspecting Git state, writing a plan file, creating files, validating project commands, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me plan a multi-agent workspace", route to the matching operation instead of stopping at generic help.

Purpose: plan, create, validate, and summarize Houmao-standard multi-agent workspaces for humans, scripts, or upstream planners.

Available functionality:

- `help`: explain this skill's purpose, operation list, common prompts, and boundaries.
- `plan`: dry-run a workspace layout and report intended filesystem, Git, local-state, submodule, launch-cwd, and validation posture.
- `create`: create or update the approved workspace topology, worktrees, links, docs, optional memo seeds, and optional launch-profile cwd values.
- `validate`: check prepared worktrees, links, submodules, launch cwd posture, and project-scope command readiness without repairing topology.
- `summarize`: report compact prepared-workspace facts for humans, scripts, or upstream planners.

Common starting prompts:

- `$houmao-utils-workspace-mgr help`
- `$houmao-utils-workspace-mgr plan in-repo workspace for <profiles>`
- `$houmao-utils-workspace-mgr create the approved workspace plan`
- `$houmao-utils-workspace-mgr validate prepared worktrees with <command>`
- `$houmao-utils-workspace-mgr summarize workspace <task-name>`

Related skills and boundaries:

- Use `houmao-agent-definition` for specialist-backed easy launch after workspace preparation.
- Use `houmao-agent-instance` for broad live-agent lifecycle launch, join, stop, relaunch, or cleanup.
- Use `houmao-memory-mgr` when the task is only editing an existing live memo rather than preparing memo seed material.
- Keep custom operator-owned workspace contracts outside this Houmao-standard workspace skill.

## Operations

| Operation | Mutates workspace topology? | Use when |
| --- | --- | --- |
| `help` | no | Explain this skill's purpose, operations, prompts, and boundaries. |
| `plan` | no, except optional plan file | Inspect local context and report intended layout, Git actions, local-state links, submodule posture, launch cwd changes, risks, and questions. |
| `create` | yes | Create or update workspace directories, Git worktrees, local-state links, submodule materialization, workspace docs, optional memo seeds, and optional launch-profile cwd settings. |
| `validate` | no topology mutation | Check prepared worktrees, required local-state links, submodule materialization, launch cwd posture, and project-scope tool readiness. |
| `summarize` | no | Report compact prepared-workspace facts for humans, scripts, or upstream planners. |

`execute` is a compatibility alias for `create`. Prefer `create` in new guidance and responses.

## Required Inputs

Recover these from the prompt, current repo, launch profiles, and local Git state before asking questions:

| Input | Required when |
| --- | --- |
| operation | Not safely inferred; default to `plan` when unclear. |
| workspace flavor | Not safely inferred; choose `in-repo` or `out-of-repo`. |
| `task-name` | `in-repo` workspace. |
| launch profiles and stable names | Planning or creating profile-bound workspaces. |
| `ws-root` | Optional override; default is `<repo-root>/houmao-ws` for `in-repo`. |
| target repo bindings | `out-of-repo` workspace. |

Optional inputs:

- validation commands or documented project commands
- submodule materialization choices
- local-state link choices
- requested task, agent, artifact, owner-state, or scratch bookkeeping directories
- plan Markdown output path
- whether to adjust launch profiles during `create`
- whether to create memo-seed Markdown and merge workspace rules into profile memo seeds

When asking for Houmao workspace-system inputs, separate `Required` values from `Optional` modifiers. If no optional inputs apply to the question, say `Optional: none for this step.` Do not use this format for the user's task/domain intent unless the question is about Houmao runtime behavior.

## Workspace Flavors

Load exactly one flavor page after choosing the workspace flavor:

| Flavor | Page | Use when |
| --- | --- | --- |
| `in-repo` | [subskills/in-repo-workspace.md](subskills/in-repo-workspace.md) | Workspace collection is rooted under the current repo. |
| `out-of-repo` | [subskills/out-of-repo-workspace.md](subskills/out-of-repo-workspace.md) | Workspace is standalone and mounts one or more target repos. |

## Routing

Choose exactly one operation page.

| Operation | Page |
| --- | --- |
| `plan` | [subskills/operations/plan.md](subskills/operations/plan.md) |
| `create`, `execute` alias | [subskills/operations/create.md](subskills/operations/create.md) |
| `validate` | [subskills/operations/validate.md](subskills/operations/validate.md) |
| `summarize` | [subskills/operations/summarize.md](subskills/operations/summarize.md) |

Read only the selected operation page, the selected flavor page, and the reference pages named by that operation page.

## References

- [subskills/reference/local-state-links.md](subskills/reference/local-state-links.md): local-only path discovery, link/skip rules, AI-tool state skips, and completeness checks.
- [subskills/reference/submodules.md](subskills/reference/submodules.md): tracked submodule materialization and validation posture.
- [subskills/reference/memo-seeds.md](subskills/reference/memo-seeds.md): optional launch-profile memo seed generation.
- [subskills/reference/workspace-contract.md](subskills/reference/workspace-contract.md): `workspace.md`, workspace summaries, ownership rules, and integration notes.
- [subskills/reference/validation-checks.md](subskills/reference/validation-checks.md): worktree readiness and project-scope command validation.

## Shared Naming

Normalize each launch profile name into a path-safe `agent-name`. Refuse empty names and collisions.

For task-scoped `in-repo` workspaces, default branch:

```text
houmao/<task-name>/<agent-name>/main
```

For other standard workspace cases, default branch:

```text
houmao/<agent-name>/main
```

For multi-repo workspaces, the same branch name may be reused in different repos. If the user asks for repo-qualified names, use `houmao/<agent-name>/<repo-name>`.

## Constraints

- Do not launch agents.
- Do not store Houmao runtime homes, logs, gateways, mailboxes, or generated provider homes inside the workspace layout unless an existing Houmao command chooses that path.
- Do not commit nested Git worktrees into a parent repo.
- Do not overwrite existing worktrees, symlinks, copied repos, local bare repos, or memo seed files without explicit confirmation.
- Do not create two worktrees that check out the same branch from the same Git repo.
- Do not point multiple agents at the same mutable submodule working tree when they are expected to commit independently.
- Do not copy submodule `.git` metadata from one checkout into another worktree.
- Do not let one agent's default writable bookkeeping path point into another agent's bookkeeping directory.
- Do not absorb arbitrary custom workspace layouts into this skill as though they were standard Houmao workspaces.
- Do not treat local-only shared repos as portable unless the user exports or pushes them.
