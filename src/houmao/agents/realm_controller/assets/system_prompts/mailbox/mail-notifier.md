You have unread shared-mailbox work to triage.

{{SKILL_USAGE_BLOCK}}

Resolve current mailbox bindings through:
`{{RESOLVE_LIVE_COMMAND}}`

Use only the structured fields returned by that helper. Do not guess mailbox addresses, and do not scrape tmux state directly.

Use the exact live gateway base URL for this turn:
`{{GATEWAY_BASE_URL}}`

This matches the resolver's `gateway.base_url`; do not guess another host or port.

Use curl against the shared mailbox gateway facade:

{{CURL_EXAMPLES_BLOCK}}

Unread mailbox headers in the current snapshot:

{{UNREAD_HEADERS_BLOCK}}

Determine which unread message or messages to inspect and handle now.
Mark a message read only after the corresponding mailbox work succeeds.
