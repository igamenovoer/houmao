---
name: houmao-agent-gateway
description: Use when a Houmao managed-agent gateway needs attachment (`--plugin-config-override`), discovery, public dashboard/endpoint checks, `web-entry` or `open-browser`, `service`/`web`/TUI/plugin (`houmao-cccc`) services, reminders, or `mail-notifier` management.
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

## Overview

Operate the per-agent Houmao gateway sidecar: `attach`/`detach`/`status` (including `--plugins-config` and `--plugin-config-override`), endpoint/dashboard discovery (`GET /` and `/v1/endpoint` `admin_mode`), `web-entry` and local `open-browser`, gateway-only `service`/`web`/TUI/`houmao-cccc` services, non-durable ranked `reminders`, and `mail-notifier`.

## Workflow

1. **Answer explicit `help` first** from **Help** without probing targets or mutating gateway state.
2. **Enforce the Actor Frame Gate**: require an explicit `--agent-id`/`--agent-name` target in `admin` posture; default to verified `agents self` in `agent` posture and require explicit coordinates/authority for peer gateways.
3. **Route non-gateway tasks cleanly**: agent `launch`/`stop`/`relaunch`/`cleanup` -> `houmao-shared-routines->houmao-agent-instance` (`native-resources()` for native skill/MCP refresh), generic inspection/usage -> `houmao-shared-routines->houmao-agent-inspect`, ordinary `request`/`prompt`/`interrupt` -> `houmao-shared-routines->houmao-agent-messaging`, `/v1/mail/*` -> `houmao-shared-routines->houmao-agent-email-comms`, access policy/keys -> `houmao-shared-routines->houmao-agent-access`, and versioned `skills`/`mcp` mounts -> `houmao-shared-routines->houmao-agent-files`.
4. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher), load the selected page in **Subcommands** (and [references/http-surface.md](references/http-surface.md) or [references/scope-and-routing.md](references/scope-and-routing.md) when direct `/v1/*` routes apply), and ask for any missing required input before execution.
5. **Execute and report** without exposing private signer material, `--access-config` secrets, or single-use `web-entry` URLs in shared logs.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, [references/http-surface.md](references/http-surface.md), and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Admin callers never treat the operator shell as `agents self`; browser entry (`web-entry` and `open-browser`) and deployment reconfiguration (`--access-config`, `--plugins-config`, `--plugin-config-override`) run in the target's execution-owner context.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `lifecycle` | Attach (foreground auxiliary window by default), detach, inspect, or configure `--access-config` / `--plugins-config` / `--plugin-config-override`. | [Lifecycle](commands/lifecycle.md) |
| `discover` | Resolve live gateway coordinates (`HOUMAO_AGENT_GATEWAY_HOST/PORT`, `gateway status`, `/v1/endpoint` `admin_mode`, `GET /` dashboard). | [Discover](commands/discover.md) |
| `gateway-services` | Operate gateway-only `prompt`/`send-keys`, `service`/`web`/headless/TUI control routes, and `houmao-cccc` plugin CLI & `/v1/plugins/{instance}/*` routes. | [Gateway Services](commands/gateway-services.md) |
| `web-entry` | Issue a 60-second single-use `gateway web-entry` bearer URL or open a local Kimi Web browser via `agents single ... open-browser`. | [Web Entry](commands/web-entry.md) |
| `reminders` | Create, inspect, update, pause, or remove non-durable ranked `/v1/reminders` (`one_off`/`repeat`, `--after-all`, `send_keys`). | [Reminders](commands/reminders.md) |
| `mail-notifier` | Inspect, enable, or disable `/v1/mail-notifier/{channel}` polling while preserving `appendix_text`. | [Mail Notifier](commands/mail-notifier.md) |
| `help` | Read-only overview of gateway lifecycle, dashboard `admin_mode`, `open-browser` vs `web-entry`, `houmao-cccc`, reminders, and `mail-notifier`. | **Help** |

## Help

Summarize `lifecycle` (attach != launch, foreground default, `--plugin-config-override`), `discover` (`GET /` dashboard and `/v1/endpoint` `admin_mode: open|keyed|unavailable`), `gateway-services` (`/v1/control/{service,web,headless,tui}/*` and `houmao-cccc` `/v1/plugins/{instance}/*`), `web-entry` vs `open-browser`, in-memory `reminders`, and `mail-notifier` read-only.

## Guardrails

- DO NOT conflate `gateway attach|detach` with launching or stopping the agent body, or pass `--background` unless explicitly requested.
- DO NOT use retired `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT` env vars, guess `{gateway.base_url}`, or scrape env vars for mail when `agents self mail resolve-live` applies.
- DO NOT describe `/v1/reminders` as durable across gateway stop/restart, drop `mail-notifier` `appendix_text` unasked, or treat endpoint reachability (`GET /` or `/v1/endpoint`) as authorization for protected routes.
- DO NOT leak single-use `web-entry` URLs, private keys, or `--access-config` / `--signer-binding` secrets into logs, mail, or shared summaries.
