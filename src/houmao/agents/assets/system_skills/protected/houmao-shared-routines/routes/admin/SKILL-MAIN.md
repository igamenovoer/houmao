---
name: houmao-shared-routines
description: Protected admin-audience router composed beneath houmao-admin-entrypoint. It is not a standalone public skill.
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

# Houmao Shared Routines: Admin Route

## Actor Frame Gate

This protected router MUST NOT execute standalone. It accepts only an immutable frame with `actor_kind=admin` and `entrypoint_name=houmao-admin-entrypoint`. If the frame is absent, changed, or agent-scoped, stop and route the caller through `$houmao-admin-entrypoint`. Protected placement is a discovery convention, not authorization.

Preserve `requested_target` and `selected_routine`. Target-sensitive routes require an explicit or unambiguously recovered target and never treat the current session as managed self.

## Direct Subskills

Select exactly one eligible row. Then explicitly load only the listed `SKILL-MAIN.md` entrypoint and the commands or references needed for the selected operation. Do not scan sibling directories, look for nested `SKILL.md`, or invoke a child independently from this parent and its actor frame.

| Route | Load | Routing Guidance |
|---|---|---|
| `project-mgr` | `subskills/houmao-project-mgr/SKILL-MAIN.md` | When to Route Here: manage or explain a Houmao project overlay and project-scoped state. |
| `credential-mgr` | `subskills/houmao-credential-mgr/SKILL-MAIN.md` | When to Route Here: manage project or native-agent credentials through supported CLI surfaces. |
| `agent-definition` | `subskills/houmao-agent-definition/SKILL-MAIN.md` | When to Route Here: manage roles, recipes, launch dossiers, specialists, profiles, or definition-backed launch preparation. |
| `operator-messaging` | `subskills/houmao-operator-messaging/SKILL-MAIN.md` | When to Route Here: clarify and dispatch human-operator messages to one or more managed agents. |
| `agent-email-comms` | `subskills/houmao-agent-email-comms/SKILL-MAIN.md` | When to Route Here: perform ordinary mailbox work or operator-origin mailbox posting. |
| `adv-usage-pattern` | `subskills/houmao-adv-usage-pattern/SKILL-MAIN.md` | When to Route Here: compose supported multi-step gateway, notifier, mailbox, and wakeup patterns. |
| `utils-workspace-mgr` | `subskills/houmao-utils-workspace-mgr/SKILL-MAIN.md` | When to Route Here: plan, create, validate, or summarize multi-agent workspace topology. |
| `ext-graphing` | `subskills/houmao-ext-graphing/SKILL-MAIN.md` | When to Route Here: author and render supported Plotly.js or Vega-Lite graphing payloads. |
| `mailbox-mgr` | `subskills/houmao-mailbox-mgr/SKILL-MAIN.md` | When to Route Here: administer mailbox roots, registrations, projections, or late bindings. |
| `memory-mgr` | `subskills/houmao-memory-mgr/SKILL-MAIN.md` | When to Route Here: inspect or change a targeted managed-agent memo or profile memo seed. |
| `agent-loop-pro` | `subskills/houmao-agent-loop-pro/SKILL-MAIN.md` | When to Route Here: author or operate the schema-rich generated-execplan loop path. |
| `agent-loop-lite` | `subskills/houmao-agent-loop-lite/SKILL-MAIN.md` | When to Route Here: author or operate the explicit Markdown and direct-SQL lite loop path. |
| `agent-instance` | `subskills/houmao-agent-instance/SKILL-MAIN.md` | When to Route Here: launch, join, list, stop, relaunch, or clean up managed-agent instances. |
| `agent-inspect` | `subskills/houmao-agent-inspect/SKILL-MAIN.md` | When to Route Here: inspect a targeted managed agent without mutation. |
| `agent-messaging` | `subskills/houmao-agent-messaging/SKILL-MAIN.md` | When to Route Here: prompt, interrupt, queue, send keys, mail, or reset a targeted running agent. |
| `agent-gateway` | `subskills/houmao-agent-gateway/SKILL-MAIN.md` | When to Route Here: operate or inspect a managed-agent gateway, reminders, or notifier state. |
| `interop-ag-ui` | `subskills/houmao-interop-ag-ui/SKILL-MAIN.md` | When to Route Here: validate, frame, render, publish, route, or interpret AG-UI events. |

The agent-only `process-emails-via-gateway` route is intentionally absent.

## Help

Help is read-only. Describe these route names as `$houmao-admin-entrypoint <route> <command>`, never as public `$houmao-<routine>` invocations.
