---
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

# Platform Boundaries

## Purpose

Use this page whenever generated loops touch Houmao platform operations rather than loop-local generated contracts.

## Core Boundary

- Generated loop material owns loop semantics.
- Maintained Houmao skills and CLI surfaces own platform mechanics.
- Do not duplicate maintained platform contracts inside generated loop skills, generated harnesses, or routed pages.

## Maintained Skill Ownership

- `houmao-shared-routines->houmao-utils-workspace-mgr`: workspace planning, creation, validation, and summaries.
- `houmao-shared-routines->houmao-mailbox-mgr`: mailbox setup, inspection, repair, cleanup, export, registration, and late mailbox binding.
- `houmao-shared-routines->houmao-agent-email-comms`: ordinary mail status, list, read, send, post, reply, mark, move, and archive operations.
- `houmao-shared-routines->houmao-process-emails-via-gateway`: notifier-driven open-mail rounds when the current round provides the gateway base URL.
- `houmao-shared-routines->houmao-agent-messaging`: managed-agent prompt, interrupt, mailbox handoff, and gateway-backed communication routing.
- `houmao-shared-routines->houmao-agent-gateway`: gateway lifecycle, notifier posture, reminders, and gateway posture.
- `houmao-shared-routines->houmao-agent-instance`: managed-agent launch, join, relaunch, stop, and lifecycle control.
- `houmao-shared-routines->houmao-agent-definition`: specialist, project-profile, launch-dossier, credential-defaulting, and pre-launch definition preparation. Treat `houmao-mgr project ...` as its underlying CLI surface for this skill.
- `houmao-shared-routines->houmao-memory-mgr`: memo seed and memory posture.
- `houmao-shared-routines->houmao-agent-inspect`: managed-agent liveness, TUI state, mailbox posture, runtime artifacts, logs, and tmux inspection.

## Generated Material Ownership

- `execplan/specs/`: loop machine contracts.
- `execplan/skills/`: generated role instructions, event handlers, tick handlers, and operator skills.
- `execplan/agents/`: participant-to-agent bindings, prompt sources, installed generated skills, Houmao system-skill preinstall posture, workspace policy, and notifier prompt text.
- `execplan/harness/`: loop-local validation, query, rendering, dynamic lookup, and controlled record application.
- `execplan/docs/`: generated human support views.

## Workspace Rule

- When a generated loop needs managed agent workspaces, `prepare-agents` first resolves concrete agent/project-profile facts when workspace setup needs agent or profile names.
- `prepare-workspace` adapts generated workspace contracts, generated agent bindings, and prepared agent/profile facts to `houmao-shared-routines->houmao-utils-workspace-mgr` `plan`, `create`, `validate`, or `summarize`.
- Generated workspace contracts may describe launch cwd, work roots, task `shared-kb/`, task `owner-states/<subdir>/...`, per-agent `states/`, shared resources, read/write rules, workspace-manager inputs, validation commands, and readiness postconditions.
- Do not create agent workspaces directly from general execution pages when the workspace manager can represent the layout.
- Keep workspace preparation separate from agent preparation; neither stage calls the other.
- Manual workspace setup is acceptable only when explicit readiness evidence satisfies the generated workspace contract.

## Launch Rule

- `prepare-agents` prepares launchable project profiles and prepared agent facts; it does not launch live agents as normal behavior.
- `validate-loop` checks read-only pre-launch readiness before `launch-agents`; do not fold live workspace readiness into `validate-execplan`.
- `launch-agents` uses maintained Houmao launch surfaces to start prepared agents and report live-agent/session facts.
- `start` sends the first loop trigger after agents are live; it does not launch agents.

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

## Operator Control Rule

- Generated loops may define one loop-local `<loop-slug>-operator-control` skill for lifecycle semantics, mode switching, manual stepping, and routing to generated harness commands.
- Generated operator-control skills own loop identity and loop-local control decisions, not platform mechanics.
- Generated harnesses may record requested control changes, run state, execution mode, operator intent events, and observed notifier posture.
- Enabling, disabling, or inspecting notifier posture remains owned by `houmao-shared-routines->houmao-agent-gateway`.
- Prompting agents remains owned by `houmao-shared-routines->houmao-agent-messaging`; ordinary mail operations remain owned by `houmao-shared-routines->houmao-agent-email-comms`.

## Harness Rule

Generated harnesses do not own:
- mailbox delivery;
- managed-agent launch;
- gateway discovery;
- memory management;
- workspace planning, creation, validation, or summaries.

Generated harnesses do own loop-local deterministic helpers such as validation, lookup, rendering, state initialization, state query, record validation, and controlled record application.
