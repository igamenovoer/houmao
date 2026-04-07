---
name: houmao-agent-messaging
description: Use Houmao's supported messaging and control surfaces to communicate with already-running managed agents through prompt, interrupt, gateway, raw-input, mailbox routing, or reset-context workflows, preferring live gateway-backed delivery when available.
license: MIT
---

# Houmao Agent Messaging

Use this Houmao skill when you need to communicate with an already-running Houmao-managed agent, whether the caller is another agent with an installed Houmao skill home or an external operator working from outside the managed session.

The trigger word `houmao` is intentional. Use the `houmao-agent-messaging` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these managed-agent communication and control actions:

- `discover`
- `prompt`
- `interrupt`
- `gateway-queue`
- `send-keys`
- `mail-handoff`
- `reset-context`

Supported surfaces for this skill include:

- `houmao-mgr agents state`
- `houmao-mgr agents gateway status`
- `houmao-mgr agents mail resolve-live`
- `houmao-mgr agents prompt`
- `houmao-mgr agents interrupt`
- `houmao-mgr agents gateway prompt`
- `houmao-mgr agents gateway interrupt`
- `houmao-mgr agents gateway send-keys`
- `houmao-mgr agents gateway tui state|history|note-prompt`
- managed-agent HTTP routes under `/houmao/agents/*`

This packaged skill does not cover:

- `houmao-mgr agents launch|join|stop|relaunch|cleanup`
- `houmao-mgr project easy specialist create|list|get|remove`
- `houmao-mgr project easy instance launch|list|get|stop`
- ordinary mailbox `status|check|read|send|reply|mark-read` operations
- mailbox transport-specific filesystem or Stalwart internals
- gateway attach or detach lifecycle work
- direct filesystem editing under runtime or mailbox paths

## Workflow

1. Identify which messaging intent the user actually wants: discovery, ordinary prompt with gateway preference, interrupt, explicit gateway queueing, raw control input, mailbox handoff, or reset-context.
2. Recover the target managed-agent selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the selected action still lacks a required target or explicit message input, ask the user in Markdown before proceeding.
4. Resolve the correct `houmao-mgr` launcher for the current workspace in this order:
   - repo-local `.venv/bin/houmao-mgr`
   - `pixi run houmao-mgr` when the workspace shows development-project hints such as `pixi.lock`, `.pixi/`, `pixi.toml`, or a Pixi-managed `pyproject.toml`
   - `uv run houmao-mgr` when the workspace shows project-local uv hints such as `uv.lock` or a uv-managed `pyproject.toml`
   - globally installed `houmao-mgr` from uv tools for the ordinary end-user case
5. Reuse that same resolved launcher for the selected messaging action.
6. Prefer the managed-agent seam first:
   - `houmao-mgr agents ...` for CLI-driven work
   - `/houmao/agents/*` for pair-managed HTTP control
7. Before ordinary prompt or mailbox handoff work, resolve current live gateway capability unless the current prompt or recent chat context already provides that fact explicitly:
   - use `houmao-mgr agents gateway status` or `GET /houmao/agents/{agent_ref}/gateway` for prompt-lane gateway decisions
   - use `houmao-mgr agents mail resolve-live` or `GET /houmao/agents/{agent_ref}/mail/resolve-live` for mailbox bindings and the exact live `gateway.base_url`
   - when mailbox work is required, use that discovery result to hand off to `houmao-agent-email-comms` for ordinary mailbox actions or `houmao-process-emails-via-gateway` for one unread-email round
8. Use direct gateway `/v1/...` HTTP only when the task genuinely needs gateway-only control behavior and the exact live `gateway.base_url` is already available from current context or supported discovery.
9. Load exactly one action page:
   - `actions/discover.md`
   - `actions/prompt.md`
   - `actions/interrupt.md`
   - `actions/gateway-queue.md`
   - `actions/send-keys.md`
   - `actions/mail.md`
   - `actions/reset-context.md`
10. Use the local references only when you need the intent matrix or the managed-agent HTTP route summary:
   - `references/intent-matrix.md`
   - `references/managed-agent-http.md`

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the intended lane or several required fields need clarification
- Name the command or route you intend to use and show only the missing fields needed for that path.

## Routing Guidance

- Use `actions/discover.md` when you first need to identify the target managed agent or discover current gateway and mailbox capability.
- Use `actions/prompt.md` when the user wants one normal conversational turn; discover gateway availability first and prefer the gateway-backed prompt lane when a live gateway exists.
- Use `actions/interrupt.md` when the user wants the transport-neutral interrupt path for one managed agent.
- Use `actions/gateway-queue.md` when the user explicitly wants gateway queue management, raw gateway-owned TUI inspection, or prompt-note provenance beyond the ordinary gateway-preferred prompt path.
- Use `actions/send-keys.md` when the user needs exact key delivery such as slash-command menus, arrow navigation, `Escape`, or partial typing in a live TUI session.
- Use `actions/mail.md` when the target has mailbox capability and you need to route the work to the correct mailbox skill after resolving live bindings.
- Use `actions/reset-context.md` when the user wants clear-context, reset-then-send, or next-prompt chat-session control.

## Guardrails

- Do not guess the target managed agent, gateway base URL, mailbox capability, or intended messaging lane.
- Do not skip live gateway discovery when prompt or outgoing mailbox routing depends on whether the target currently has a gateway.
- Do not treat raw `send-keys` as a substitute for ordinary prompt-turn work.
- Do not redirect raw terminal shaping to `agents prompt` or `agents gateway prompt`.
- Do not guess a direct gateway host or port when the exact live `gateway.base_url` is not already available.
- Do not treat this skill as the owner of ordinary mailbox operations; hand mailbox work to `houmao-agent-email-comms` or `houmao-process-emails-via-gateway`.
- Do not restate filesystem mailbox layout, Stalwart transport detail, or the `/v1/mail/*` contract in full here; delegate that work to the mailbox skills.
- Do not invent unsupported `houmao-mgr` reset-context flags.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for managed-agent messaging.
