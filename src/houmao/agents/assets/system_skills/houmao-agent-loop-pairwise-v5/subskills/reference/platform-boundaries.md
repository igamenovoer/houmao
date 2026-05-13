# Platform Boundaries

## Purpose

Use this page whenever generated loops touch Houmao platform operations rather than loop-local generated contracts.

## Core Boundary

- Generated loop material owns loop semantics.
- Maintained Houmao skills and CLI surfaces own platform mechanics.
- Do not duplicate maintained platform contracts inside generated loop skills, generated harnesses, or v5 routed pages.

## Maintained Skill Ownership

- `houmao-utils-workspace-mgr`: workspace planning and creation.
- `houmao-mailbox-mgr`: mailbox setup, inspection, repair, cleanup, export, registration, and late mailbox binding.
- `houmao-agent-email-comms`: ordinary mail status, list, read, send, post, reply, mark, move, and archive operations.
- `houmao-process-emails-via-gateway`: notifier-driven open-mail rounds when the current round provides the gateway base URL.
- `houmao-agent-messaging`: managed-agent prompt, interrupt, mailbox handoff, and gateway-backed communication routing.
- `houmao-agent-gateway`: gateway lifecycle, notifier posture, reminders, and gateway posture.
- `houmao-agent-instance`: managed-agent launch, join, relaunch, stop, and lifecycle control.
- `houmao-specialist-mgr` and supported `houmao-mgr project easy` surfaces: specialist/profile preparation when needed.
- `houmao-memory-mgr`: memo seed and memory posture.
- `houmao-agent-inspect`: managed-agent liveness, TUI state, mailbox posture, runtime artifacts, logs, and tmux inspection.

## Generated Material Ownership

- `execplan/specs/`: loop machine contracts.
- `execplan/skills/`: generated role instructions, event handlers, tick handlers, and operator skills.
- `execplan/agents/`: participant-to-agent bindings, prompt sources, installed generated skills, support skills, workspace policy, and notifier prompt text.
- `execplan/harness/`: loop-local validation, query, rendering, dynamic lookup, and controlled record application.
- `execplan/docs/`: generated human support views.

## Workspace Rule

- When a generated loop needs managed agent workspaces, `prepare-workspace` adapts generated workspace contracts to `houmao-utils-workspace-mgr`.
- Generated workspace contracts may describe launch cwd, work roots, shared resources, writable temp/artifact paths, notes paths, read/write rules, workspace-manager inputs, and readiness postconditions.
- Do not create agent workspaces directly from general execution pages when the workspace manager can represent the layout.
- Keep workspace preparation separate from agent preparation; neither stage calls the other.

## Mail And Gateway Rule

Generated loop skills must not implement:
- custom mailbox storage;
- custom mailbox state management;
- ad hoc gateway discovery;
- local substitutes for ordinary mail send, read, reply, and archive behavior.

Generated loops may define:
- message families;
- payload schemas;
- render templates;
- reply expectations;
- loop-local state effects caused by mail.

## Harness Rule

Generated harnesses do not own:
- mailbox delivery;
- managed-agent launch;
- gateway discovery;
- memory management;
- workspace creation.

Generated harnesses do own loop-local deterministic helpers such as validation, lookup, rendering, state initialization, state query, record validation, and controlled record application.
