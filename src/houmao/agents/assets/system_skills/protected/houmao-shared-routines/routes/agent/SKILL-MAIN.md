---
name: houmao-shared-routines
description: Protected managed-agent router composed beneath houmao-agent-entrypoint. It is not a standalone public skill.
license: MIT
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

# Houmao Shared Routines: Agent Route

## Actor Frame Gate

This protected router MUST NOT execute standalone. It accepts only an immutable frame with `actor_kind=agent`, `entrypoint_name=houmao-agent-entrypoint`, and a non-empty `verified_self_identity` produced by `houmao-mgr --print-json agents self identity` for this substantive route. If the frame is absent, changed, or unverified, stop and route the caller through `$houmao-agent-entrypoint`. Protected placement is a discovery convention, not authorization.

Use verified self by default. A peer operation requires an explicit peer target and does not change the actor.

## Direct Subskills

Select exactly one eligible row. Then explicitly load only the listed `SKILL-MAIN.md` entrypoint and the commands or references needed for the selected operation. Do not scan sibling directories, look for nested `SKILL.md`, or invoke a child independently from this parent and its actor frame.

| Route | Load | Routing Guidance |
|---|---|---|
| `process-emails-via-gateway` | `subskills/houmao-process-emails-via-gateway/SKILL-MAIN.md` | When to Route Here: process exactly one notifier-driven unread-mail round with prompt-provided gateway context. |
| `agent-email-comms` | `subskills/houmao-agent-email-comms/SKILL-MAIN.md` | When to Route Here: perform ordinary self mailbox work, transport fallback, or explicit peer mail work. |
| `adv-usage-pattern` | `subskills/houmao-adv-usage-pattern/SKILL-MAIN.md` | When to Route Here: compose supported multi-step gateway, notifier, mailbox, and wakeup patterns. |
| `utils-workspace-mgr` | `subskills/houmao-utils-workspace-mgr/SKILL-MAIN.md` | When to Route Here: inspect or prepare workspace topology using verified-self context and explicit paths. |
| `ext-graphing` | `subskills/houmao-ext-graphing/SKILL-MAIN.md` | When to Route Here: author and render supported Plotly.js or Vega-Lite graphing payloads. |
| `mailbox-mgr` | `subskills/houmao-mailbox-mgr/SKILL-MAIN.md` | When to Route Here: administer the verified agent's mailbox binding or an explicitly scoped mailbox root. |
| `memory-mgr` | `subskills/houmao-memory-mgr/SKILL-MAIN.md` | When to Route Here: inspect or change verified self memory, or an explicitly targeted peer when supported. |
| `agent-loop-pro` | `subskills/houmao-agent-loop-pro/SKILL-MAIN.md` | When to Route Here: author or operate the schema-rich generated-execplan loop path. |
| `agent-loop-lite` | `subskills/houmao-agent-loop-lite/SKILL-MAIN.md` | When to Route Here: author or operate the explicit Markdown and direct-SQL lite loop path. |
| `agent-instance` | `subskills/houmao-agent-instance/SKILL-MAIN.md` | When to Route Here: inspect or operate self-scoped lifecycle follow-up, or an explicit peer route when supported. |
| `agent-inspect` | `subskills/houmao-agent-inspect/SKILL-MAIN.md` | When to Route Here: inspect verified self by default or an explicitly named peer. |
| `agent-messaging` | `subskills/houmao-agent-messaging/SKILL-MAIN.md` | When to Route Here: communicate with an explicitly named peer while retaining the agent actor. |
| `agent-gateway` | `subskills/houmao-agent-gateway/SKILL-MAIN.md` | When to Route Here: operate or inspect the verified agent's gateway, reminders, or notifier state. |
| `interop-ag-ui` | `subskills/houmao-interop-ag-ui/SKILL-MAIN.md` | When to Route Here: validate, frame, render, publish, route, or interpret AG-UI events. |

The admin-only `project-mgr`, `credential-mgr`, `agent-definition`, and `operator-messaging` routes are intentionally absent.

## Help

Help is read-only. Describe these route names as `$houmao-agent-entrypoint <route> <command>`, never as public `$houmao-<routine>` invocations. Do not present an agent welcome.
