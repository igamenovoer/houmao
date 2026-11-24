---
name: houmao-agent-gateway
description: Use when a Houmao managed-agent gateway needs attachment, deployment configuration, discovery, browser entry, live control, reminders, or mail-notifier management.
license: MIT
metadata:
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

## Workflow

1. **Answer explicit help** from [Help](#help) before target discovery, command execution, or action-page loading.
2. **Validate actor and target** using [Actor Frame Gate](#actor-frame-gate). Recover explicit inputs from the request first and recent context second. Ask about any required input still missing or conflicting.
3. **Choose the owning operation** from [Subcommands](#subcommands) and load only its linked page. Use [Routing Guidance](#routing-guidance) when the task belongs to another routine.
4. **Select one manager launcher** for the turn. Honor an explicit choice. Otherwise, use `command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr` if absent, then an appropriate workspace launcher if those cannot satisfy the task.
5. **Use the supported scope** with the known inputs. Prefer scoped manager commands or an already selected pair-managed route. Consult the [gateway HTTP summary](references/http-surface.md) when the request needs direct HTTP and the target and caller authority are established.
6. **Report the operation result** from the selected gateway without exposing proof material or browser entry links.

If the request does not map cleanly to this workflow, use the native planning tool to select a route from the validated actor, target, and gateway capabilities, then follow the owning operation.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent; otherwise stop before gateway routing.

- Admin branch: require the managed-agent target whose gateway is being operated or inspected; never treat the operator shell as self.
- Agent branch: require freshly verified self identity and use the verified agent's gateway by default. A peer gateway requires an explicit target and a supported cross-agent route.

Preserve the branch and target through each operation. Browser entry requires an explicit selection in the target's owner execution context.

Use this Houmao skill when the task is specifically about the managed agent gateway itself: attaching or detaching the live sidecar, discovering the current live gateway from inside or outside the attached session, using gateway-only control or inspection surfaces, managing ranked live reminders, or managing the gateway mail-notifier. For broader managed-agent inspection outside those gateway-owned concerns, use `houmao-shared-routines->houmao-agent-inspect`.

The trigger word `houmao` is intentional. Enter this parent-scoped routine only through `houmao-shared-routines->houmao-agent-gateway`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$houmao-shared-routines agent-gateway help`, `help for houmao-agent-gateway`, `usage for houmao-agent-gateway`, `available functionality for houmao-agent-gateway`, or what this skill can do, answer from this section before choosing a gateway action, reference page, command, HTTP route, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me enable the mail notifier", route to the matching workflow instead of stopping at generic help.

Purpose: operate the managed-agent gateway sidecar itself, including lifecycle, discovery, gateway-only control, reminders, and mail-notifier behavior.

Available functionality:

- Attach, detach, and inspect live gateway lifecycle state.
- Discover the current live gateway from inside or outside the attached session.
- Issue one private, short-lived browser link for a live managed Web agent.
- Use gateway-only prompt, interrupt, raw input, TUI state, history, watch, and note-prompt surfaces.
- List, create, update, pause, or remove ranked live reminders.
- Inspect, enable, or disable gateway mail-notifier behavior.

Common starting prompts:

- `$houmao-shared-routines agent-gateway help`
- `$houmao-shared-routines agent-gateway discover for <agent>`
- `$houmao-admin-entrypoint agent-gateway web-entry for <agent>`
- `$houmao-shared-routines agent-gateway reminders list for <agent>`
- `$houmao-shared-routines agent-gateway mail-notifier status for <agent>`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-agent-instance` for starting, stopping, relaunching, or cleaning up the agent process.
- Use `houmao-shared-routines->houmao-agent-inspect` for generic liveness, mailbox posture, runtime artifacts, logs, or tmux inspection.
- Use `houmao-shared-routines->houmao-agent-messaging` for ordinary prompt, interrupt, raw input, or mailbox handoff.
- Use `houmao-shared-routines->houmao-agent-email-comms` for the shared `/v1/mail/*` mailbox contract.
- Use `houmao-shared-routines->houmao-agent-access` for retained policy, live roster changes, or signed peer requests.
- Use `houmao-shared-routines->houmao-agent-files` for a gateway's versioned logical mounts.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `help` | Explain gateway operations and owning routes. | [Help](#help) |
| `lifecycle` | Attach, detach, inspect, or configure a gateway sidecar. | [Lifecycle](commands/lifecycle.md) |
| `discover` | Establish the current target's live gateway coordinates and available scope. | [Discover](commands/discover.md) |
| `gateway-services` | Operate gateway-only prompt, input, TUI, or headless surfaces. | [Gateway Services](commands/gateway-services.md) |
| `web-entry` | Issue one private browser link for a live managed Web agent. | [Web Entry](commands/web-entry.md) |
| `reminders` | Inspect or manage ranked live reminders. | [Reminders](commands/reminders.md) |
| `mail-notifier` | Inspect or manage background unread-mail notifications. | [Mail Notifier](commands/mail-notifier.md) |

Supported surfaces for this skill include:

- `houmao-mgr agents single --agent-id <id> gateway attach|detach|status` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway prompt|interrupt|send-keys` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway tui state|history|watch|note-prompt` or `--agent-name <name>`
- `houmao-mgr agents single --agent-id <id> gateway web-entry` or `--agent-name <name>` from the owner execution context
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
- Use `commands/web-entry.md` when the execution owner wants a short-lived browser link to the selected live Web agent.
- Use `commands/reminders.md` when the task is to create, inspect, update, pause, or delete ranked live reminders for the attached agent.
- Use `commands/mail-notifier.md` when the user wants background open-mail prompting through the live gateway.
- Use `houmao-shared-routines->houmao-agent-inspect` for generic managed-agent liveness, mailbox posture, runtime artifacts, non-gateway logs, or tmux-backing inspection.
- Use `houmao-shared-routines->houmao-agent-instance` for starting or stopping the managed agent itself.
- Use `houmao-shared-routines->houmao-agent-messaging` for ordinary prompt, interrupt, or mailbox routing across already-running managed agents.
- Use `houmao-shared-routines->houmao-agent-email-comms` for the exact shared `/v1/mail/*` route contract after you already have the correct live `gateway.base_url`.
- Use `houmao-shared-routines->houmao-agent-access` to provision or inspect retained policy, change live administrator enrollment, or call the selected gateway with a verified peer signer.
- Use `houmao-shared-routines->houmao-agent-files` for mount discovery, draft edits, and publication. Use `houmao-shared-routines->houmao-agent-instance->native-resources()` for native skill and MCP freshness.

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
- DO NOT treat a reachable endpoint as permission to call a protected operation.
- DO NOT place a one-time entry URL, key, or proof in a report, shared log, or recorded prompt.
