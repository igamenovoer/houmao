# Spec Delta

## MODIFIED Requirements

### Requirement: Shared gateway mailbox facade exposes lifecycle routes
For loopback-bound gateways, the shared mailbox facade SHALL expose `GET /v1/mail/status` as a summary of both optional bindings and the derived canonical mail identity. Mailbox-disabled agents SHALL receive a normal empty-binding summary.

The gateway SHALL expose channel-selected lifecycle routes under `/v1/mail/{channel}/` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, where `channel` is `offline` or `online`. The former unqualified lifecycle routes SHALL NOT infer a channel from the canonical mail identity.

List SHALL return triage metadata without marking read. Peek SHALL return selected content without changing read state. Read SHALL return content and mark read. Mark SHALL support recipient-local read/answered state. Move SHALL update supported boxes. Archive SHALL close inbox work through the selected backend.

All lifecycle requests SHALL identify their expected binding ID, obtained from status or current round context, and use runtime-owned authority and scoped references. A replaced binding SHALL fail explicitly even for send/post requests without a message reference. Unsupported operations, absent bindings, and backend failures SHALL be explicit. Callers SHALL NOT need filesystem indexes, mailbox scripts, or provider-native objects. Mail operations SHALL retain the existing loopback listener policy.

#### Scenario: Peek does not mutate read state through the gateway
- **WHEN** a caller peeks through the selected channel using a matching scoped reference
- **THEN** it receives that message's content without changing recipient read state

#### Scenario: Read mutates read state through the gateway
- **WHEN** a caller reads through the selected channel using a matching scoped reference
- **THEN** it receives that message's content and read state becomes true for that mailbox owner

#### Scenario: Archive shortcut remains available
- **WHEN** a caller archives selected references through their matching channel
- **THEN** the selected backend reports them archived and no longer open inbox work

#### Scenario: Channel omission does not use canonical precedence
- **WHEN** a caller uses an unqualified lifecycle operation without selecting a channel
- **THEN** the request fails explicitly instead of selecting the preferred online address

#### Scenario: Empty status remains readable
- **WHEN** an agent has no offline or online binding
- **THEN** summary status reports both slots absent and no canonical mail identity
- **AND THEN** ordinary core status and control remain available

#### Scenario: A new send pins its intended mailbox
- **WHEN** an account is replaced after a caller observes its binding ID but before a send begins
- **THEN** the send fails with a binding conflict
- **AND THEN** it is not submitted from the replacement account

### Requirement: Gateway reply marks the parent message answered
When a channel-selected gateway reply succeeds, the adapter SHALL mark the parent message `answered=true` and `read=true` for the owning mailbox. Reply SHALL preserve originating channel and binding scope and SHALL NOT archive the parent message.

#### Scenario: Gateway reply acknowledges without closing the mail
- **WHEN** a caller replies through the matching channel and binding
- **THEN** the parent becomes read and answered for that owner
- **AND THEN** it remains open inbox work until archive or a closing move succeeds

### Requirement: Gateway diagnostic logs capture HTTP and mailbox failure evidence without raw sensitive content
When gateway diagnostic logging is enabled, the gateway SHALL record compact diagnostic entries for gateway HTTP requests and outcomes, including validation failures that occur before an endpoint handler is invoked.

Diagnostic entries for HTTP requests SHALL include at minimum method, path, status code, duration, request identifier, and diagnostic event code when those values are available.

Diagnostic entries for gateway mailbox facade operations SHALL include safe operational metadata such as operation name, transport, sender address, recipient addresses, generated message identifier when available, recipient count when available, result status, and repair guidance when applicable.

Diagnostic entries SHALL NOT include mailbox message body content, raw prompt text, attachment contents, authorization headers, cookie headers, bearer tokens, credential material, or environment secrets by default.

#### Scenario: Malformed mailbox send request is captured
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a caller submits a malformed `POST /v1/mail/offline/send` request that fails request-body validation before route handling
- **THEN** the gateway records a diagnostic entry for the failed HTTP request
- **AND THEN** the entry includes the route, status code, and normalized validation error locations
- **AND THEN** the entry does not include a mailbox body or raw request body dump

#### Scenario: Mailbox delivery failure records repair context safely
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a gateway mailbox send reaches mailbox delivery but fails because mailbox-local state is unreadable or missing
- **THEN** the gateway records a diagnostic entry for the mailbox failure
- **AND THEN** the entry includes the operation, transport, safe participant metadata, error category, and repair hint when available
- **AND THEN** the entry does not include the message body or attachment contents

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health inspection, status inspection, gateway-managed request submission, reminder registration and inspection, gateway-owned notifier control, and, when permitted by mailbox bindings and listener policy, shared mailbox operations on the resolved listener address for that session.

The base gateway HTTP API SHALL expose `GET /health`, `GET /v1/status`, and `POST /v1/requests`.

The reminder HTTP API SHALL additionally expose `POST /v1/reminders`, `GET /v1/reminders`, `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, and `DELETE /v1/reminders/{reminder_id}`.

For loopback listeners, that HTTP API SHALL expose the dual-binding summary `GET /v1/mail/status` and channel-selected lifecycle routes `POST /v1/mail/{channel}/{operation}` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`. The channel SHALL be explicitly `offline` or `online`, and lifecycle requests SHALL identify the expected binding ID.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier/{channel}`, `GET /v1/mail-notifier/{channel}`, and `DELETE /v1/mail-notifier/{channel}`.

`GET /health` SHALL return a structured response suitable for runtime launch-readiness checks and SHALL include gateway protocol-version information.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

`GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The reminder routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The reminder request models SHALL support either semantic `prompt` delivery or raw `send_keys` delivery, but SHALL require exactly one of those delivery forms for each reminder definition.

