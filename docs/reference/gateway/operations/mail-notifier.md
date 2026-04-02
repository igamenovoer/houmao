# Gateway Mail-Notifier

The gateway mail-notifier is a background polling loop within the agent gateway that periodically checks the agent's mailbox for unread messages and submits notification prompts through the gateway's request queue.

## How It Works

When enabled, the mail-notifier runs as a daemon thread inside the gateway process:

1. **Poll**: At the configured interval, the notifier calls the agent's mailbox adapter to retrieve unread messages.
2. **Deduplicate**: A SHA256 digest of sorted message references prevents re-notification for the same set of unread messages.
3. **Block check**: If the agent is currently busy (an execution is in progress), the cycle is skipped and audited as `busy_skip`.
4. **Prompt**: When new unread messages are found and the agent is not busy, the notifier renders a notification prompt from a packaged template and enqueues it as an internal `mail_notifier_prompt` request in the gateway's SQLite request queue.

The notification prompt instructs the agent to list unread mail, process relevant messages, and mark them as read. It includes the gateway's base URL and available mail endpoint routes so the agent can operate through the gateway's `/v1/mail/*` facade.

```
┌──────────────────────────────────────────────────┐
│                  Gateway Process                  │
│                                                   │
│  ┌─────────────┐     ┌──────────────────┐        │
│  │ Mail-       │────▶│ Mailbox Adapter   │        │
│  │ Notifier    │     │ (filesystem or    │        │
│  │ Thread      │     │  stalwart)        │        │
│  └──────┬──────┘     └──────────────────┘        │
│         │                                         │
│         │ enqueue prompt                          │
│         ▼                                         │
│  ┌──────────────┐     ┌──────────────────┐       │
│  │ Request      │────▶│ TUI / Headless   │       │
│  │ Queue        │     │ Agent            │       │
│  │ (SQLite)     │     │                  │       │
│  └──────────────┘     └──────────────────┘       │
└──────────────────────────────────────────────────┘
```

## Configuration

The mail-notifier is managed through `houmao-mgr agents gateway mail-notifier` commands:

| Command | Description |
|---|---|
| `enable --interval-seconds N` | Start or reconfigure the notifier with polling interval N seconds (>= 1). |
| `disable` | Stop the notifier. No further notification prompts are submitted until re-enabled. |
| `status` | Show current state: enabled/disabled, interval, last poll time, last notification time, errors. |

The notifier can be reconfigured at runtime — changing the interval takes effect on the next poll cycle without restarting the gateway.

## Status Fields

The `status` response includes:

| Field | Description |
|---|---|
| `enabled` | Whether the notifier is currently polling. |
| `interval_seconds` | Configured polling interval (null when disabled). |
| `supported` | Whether the notifier is supported given the current mailbox configuration. |
| `support_error` | Reason the notifier cannot run (e.g., no mailbox binding). |
| `last_poll_at_utc` | ISO timestamp of the last successful poll cycle. |
| `last_notification_at_utc` | ISO timestamp of the last submitted notification prompt. |
| `last_error` | Error message from the most recent failed poll cycle. |

## Gateway Lifecycle Integration

- The notifier thread starts when the gateway service initializes and runs until the gateway shuts down.
- On gateway shutdown, the notifier thread is signaled via a stop event and joined with a 2-second timeout.
- The notifier reads its enabled state from durable storage on each cycle, so `enable`/`disable` commands take effect immediately.
- When the gateway is not attached to an agent, the notifier thread idles at a 0.2-second check interval waiting for configuration.

## Notification Prompt Template

The notification prompt is rendered from a packaged template at `system_prompts/mailbox/mail-notifier.md` with these placeholders:

| Placeholder | Substitution |
|---|---|
| `{{SKILL_USAGE_BLOCK}}` | Paths to installed mailbox skill documentation. |
| `{{GATEWAY_BASE_URL}}` | The gateway's HTTP base URL (e.g., `http://127.0.0.1:8000`). |
| `{{FULL_ENDPOINT_URLS_BLOCK}}` | Available mail endpoint routes (`GET /v1/mail/status`, `POST /v1/mail/check`, etc.). |

## Gateway HTTP API

The notifier is exposed through these gateway endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/mail-notifier` | Retrieve current notifier status. |
| `PUT` | `/v1/mail-notifier` | Enable or reconfigure the notifier. |
| `DELETE` | `/v1/mail-notifier` | Disable the notifier. |

## See Also

- [agents gateway mail-notifier](../../cli/agents-gateway.md#mail-notifier) — CLI commands
- [Agent Gateway Reference](../index.md) — gateway subsystem overview
- [Mailbox Reference](../../mailbox/index.md) — mailbox subsystem details
