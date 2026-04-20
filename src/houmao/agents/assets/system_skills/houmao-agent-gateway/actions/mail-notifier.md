# Manage Gateway Mail-Notifier

Use this action when the live gateway should poll the attached agent's mailbox and submit reminder prompts for open inbox mail.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and notifier action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target or interval, ask the user in Markdown before proceeding.
4. Run `agents gateway status` first when current context does not already confirm that a live gateway is attached.
5. Use `status` to inspect whether notifier polling is enabled and whether the current mailbox binding supports it.
6. Use `enable --interval-seconds <n>` to start or reconfigure polling. The default `any_inbox` mode notifies for any unarchived inbox mail, including read or answered mail; use `--mode unread_only` only when the caller explicitly wants lower-noise unread-only wakeups. Add `--appendix-text <text>` only when the caller wants runtime-specific guidance appended to notifier prompts; omit it to preserve the current appendix, and pass an empty string to clear it. Keep `--context-error-policy continue_current` and `--pre-notification-context-action none` unless the caller explicitly asks for context recovery or pre-notification compaction.
7. Use `disable` to stop notifier polling.
8. When the caller is already operating through the pair-managed HTTP API, use `/houmao/agents/{agent_ref}/gateway/mail-notifier` instead of direct gateway `/v1/mail-notifier`.
9. Report whether the notifier is enabled now, the current interval, mode, appendix text, and any support or last-error fields that matter.

## Command Shapes

CLI notifier control:

```text
<chosen houmao-mgr launcher> agents gateway mail-notifier status --agent-name <name>
<chosen houmao-mgr launcher> agents gateway mail-notifier enable --agent-name <name> --interval-seconds 60
<chosen houmao-mgr launcher> agents gateway mail-notifier enable --agent-name <name> --interval-seconds 60 --mode unread_only
<chosen houmao-mgr launcher> agents gateway mail-notifier enable --agent-name <name> --interval-seconds 60 --appendix-text "Prioritize billing notices first."
<chosen houmao-mgr launcher> agents gateway mail-notifier enable --agent-name <name> --interval-seconds 60 --context-error-policy clear_context
<chosen houmao-mgr launcher> agents gateway mail-notifier enable --agent-name <name> --interval-seconds 60 --pre-notification-context-action compact
<chosen houmao-mgr launcher> agents gateway mail-notifier disable --agent-name <name>
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

- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`

Direct live gateway routes:

- `GET {gateway.base_url}/v1/mail-notifier`
- `PUT {gateway.base_url}/v1/mail-notifier`
- `DELETE {gateway.base_url}/v1/mail-notifier`

## Guardrails

- Do not treat the notifier as durable work recovery; it is live gateway background behavior.
- Do not enable the notifier without a valid attached mailbox configuration.
- Do not imply degraded context automatically clears context; the default preserves current context.
- Do not use Codex-specific degraded error labels for other CLI tools. Only `unknown` is shared across tools.
- Do not describe `unread_only` as a completion signal. Processed mail should be archived so `any_inbox` mode stops notifying for it.
- Do not describe `mail-notifier` as the same thing as `/v1/reminders`; the notifier is mailbox-driven polling and uses its own dedicated control routes.
- Do not invent `houmao-mgr agents mail-notifier ...` commands outside the `agents gateway` family.
