---
name: houmao-agent-messaging
description: Use when a Houmao managed agent must receive an attributed work `request`, direct `prompt`, `interrupt`, `gateway-queue` submission, raw `send-keys`, `mail` handoff, or `reset-context` action.
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

## Overview

Communicate with running Houmao-managed agents across strictly separated channels: attributed `request` (`agent-requester` default), verbatim `prompt` (`agent-operator`), `interrupt`, `gateway-queue`, raw TUI `send-keys`, `mail` handoff, and `reset-context`.

## Workflow

1. **Answer explicit `help` first** from **Help** without probing targets or sending messages.
2. **Enforce the Actor Frame Gate**: require an explicit target in `admin` posture; in verified `agent` posture, messaging is peer-directed so require an explicit peer target while keeping `actor_kind=agent` (route read-only inspection to `houmao-shared-routines->houmao-agent-inspect`).
3. **Select the exact channel** from **Subcommands** (consulting [references/intent-matrix.md](references/intent-matrix.md) or [references/managed-agent-http.md](references/managed-agent-http.md) when choosing between `request`, `prompt`, `gateway-queue`, `send-keys`, `mail`, and out-of-band `houmao-cccc` group chat).
4. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher) and ask for any missing target or message body before execution.
5. **Execute the selected command page** and report exact delivery or refusal evidence without silently retrying across another channel.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, [references/intent-matrix.md](references/intent-matrix.md), and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Never infer target identity from the enclosing pane or promote a peer-messaging `agent` caller into `admin`. Route ordinary `/v1/mail/*` operations after contact resolution to `houmao-shared-routines->houmao-agent-email-comms`, notifier rounds to `houmao-shared-routines->houmao-process-emails-via-gateway`, gateway lifecycle/reminders/`houmao-cccc` plugin attach to `houmao-shared-routines->houmao-agent-gateway`, and policy/key grants to `houmao-shared-routines->houmao-agent-access`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `discover` | Resolve target liveness, run mode (`headless`, `service`, `tui`, `web`), gateway, or mail contact. | [Discover](commands/discover.md) |
| `request` | Submit quoted, attributed task work (`--text`) under target `agent-requester` permission (`agent.request.submit`). | [Request](commands/request.md) |
| `prompt` | Submit one verbatim turn under `agent-operator` direct-input authority (`agent.prompt.direct`) across `claude`, `codex`, `dsh`, and `kimi`. | [Prompt](commands/prompt.md) |
| `interrupt` | Request transport-neutral interruption (`agents single\|self interrupt`). | [Interrupt](commands/interrupt.md) |
| `gateway-queue` | Submit gateway prompts with explicit `--admission-policy ready-only\|if-no-pending\|always` or TUI provenance. | [Gateway Queue](commands/gateway-queue.md) |
| `send-keys` | Deliver exact raw TUI keystrokes (`Escape`, arrows, slash menus; alias `raw-input`). | [Send Keys](commands/send-keys.md) |
| `mail` | Resolve recipient contact (`mail resolve-live`) and hand off to `houmao-agent-email-comms` (alias `mail-handoff`). | [Mail](commands/mail.md) |
| `reset-context` | Reset or prepare next-prompt conversation session context where supported. | [Reset Context](commands/reset-context.md) |
| `help` | Read-only overview of channel separation (`request` vs `prompt` vs `send-keys` vs `mail` vs `houmao-cccc`). | **Help** |

## Channel Separation and `houmao-cccc` Boundary (`Help`)

- **`request` vs `prompt`**: `request` wraps and attributes task text under the target's standing instructions (`agent-requester` default; `/clear` arrives as quoted text), whereas `prompt` injects a direct turn (`agent-operator` required on keyed gateways).
- **`houmao-cccc` group chat vs Houmao messaging**: `houmao-cccc` (`houmao-cccc chat send|reply|pull|deliveries` over `/v1/plugins/{instance}/*` or `--direct-profile`) is an optional CCCC group-chat and Actor-queue transport, separate from native Houmao `request`, `prompt`, and `/v1/mail/*`.

Explicit `help` explains these channels read-only.

## Guardrails

- DO NOT guess targets, prompt/request bodies, or live gateway URLs, or retry a refused/failed `request` via `prompt`, `send-keys`, `--unsigned`, or `mail` without explicit caller direction.
- DO NOT substitute raw `send-keys` for conversational `prompt`/`request` turns or route raw TUI keystrokes through `prompt`.
- DO NOT conflate `houmao-cccc` chat with Houmao `prompt` or `mail`, or invent unsupported `reset-context` CLI flags.
