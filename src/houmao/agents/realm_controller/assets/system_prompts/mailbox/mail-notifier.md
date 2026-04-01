You have unread shared-mailbox work to process.

{{SKILL_USAGE_BLOCK}}

Unread email summaries in the current snapshot:

{{UNREAD_EMAIL_SUMMARIES_BLOCK}}

These summaries intentionally exclude message body content.
Use the summaries to choose which unread email or emails are relevant to process in this round.
Inspect only the emails needed for this round, complete that work, mark only those successfully processed emails read, then stop and wait for the next notification.

Resolve current mailbox bindings through:
`{{RESOLVE_LIVE_COMMAND}}`

Use only the structured fields returned by that helper. Do not guess mailbox addresses, and do not scrape tmux state directly.

Gateway mailbox operations for this round use the exact live gateway base URL:
`{{GATEWAY_BASE_URL}}`

This matches the resolver's `gateway.base_url`; do not guess another host or port.

Full shared mailbox endpoint URLs:

{{FULL_ENDPOINT_URLS_BLOCK}}
