---
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

# Messaging Intent Matrix

Use this table when you know what you want to do but need the supported Houmao surface that matches that intent.

For generic read-only managed-agent inspection that is not inseparable from a messaging workflow, use `houmao-shared-routines->houmao-agent-inspect` instead of this matrix.

| Intent | Preferred CLI Surface | Preferred HTTP Surface | Notes |
| --- | --- | --- | --- |
| Discover target and capability | `agents single ... state`, `agents single ... gateway status`, or `agents single ... mail resolve-live` | `GET /houmao/agents/{agent_ref}`, `GET /gateway`, `GET /mail/resolve-live` | Query only the evidence the request needs. |
| Ordinary prompt turn | `agents single ... prompt` or `agents self prompt` | `POST /houmao/agents/{agent_ref}/requests` | The manager checks readiness through the selected authority. A detached gateway allows an authorized direct owner route. |
| Transport-neutral interrupt | `agents single ... interrupt` or `agents self interrupt` | `POST /houmao/agents/{agent_ref}/requests` | Use this for ordinary interrupt requests across TUI and headless transports. TUI interrupt means best-effort `Escape`; headless interrupt targets active execution and may no-op when idle. |
| Submit while busy only when no provider prompt is pending | `agents single ... gateway prompt --admission-policy if-no-pending` or the matching `agents self` path | Schema-v2 `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with `admission_policy=if_no_pending` | Pending `yes` or `unknown` backs off. The decision is observational, not a reservation. |
| Submit regardless of tracked TUI posture | `agents single ... gateway prompt --admission-policy always` or the matching `agents self` path | Schema-v2 `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with `admission_policy=always` | Use only when the caller explicitly wants to bypass readiness and provider-pending checks. Structural gateway checks still apply. |
| Gateway-durable prompt or interrupt | managed request surface, not direct `gateway prompt` | `POST /houmao/agents/{agent_ref}/gateway/requests` | Durable accepted work is independent from provider-native `surface.pending_input`. |
| Gateway-owned TUI inspection or prompt provenance | `agents single ... gateway tui state|history|note-prompt` or `agents self gateway tui ...` | `GET /gateway/tui/state`, `GET /gateway/tui/history`, `POST /gateway/tui/note-prompt` | Inspection and provenance, not the default prompt-turn path. |
| Exact raw control input | `agents single ... gateway send-keys` or `agents self gateway send-keys` | `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` | Use for slash menus, arrows, `Escape`, or partial typing. |
| Mailbox handoff | `agents single ... mail resolve-live` for recipient contact | `GET /mail/resolve-live` | For ordinary mail, use published contact and hand off to the sender's `agents self mail send --channel <channel>` workflow. A notifier round uses its verified live gateway. |
| Reset context and send immediately | no first-class CLI flag today | `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with `chat_session.mode = "new"` | Direct gateway `/v1/control/prompt` is lower-level fallback only when the exact live base URL is already known. |
| Prepare next headless prompt session without sending now | no first-class CLI flag today | `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` | Direct gateway `/v1/control/headless/next-prompt-session` is the lower-level fallback only when the exact live base URL is already known. |