Reminder-route validation failures SHALL return HTTP `422`. Unknown reminder identifiers on `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` SHALL return HTTP `404`.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, listing, peeking, reading, ordinary `send`, operator-origin `post`, `reply`, explicit marking, moving, and archive behavior.

Ordinary `send`, `reply`, read, mark, move, and archive behavior SHALL continue using the shared mailbox abstraction across both the filesystem and `stalwart` transports. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Request-validation failures on `POST /v1/requests` SHALL return HTTP `422`. Explicit gateway policy rejection SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Summary status SHALL remain a normal empty-binding response when neither slot is configured. Lifecycle calls selecting an absent binding SHALL fail explicitly rather than pretending mailbox support exists. Unqualified lifecycle routes SHALL NOT infer a channel. When the live gateway listener is bound to `0.0.0.0`, the `/v1/mail/*` routes SHALL fail explicitly as unavailable until an authentication model exists for broader listeners.

Read-oriented HTTP endpoints and mailbox read routes SHALL NOT consume the terminal-mutation slot solely to report current gateway health, core status, reminder state, notifier status, or shared mailbox state.

#### Scenario: Reminder registration uses the live gateway HTTP surface
- **WHEN** a caller needs to register, inspect, update, or cancel live reminders for an attached gateway-managed session
- **THEN** the caller uses the dedicated `/v1/reminders` route family on that live gateway listener
- **AND THEN** the caller does not need to mutate private runtime state or transport queue artifacts directly

#### Scenario: Send-keys reminder request is validated through the reminder route family
- **WHEN** a caller submits a reminder definition with `send_keys` through `/v1/reminders`
- **THEN** the reminder request is validated on that reminder route family
- **AND THEN** the caller does not need to use a separate reminder-specific control-input route

#### Scenario: Unknown reminder identifier fails explicitly
- **WHEN** a caller requests `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` for a non-existent reminder
- **THEN** the gateway rejects that call explicitly
- **AND THEN** it does not pretend that the requested reminder still exists

### Requirement: Gateway notifier records structured per-poll decision auditing for later review
When gateway-owned notifier behavior is enabled, the gateway SHALL record one structured notifier-decision audit record for each enabled poll cycle in a queryable SQLite audit table under the gateway state root.

Each record SHALL capture enough detail to explain what the notifier saw and why it enqueued or skipped work, including at minimum:

- poll time,
- owner, selected channel, and binding identity,
- unread-count observation,
- unread-set identity or equivalent deduplication summary,
- request-admission state,
- active-execution state,
- queue depth,
- the notifier decision outcome, and
- enqueue identifiers or skip detail when applicable.

The gateway MAY continue to keep `gateway.log` rate-limited and human-oriented, but that human log SHALL NOT be the only durable source of per-poll notifier decision history.

Detailed per-poll decision history SHALL remain available through that durable audit table even if `GET /v1/mail-notifier/{channel}` remains a compact status snapshot without last-decision summary fields.

#### Scenario: Busy poll records an explicit skip decision
- **WHEN** a notifier poll cycle finds unread mail while gateway admission is not open, active execution is running, or queue depth is non-zero
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record identifies the decision as a busy or ineligible skip and includes the eligibility inputs that caused the skip

#### Scenario: Enqueue poll records the created reminder request
- **WHEN** a notifier poll cycle finds unread mail and the gateway enqueues an internal reminder prompt
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record includes the reminder decision outcome and the created internal request identifier

#### Scenario: Durable audit history remains the detailed inspection surface
- **WHEN** an operator or demo helper needs the latest detailed notifier decision data
- **THEN** it can inspect the durable SQLite notifier audit history under the gateway root
- **AND THEN** the gateway does not need to expose additional last-decision summary fields on `GET /v1/mail-notifier/{channel}` in order to satisfy this requirement

### Requirement: Gateway operator-origin post defaults to operator mailbox replies
`POST /v1/mail/offline/post` SHALL default omitted `reply_policy` fields to `operator_mailbox`.

The gateway mailbox post request model SHALL continue to accept explicit `reply_policy` values of `none` and `operator_mailbox`.

When `reply_policy` is omitted or set to `operator_mailbox`, the created operator-origin message SHALL record reply-enabled policy metadata and route replies to `HOUMAO-operator@houmao.localhost`.

When `reply_policy` is explicitly set to `none`, the created operator-origin message SHALL remain no-reply and later replies against that message SHALL fail explicitly.

Pair-managed mail-post proxy request models that inherit the live gateway mailbox post model SHALL preserve this same omitted-field default.

#### Scenario: Direct gateway post omitted policy creates a reply-enabled message
- **WHEN** a caller posts to `/v1/mail/offline/post` with subject and body but without `reply_policy`
- **THEN** the gateway creates an operator-origin message with reply policy `operator_mailbox`
- **AND THEN** a later `/v1/mail/offline/reply` against that message is accepted and routed to `HOUMAO-operator@houmao.localhost`

#### Scenario: Direct gateway explicit no-reply policy is honored
- **WHEN** a caller posts to `/v1/mail/offline/post` with `reply_policy` set to `none`
- **THEN** the gateway creates an operator-origin message with no-reply policy metadata
- **AND THEN** a later `/v1/mail/offline/reply` against that message fails explicitly

#### Scenario: Pair-managed proxy preserves gateway post default
- **WHEN** a pair-managed caller posts operator-origin mail without `reply_policy`
- **THEN** the pair-managed proxy forwards a request that resolves to the gateway's `operator_mailbox` default
- **AND THEN** the resulting message has the same reply-enabled behavior as direct `/v1/mail/offline/post`
