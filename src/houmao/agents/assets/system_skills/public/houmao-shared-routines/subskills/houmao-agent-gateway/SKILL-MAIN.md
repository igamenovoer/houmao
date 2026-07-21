---
name: houmao-agent-gateway
description: Use when a live Houmao managed-agent gateway must be attached, detached, discovered, operated, or inspected, including gateway services, reminders, and mail-notifier behavior.
license: MIT
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

# Houmao Agent Gateway

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent; otherwise stop before gateway routing.

- Admin branch: require the managed-agent target whose gateway is being operated or inspected; never treat the operator shell as self.
- Agent branch: require freshly verified self identity and use the verified agent's gateway by default. A peer gateway requires an explicit target and a supported cross-agent route.

Preserve the branch and target through lifecycle, discovery, reminders, services, and notifier commands.

Use this Houmao skill when the task is specifically about the managed agent gateway itself: attaching or detaching the live sidecar, discovering the current live gateway from inside or outside the attached session, using gateway-only control or inspection surfaces, managing ranked live reminders, or managing the gateway mail-notifier. For broader managed-agent inspection outside those gateway-owned concerns, use `houmao-shared-routines->houmao-agent-inspect`.

The trigger word `houmao` is intentional. Enter this parent-scoped routine only through `houmao-shared-routines->houmao-agent-gateway`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$houmao-shared-routines agent-gateway help`, `help for houmao-agent-gateway`, `usage for houmao-agent-gateway`, `available functionality for houmao-agent-gateway`, or what this skill can do, answer from this section before choosing a gateway action, reference page, command, HTTP route, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me enable the mail notifier", route to the matching workflow instead of stopping at generic help.

Purpose: operate the managed-agent gateway sidecar itself, including lifecycle, discovery, gateway-only control, reminders, and mail-notifier behavior.

Available functionality:

- Attach, detach, and inspect live gateway lifecycle state.
- Discover the current live gateway from inside or outside the attached session.
- Use gateway-only prompt, interrupt, raw input, TUI state, history, watch, and note-prompt surfaces.
- List, create, update, pause, or remove ranked live reminders.
- Inspect, enable, or disable gateway mail-notifier behavior.

Common starting prompts:

- `$houmao-shared-routines agent-gateway help`
- `$houmao-shared-routines agent-gateway discover for <agent>`
- `$houmao-shared-routines agent-gateway reminders list for <agent>`
- `$houmao-shared-routines agent-gateway mail-notifier status for <agent>`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-agent-instance` for starting, stopping, relaunching, or cleaning up the agent process.
- Use `houmao-shared-routines->houmao-agent-inspect` for generic liveness, mailbox posture, runtime artifacts, logs, or tmux inspection.
- Use `houmao-shared-routines->houmao-agent-messaging` for ordinary prompt, interrupt, raw input, or mailbox handoff.
- Use `houmao-shared-routines->houmao-agent-email-comms` for the shared `/v1/mail/*` mailbox contract.

## Subcommands

This packaged skill covers exactly these gateway actions:

- `help` (read-only meta operation)
- `lifecycle`
- `discover`
- `gateway-services`
- `reminders`
- `mail-notifier`

Supported surfaces for this skill include:

- `houmao-mgr agents single --agent-id <id> gateway attach|detach|status` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway prompt|interrupt|send-keys` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway tui state|history|watch|note-prompt` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway reminders list|get|create|set|remove` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway mail-notifier status|enable|disable` or `--agent-name <name>`
- `houmao-mgr agents self gateway ...` for the current managed tmux session
- `houmao-mgr agents self mail resolve-live`
- live gateway env vars `HOUMAO_AGENT_GATEWAY_HOST`, `HOUMAO_AGENT_GATEWAY_PORT`, `HOUMAO_GATEWAY_PROTOCOL_VERSION`, and `HOUMAO_GATEWAY_STATE_PATH`
- live gateway HTTP routes under `/v1/status`, `/v1/requests`, `/v1/control/*`, `/v1/reminders`, and `/v1/mail-notifier`
- pair-managed HTTP routes under `/houmao/agents/{agent_ref}/gateway*`, including `/gateway/reminders*`

This packaged skill does not cover:

