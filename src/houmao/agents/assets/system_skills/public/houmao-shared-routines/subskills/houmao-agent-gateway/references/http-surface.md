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

# Gateway HTTP Surface Summary

Use direct gateway `/v1/...` only when the exact live `gateway.base_url` is already available from current context or supported discovery.

## Discovery

- `GET {gateway.base_url}/health`
- `GET {gateway.base_url}/v1/status`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

## Gateway Lifecycle And Pair-Managed Control

- `POST /houmao/agents/{agent_ref}/gateway/attach`
- `POST /houmao/agents/{agent_ref}/gateway/detach`
- `POST /houmao/agents/{agent_ref}/gateway/requests`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`
- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`
- `GET /houmao/agents/{agent_ref}/gateway/reminders`
- `POST /houmao/agents/{agent_ref}/gateway/reminders`
- `GET /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`
- `PUT /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`
- `DELETE /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`
- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`

## Direct Live Gateway Routes

- `GET {gateway.base_url}/v1/status`
- `POST {gateway.base_url}/v1/requests`
- `POST {gateway.base_url}/v1/control/prompt`
- `POST {gateway.base_url}/v1/control/send-keys`
- `GET {gateway.base_url}/v1/control/headless/state`
- `POST {gateway.base_url}/v1/control/headless/next-prompt-session`
- `GET {gateway.base_url}/v1/control/tui/state`
- `GET {gateway.base_url}/v1/control/tui/history`
- `POST {gateway.base_url}/v1/control/tui/note-prompt`
- `POST {gateway.base_url}/v1/reminders`
- `GET {gateway.base_url}/v1/reminders`
- `GET {gateway.base_url}/v1/reminders/{reminder_id}`
- `PUT {gateway.base_url}/v1/reminders/{reminder_id}`
- `DELETE {gateway.base_url}/v1/reminders/{reminder_id}`
- `GET {gateway.base_url}/v1/mail-notifier/{channel}`
- `PUT {gateway.base_url}/v1/mail-notifier/{channel}`
- `DELETE {gateway.base_url}/v1/mail-notifier/{channel}`

## Shared Mailbox Facade

- `GET {gateway.base_url}/v1/mail/status`
- `POST {gateway.base_url}/v1/mail/{channel}/list`
- `POST {gateway.base_url}/v1/mail/{channel}/peek`
- `POST {gateway.base_url}/v1/mail/{channel}/read`
- `POST {gateway.base_url}/v1/mail/{channel}/send`
- `POST {gateway.base_url}/v1/mail/{channel}/post`
- `POST {gateway.base_url}/v1/mail/{channel}/reply`
- `POST {gateway.base_url}/v1/mail/{channel}/mark`
- `POST {gateway.base_url}/v1/mail/{channel}/move`
- `POST {gateway.base_url}/v1/mail/{channel}/archive`

Use `houmao-shared-routines->houmao-agent-email-comms` for the exact `/v1/mail/*` request contract once the live base URL is known.

## Reminder Layering

- Prefer `houmao-mgr agents single ... gateway reminders ...` or `houmao-mgr agents self gateway reminders ...` for operator-facing CLI work.
- Use `/houmao/agents/{agent_ref}/gateway/reminders...` when the current task is already operating through pair-managed HTTP.
- Use direct `{gateway.base_url}/v1/reminders...` only when the task genuinely needs the lower-level live gateway contract.

Mail lifecycle bodies use schema version 2 and require `expected_binding_id` from the explicitly selected channel. Summary status reports both channels. Canonical identity never routes delivery, and conflicts do not authorize automatic resend to another binding.
