---
name: houmao-utils-workspace-mgr
description: Use when planning, creating, validating, or summarizing a Houmao-standard multi-agent workspace across `in-repo` or `out-of-repo` roots, Git worktrees, local-state links, submodules, `--executor` or DSH Web `--workdir` bindings, or memo seeds.
metadata:
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

## Overview

Plan, create, validate, and summarize Houmao-standard multi-agent workspace topologies (`in-repo` and `out-of-repo`), Git worktrees, local-state symlinks, submodule posture, and profile/launch `workdir` bindings without launching agents.

## Workflow

1. **Answer explicit `help` first** from **Help** without inspecting Git, writing plan files, or mutating directories.
2. **Enforce the Actor Frame Gate** and keep this routine strictly scoped to multi-agent workspace topology (route individual definition-owned auxiliary workspaces to `houmao-shared-routines->houmao-agent-instance->private-workspace()`, live memo edits to `houmao-shared-routines->houmao-memory-mgr`, and post-setup launches to `houmao-shared-routines->houmao-agent-definition` or `houmao-agent-instance`).
3. **Select one subcommand** from **Subcommands** (defaulting any unclear request to read-only `plan`) and one flavor from **Workspace Flavors** (`in-repo` vs `out-of-repo`), asking with `Required` / `Optional` labels if `task-name`, flavor, profiles, or target repo bindings remain ambiguous.
4. **Load only the selected command page, flavor page, and required references** (including [references/git-worktree-and-ignore-rules.md](references/git-worktree-and-ignore-rules.md) and [references/workspace-contract.md](references/workspace-contract.md)).
5. **Execute the operation** while respecting Git branch isolation, `--executor` target-context workdir paths, and DSH Web (`--mode web`) `--workdir` session bindings, then return topology, Git/validation evidence, and launch handoffs.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **Workspace Flavors**, and **References**, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Admin callers require explicit project and workspace paths before `create`; verified `agent` callers supply self context but still require explicit workspace paths and cannot mutate peer workspaces unasked.

## Subcommands

`execute` is a compatibility alias for `create` (prefer `create`).

| Subcommand | Mutates Topology | Use For | Detail |
| --- | --- | --- | --- |
| `plan` | No (optional plan file only) | Default read-only dry-run of layout, Git branches, symlinks, submodules, `workdir` bindings, and risks. | [commands/plan.md](commands/plan.md) |
| `create` | Yes | Materialize approved directories, Git worktrees, ignores, links, `workspace.md`, optional memo seeds, and profile `workdir` updates (alias `execute`). | [commands/create.md](commands/create.md) |
| `validate` | No | Verify worktrees, local-state links, submodules, `workdir` bindings, and project tool readiness without repairing. | [commands/validate.md](commands/validate.md) |
| `summarize` | No | Emit compact consumer-neutral workspace facts for operators, scripts, or loop planners. | [commands/summarize.md](commands/summarize.md) |
| `help` | No | Explain operations, `in-repo` vs `out-of-repo` flavors, branch naming, and `--executor` / DSH Web `workdir` boundaries. | **Help** |

## Workspace Flavors, Naming, and `--executor` / DSH Web Workdirs

| Flavor | Layout Root & Default Launch `workdir` | Default Agent Branch | Detail |
| --- | --- | --- | --- |
| `in-repo` | `<repo-root>/houmao-ws/<task-name>/`; launch `workdir`: `<repo-root>` (mutations in `<agent>/repo/`) | `houmao/<task-name>/<agent-name>/main` | [commands/in-repo-workspace.md](commands/in-repo-workspace.md) |
| `out-of-repo` | Standalone `<ws-root>/`; launch `workdir`: `<ws-root>/<agent-name>` (or focused `repos/<project>`) | `houmao/<agent-name>/main` (or `houmao/<agent-name>/<repo-name>`) | [commands/out-of-repo-workspace.md](commands/out-of-repo-workspace.md) |

- **`--executor` and DSH Web (`--mode web`) `workdir` bindings**: when profiles or launches bind an `--executor` target context, every planned workspace root, Git worktree, and `--workdir` path must exist and be validated inside that execution owner's filesystem context; for DSH Web (`--mode web`), the launch/profile `--workdir` binds the browser session's active workspace root at birth, so align `--workdir` explicitly with the intended shared visibility surface (`<repo-root>`) or private agent checkout (`<agent>/repo/` or `<ws-root>/<agent>`).
- **References**: [references/git-worktree-and-ignore-rules.md](references/git-worktree-and-ignore-rules.md), [references/local-state-links.md](references/local-state-links.md), [references/submodules.md](references/submodules.md), [references/memo-seeds.md](references/memo-seeds.md), [references/workspace-contract.md](references/workspace-contract.md), and [references/validation-checks.md](references/validation-checks.md).

## Help

Summarize `plan` (read-only default), `create` (`execute`), `validate`, `summarize`, `in-repo` vs `out-of-repo` layouts, `houmao/.../main` branch isolation, `--executor` / DSH Web `--workdir` alignment, and the separation from `private-workspace` and agent launch.

## Guardrails

- DO NOT launch agents or absorb definition-owned `private-workspace` (`houmao-shared-routines->houmao-agent-instance->private-workspace()`) into this skill.
- DO NOT store Houmao runtime homes, logs, gateways, or mailboxes inside the workspace tree unless a maintained `houmao-mgr` command places them there.
- DO NOT check out the same branch in two worktrees of the same repo, commit nested worktrees into a parent repo, share mutable submodule working trees across committing agents, or copy submodule `.git` metadata.
- DO NOT overwrite existing worktrees, symlinks, bare repos, or memo seeds without confirmation, point an agent's writable bookkeeping into a sibling's directory, or treat local `.shared-repos/*.git` bare repos as remote-portable without export/push.
