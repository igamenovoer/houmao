---
name: houmao-admin-welcome
description: Read-only first-use orientation for a human operator choosing a Houmao workflow. Use implicitly only for first-use, orientation, comparison, or guided-tour intent; concrete operational requests belong at houmao-admin-entrypoint.
license: MIT
---

# Houmao Admin Welcome

This public skill is the read-only guide for a human operator. It teaches the Houmao model, inspects narrowly scoped state when useful, and hands executable work to `$houmao-admin-entrypoint`. It is a sibling of the admin entrypoint and contains no protected routines.

## Read-Only Gate

Welcome may read documentation, list project state, inspect whether a Houmao project overlay exists, and compare available paths. It MUST NOT create or edit files, credentials, mailboxes, gateways, messages, agent definitions, agent instances, workspaces, loop state, or runtime state. It MUST NOT send prompts or mail, start or stop services, launch or stop agents, adopt a session, or invoke a mutating protected route.

If the user asks to perform concrete work, stop the welcome route and hand the request to `$houmao-admin-entrypoint` with all known context. Do not silently execute it from welcome.

## Commands

- `help`: explain the welcome boundary and command surface; read [commands/help.md](commands/help.md).
- `show-options`: compare the five curated guided paths; read [commands/show-options.md](commands/show-options.md).
- `choose-path`: select a path from the user's goal and current posture; read [commands/choose-path.md](commands/choose-path.md).
- `show-command-map`: show public admin-entrypoint invocations without exposing protected skills as standalone selectors; read [commands/show-command-map.md](commands/show-command-map.md).
- `next-step`: choose one read-only next orientation step; read [commands/next-step.md](commands/next-step.md).
- `start-guided-tour`: inspect the current posture and begin a curated path; read [commands/start-guided-tour.md](commands/start-guided-tour.md) and [references/orientation.md](references/orientation.md).

An empty invocation is equivalent to `start-guided-tour`.

## Curated Paths

The five maintained paths are Single Agent Full Run, Operator-Controlled Agent Team, Pro Agent Loop, Subsystem Exploration, and Existing Project Reorientation. Read [references/orientation.md](references/orientation.md) to classify current posture. Read [references/guided-paths.md](references/guided-paths.md) only after selecting a path; it contains the teaching sequences and exact handoff prompts. Read [references/concepts.md](references/concepts.md) for the self-contained concept glossary and [references/question-style.md](references/question-style.md) for explanatory welcome questions.

## Handoff Contract

Use [references/admin-handoff.md](references/admin-handoff.md). Preserve the selected path, explicit project or agent targets, current posture, constraints, confirmed choices, unresolved required inputs, and the requested operation. The executable invocation always starts with `$houmao-admin-entrypoint`; protected route names may follow it as arguments but never appear as `$houmao-*` public skill invocations.

## Trigger Boundary

Implicit activation is narrow: first-use orientation, “what can Houmao do,” path comparison, guided-tour requests, and reorientation. A concrete request such as “stop agent X,” “send this message,” or “create a credential” bypasses welcome and enters `$houmao-admin-entrypoint` directly.
