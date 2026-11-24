---
name: houmao-agent-messaging
description: Use when an already-running Houmao managed agent needs a prompt, interrupt, gateway queue item, raw terminal input, mailbox handoff, or context reset.
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

# Houmao Agent Messaging

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Select an operation from **Subcommands** and apply **Actor Frame Gate**.
2. If the request is really about generic read-only inspection of liveness, mailbox posture, logs, runtime artifacts, or tmux backing, route it to `houmao-shared-routines->houmao-agent-inspect` instead of handling it as messaging.
3. Recover the target managed-agent selector from the current prompt first and recent chat context second when it was stated explicitly.
4. If the selected action still lacks a required target or explicit message input, ask the user in Markdown before proceeding.
5. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
6. Reuse that same chosen launcher for the selected messaging action.
7. Use managed records and capabilities to resolve the target. Select a peer with `agents single --agent-id` or `--agent-name`, select verified self with `agents self`, or preserve the caller's pair-managed `/houmao/agents/*` scope.
8. When an ordinary mail request supplies a name, resolve its address for the selected channel using `agents single ... mail resolve-live`. Published contact is sufficient for addressing the message. Hand off delivery through the verified sender's `agents self mail send --channel <channel>` workflow in `houmao-shared-routines->houmao-agent-email-comms`. Reserve gateway verification for tasks that require it, such as a notifier-driven open-mail round in `houmao-shared-routines->houmao-process-emails-via-gateway`.
9. Use direct gateway HTTP only with the exact live target and its supported authorization. Use `houmao-shared-routines->houmao-agent-access` when the caller needs an independently signed request.
10. Load the selected command page from **Subcommands**.
11. Use the local references only when you need the intent matrix or the managed-agent HTTP route summary:
   - `references/intent-matrix.md`
   - `references/managed-agent-http.md`


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent; otherwise stop before messaging routing.

- Admin branch: act for the human operator and require an explicit managed-agent target before prompt, interrupt, gateway, key, mail, or reset work.
- Agent branch: require freshly verified self identity. Messaging is peer-directed, so require an explicit peer target and keep the caller in the agent actor.

Do not infer target identity from the current pane or promote an agent caller into the admin actor.

Use this Houmao skill to communicate with a managed agent as a verified agent or an external operator. Prompts need a reachable runtime. Mail can reach a registered address while the recipient is offline. For generic read-only inspection, use `houmao-shared-routines->houmao-agent-inspect`.

The trigger word `houmao` is intentional. Enter this parent-scoped routine only through `houmao-shared-routines->houmao-agent-messaging`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$houmao-shared-routines agent-messaging help`, `help for houmao-agent-messaging`, `usage for houmao-agent-messaging`, `available functionality for houmao-agent-messaging`, or what this skill can do, answer from this section before choosing a messaging action, gateway or mailbox route, command, HTTP route, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me send this prompt to an agent", route to the matching workflow instead of stopping at generic help.

Purpose: communicate with already-running Houmao-managed agents through supported prompt, interrupt, gateway, raw-input, mailbox handoff, and reset-context surfaces.

Available functionality:

- Discover target agents and current gateway or mailbox capability.
- Send ordinary prompts, interrupts, policy-controlled gateway prompts, and raw key input.
- Resolve recipient contact and route mailbox work through `mail` (alias `mail-handoff`).
- Apply reset-context or reset-then-send workflow guidance.

Common starting prompts:

- `$houmao-shared-routines agent-messaging help`
- `$houmao-shared-routines agent-messaging prompt <agent> with "<message>"`
- `$houmao-shared-routines agent-messaging interrupt <agent>`
- `$houmao-shared-routines agent-messaging reset context for <agent>`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-agent-inspect` for generic read-only liveness, mailbox posture, logs, artifacts, or tmux inspection.
- Use `houmao-shared-routines->houmao-agent-gateway` for gateway attach, detach, reminders, mail-notifier, or gateway-owned mutation.
- Use `houmao-shared-routines->houmao-agent-email-comms` for ordinary mailbox actions after mailbox routing is selected.
- Use `houmao-shared-routines->houmao-agent-instance` for live-agent launch, stop, relaunch, or cleanup.

## Subcommands

| Subcommand | Detail | Use For |
| --- | --- | --- |
| `help` | [Help](#help) | Read-only usage. |
| `discover` | [Discover](commands/discover.md) | Resolve identity, liveness, or messaging capability. |
| `request` | [Request](commands/request.md) | Send quoted work through the target's requester permission. |
| `prompt` | [Prompt](commands/prompt.md) | Submit one verbatim managed prompt with direct-input authority. |
| `interrupt` | [Interrupt](commands/interrupt.md) | Request a transport-neutral interruption. |
| `gateway-queue` | [Gateway Queue](commands/gateway-queue.md) | Use explicit gateway admission or queue behavior. |
| `send-keys` | [Send Keys](commands/send-keys.md) | Deliver exact raw TUI keys. Alias `raw-input`. |
| `mail` | [Mail](commands/mail.md) | Resolve contact and route to mailbox delivery. Alias `mail-handoff`. |
| `reset-context` | [Reset Context](commands/reset-context.md) | Reset or select a supported conversation context. |

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
- DO NOT use this format for user-task or domain-intent questions unless the question is about Houmao runtime behavior.

## Routing Guidance

- Use `houmao-shared-routines->houmao-agent-inspect` when the user wants generic managed-agent inspection of current liveness, mailbox posture, runtime artifacts, logs, or direct tmux backing.
- Use `commands/discover.md` when you first need to identify the target managed agent or discover current gateway and mailbox capability.
- Use `commands/prompt.md` for one normal conversational turn through the managed prompt command.
- Use `commands/interrupt.md` when the user wants the transport-neutral interrupt path for one managed agent.
- Use `commands/gateway-queue.md` when the user explicitly wants a gateway prompt-admission policy, gateway-owned TUI inspection, or prompt-note provenance.
- Use `commands/send-keys.md` when the user needs exact key delivery such as slash-command menus, arrow navigation, `Escape`, or partial typing in a live TUI session.
- Use `commands/mail.md` to resolve contact or route work to the mailbox skill.
- Use `commands/reset-context.md` when the user wants clear-context, reset-then-send, or next-prompt chat-session control.

## Guardrails

- DO NOT guess the target managed agent, gateway base URL, mailbox capability, or intended messaging lane.
- DO NOT present this skill as the owner of generic managed-agent inspection; use `houmao-shared-routines->houmao-agent-inspect` for that broader read-only work.
- DO NOT use gateway-specific control or a notifier round without verifying live gateway availability.
- DO NOT treat raw `send-keys` as a substitute for ordinary prompt-turn work.
- DO NOT redirect raw terminal shaping to `agents single ... prompt`, `agents self prompt`, or gateway prompt surfaces.
- DO NOT guess a direct gateway host or port when the exact live `gateway.base_url` is not already available.
- DO NOT skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- DO NOT probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- DO NOT treat this skill as the owner of ordinary mailbox operations; hand mailbox work to `houmao-shared-routines->houmao-agent-email-comms` or `houmao-shared-routines->houmao-process-emails-via-gateway`.
- DO NOT restate filesystem mailbox layout, Stalwart transport detail, or the `/v1/mail/*` contract in full here; delegate that work to the mailbox skills.
- DO NOT invent unsupported `houmao-mgr` reset-context flags.
- DO NOT use deprecated `houmao-cli` or removed standalone CAO launcher workflows for managed-agent messaging.
