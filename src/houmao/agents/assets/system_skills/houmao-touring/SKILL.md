---
name: houmao-touring
description: Use Houmao's manual guided touring skill to orient first-time or re-orienting users across project setup, mailbox setup, specialist authoring, launches, live-agent operations, and lifecycle follow-up.
license: MIT
---

# Houmao Touring

Use this Houmao skill only when the user explicitly asks for `houmao-touring` or clearly asks for a first-time guided Houmao tour. This is a manual guided tour skill, not the default entrypoint for ordinary direct-operation requests.

`houmao-touring` is intentionally above the direct-operation skills. It inspects current Houmao state, explains the current posture in plain language, offers the next likely branches, and routes the selected work to the maintained Houmao-owned skill that owns that surface.

The trigger word `houmao` is intentional. Use the `houmao-touring` skill name directly when you intend to activate this Houmao-owned skill.

## Welcome Message

When the user starts the guided tour, present a concise welcome before or alongside the current-state orientation. Keep it user-facing, adapt it to the current project state, and do not imply that the user must restart from the beginning when Houmao state already exists.

Suggested baseline:

Welcome to Houmao. Houmao is a framework and CLI toolkit for orchestrating teams of loosely coupled CLI-based AI agents such as Claude, Codex, and Gemini. Each agent is a real CLI process with its own disk state, memory, and native TUI; Houmao coordinates the team through reusable specialists, mailbox messaging, per-agent gateways, and loop plans.

A typical first setup path is:

1. Create or inspect a Houmao project and initialize the mailbox root.
2. Create a specialist: customize its system prompt, choose the provider/tooling posture, and select credentials.
3. Create an optional launch profile: set the agent name, working directory, launch defaults, and any extra system prompt customization.
4. Set up and register the agent mail account.
5. Launch the agent. The default tour posture is a visible TUI managed agent with a foreground gateway sidecar; when mailbox is ready, enable gateway mail-notifier polling every 5 seconds so the agent can process new mail.

Start by checking what already exists here, then suggest the next likely branch instead of restarting from scratch.

## Scope

This packaged skill covers a branching guided tour for:

- current-state orientation
- project overlay setup or inspection
- project-local mailbox setup or inspection
- specialist creation
- optional easy-profile creation
- easy-instance launch
- post-launch prompt entry
- post-launch read-only inspection or screen watching
- ordinary mailbox send or read entry
- gateway mail-notifier follow-up when a live gateway and mailbox are both ready
- reminders
- advanced pairwise agent-loop creation guidance
- managed-agent inspection, stop, relaunch, and cleanup follow-up

This packaged skill does not cover:

- ordinary direct-operation requests that the user did not ask to route through the tour
- low-level command ownership for project, mailbox, specialist, messaging, gateway, loop-planning, or lifecycle actions
- ad hoc filesystem editing under `.houmao/`, runtime, or mailbox paths
- destructive cleanup as an automatic side effect of stop

## Workflow

1. Confirm that the user explicitly wants the guided touring experience instead of one narrow direct-operation task.
2. Present the welcome message, including the typical first setup path, unless the recent conversation already covered it.
3. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
4. Start from current-state orientation rather than assuming the tour begins at project initialization:
   - inspect project posture through `houmao-mgr project status`
   - inspect reusable specialists through `houmao-mgr project easy specialist list` or `houmao-mgr project easy specialist get --name <name>` when the branch needs them
   - inspect reusable profiles through `houmao-mgr project easy profile list` or `houmao-mgr project easy profile get --name <name>` when the branch needs them
   - inspect running managed agents through `houmao-mgr agents list`
   - inspect one live managed agent through `houmao-mgr agents state`, `houmao-mgr agents gateway status`, or `houmao-mgr agents mail resolve-live` when the branch needs live capability
5. Explain the current posture in plain language and offer the next likely branches.
6. Load exactly one branch page for the next selected tour branch:
   - `branches/orient.md`
   - `branches/setup-project-and-mailbox.md`
   - `branches/author-and-launch.md`
   - `branches/live-operations.md`
   - `branches/advanced-usage.md`
   - `branches/lifecycle-follow-up.md`
7. Route execution to the maintained Houmao-owned skill that owns the selected branch.
8. After that branch completes, summarize the new current state and offer the next likely branches again.

## Branches

- Read [branches/orient.md](branches/orient.md) to inspect current Houmao posture and present the next likely tour branches.
- Read [branches/setup-project-and-mailbox.md](branches/setup-project-and-mailbox.md) when the user wants project overlay setup or optional project-local mailbox setup.
- Read [branches/author-and-launch.md](branches/author-and-launch.md) when the user wants to create specialists or profiles, or launch another agent.
- Read [branches/live-operations.md](branches/live-operations.md) when the user wants to prompt a running agent, inspect live state or screen posture, send mailbox work, enable automatic mailbox polling through the gateway, or create reminders.
- Read [branches/advanced-usage.md](branches/advanced-usage.md) when the user wants tour-level guidance for advanced pairwise agent-loop creation through `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2`.
- Read [branches/lifecycle-follow-up.md](branches/lifecycle-follow-up.md) when the user wants to inspect, stop, relaunch, or clean up managed-agent sessions.

## References

- Read [references/question-style.md](references/question-style.md) when the tour needs to ask for user input in a first-time-user-friendly way with explanations, examples, and recommended defaults or skip options.

## Routing Guidance

- Route project overlay setup or explanation to `houmao-project-mgr`.
- Route mailbox administration to `houmao-mailbox-mgr`.
- Route specialist or profile authoring plus easy-instance launch to `houmao-specialist-mgr`.
- Route generic managed-agent inspection, live screen watching, mailbox-posture inspection, and runtime artifact inspection to `houmao-agent-inspect`.
- Route ordinary prompt or mailbox-routing entry for running agents to `houmao-agent-messaging`.
- Route gateway watch, gateway mail-notifier, and reminder work to `houmao-agent-gateway`.
- Route ordinary mailbox send, read, reply, or archive follow-up to `houmao-agent-email-comms`.
- Route advanced stable pairwise loop creation to `houmao-agent-loop-pairwise` only after the user selects or explicitly invokes that skill.
- Route advanced enriched pairwise loop creation to `houmao-agent-loop-pairwise-v2` only after the user selects or explicitly invokes that skill.
- Route elemental immediate driver-worker edge protocol details to `houmao-adv-usage-pattern`, not to the touring skill.
- Route stop, relaunch, and cleanup follow-up to `houmao-agent-instance`.

## Guardrails

- Do not activate `houmao-touring` unless the user explicitly asked for the guided tour experience.
- Do not force a linear step order or restart the user from project initialization when current Houmao state already exists.
- Do not claim ownership of the direct-operation command shapes that belong to the maintained Houmao skill families.
- Do not invent top-level `houmao-mgr easy ...` or `houmao-mgr specialists ...` commands; reusable specialist and profile inspection lives under `houmao-mgr project easy ...`.
- Do not collapse stop, relaunch, and cleanup into one vague “manage agent” action.
- Do not ask terse operator-style missing-input questions when the tour needs first-time-user guidance; use the question-style reference instead.
- Do not silently auto-route generic pairwise loop planning or pairwise run-control requests into `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2`; ask the user to select or explicitly invoke the desired pairwise skill.
- Do not restate composed pairwise topology, run-control details, or elemental pairwise edge-loop protocol inline; keep those on the selected pairwise loop skill and `houmao-adv-usage-pattern`.
- Do not auto-run cleanup after stop or treat cleanup as safe for a live session.
