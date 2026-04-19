# Gateway Mail-Notifier

The gateway mail-notifier is a gateway-owned background polling loop that checks the agent's mailbox for open inbox work and injects notification prompts into the gateway request queue.

## What It Does

Use the mail-notifier when a live gateway should wake the agent for shared-mailbox inbox work without requiring another process to poll the mailbox. The default `any_inbox` mode wakes while any inbox mail remains unarchived. The opt-in `unread_only` mode wakes only for unread unarchived inbox mail.

The notifier is part of the live gateway process:

- it polls eligible inbox state through the configured mailbox adapter,
- it renders one gateway-owned notification prompt from a packaged template,
- it enqueues that prompt as an internal `mail_notifier_prompt` request when the gateway is ready.

The prompt is a wake-up bridge between mailbox state and the agent's next prompt round. It is not itself the mailbox processing workflow.

Notifier configuration also carries optional `appendix_text`. When non-empty, that text is appended to each rendered notifier prompt as additional runtime guidance. Use it for run-specific wake-up context such as "handle billing notices first" or "ignore FYI digests for this project"; do not use it to replace the mailbox-processing workflow itself.

## Current Polling Cycle

When the notifier is enabled, the current implementation runs this cycle:

1. Read the notifier record from gateway storage to confirm that polling is enabled and an interval is configured.
2. Wait until the next scheduled poll time on the gateway's monotonic clock.
3. Refresh current gateway status and verify that mailbox support is available from the runtime-owned manifest and mailbox binding.
4. Ask the mailbox adapter for the current eligible inbox set: `read_state=any`, `answered_state=any`, `archived=false` in `any_inbox` mode, or `read_state=unread`, `answered_state=any`, `archived=false` in `unread_only` mode.
5. If there is no eligible mail, record an `empty` audit row and stop this cycle.
6. If eligible mail exists, compute a SHA256 digest from the sorted eligible `message_ref` values.
7. Check whether prompt enqueueing is currently blocked by gateway readiness.
8. If the gateway is ready, render the notification prompt and enqueue one internal `mail_notifier_prompt` request.
9. Reschedule the next poll as `now + interval_seconds`.

The digest is currently used for notifier state or audit visibility only. It is not used to suppress later prompt enqueueing for the same unchanged unread snapshot.

## Current Repeat-Notification Behavior

The current implementation may enqueue repeated notifier prompts for the same unchanged eligible inbox snapshot while those messages remain unarchived and eligible for the selected mode.

Important source-truth details:

- the notifier computes `unread_digest` from eligible `message_ref` values,
- the notifier audit trail stores that digest,
- the current enqueue path does not compare the new digest against a previously notified digest before deciding to enqueue,
- `last_notified_digest` exists in the notifier record model, but the current cycle writes it as `None` rather than using it to suppress repeated wakeups.

Practical effect:

- unchanged eligible inbox mail can wake the agent again on later notifier cycles,
- in `any_inbox` mode, repeated wakeups stop when the message is archived, moved out of inbox, deleted, the notifier is disabled, or the gateway stays unavailable or busy long enough that nothing can be enqueued,
- in `unread_only` mode, marking a message read also removes it from notifier eligibility, so use this mode only when that lower-noise trade-off is intended.

## Readiness-Gated Enqueueing

Eligible mail does not immediately guarantee a prompt. The notifier enqueues only when the gateway is ready to accept prompt work.

The current busy checks include:

- `request_admission = open`
- `active_execution = idle`
- `queue_depth = 0`
- prompt-readiness for the current dispatch mode

If the managed session is busy or not prompt-ready, the cycle is audited as `busy_skip` and the eligible mail remains in the inbox for a later cycle.

Recoverable degraded chat context is diagnostic, not a busy condition by itself. If the session is otherwise prompt-ready and queue admission passes, the notifier enqueues the normal current-context prompt work and does not send `/new`, `/clear`, or any other reset signal solely because degraded context is present. Clean-context notifier work is reported only when a clean-context workflow actually ran.

For TUI-backed dispatch, the notifier also checks prompt-readiness reasons from the live TUI surface. For headless dispatch, it checks the active direct-turn or terminal-surface readiness state before enqueueing.

## Configuration

The mail-notifier is managed through `houmao-mgr agents gateway mail-notifier`:

