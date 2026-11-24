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

# Managed-Agent HTTP Route Summary

Prefer the pair-managed `/houmao/agents/*` routes when they satisfy the task. Use direct gateway `/v1/...` only when the lower-level route is required and the exact live `gateway.base_url` is available from current context or supported discovery.

## Discovery

- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

## Ordinary Prompt

- `POST /houmao/agents/{agent_ref}/requests`

Use `/requests` for ordinary managed-agent prompting. Use the gateway control routes for explicit gateway behavior.

## Transport-Neutral Interrupt

- `POST /houmao/agents/{agent_ref}/requests`

Use this route family for the normal managed-agent interrupt surface across both TUI and headless transports.
For TUI-backed managed agents, ordinary interrupt means one best-effort `Escape` delivery through the resolved managed-agent control path, even when tracked TUI state currently looks idle.
For headless managed agents, ordinary interrupt targets active execution and may return explicit no-op detail when no headless work is active.
Do not switch to raw `send-keys` merely to get the normal TUI interrupt behavior.

## Explicit Gateway Queue And Direct Gateway Control

- `POST /houmao/agents/{agent_ref}/gateway/requests`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`

Use `/gateway/requests` for queued gateway work. Use `/gateway/control/*` for immediate gateway-owned control behavior such as prompt control, raw key delivery, or headless next-prompt-session selection.

## Gateway-Owned TUI Inspection

- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

Use these routes when you need the exact raw gateway-owned tracker surface instead of the broader managed-agent history view.

## Mailbox Discovery Handoff

- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

Use a known recipient address or resolve it for the requested channel. Published contact is sufficient for the recipient address. Hand ordinary mail off to `houmao-shared-routines->houmao-agent-email-comms`. Use a verified live gateway when handing off a notifier round to `houmao-shared-routines->houmao-process-emails-via-gateway`.

## Direct Gateway HTTP

Only use these lower-level routes when the task requires the direct gateway seam and the exact live `gateway.base_url` is already available:

- `POST {gateway.base_url}/v1/control/prompt`
- `POST {gateway.base_url}/v1/control/send-keys`
- `GET {gateway.base_url}/v1/control/headless/state`
- `POST {gateway.base_url}/v1/control/headless/next-prompt-session`

Do not guess the gateway host or port.
