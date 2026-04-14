---
name: houmao-agent-inspect
description: Use Houmao's supported read-only inspection surfaces to inspect Houmao-managed agents, including liveness, TUI state, mailbox posture, runtime artifacts, logs, and tmux inspection once the session name is identified.
license: MIT
---

# Houmao Agent Inspect

Use this Houmao skill when the task is to inspect the current state of one Houmao-managed agent without mutating that agent. This is the canonical Houmao-owned skill for generic managed-agent inspection across summary state, transport detail, live screen posture, mailbox posture, runtime artifacts, and logs.

The trigger word `houmao` is intentional. Use the `houmao-agent-inspect` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these read-only inspection actions:

- `discover`
- `screen`
- `mailbox`
- `logs`
- `artifacts`

Supported surfaces for this skill include:

- `houmao-mgr agents list`
- `houmao-mgr agents state`
- `houmao-mgr agents gateway status`
- `houmao-mgr agents gateway tui state|history|watch`
- `houmao-mgr agents mail resolve-live|status|list`
- `houmao-mgr agents mailbox status`
- `houmao-mgr agents turn status|events|stdout|stderr`
- managed-agent HTTP routes under `/houmao/agents/*`, including `/state`, `/state/detail`, `/history`, `/gateway`, `/gateway/tui/*`, `/mail/*`, and `/turns/*`
- runtime-owned artifacts such as `manifest.json`, `gateway/state.json`, `gateway/events.jsonl`, `gateway/logs/gateway.log`, and headless turn artifacts under the session root
- direct local tmux pane capture once managed-agent surfaces have identified the exact tmux session or pane target

This packaged skill does not cover:

- `houmao-mgr agents prompt|interrupt`
- `houmao-mgr agents gateway attach|detach|prompt|interrupt|send-keys`
- mailbox send, reply, post, or archive work
- mailbox registration, unregister, cleanup, or mailbox-root administration
- agent stop, relaunch, cleanup, or other lifecycle mutation
- automatic terminal-recorder workflows when the user did not explicitly ask for replay-grade capture

## Workflow

1. Identify the inspection intent first: discovery, visible screen posture, mailbox posture, logs, or runtime artifacts.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the selected action still lacks a required target, ask the user in Markdown before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Reuse that same chosen launcher for the selected inspection action.
6. Follow the identify-first evidence ladder:
   - identify the target through `agents list` or an explicit selector
   - read summary state through `agents state` or `GET /houmao/agents/{agent_ref}/state`
   - use transport-specific detail through `GET /houmao/agents/{agent_ref}/state/detail`, live gateway status, or live gateway TUI state when needed to recover the exact tmux session name or pane target
   - once the exact tmux session or pane target is identified for a TUI-backed agent, inspect the live pane with local tmux capture before using gateway TUI tracker state or history
   - inspect mailbox posture, logs, or runtime artifacts through the owned read-only surfaces for that domain
   - use direct local tmux attach only when the caller explicitly needs an attached live pane
7. When the caller is already operating through pair-managed HTTP control, allow the matching `/houmao/agents/*` inspection routes instead of forcing a CLI-only path.
8. Load exactly one action page:
   - `actions/discover.md`
   - `actions/screen.md`
   - `actions/mailbox.md`
   - `actions/logs.md`
   - `actions/artifacts.md`

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the intended lane or several required fields need clarification
- Name the command or route you intend to use and show only the missing fields needed for that path.

## Routing Guidance

- Use `actions/discover.md` when you first need to identify the target managed agent, confirm liveness, or decide which deeper inspection lane applies.
- Use `actions/screen.md` when the user wants to inspect what is visible right now for a TUI-backed agent, inspect raw gateway-owned TUI tracker state, or explicitly peek the live tmux pane.
- Use `actions/mailbox.md` when the user wants actor-scoped mailbox identity, unread posture, current live mailbox capability, or late local mailbox-binding posture.
- Use `actions/logs.md` when the user wants headless turn logs, durable turn events, gateway logs, or append-only runtime evidence.
- Use `actions/artifacts.md` when the user wants the durable runtime file inventory, manifest-backed session pointers, or stable artifact paths under the session root.
- Use `houmao-agent-messaging` for prompt, interrupt, queueing, raw input, mailbox send or reply, or reset-context work.
- Use `houmao-agent-gateway` for gateway lifecycle, gateway-only control, reminders, mail-notifier control, or other gateway-owned mutation.
- Use `houmao-mailbox-mgr` for mailbox-root administration, mailbox registrations, projected mailbox structure, or late mailbox binding changes.
- Use `houmao-agent-instance` for stop, relaunch, cleanup, or other lifecycle mutation.

## Guardrails

- Do not guess the target managed agent, transport kind, or intended inspection lane.
- Do not start generic inspection from raw tmux attach, raw pane capture, or direct filesystem spelunking before managed-agent summary and detail surfaces have identified the target and exact tmux session or pane.
- Do not present prompt, interrupt, gateway mutation, mailbox mutation, or lifecycle mutation as part of this inspection skill.
- Do not guess a live `gateway.base_url`, session root, or tmux session name when the supported discovery surfaces have not established them.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not treat `gateway/logs/gateway.log` or `gateway/events.jsonl` as the source of truth for durable manifest or queue state.
- Do not auto-invoke the terminal recorder when the user asked only for ordinary inspection.
