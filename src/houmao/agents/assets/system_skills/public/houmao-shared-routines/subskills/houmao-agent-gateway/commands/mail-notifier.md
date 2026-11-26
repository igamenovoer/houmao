# Manage Gateway Mail-Notifier

Use this action when the live gateway should poll the attached agent's mailbox and submit reminder prompts for open inbox mail.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the explicit `offline|online` channel, target selector, and notifier action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required channel, target, or interval, ask the user in Markdown before proceeding.
4. Run `agents single ... gateway status` or `agents self gateway status` first when current context does not already confirm that a live gateway is attached.
5. Run `agents single ... gateway mail-notifier status|enable|disable --channel <channel>` for selected-agent CLI notifier work, or `agents self gateway mail-notifier status|enable|disable --channel <channel>` for current-session CLI notifier work.
6. Use `enable` with `interval_seconds` to start or reconfigure polling. The default `any_inbox` mode notifies for any unarchived inbox mail, including read or answered mail; use `mode=unread_only` only when the caller explicitly wants lower-noise unread-only wakeups. Add `appendix_text` only when the caller wants runtime-specific guidance appended to notifier prompts; omit it to preserve the current appendix, and pass an empty string to clear it. Keep context recovery or pre-notification compaction omitted unless the caller explicitly asks for it.
7. Use `disable` to stop notifier polling.
8. When the caller is already operating through the pair-managed HTTP API, use `/houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}` instead of direct gateway `/v1/mail-notifier/{channel}`.
9. Report whether the notifier is enabled now, the current interval, mode, appendix text, and any support or last-error fields that matter.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
The two channels keep independent configuration, schedules, appendix text, audit, and binding-scoped compaction bookkeeping. Online canonical identity does not select a channel. Periodic reminders continue for unchanged eligible inbox work; read or answered state alone is not completion. Disabling one channel preserves the other.

## Command Shapes

Run direct scoped notifier commands:

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway mail-notifier status --channel <channel>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway mail-notifier enable --channel <channel> --interval-seconds <seconds>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway mail-notifier disable --channel <channel>
<chosen houmao-mgr launcher> agents self gateway mail-notifier status --channel <channel>
```

Mode values:

- `any_inbox`: default. Notify while any inbox mail remains unarchived, regardless of read or answered state.
- `unread_only`: notify only while unread inbox mail remains unarchived. Read-but-unarchived work will not trigger another notifier prompt by itself in this mode.

Appendix behavior:

- `appendix_text` is queryable in notifier status and appended to rendered notifier prompts only when non-empty.
- Omitted `appendix_text` on `PUT` preserves the stored runtime appendix.
- Non-empty `appendix_text` replaces the stored runtime appendix.
- Empty `appendix_text` clears the stored runtime appendix.
- `DELETE` disables polling but does not clear the stored appendix.

Context policy behavior:

- `context_error_policy=continue_current`: default. Degraded context remains diagnostic and does not trigger a reset by itself.
- `context_error_policy=clear_context`: opt-in. Clear context only when the live degraded diagnostic is recognized for the owning CLI tool.
- `pre_notification_context_action=none`: default. Do not run preflight context actions.
- `pre_notification_context_action=compact`: opt-in preflight. Supported for Codex TUI via `/compact`; unsupported tools or backends should report support errors.

Pair-managed notifier routes:

- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`

Direct live gateway routes:

Apply the target and caller checks in the [gateway HTTP summary](../references/http-surface.md) before making a direct request.

- `GET {gateway.base_url}/v1/mail-notifier/{channel}`
- `PUT {gateway.base_url}/v1/mail-notifier/{channel}`
- `DELETE {gateway.base_url}/v1/mail-notifier/{channel}`

## Binding And Round Context

- Require a configured binding for the selected channel; never substitute the other channel.
- A notifier round carries the exact URL, channel, and expected binding ID. Missing context or a mismatch ends the round.

## Guardrails

- DO NOT treat the notifier as durable work recovery; it is live gateway background behavior.
- DO NOT imply degraded context automatically clears context; the default preserves current context.
- DO NOT use Codex-specific degraded error labels for other CLI tools. Only `unknown` is shared across tools.
- DO NOT describe `unread_only` as a completion signal. Processed mail should be archived so `any_inbox` mode stops notifying for it.
- DO NOT describe `mail-notifier` as the same thing as `/v1/reminders`; the notifier is mailbox-driven polling and uses its own dedicated control routes.
- DO NOT invent unscoped mail-notifier commands outside the `agents single ... gateway` or `agents self gateway` families.
- DO NOT add notifier policy fields unless the user explicitly requested them.

Both modes use the authoritative Inbox. A backend's direct Archive delivery never enters the reminder set. For processed Inbox work on a protected binding, the agent reports completion for separately authorized owner filing. `any_inbox` can repeat while the item remains in Inbox, and `unread_only` keeps its normal read-state filter.
