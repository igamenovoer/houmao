---
name: houmao-agent-gateway
description: Use Houmao's supported gateway lifecycle and gateway-only control surfaces to attach, discover, operate, and inspect a live managed-agent gateway, including reminders and mail-notifier behavior.
license: MIT
---

# Houmao Agent Gateway

Use this Houmao skill when the task is specifically about the managed agent gateway itself: attaching or detaching the live sidecar, discovering the current live gateway from inside or outside the attached session, using gateway-only control or inspection surfaces, managing ranked live reminders, or managing the gateway mail-notifier.

The trigger word `houmao` is intentional. Use the `houmao-agent-gateway` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these gateway actions:

- `lifecycle`
- `discover`
- `gateway-services`
- `reminders`
- `mail-notifier`

Supported surfaces for this skill include:

- `houmao-mgr agents gateway attach|detach|status`
- `houmao-mgr agents gateway prompt|interrupt|send-keys`
- `houmao-mgr agents gateway tui state|history|watch|note-prompt`
- `houmao-mgr agents gateway mail-notifier status|enable|disable`
- `houmao-mgr agents mail resolve-live`
- live gateway env vars `HOUMAO_AGENT_GATEWAY_HOST`, `HOUMAO_AGENT_GATEWAY_PORT`, `HOUMAO_GATEWAY_PROTOCOL_VERSION`, and `HOUMAO_GATEWAY_STATE_PATH`
- live gateway HTTP routes under `/v1/status`, `/v1/requests`, `/v1/control/*`, `/v1/reminders`, and `/v1/mail-notifier`
- pair-managed HTTP routes under `/houmao/agents/{agent_ref}/gateway*`

This packaged skill does not cover:

- `houmao-mgr agents launch|join|stop|relaunch|cleanup`
- ordinary transport-neutral `houmao-mgr agents prompt|interrupt`
- transport-specific mailbox internals
- the full `/v1/mail/*` route contract
- direct editing of runtime files under `.houmao/`
- retired gateway discovery env such as `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT`

## Workflow

1. Identify which gateway intent the user actually wants: lifecycle, current-session discovery, gateway-only control, reminders, or mail-notifier.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the selected action still lacks a required target or direct-gateway input, ask the user in Markdown before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Reuse that same chosen launcher for the selected gateway action.
6. Prefer the managed-agent seam first for outside callers:
   - `houmao-mgr agents gateway ...` for CLI-driven work
   - `/houmao/agents/*/gateway...` for pair-managed HTTP control
7. When the caller is already the attached agent or another process inside the same managed tmux session:
   - use manifest-first current-session discovery through `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` second
   - use live gateway env only after the task genuinely needs direct gateway `/v1/...` HTTP
   - use `houmao-mgr agents mail resolve-live` when shared mailbox work needs the exact live `gateway.base_url`
8. Load exactly one action page:
   - `actions/lifecycle.md`
   - `actions/discover.md`
   - `actions/gateway-services.md`
   - `actions/reminders.md`
   - `actions/mail-notifier.md`
9. Use the local references only when you need the routing boundary or the HTTP route summary:
   - `references/scope-and-routing.md`
   - `references/http-surface.md`

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the intended lane or several required fields need clarification
- Name the command or route you intend to use and show only the missing fields needed for that path.

## Routing Guidance

- Use `actions/lifecycle.md` when the user wants to attach, detach, or inspect the live gateway from outside the attached agent session.
- Use `actions/discover.md` when the user needs to find the live gateway from inside the attached session or decide whether to stay on the managed-agent seam versus direct gateway `/v1/...`.
- Use `actions/gateway-services.md` when the task needs gateway-owned control, queued gateway requests, raw input delivery, TUI inspection, or headless session control.
- Use `actions/reminders.md` when the task is to create, inspect, update, pause, or delete ranked live reminders for the attached agent.
- Use `actions/mail-notifier.md` when the user wants background unread-mail prompting through the live gateway.
- Use `houmao-agent-instance` for starting or stopping the managed agent itself.
- Use `houmao-agent-messaging` for ordinary prompt, interrupt, or mailbox routing across already-running managed agents.
- Use `houmao-agent-email-comms` for the exact shared `/v1/mail/*` route contract after you already have the correct live `gateway.base_url`.

## Guardrails

- Do not treat gateway attach or detach as the same thing as launching or stopping the managed agent.
- Do not guess the target managed agent, current-session manifest, or live gateway host and port.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not teach `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT` as supported current-session discovery.
- Do not scrape live gateway env for shared mailbox work when `houmao-mgr agents mail resolve-live` is the supported exact `gateway.base_url` resolver.
- Do not describe `/v1/reminders` as durable across gateway stop or restart.
- Do not invent unsupported pair-managed reminder routes under `/houmao/agents/{agent_ref}/gateway/reminders`.
- Do not restate transport-specific mailbox detail here; delegate that to the mailbox skill family.
