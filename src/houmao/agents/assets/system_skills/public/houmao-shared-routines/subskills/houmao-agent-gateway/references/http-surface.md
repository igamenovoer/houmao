---
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

# Gateway HTTP Surface Summary

Prefer scoped `houmao-mgr` commands or an established pair-managed `/houmao/agents/{agent_ref}/*` route; use direct `{gateway.base_url}/v1/...` only when exact HTTP contracts apply and target identity + caller proof are verified.

## Public Discovery, Dashboard, and `admin_mode`

- `GET {gateway.base_url}/` — public read-only HTML/JSON operator dashboard summarizing live gateway status, mode, and admission posture without granting protected-route access.
- `GET {gateway.base_url}/health` — liveness probe.
- `GET {gateway.base_url}/v1/endpoint` — public endpoint descriptor reporting identity, context, generation, presence, capabilities, and `admin_mode: open | keyed | unavailable` (`open` = initialized empty admin roster admits unauthenticated calls subject to operation prerequisites; `keyed` = requires verified enrolled key/proof or configured `default-group`; `unavailable` = policy uninitialized/unreadable, establishing no open access).
- `GET {gateway.base_url}/v1/status` and `GET {gateway.base_url}/v1/usage` (durable turn token/cost usage; pair-managed `GET /houmao/agents/{agent_ref}/usage`).
- Pair-managed discovery: `GET /houmao/agents/{agent_ref}/gateway` and `GET /houmao/agents/{agent_ref}/mail/resolve-live`.

For independently signed JSON calls, use `houmao-shared-routines->houmao-agent-access->request()` with `--url`, `--context-id`, `--generation`, `--presence`, and `--ca-bundle`; for versioned `skills`/`mcp` mounts (`/v1/files/*`), use `houmao-shared-routines->houmao-agent-files`.

## Control Routes Across `tui`, `headless`, `service`, and `web`

| Surface | Direct Live Gateway (`/v1/...`) | Pair-Managed (`/houmao/agents/{agent_ref}/gateway/...`) |
| --- | --- | --- |
| Lifecycle & queue | `POST /v1/requests`, `POST /v1/control/prompt`, `POST /v1/control/send-keys` | `POST .../attach`, `POST .../detach`, `POST .../requests`, `POST .../control/{prompt,send-keys}` |
| `tui` mode | `GET /v1/control/tui/{state,history}`, `POST /v1/control/tui/note-prompt` | `GET .../tui/{state,history}`, `POST .../tui/note-prompt` |
| `headless` mode | `GET /v1/control/headless/state`, `POST /v1/control/headless/next-prompt-session` | `GET .../control/headless/state`, `POST .../control/headless/next-prompt-session` |
| `service` mode | `GET /v1/control/service/state`, `GET /v1/control/service/requests/{request_id}` | `GET .../control/service/state`, `GET .../control/service/requests/{request_id}` |
| `web` mode | `GET /v1/control/web/state`, `GET /v1/control/web/history` | `GET .../control/web/state`, `GET .../control/web/history` |
| Reminders & notifier | `GET\|POST /v1/reminders`, `GET\|PUT\|DELETE /v1/reminders/{id}`, `GET\|PUT\|DELETE /v1/mail-notifier/{channel}` | `GET\|POST .../reminders`, `GET\|PUT\|DELETE .../reminders/{id}`, `GET\|PUT\|DELETE .../mail-notifier` |

## Shared Mailbox Facade and Gateway Plugins (`houmao-cccc`)

- **Shared mailbox (`/v1/mail/*`, `schema_version: 3`)**: `GET /v1/mail/status` and `POST /v1/mail/{channel}/{list,peek,read,send,post,reply,mark,move,archive}` with pinned `expected_binding_id` (`offline` vs `online` isolated; details in `houmao-shared-routines->houmao-agent-email-comms`).
- **Gateway plugins (`/v1/plugins/{instance}/*`)**: attached plugins (configured via `--plugins-config` and `--plugin-config-override INSTANCE=JSON`) mount under `/v1/plugins/{instance}/*`. For `houmao-cccc` (default instance `cccc`), routes expose binding/capabilities/members/connection plus `delivery`, `chat`, and `mail` operations driven through the `houmao-cccc` CLI.
