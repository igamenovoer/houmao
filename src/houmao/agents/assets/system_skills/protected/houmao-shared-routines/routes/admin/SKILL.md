---
name: houmao-shared-routines
description: Protected admin-audience router composed beneath houmao-admin-entrypoint. It is not a standalone public skill.
license: MIT
---

# Houmao Shared Routines: Admin Route

## Actor Frame Gate

This protected router MUST NOT execute standalone. It accepts only an immutable frame with `actor_kind=admin` and `entrypoint_name=houmao-admin-entrypoint`. If the frame is absent, changed, or agent-scoped, stop and route the caller through `$houmao-admin-entrypoint`. Protected placement is a discovery convention, not authorization.

Preserve `requested_target` and `selected_routine`. Target-sensitive routes require an explicit or unambiguously recovered target and never treat the current session as managed self.

## Direct Subskills

- **project-mgr**: When to Route Here: manage or explain a Houmao project overlay and project-scoped state.
- **credential-mgr**: When to Route Here: manage project or native-agent credentials through supported CLI surfaces.
- **agent-definition**: When to Route Here: manage roles, recipes, launch dossiers, specialists, profiles, or definition-backed launch preparation.
- **operator-messaging**: When to Route Here: clarify and dispatch human-operator messages to one or more managed agents.
- **agent-email-comms**: When to Route Here: perform ordinary mailbox work or operator-origin mailbox posting.
- **adv-usage-pattern**: When to Route Here: compose supported multi-step gateway, notifier, mailbox, and wakeup patterns.
- **utils-workspace-mgr**: When to Route Here: plan, create, validate, or summarize multi-agent workspace topology.
- **ext-graphing**: When to Route Here: author and render supported Plotly.js or Vega-Lite graphing payloads.
- **mailbox-mgr**: When to Route Here: administer mailbox roots, registrations, projections, or late bindings.
- **memory-mgr**: When to Route Here: inspect or change a targeted managed-agent memo or profile memo seed.
- **agent-loop-pro**: When to Route Here: author or operate the schema-rich generated-execplan loop path.
- **agent-loop-lite**: When to Route Here: author or operate the explicit Markdown and direct-SQL lite loop path.
- **agent-instance**: When to Route Here: launch, join, list, stop, relaunch, or clean up managed-agent instances.
- **agent-inspect**: When to Route Here: inspect a targeted managed agent without mutation.
- **agent-messaging**: When to Route Here: prompt, interrupt, queue, send keys, mail, or reset a targeted running agent.
- **agent-gateway**: When to Route Here: operate or inspect a managed-agent gateway, reminders, or notifier state.
- **interop-ag-ui**: When to Route Here: validate, frame, render, publish, route, or interpret AG-UI events.

The agent-only `process-emails-via-gateway` route is intentionally absent.

## Help

Help is read-only. Describe these route names as `$houmao-admin-entrypoint <route> <command>`, never as public `$houmao-<routine>` invocations.
