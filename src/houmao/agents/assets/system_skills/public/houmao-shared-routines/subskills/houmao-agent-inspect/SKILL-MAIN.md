---
name: houmao-agent-inspect
description: Use when read-only evidence is needed for a Houmao-managed or external agent's liveness, `service`/`web`/TUI state, durable turn usage (`/v1/usage`), mailbox posture, runtime artifacts, logs, or recorded tmux pane.
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

# Houmao Agent Inspect

## Overview

Collect strictly read-only evidence for Houmao-managed and `agents external` instances across summary state (`execution_binding`, gateway access mode/`default-group`), `service`/`web`/TUI surfaces, durable turn usage (`/v1/usage` and `usage/records.sqlite3`), mailbox posture, artifacts, logs, and socket-qualified tmux panes.

## Workflow

1. **Answer explicit `help` first** from **Help** without running commands or touching runtime state.
2. **Enforce the Actor Frame Gate**: require an explicit target in `admin` posture; default to verified self in `agent` posture and require an explicit peer identifier for peer inspection.
3. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher) and ask for any missing target or turn/request ID before proceeding.
4. **Follow the managed-first evidence hierarchy**:
   - Start with `agents single|self state` (or `GET /houmao/agents/{agent_ref}/managed-state`, `agents external list|get` for remote imports) to read liveness, `execution_binding`, gateway `admin_mode`/`default-group`, `manifest_path`, and `session_root`.
   - Use mode-appropriate managed surfaces (`gateway status`, `/v1/control/service/{state,requests/{request_id}}`, `/v1/control/web/{state,history}`, `gateway tui state|history|watch`, `turn status|events|stdout|stderr`, and `GET /v1/usage` or `/houmao/agents/{agent_ref}/usage`).
   - Drop to socket-qualified local tmux capture (`env -u TMUX -u TMUX_PANE tmux -S "$TMUX_SOCKET" -N capture-pane`) in [commands/screen.md](commands/screen.md) only when managed surfaces cannot answer a local pane question.
5. **Load the selected page in Subcommands** and report read-only findings clearly.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded read-only inspection plan from **Subcommands** and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Inspection is strictly read-only in both branches. Route `request`/`prompt`/`interrupt`/`send-keys` to `houmao-shared-routines->houmao-agent-messaging`, gateway `attach`/`detach`/reminders/`mail-notifier` to `houmao-shared-routines->houmao-agent-gateway`, mailbox binding/root mutations to `houmao-shared-routines->houmao-mailbox-mgr`, and `stop`/`relaunch`/`cleanup` to `houmao-shared-routines->houmao-agent-instance`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `discover` | Identify local (`agents global list`) or `agents external` targets and read `state` (`execution_binding`, policy/`default-group`, `service`/`web`/gateway status). | [Discover](commands/discover.md) |
| `screen` | Inspect gateway-tracked TUI state or capture a verified `tmux -S "$TMUX_SOCKET" -N` pane. | [Screen](commands/screen.md) |
| `mailbox` | Inspect `offline`/`online` mailbox bindings, availability, and unread summaries read-only. | [Mailbox](commands/mailbox.md) |
| `logs` | Inspect durable turn usage (`/v1/usage`, `usage-*.json`), headless `turn` traces, `service` requests, `web` history, and gateway logs. | [Logs](commands/logs.md) |
| `artifacts` | Locate `manifest.json`, `usage/records.sqlite3`, `gateway/state.json`, and turn artifacts under `session_root`. | [Artifacts](commands/artifacts.md) |
| `help` | Read-only overview of managed-first inspection surfaces, usage accounting, and boundaries. | **Help** |

## Help

Summarize `discover`, `screen`, `mailbox`, `logs` (including `/v1/usage` and `/houmao/agents/{agent_ref}/usage`), and `artifacts` (`usage/records.sqlite3`) across `headless`, `service`, `tui`, `web`, and `agents external` targets without running commands. Concrete inspection requests execute the matching subcommand.

## Guardrails

- DO NOT mutate agents, send prompts/requests/keys/mail, attach/detach gateways, or alter lifecycle state during inspection.
- DO NOT jump to raw tmux or filesystem files before `state` / `managed-state` establishes the target, or guess gateway URLs, `session_root` paths, or tmux sockets (always clear `TMUX`/`TMUX_PANE` and pass `tmux -S "$TMUX_SOCKET" -N`).
- DO NOT treat `gateway.log` or `events.jsonl` as authoritative manifest/queue state, or auto-start a terminal recorder unless the caller explicitly requests replay-grade capture.
