---
name: houmao-agent-messaging
description: Use Houmao's supported messaging and control surfaces to communicate with already-running managed agents through prompt, interrupt, gateway, raw-input, mailbox routing, or reset-context workflows, preferring live gateway-backed delivery when available.
license: MIT
---

# Houmao Agent Messaging

## Actor Frame Gate

This protected routine MUST NOT execute standalone. Require an immutable frame from `houmao-admin-entrypoint` or `houmao-agent-entrypoint`; otherwise stop and direct the caller through the matching public entrypoint.

- Admin branch: act for the human operator and require an explicit managed-agent target before prompt, interrupt, gateway, key, mail, or reset work.
- Agent branch: require freshly verified self identity. Messaging is peer-directed, so require an explicit peer target and keep the caller in the agent actor.

Do not infer target identity from the current pane or promote an agent caller into the admin actor.

Use this Houmao skill when you need to communicate with an already-running Houmao-managed agent, whether the caller is another agent with an installed Houmao skill home or an external operator working from outside the managed session. If the real task is generic read-only managed-agent inspection rather than communication, use `<public-entrypoint>->houmao-shared-routines->agent-inspect` instead.

The trigger word `houmao` is intentional. Enter this protected routine only through the actor-qualified route `<public-entrypoint>->houmao-shared-routines->agent-messaging`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$<public-entrypoint> agent-messaging help`, `help for houmao-agent-messaging`, `usage for houmao-agent-messaging`, `available functionality for houmao-agent-messaging`, or what this skill can do, answer from this section before choosing a messaging action, gateway or mailbox route, command, HTTP route, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me send this prompt to an agent", route to the matching workflow instead of stopping at generic help.

Purpose: communicate with already-running Houmao-managed agents through supported prompt, interrupt, gateway, raw-input, mailbox handoff, and reset-context surfaces.

Available functionality:

- Discover target agents and current gateway or mailbox capability.
- Send ordinary prompts, interrupts, policy-controlled gateway prompts, and raw key input.
- Route mailbox handoff work to the correct mailbox skill after resolving live bindings.
- Apply reset-context or reset-then-send workflow guidance.

Common starting prompts:

- `$<public-entrypoint> agent-messaging help`
- `$<public-entrypoint> agent-messaging prompt <agent> with "<message>"`
- `$<public-entrypoint> agent-messaging interrupt <agent>`
- `$<public-entrypoint> agent-messaging reset context for <agent>`

Related skills and boundaries:

- Use `<public-entrypoint>->houmao-shared-routines->agent-inspect` for generic read-only liveness, mailbox posture, logs, artifacts, or tmux inspection.
- Use `<public-entrypoint>->houmao-shared-routines->agent-gateway` for gateway attach, detach, reminders, mail-notifier, or gateway-owned mutation.
- Use `<public-entrypoint>->houmao-shared-routines->agent-email-comms` for ordinary mailbox actions after mailbox routing is selected.
- Use `<public-entrypoint>->houmao-shared-routines->agent-instance` for live-agent launch, stop, relaunch, or cleanup.

## Scope

This packaged skill covers exactly these managed-agent communication and control actions:

- `help` (read-only meta operation)
- `discover`
- `prompt`
- `interrupt`
- `gateway-queue`
- `send-keys`
- `mail-handoff`
- `reset-context`

Supported surfaces for this skill include:

- `houmao-mgr agents single --agent-id <id> state` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway status` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> mail resolve-live` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> prompt` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> interrupt` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway prompt|interrupt|send-keys` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway tui state|history|note-prompt` or `--agent-name <name>`
- `houmao-mgr agents self prompt|interrupt|gateway|mail` for the current managed tmux session
- managed-agent HTTP routes under `/houmao/agents/*`

This packaged skill does not cover:

- `houmao-mgr project agents launch`, `houmao-mgr agents self join`, and selected lifecycle under `houmao-mgr agents single ...`
- `houmao-mgr project specialist create|list|get|remove`
- `houmao-mgr project agents launch|list|get|stop`
- generic managed-agent inspection of liveness, mailbox posture, runtime artifacts, logs, or direct tmux backing
- ordinary mailbox `status|list|peek|read|send|reply|archive` operations
- mailbox transport-specific filesystem or Stalwart internals
- gateway attach or detach lifecycle work
- direct filesystem editing under runtime or mailbox paths

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Identify which messaging intent the user actually wants: discovery, ordinary prompt with gateway preference, interrupt, explicit gateway prompt admission, raw control input, mailbox handoff, or reset-context.
2. If the request is really about generic read-only inspection of liveness, mailbox posture, logs, runtime artifacts, or tmux backing, route it to `<public-entrypoint>->houmao-shared-routines->agent-inspect` instead of handling it as messaging.
3. Recover the target managed-agent selector from the current prompt first and recent chat context second when it was stated explicitly.
4. If the selected action still lacks a required target or explicit message input, ask the user in Markdown before proceeding.
5. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
6. Reuse that same chosen launcher for the selected messaging action.
7. Prefer the managed-agent seam first:
   - `houmao-mgr agents single ...` for selected-agent CLI-driven work
   - `houmao-mgr agents self ...` for current-session CLI-driven work
   - `/houmao/agents/*` for pair-managed HTTP control
8. Before ordinary prompt or mailbox handoff work, resolve current live gateway capability unless the current prompt or recent chat context already provides that fact explicitly:
   - use `houmao-mgr agents single ... gateway status`, `houmao-mgr agents self gateway status`, or `GET /houmao/agents/{agent_ref}/gateway` for prompt-lane gateway decisions
   - use `houmao-mgr agents single ... mail resolve-live`, `houmao-mgr agents self mail resolve-live`, or `GET /houmao/agents/{agent_ref}/mail/resolve-live` for mailbox bindings and the exact live `gateway.base_url`
   - when mailbox work is required, use that discovery result to hand off to `<public-entrypoint>->houmao-shared-routines->agent-email-comms` for ordinary mailbox actions or `<public-entrypoint>->houmao-shared-routines->process-emails-via-gateway` for one open-mail round
9. Use direct gateway `/v1/...` HTTP only when the task genuinely needs gateway-only control behavior and the exact live `gateway.base_url` is already available from current context or supported discovery.
10. Load exactly one action page:
   - `commands/discover.md`
   - `commands/prompt.md`
   - `commands/interrupt.md`
   - `commands/gateway-queue.md`
   - `commands/send-keys.md`
   - `commands/mail.md`
   - `commands/reset-context.md`
11. Use the local references only when you need the intent matrix or the managed-agent HTTP route summary:
   - `references/intent-matrix.md`
   - `references/managed-agent-http.md`

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected messaging path, such as managed-agent selector, action, prompt text, interrupt body, key sequence, mailbox intent, reset-context intent, or direct gateway base URL
  - `Optional`: launcher preference, gateway preference, mailbox route preference, output format, raw-input modifiers, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when the intended lane or several required fields need clarification
- Name the command or route you intend to use and show only the missing fields needed for that path.
- Do not use this format for user-task or domain-intent questions unless the question is about Houmao runtime behavior.

## Routing Guidance

- Use `<public-entrypoint>->houmao-shared-routines->agent-inspect` when the user wants generic managed-agent inspection of current liveness, mailbox posture, runtime artifacts, logs, or direct tmux backing.
- Use `commands/discover.md` when you first need to identify the target managed agent or discover current gateway and mailbox capability.
- Use `commands/prompt.md` when the user wants one normal conversational turn; discover gateway availability first and prefer the gateway-backed prompt lane when a live gateway exists.
- Use `commands/interrupt.md` when the user wants the transport-neutral interrupt path for one managed agent.
- Use `commands/gateway-queue.md` when the user explicitly wants a nondefault gateway prompt-admission policy, raw gateway-owned TUI inspection, or prompt-note provenance beyond the ordinary gateway-preferred prompt path.
- Use `commands/send-keys.md` when the user needs exact key delivery such as slash-command menus, arrow navigation, `Escape`, or partial typing in a live TUI session.
- Use `commands/mail.md` when the target has mailbox capability and you need to route the work to the correct mailbox skill after resolving live bindings.
- Use `commands/reset-context.md` when the user wants clear-context, reset-then-send, or next-prompt chat-session control.

## Guardrails

- Do not guess the target managed agent, gateway base URL, mailbox capability, or intended messaging lane.
- Do not present this skill as the owner of generic managed-agent inspection; use `<public-entrypoint>->houmao-shared-routines->agent-inspect` for that broader read-only work.
- Do not skip live gateway discovery when prompt or outgoing mailbox routing depends on whether the target currently has a gateway.
- Do not treat raw `send-keys` as a substitute for ordinary prompt-turn work.
- Do not redirect raw terminal shaping to `agents single ... prompt`, `agents self prompt`, or gateway prompt surfaces.
- Do not guess a direct gateway host or port when the exact live `gateway.base_url` is not already available.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not treat this skill as the owner of ordinary mailbox operations; hand mailbox work to `<public-entrypoint>->houmao-shared-routines->agent-email-comms` or `<public-entrypoint>->houmao-shared-routines->process-emails-via-gateway`.
- Do not restate filesystem mailbox layout, Stalwart transport detail, or the `/v1/mail/*` contract in full here; delegate that work to the mailbox skills.
- Do not invent unsupported `houmao-mgr` reset-context flags.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows for managed-agent messaging.