- `houmao-mgr project agents launch`, `houmao-mgr agents self join`, and selected lifecycle under `houmao-mgr agents single ...`
- generic managed-agent inspection of liveness, mailbox posture, runtime artifacts, non-gateway logs, or tmux backing when the target is not gateway-specific
- ordinary transport-neutral `houmao-mgr agents single ... prompt|interrupt` or `houmao-mgr agents self prompt|interrupt`
- transport-specific mailbox internals
- the full `/v1/mail/*` route contract
- direct editing of runtime files under `.houmao/`
- retired gateway discovery env such as `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT`

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Identify which gateway intent the user actually wants: lifecycle, current-session discovery, gateway-only control, reminders, or mail-notifier.
2. If the request is really about generic managed-agent inspection rather than a gateway-owned concern, route it to `houmao-shared-routines->houmao-agent-inspect`.
3. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
4. If the selected action still lacks a required target or direct-gateway input, ask the user in Markdown before proceeding.
5. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
6. Reuse that same chosen launcher for the selected gateway action.
7. For supported `houmao-mgr agents single ... gateway ...` or `houmao-mgr agents self gateway ...` command authoring, build the direct command before executing:
   - `agents.single.gateway.status|attach|detach|prompt|interrupt|send-keys`
   - `agents.self.gateway.status|attach|detach|prompt|interrupt|send-keys`
   - `agents.single.gateway.tui.state|history|watch|note-prompt`
   - `agents.self.gateway.tui.state|history|watch|note-prompt`
   - `agents.single.gateway.mail-notifier.status|enable|disable`
   - `agents.self.gateway.mail-notifier.status|enable|disable`
   - `agents.single.gateway.reminders.list|get|create|set|remove`
   - `agents.self.gateway.reminders.list|get|create|set|remove`
8. Include only fields the user explicitly supplied or that were recovered from explicit recent context.
9. If required input is missing or explicit inputs conflict, stop and recover the missing or conflicting input before running the target command.
10. Prefer the managed-agent seam first for outside callers:
   - `houmao-mgr agents single ... gateway ...` for selected-agent CLI-driven work
   - `houmao-mgr agents self gateway ...` for current-session CLI-driven work
   - `/houmao/agents/*/gateway...` for pair-managed HTTP control
11. When the caller is already the attached agent or another process inside the same managed tmux session:
   - use manifest-first current-session discovery through `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` second
   - use live gateway env only after the task genuinely needs direct gateway `/v1/...` HTTP
   - run `agents self mail resolve-live` when shared mailbox work needs the exact current-session live `gateway.base_url`
12. Load exactly one action page:
   - `commands/lifecycle.md`
   - `commands/discover.md`
   - `commands/gateway-services.md`
   - `commands/reminders.md`
   - `commands/mail-notifier.md`
13. Use the local references only when you need the routing boundary or the HTTP route summary:
   - `references/scope-and-routing.md`
   - `references/http-surface.md`


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected gateway path, such as managed-agent selector, action, direct gateway base URL, prompt body, key sequence, reminder fields, notifier action, or interval
  - `Optional`: launcher preference, gateway lane, execution posture, output format, reminder options, notifier filters, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when the intended lane or several required fields need clarification
- Name the command or route you intend to use and show only the missing fields needed for that path.
- DO NOT use this format for user-task or domain-intent questions unless the question is about Houmao runtime behavior.

## Routing Guidance

- Use `commands/lifecycle.md` when the user wants to attach, detach, or inspect the live gateway from outside the attached agent session.
- Use `commands/discover.md` when the user needs to find the live gateway from inside the attached session or decide whether to stay on the managed-agent seam versus direct gateway `/v1/...`.
- Use `commands/gateway-services.md` when the task needs gateway-owned control, queued gateway requests, raw input delivery, TUI inspection, or headless session control.
- Use `commands/reminders.md` when the task is to create, inspect, update, pause, or delete ranked live reminders for the attached agent.
- Use `commands/mail-notifier.md` when the user wants background open-mail prompting through the live gateway.
- Use `houmao-shared-routines->houmao-agent-inspect` for generic managed-agent liveness, mailbox posture, runtime artifacts, non-gateway logs, or tmux-backing inspection.
- Use `houmao-shared-routines->houmao-agent-instance` for starting or stopping the managed agent itself.
- Use `houmao-shared-routines->houmao-agent-messaging` for ordinary prompt, interrupt, or mailbox routing across already-running managed agents.
- Use `houmao-shared-routines->houmao-agent-email-comms` for the exact shared `/v1/mail/*` route contract after you already have the correct live `gateway.base_url`.

## Guardrails

- DO NOT treat gateway attach or detach as the same thing as launching or stopping the managed agent.
- DO NOT present this skill as the canonical owner of generic managed-agent inspection when the request is not gateway-specific.
- DO NOT guess the target managed agent, current-session manifest, or live gateway host and port.
- DO NOT skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- DO NOT probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- DO NOT teach `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT` as supported current-session discovery.
- DO NOT scrape live gateway env for shared mailbox work when `agents.self.mail.resolve-live` is the supported exact current-session `gateway.base_url` resolver.
- DO NOT describe `/v1/reminders` as durable across gateway stop or restart.
- DO NOT invent reminder surfaces beyond the supported `houmao-mgr agents single ... gateway reminders ...`, `houmao-mgr agents self gateway reminders ...`, `/houmao/agents/{agent_ref}/gateway/reminders...`, and direct `/v1/reminders` routes.
- DO NOT invent alternate gateway CLI shapes; use the direct scoped gateway commands shown in this skill package.
- DO NOT restate transport-specific mailbox detail here; delegate that to the mailbox skill family.
