---
name: houmao-agent-instance
description: Use when a Houmao managed-agent instance must be launched, joined, listed, stopped, relaunched, or cleaned up, when registering `agents external` imports or reconciling `--executor` locators, or when accessing native resources, runtime variables, mindsets, or private workspaces.
license: MIT
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

# Houmao Agent Instance

## Overview

Manage Houmao managed-agent instance lifecycle (`launch`, `join`, `list`, `stop`, `relaunch`, `cleanup`), external communication-only imports (`agents external`), executor locator maintenance (`admin executors`), native-home freshness, and definition-owned `instance-state` surfaces (`runtime-variables`, `mindsets`, `private-workspace`).

## Workflow

1. **Answer explicit `help` first** from **Help** without running commands or mutating runtime or registry state.
2. **Enforce the Actor Frame Gate** and route neighboring tasks before mutating: specialist/profile authoring to `houmao-shared-routines->houmao-agent-definition`, read-only state/usage/logs/screen inspection to `houmao-shared-routines->houmao-agent-inspect`, `request`/`prompt`/`interrupt` to `houmao-shared-routines->houmao-agent-messaging`, gateway sidecars (`web-entry`, `reminders`, `mail-notifier`) to `houmao-shared-routines->houmao-agent-gateway`, and versioned gateway mounts to `houmao-shared-routines->houmao-agent-files`.
3. **Select one operation** from **Subcommands** (or apply **External Agents, Executors, and Browser Handoffs** when managing `agents external`, `admin executors`, or `open-browser`), recovering required inputs from explicit prompt or recent context without guessing.
4. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher) and load only the selected command page.
5. **Execute the command** with only user-requested or lane-required flags and report exact lifecycle, locator, or `instance-state` outcomes.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **External Agents, Executors, and Browser Handoffs**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Admin callers require an explicit project or `--agent-id`/`--agent-name` target and never default to `agents self`. Verified `agent` callers use `agents self` only for supported self follow-up (`relaunch`, `refresh`/`home`, read-only `instance-state` reads and `mindsets snapshot`), cannot mutate their own `runtime-variables`/`mindsets`/`private-workspace` mappings through self-read routes, and require explicit targets for peer work. Session `join` transitions actor posture only through the parent entrypoint's adoption handoff after `agents self join` succeeds.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `launch` | Launch a project-scoped instance (`--profile` or `--specialist`, `--mode`, `--tmux-server`, `--executor`, `--reuse-home`, `--force`). | [Launch](commands/launch.md) |
| `join` | Adopt a running supported provider session via `agents self join` and operator handoff. | [Join](commands/join.md) |
| `list` | List local live managed instances (`agents global list`) or registered `agents external list`. | [List](commands/list.md) |
| `stop` | Stop a selected managed instance (`agents single ... stop`). | [Stop](commands/stop.md) |
| `relaunch` | Revive or restart a session on its recorded `--tmux-server`/mode without rebuilding home (plus DSH ACP gateway re-attach notes). | [Relaunch](commands/relaunch.md) |
| `cleanup` | Remove stopped-session `session` or `logs` artifacts (`agents single ... cleanup`). | [Cleanup](commands/cleanup.md) |
| `native-resources` | Inspect active `home`, check common skill/MCP freshness, or run qualified `refresh` (never mutates gateway mounts). | [Native Resources](commands/native-resources.md) |
| `runtime-variables` | Read (`agents self`) or CAS-update (`agents single`, `--expected-revision`) non-secret typed instance variables. | [Runtime Variables](commands/runtime-variables.md) |
| `mindsets` | Take atomic fail-closed skill snapshots (`agents self`) or manage revisioned question sets (`agents single`). | [Mindsets](commands/mindsets.md) |
| `private-workspace` | Resolve or manage an individual agent's TOML/SQLite auxiliary workspace (`doctor`, zero drift, `--confirm` cleanup). | [Private Workspace](commands/private-workspace.md) |
| `help` | Read-only summary of lifecycle verbs, `agents external`, `admin executors`, `open-browser`, and `instance-state` boundaries. | **Help** |

## External Agents, Executors, and Browser Handoffs

- **Remote communication-only imports (`agents external`)**: register, inspect, re-verify, or remove local pointers to remotely owned agents on `houmao-passive-server` via `houmao-mgr agents external {register|list|get|verify|remove}` (`register --name <alias> --api-base-url <url> --agent-ref <id-or-name> [--gateway-enabled|--no-gateway-enabled] [--replace]`). `remove` deletes only the local import without stopping or modifying the remote agent.
- **Executor bindings and locators**: pass `--executor <profile>` at launch to bind a trusted execution-owner context; maintain operator-side locators without provisioning contexts or deleting agents via `houmao-mgr admin executors {reconcile|forget}`.
- **Native Web browser handoff (`open-browser`)**: for an active local Kimi Web (`--mode web`) owner, run `houmao-mgr agents single --agent-id|--agent-name ... open-browser` to open the native browser directly; for gateway-issued 60-second single-use Web entry links, use `houmao-shared-routines->houmao-agent-gateway->web-entry()`.

## Help

Summarize project-scoped `launch`, `join`, `list`, `stop`, `relaunch`, stopped-only `cleanup`, `agents external`, `admin executors`, `open-browser`, `native-resources`, `runtime-variables`, `mindsets`, and `private-workspace` (distinct from multi-agent topologies in `houmao-shared-routines->houmao-utils-workspace-mgr`) read-only.

## Guardrails

- DO NOT guess missing launch sources (`--profile` vs `--specialist`), target selectors, or cleanup scopes, or silently replace unavailable `relaunch` with a fresh `launch`.
- DO NOT run `cleanup` against a live session, route instance cleanup to `agents self cleanup` or `admin cleanup runtime`, or treat `agents external remove` / `admin executors forget` as stopping the owning agent.
- DO NOT store secrets in `runtime-variables`, continue a mindset-required skill after `mindsets snapshot` fails, mutate gateway logical mounts from `refresh`, or hand-edit private-workspace TOML/SQLite files.
- DO NOT conflate individual `private-workspace` with multi-agent worktrees (`houmao-shared-routines->houmao-utils-workspace-mgr`) or use `agents self` state commands in `admin` posture.
