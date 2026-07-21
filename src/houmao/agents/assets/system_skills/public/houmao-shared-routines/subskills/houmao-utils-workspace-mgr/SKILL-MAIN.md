---
name: houmao-utils-workspace-mgr
description: Use when a Houmao-standard multi-agent workspace must be planned, created, validated, or summarized across in-repo or out-of-repo roots, Git worktrees, local-state links, submodules, launch cwd, or memo seeds.
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Workspace Manager

## Workflow

1. **Handle explicit help first** without Git inspection, plan-file writes, topology mutation, or missing-input questions.
2. **Validate the inherited actor frame** from `houmao-shared-routines` and preserve its project, agent, and workspace context.
3. **Select one subcommand** from **Subcommands**; default an unclear operation to read-only `plan`.
4. **Resolve required inputs and one workspace flavor**, then load only the selected operation page, flavor page, and named references.
5. **Execute the operation** while preserving repository safety, local-state link, submodule, launch-cwd, memo-seed, and validation contracts.
6. **Return the result** with topology, Git effects, validation evidence, risks, blockers, and downstream launch handoff when requested.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the workspace subcommands, flavors, repository constraints, actor frame, and user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent; otherwise stop before workspace routing.

- Admin branch: require an explicit project and workspace path before creation, and act for the human operator.
- Agent branch: require freshly verified self identity. Verified self supplies agent context but never supplies a missing workspace path or permission to alter a peer workspace.

Preserve the actor frame through planning, creation, validation, and summary commands.

## Activation

- Use this Houmao skill when the user asks for Houmao-standard workspace planning, creation, validation, or summaries.
- This skill is independent workspace infrastructure. Upstream plans may request workspaces, but this skill's own contract is workspace preparation only.
- If the user invokes explicit help intent, answer from `## Help` before defaulting to `plan`.
- If the operation is unclear, default to `plan`.
- DO NOT launch agents from this skill. Use `houmao-shared-routines->houmao-agent-instance` or `houmao-shared-routines->houmao-agent-definition` after workspace preparation when launch is requested.

## Help

When the user asks `$houmao-shared-routines utils-workspace-mgr help`, `help for houmao-utils-workspace-mgr`, `usage for houmao-utils-workspace-mgr`, `available functionality for houmao-utils-workspace-mgr`, or what this skill can do, answer from this section before choosing an operation, inspecting Git state, writing a plan file, creating files, validating project commands, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me plan a multi-agent workspace", route to the matching operation instead of stopping at generic help.

Purpose: plan, create, validate, and summarize Houmao-standard multi-agent workspaces for humans, scripts, or upstream planners.

Available functionality:

- `help`: explain this skill's purpose, operation list, common prompts, and boundaries.
- `plan`: dry-run a workspace layout and report intended filesystem, Git, local-state, submodule, launch-cwd, and validation posture.
- `create`: create or update the approved workspace topology, worktrees, links, docs, optional memo seeds, and optional launch-profile cwd values.
- `validate`: check prepared worktrees, links, submodules, launch cwd posture, and project-scope command readiness without repairing topology.
- `summarize`: report compact prepared-workspace facts for humans, scripts, or upstream planners.

Common starting prompts:

- `$houmao-shared-routines utils-workspace-mgr help`
- `$houmao-shared-routines utils-workspace-mgr plan in-repo workspace for <profiles>`
- `$houmao-shared-routines utils-workspace-mgr create the approved workspace plan`
- `$houmao-shared-routines utils-workspace-mgr validate prepared worktrees with <command>`
- `$houmao-shared-routines utils-workspace-mgr summarize workspace <task-name>`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-agent-definition` for specialist-backed easy launch after workspace preparation.
- Use `houmao-shared-routines->houmao-agent-instance` for broad live-agent lifecycle launch, join, stop, relaunch, or cleanup.
- Use `houmao-shared-routines->houmao-memory-mgr` when the task is only editing an existing live memo rather than preparing memo seed material.
- Keep custom operator-owned workspace contracts outside this Houmao-standard workspace skill.

## Subcommands

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
| `in-repo` | [commands/in-repo-workspace.md](commands/in-repo-workspace.md) | Workspace collection is rooted under the current repo. |
| `out-of-repo` | [commands/out-of-repo-workspace.md](commands/out-of-repo-workspace.md) | Workspace is standalone and mounts one or more target repos. |

## Routing

Choose exactly one operation page.

| Operation | Page |
| --- | --- |
| `plan` | [commands/plan.md](commands/plan.md) |
| `create`, `execute` alias | [commands/create.md](commands/create.md) |
| `validate` | [commands/validate.md](commands/validate.md) |
| `summarize` | [commands/summarize.md](commands/summarize.md) |

Read only the selected operation page, the selected flavor page, and the reference pages named by that operation page.

## References

- [references/local-state-links.md](references/local-state-links.md): local-only path discovery, link/skip rules, AI-tool state skips, and completeness checks.
- [references/submodules.md](references/submodules.md): tracked submodule materialization and validation posture.
- [references/memo-seeds.md](references/memo-seeds.md): optional launch-profile memo seed generation.
- [references/workspace-contract.md](references/workspace-contract.md): `workspace.md`, workspace summaries, ownership rules, and integration notes.
- [references/validation-checks.md](references/validation-checks.md): worktree readiness and project-scope command validation.

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

## Guardrails

- DO NOT launch agents.
- DO NOT store Houmao runtime homes, logs, gateways, mailboxes, or generated provider homes inside the workspace layout unless a maintained Houmao command chooses that path.
- DO NOT commit nested Git worktrees into a parent repo.
- DO NOT overwrite existing worktrees, symlinks, copied repos, local bare repos, or memo seed files without explicit confirmation.
- DO NOT create two worktrees that check out the same branch from the same Git repo.
- DO NOT point multiple agents at the same mutable submodule working tree when they are expected to commit independently.
- DO NOT copy submodule `.git` metadata from one checkout into another worktree.
- DO NOT let one agent's default writable bookkeeping path point into another agent's bookkeeping directory.
- DO NOT absorb arbitrary custom workspace layouts as though they were standard Houmao workspaces.
- DO NOT treat local-only shared repos as portable unless the user exports or pushes them.
