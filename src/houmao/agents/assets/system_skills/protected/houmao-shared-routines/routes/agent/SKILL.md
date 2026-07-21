---
name: houmao-shared-routines
description: Protected managed-agent router composed beneath houmao-agent-entrypoint. It is not a standalone public skill.
license: MIT
---

# Houmao Shared Routines: Agent Route

## Actor Frame Gate

This protected router MUST NOT execute standalone. It accepts only an immutable frame with `actor_kind=agent`, `entrypoint_name=houmao-agent-entrypoint`, and a non-empty `verified_self_identity` produced by `houmao-mgr --print-json agents self identity` for this substantive route. If the frame is absent, changed, or unverified, stop and route the caller through `$houmao-agent-entrypoint`. Protected placement is a discovery convention, not authorization.

Use verified self by default. A peer operation requires an explicit peer target and does not change the actor.

## Direct Subskills

- **process-emails-via-gateway**: When to Route Here: process exactly one notifier-driven unread-mail round with prompt-provided gateway context.
- **agent-email-comms**: When to Route Here: perform ordinary self mailbox work, transport fallback, or explicit peer mail work.
- **adv-usage-pattern**: When to Route Here: compose supported multi-step gateway, notifier, mailbox, and wakeup patterns.
- **utils-workspace-mgr**: When to Route Here: inspect or prepare workspace topology using verified-self context and explicit paths.
- **ext-graphing**: When to Route Here: author and render supported Plotly.js or Vega-Lite graphing payloads.
- **mailbox-mgr**: When to Route Here: administer the verified agent's mailbox binding or an explicitly scoped mailbox root.
- **memory-mgr**: When to Route Here: inspect or change verified self memory, or an explicitly targeted peer when supported.
- **agent-loop-pro**: When to Route Here: author or operate the schema-rich generated-execplan loop path.
- **agent-loop-lite**: When to Route Here: author or operate the explicit Markdown and direct-SQL lite loop path.
- **agent-instance**: When to Route Here: inspect or operate self-scoped lifecycle follow-up, or an explicit peer route when supported.
- **agent-inspect**: When to Route Here: inspect verified self by default or an explicitly named peer.
- **agent-messaging**: When to Route Here: communicate with an explicitly named peer while retaining the agent actor.
- **agent-gateway**: When to Route Here: operate or inspect the verified agent's gateway, reminders, or notifier state.
- **interop-ag-ui**: When to Route Here: validate, frame, render, publish, route, or interpret AG-UI events.

The admin-only `project-mgr`, `credential-mgr`, `agent-definition`, and `operator-messaging` routes are intentionally absent.

## Help

Help is read-only. Describe these route names as `$houmao-agent-entrypoint <route> <command>`, never as public `$houmao-<routine>` invocations. Do not present an agent welcome.
