# Manage Gateway Mail-Notifier

Use this action when the live gateway should poll the attached agent's mailbox and submit reminder prompts for unread messages.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the target selector and notifier action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target or interval, ask the user in Markdown before proceeding.
4. Run `agents gateway status` first when current context does not already confirm that a live gateway is attached.
5. Use `status` to inspect whether notifier polling is enabled and whether the current mailbox binding supports it.
6. Use `enable --interval-seconds <n>` to start or reconfigure polling.
7. Use `disable` to stop notifier polling.
8. When the caller is already operating through the pair-managed HTTP API, use `/houmao/agents/{agent_ref}/gateway/mail-notifier` instead of direct gateway `/v1/mail-notifier`.
9. Report whether the notifier is enabled now, the current interval, and any support or last-error fields that matter.

## Command Shapes

CLI notifier control:

```text
<resolved houmao-mgr launcher> agents gateway mail-notifier status --agent-name <name>
<resolved houmao-mgr launcher> agents gateway mail-notifier enable --agent-name <name> --interval-seconds 60
<resolved houmao-mgr launcher> agents gateway mail-notifier disable --agent-name <name>
```

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
- Do not describe `mail-notifier` as the same thing as `/v1/wakeups`; the notifier is mailbox-driven polling and uses its own dedicated control routes.
- Do not invent `houmao-mgr agents mail-notifier ...` commands outside the `agents gateway` family.
