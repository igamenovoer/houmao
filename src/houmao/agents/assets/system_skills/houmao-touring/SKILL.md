---
name: houmao-touring
description: Use Houmao's manual guided touring skill to orient first-time or re-orienting users across project setup, mailbox setup, specialist authoring, launches, live-agent operations, and lifecycle follow-up.
license: MIT
---

# Houmao Touring

Use this Houmao skill only when the user explicitly asks for `houmao-touring` or clearly asks for a first-time guided Houmao tour. This is a manual guided tour skill, not the default entrypoint for ordinary direct-operation requests.

`houmao-touring` is intentionally above the direct-operation skills. It inspects current Houmao state, explains the current posture in plain language, offers the next likely branches, and routes the selected work to the maintained Houmao-owned skill that owns that surface.

The trigger word `houmao` is intentional. Use the `houmao-touring` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers a branching guided tour for:

- current-state orientation
- project overlay setup or inspection
- project-local mailbox setup or inspection
- specialist creation
- optional easy-profile creation
- easy-instance launch
- post-launch prompt entry
- gateway or TUI state watching
- ordinary mailbox send or read entry
- reminders
- managed-agent list, stop, relaunch, and cleanup follow-up

This packaged skill does not cover:

- ordinary direct-operation requests that the user did not ask to route through the tour
- low-level command ownership for project, mailbox, specialist, messaging, gateway, or lifecycle actions
- ad hoc filesystem editing under `.houmao/`, runtime, or mailbox paths
- destructive cleanup as an automatic side effect of stop

## Workflow

1. Confirm that the user explicitly wants the guided touring experience instead of one narrow direct-operation task.
2. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
3. Start from current-state orientation rather than assuming the tour begins at project initialization:
   - inspect project posture through `houmao-mgr project status`
   - inspect reusable specialists through `houmao-mgr project easy specialist list` or `houmao-mgr project easy specialist get --name <name>` when the branch needs them
   - inspect reusable profiles through `houmao-mgr project easy profile list` or `houmao-mgr project easy profile get --name <name>` when the branch needs them
   - inspect running managed agents through `houmao-mgr agents list`
   - inspect one live managed agent through `houmao-mgr agents state`, `houmao-mgr agents gateway status`, or `houmao-mgr agents mail resolve-live` when the branch needs live capability
4. Explain the current posture in plain language and offer the next likely branches.
5. Load exactly one branch page for the next selected tour branch:
   - `branches/orient.md`
   - `branches/setup-project-and-mailbox.md`
   - `branches/author-and-launch.md`
   - `branches/live-operations.md`
   - `branches/lifecycle-follow-up.md`
6. Route execution to the maintained Houmao-owned skill that owns the selected branch.
7. After that branch completes, summarize the new current state and offer the next likely branches again.

## Branches

- Read [branches/orient.md](branches/orient.md) to inspect current Houmao posture and present the next likely tour branches.
- Read [branches/setup-project-and-mailbox.md](branches/setup-project-and-mailbox.md) when the user wants project overlay setup or optional project-local mailbox setup.
- Read [branches/author-and-launch.md](branches/author-and-launch.md) when the user wants to create specialists or profiles, or launch another agent.
- Read [branches/live-operations.md](branches/live-operations.md) when the user wants to prompt a running agent, watch gateway or TUI state, send mailbox work, or create reminders.
- Read [branches/lifecycle-follow-up.md](branches/lifecycle-follow-up.md) when the user wants to inspect, stop, relaunch, or clean up managed-agent sessions.

## References

- Read [references/question-style.md](references/question-style.md) when the tour needs to ask for user input in a first-time-user-friendly way with explanations, examples, and recommended defaults or skip options.

## Routing Guidance

- Route project overlay setup or explanation to `houmao-project-mgr`.
- Route mailbox administration to `houmao-mailbox-mgr`.
- Route specialist or profile authoring plus easy-instance launch to `houmao-specialist-mgr`.
- Route ordinary prompt or mailbox-routing entry for running agents to `houmao-agent-messaging`.
- Route gateway watch and reminder work to `houmao-agent-gateway`.
- Route ordinary mailbox send, read, reply, or mark-read follow-up to `houmao-agent-email-comms`.
- Route managed-agent list, stop, relaunch, and cleanup follow-up to `houmao-agent-instance`.

## Guardrails

- Do not activate `houmao-touring` unless the user explicitly asked for the guided tour experience.
- Do not force a linear step order or restart the user from project initialization when current Houmao state already exists.
- Do not claim ownership of the direct-operation command shapes that belong to the maintained Houmao skill families.
- Do not invent top-level `houmao-mgr easy ...` or `houmao-mgr specialists ...` commands; reusable specialist and profile inspection lives under `houmao-mgr project easy ...`.
- Do not collapse stop, relaunch, and cleanup into one vague “manage agent” action.
- Do not ask terse operator-style missing-input questions when the tour needs first-time-user guidance; use the question-style reference instead.
- Do not auto-run cleanup after stop or treat cleanup as safe for a live session.
