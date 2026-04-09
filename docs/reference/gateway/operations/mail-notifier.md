# Gateway Mail-Notifier

The gateway mail-notifier is a gateway-owned background polling loop that checks the agent's mailbox for unread messages and injects notification prompts into the gateway request queue.

## What It Does

Use the mail-notifier when a live gateway should wake the agent for unread shared-mailbox work without requiring another process to poll the mailbox.

The notifier is part of the live gateway process:

- it polls unread state through the configured mailbox adapter,
- it renders one gateway-owned notification prompt from a packaged template,
- it enqueues that prompt as an internal `mail_notifier_prompt` request when the gateway is ready.

The prompt is a wake-up bridge between mailbox state and the agent's next prompt round. It is not itself the mailbox processing workflow.

## Current Polling Cycle

When the notifier is enabled, the current implementation runs this cycle:

1. Read the notifier record from gateway storage to confirm that polling is enabled and an interval is configured.
2. Wait until the next scheduled poll time on the gateway's monotonic clock.
3. Refresh current gateway status and verify that mailbox support is available from the runtime-owned manifest and mailbox binding.
4. Ask the mailbox adapter for the full unread set.
5. If there is no unread mail, record an `empty` audit row and stop this cycle.
6. If unread mail exists, compute a SHA256 digest from the sorted unread `message_ref` values.
7. Check whether prompt enqueueing is currently blocked by gateway readiness.
8. If the gateway is ready, render the notification prompt and enqueue one internal `mail_notifier_prompt` request.
9. Reschedule the next poll as `now + interval_seconds`.

The digest is currently used for notifier state or audit visibility only. It is not used to suppress later prompt enqueueing for the same unchanged unread snapshot.

## Current Repeat-Notification Behavior

The current implementation may enqueue repeated notifier prompts for the same unchanged unread snapshot while those messages remain unread.

Important source-truth details:

- the notifier computes `unread_digest` from unread `message_ref` values,
- the notifier audit trail stores that digest,
- the current enqueue path does not compare the new digest against a previously notified digest before deciding to enqueue,
- `last_notified_digest` exists in the notifier record model, but the current cycle writes it as `None` rather than using it to suppress repeated wakeups.

Practical effect:

- unchanged unread self-mail can wake the agent again on later notifier cycles,
- repeated wakeups stop only when the unread set changes, the messages are marked read or deleted, the notifier is disabled, or the gateway stays unavailable or busy long enough that nothing can be enqueued.

## Readiness-Gated Enqueueing

Unread mail does not immediately guarantee a prompt. The notifier enqueues only when the gateway is ready to accept prompt work.

The current busy checks include:

- `request_admission = open`
- `active_execution = idle`
- `queue_depth = 0`
- prompt-readiness for the current dispatch mode

If the managed session is busy or not prompt-ready, the cycle is audited as `busy_skip` and the unread mail remains unread for a later cycle.

For TUI-backed dispatch, the notifier also checks prompt-readiness reasons from the live TUI surface. For headless dispatch, it checks the active direct-turn or terminal-surface readiness state before enqueueing.

## Configuration

The mail-notifier is managed through `houmao-mgr agents gateway mail-notifier`:

| Command | Description |
| --- | --- |
| `status` | Show whether notifier polling is enabled and report last-check metadata. |
| `enable --interval-seconds N` | Enable or reconfigure polling with interval `N` seconds. The current request model requires `N > 0`. |
| `disable` | Disable polling and stop future notifier prompt enqueueing. |

The live gateway rereads notifier state from storage on each cycle, so enable, disable, and interval changes take effect without restarting the gateway.

## Status Fields

`GET /v1/mail-notifier` returns:

| Field | Meaning |
| --- | --- |
| `enabled` | Whether the notifier currently polls. |
| `interval_seconds` | Current polling interval in seconds, or `null` when disabled. |
| `supported` | Whether the current session configuration supports mailbox-backed notifier behavior. |
| `support_error` | Why mailbox-backed notifier behavior is unsupported, when applicable. |
| `last_poll_at_utc` | Timestamp of the last completed poll attempt. |
| `last_notification_at_utc` | Timestamp of the last cycle that successfully enqueued a notifier prompt. |
| `last_error` | Most recent poll or mailbox-support error, when present. |

## Audit Outcomes

Notifier audit rows currently use these outcomes in practice:

| Outcome | Meaning |
| --- | --- |
| `empty` | The unread set was empty for that poll cycle. |
| `busy_skip` | Unread mail existed, but the gateway was busy or not prompt-ready. |
| `enqueued` | The notifier rendered the prompt and enqueued one internal request. |
| `poll_error` | Mailbox support failed or unread polling raised an error. |

The storage model still has a `dedup_skip` outcome shape, but the current notifier cycle does not emit it because the current implementation does not perform digest-based suppression.

## Notification Prompt And Skill Guidance

The notifier renders its prompt from:

```text
src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md
```

That template includes:

- a tool-specific skill-usage block,
- the exact live `gateway.base_url`,
- a rendered block of full `/v1/mail/*` endpoint URLs.

The prompt tells the agent to:

1. list unread mail through the shared gateway mailbox API,
2. choose the relevant unread email or emails for this round,
3. complete that work,
4. mark only the successfully processed selected emails read,
5. stop and wait for the next notification.

The skill-usage block is derived from the runtime-owned manifest and projected mailbox skill installation for the current tool.

Current source behavior:

- when the installed round-oriented mailbox skill is available, the prompt tells the agent to use the installed Houmao email-processing skill `houmao-process-emails-via-gateway`,
- the prompt uses native installed-skill invocation guidance for the current tool rather than telling the agent to inspect `SKILL.md` files,
- when the lower-level mailbox communication skill is also installed, the prompt tells the agent to use `houmao-agent-email-comms` for exact `/v1/mail/*` contract details or no-gateway transport guidance,
- when the round-oriented mailbox skill is not installed, the prompt falls back to direct endpoint guidance.

## Lifecycle Integration

- The notifier loop starts with gateway service initialization and runs until gateway shutdown.
- When polling is disabled or unconfigured, the loop idles on a short internal check interval instead of exiting.
- On shutdown, the gateway signals the notifier thread through the shared stop event and joins it.
- The notifier depends on live gateway readiness. It does not bypass the gateway request queue or prompt-readiness checks.
- The notifier is a live gateway feature. It is not a durable mailbox backlog or reminder queue.

## HTTP Surface

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/v1/mail-notifier` | Inspect current notifier status. |
| `PUT` | `/v1/mail-notifier` | Enable or reconfigure polling. |
| `DELETE` | `/v1/mail-notifier` | Disable polling. |

## See Also

- [agents gateway mail-notifier](../../cli/agents-gateway.md#mail-notifier)
- [Gateway Mailbox Facade](mailbox-facade.md)
- [Gateway Reminders](reminders.md)
- [Agent Gateway Reference](../index.md)

## Source References

- [`src/houmao/agents/realm_controller/gateway_service.py`](../../../src/houmao/agents/realm_controller/gateway_service.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md`](../../../src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md)