| Command | Description |
| --- | --- |
| `status` | Show whether notifier polling is enabled and report last-check metadata. |
| `enable --interval-seconds N [--mode any_inbox|unread_only] [--appendix-text TEXT]` | Enable or reconfigure polling with interval `N` seconds, the selected mode, and optionally a prompt appendix. The current request model requires `N > 0`; the mode defaults to `any_inbox`. |
| `disable` | Disable polling and stop future notifier prompt enqueueing. Disabling does not clear stored `appendix_text`. |

The live gateway rereads notifier state from storage on each cycle, so enable, disable, and interval changes take effect without restarting the gateway.

Appendix update rules:

- Omitting `--appendix-text` preserves the currently stored appendix.
- Passing non-empty `--appendix-text TEXT` replaces the stored appendix.
- Passing an empty string clears the stored appendix, for example `--appendix-text ''`.

## Status Fields

`GET /v1/mail-notifier` returns:

| Field | Meaning |
| --- | --- |
| `enabled` | Whether the notifier currently polls. |
| `interval_seconds` | Current polling interval in seconds, or `null` when disabled. |
| `mode` | Effective notifier mode, `any_inbox` or `unread_only`, including when disabled. |
| `appendix_text` | Effective prompt appendix text. Empty string means no appendix is rendered. |
| `supported` | Whether the current session configuration supports mailbox-backed notifier behavior. |
| `support_error` | Why mailbox-backed notifier behavior is unsupported, when applicable. |
| `last_poll_at_utc` | Timestamp of the last completed poll attempt. |
| `last_notification_at_utc` | Timestamp of the last cycle that successfully enqueued a notifier prompt. |
| `last_error` | Most recent poll or mailbox-support error, when present. |

## Audit Outcomes

Notifier audit rows currently use these outcomes in practice:

| Outcome | Meaning |
| --- | --- |
| `empty` | The eligible inbox set was empty for that poll cycle. |
| `busy_skip` | Eligible inbox mail existed, but the gateway was busy or not prompt-ready. |
| `enqueued` | The notifier rendered the prompt and enqueued one internal request. |
| `poll_error` | Mailbox support failed or unread polling raised an error. |

The storage model still has a `dedup_skip` outcome shape, but the current notifier cycle does not emit it because the current implementation does not perform digest-based suppression.

## Notification Prompt And Skill Guidance

The notifier renders its prompt from:

```text
src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md
```

That template includes:

- a concise tool-specific skill-usage block,
- the exact live `gateway.base_url`,
- a one-line `/v1/mail/*` endpoint summary.

The prompt tells the agent to:

1. process relevant inbox mail through the shared gateway mailbox API,
2. complete that work,
3. archive only completed messages after any required reply succeeds,
4. stop after the round.

The skill-usage block is derived from the runtime-owned manifest and projected mailbox skill installation for the current tool.

When `appendix_text` is non-empty, the rendered prompt also includes:

```text
Additional runtime guidance:
<appendix_text>
```

Current source behavior:

- when the installed round-oriented mailbox skill is available, the prompt gives a concise native invocation for `houmao-process-emails-via-gateway`,
- the prompt uses native installed-skill invocation guidance for the current tool rather than telling the agent to inspect `SKILL.md` files,
- when the lower-level mailbox communication skill is also installed, the prompt names `houmao-agent-email-comms` only as an optional details reference,
- when the round-oriented mailbox skill is not installed, the prompt falls back to the compact mailbox API summary.

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
| `PUT` | `/v1/mail-notifier` | Enable or reconfigure polling. Body fields are `interval_seconds`, optional `mode`, and optional `appendix_text`. Omitted `appendix_text` preserves the stored appendix; an empty string clears it. |
| `DELETE` | `/v1/mail-notifier` | Disable polling without clearing stored appendix text. |

## See Also

- [agents gateway mail-notifier](../../cli/agents-gateway.md#mail-notifier)
- [Gateway Mailbox Facade](mailbox-facade.md)
- [Gateway Reminders](reminders.md)
- [Agent Gateway Reference](../index.md)

## Source References

- [`src/houmao/agents/realm_controller/gateway_service.py`](../../../../src/houmao/agents/realm_controller/gateway_service.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md`](../../../../src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md)
