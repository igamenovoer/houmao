# Spec Delta

## MODIFIED Requirements

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health, endpoint discovery, enabled public input, status, gateway-managed request submission, reminders, notifier control, and shared mailbox operations on the resolved listener address. Admission SHALL check current owner policy for the verified caller, target domain, canonical resource, and action.

#### Scenario: Gateway HTTP routes apply resource and authority rules

- **GIVEN** the gateway serves its HTTP API on the resolved listener address
- **THEN** each operation uses the canonical resource and action for its effect, including when another surface reaches that effect

The gateway-admin role SHALL authorize every supported client-facing action for the selected target domain. A valid empty administrator roster SHALL give every caller the same permissions as an enrolled administrator. Local policy administration, OS ownership, and internal service identities SHALL retain their own authority. Operation-specific proof, target, transport, and runtime checks SHALL still apply.

The base API SHALL expose uncredentialed `GET /health` and `GET /v1/endpoint`. `GET /v1/status` and `POST /v1/requests` SHALL require their respective status-read and request-submit permissions. The public input setting SHALL enable `POST /v1/messages` and `POST /v1/public/prompt` under the public handoff contract.

The gateway SHALL expose the current SSHSIG challenge and live administrator enrollment operations defined by authenticated gateway access. First registration on a running gateway SHALL require the enrollment proof and a valid empty roster.

The reminder HTTP API SHALL additionally expose `POST /v1/reminders`, `GET /v1/reminders`, `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, and `DELETE /v1/reminders/{reminder_id}`.

The HTTP API SHALL expose the dual-binding summary `GET /v1/mail/status` and channel-selected lifecycle routes `POST /v1/mail/{channel}/{operation}` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`. Each operation SHALL require its own permission, including operator-origin `post`. The channel SHALL be explicitly `offline` or `online`, and lifecycle requests SHALL identify the expected binding ID.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier/{channel}`, `GET /v1/mail-notifier/{channel}`, and `DELETE /v1/mail-notifier/{channel}`.

`GET /health` SHALL return only process health and gateway protocol-version information in a structured response suitable for runtime launch-readiness checks.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

`GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The reminder routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The reminder request models SHALL support either semantic `prompt` delivery or raw `send_keys` delivery, but SHALL require exactly one of those delivery forms for each reminder definition.

Reminder-route validation failures SHALL return HTTP `422`. Unknown reminder identifiers on `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` SHALL return HTTP `404`.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL cover mailbox status, ordinary lifecycle operations, and owner-authorized policy application on the selected channel. Policy application SHALL use mailbox-owner proof as well as gateway admission.

Ordinary `send`, `reply`, read, mark, move, and archive operations SHALL use the shared mailbox abstraction across both the filesystem and `stalwart` transports, subject to the selected binding's supported operations. The mail backend SHALL control placement for protected bindings. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Missing required proof or any invalid supplied proof SHALL return HTTP `401` with applicable challenge information before request processing. Request-validation failures on admitted `POST /v1/requests` SHALL return HTTP `422`. A validly resolved caller lacking the operation permission SHALL receive HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Summary status SHALL remain a normal empty-binding response when neither slot is configured. Lifecycle calls selecting an absent binding SHALL fail explicitly. Unqualified lifecycle routes SHALL NOT infer a channel. Protected mailbox routes SHALL apply caller authority and binding checks on loopback and broader listeners.

For an admitted `POST /v1/mail/{channel}/list` request that fails body validation, the gateway SHALL return structured `detail` entries with error types and schema-defined locations. Unknown body keys SHALL use `["body"]` as the location. The response SHALL give fixed guidance to use `read_state: "unread"` to list unread mail when a body field is unsupported. Validation responses SHALL omit submitted values, arbitrary field names, raw validator messages, and raw request bodies.

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

#### Scenario: A keyed caller has an explicit operation grant

- **WHEN** an enrolled non-admin signer proves its caller identity and owner policy grants the requested operation on the selected target
- **THEN** the operation proceeds with the caller's identity and its ordinary resource checks
- **AND THEN** a request for an action outside the caller's effective grants and roles receives HTTP 403

#### Scenario: Enrolled and open administrators can use the same operations

- **WHEN** an enrolled administrator in keyed mode or an unsigned caller under a valid empty roster requests a supported client-facing action for the selected target domain
- **THEN** both receive the same operation permissions, including owner-file attachment and installed plugin actions
- **AND THEN** each request retains its caller provenance and applies the operation's normal proof, transport, validation, and runtime guards

#### Scenario: An invalid proof accompanies an open operation

- **WHEN** a caller supplies invalid proof for an operation available to unsigned callers
- **THEN** the gateway returns HTTP 401 without processing the operation

#### Scenario: Authorized request names a superseded execution

- **WHEN** an admitted request refers to a gateway instance, agent generation, or resource binding that changes before the protected effect
- **THEN** the gateway refuses the request and leaves the replacement untouched

#### Scenario: An admitted mail-list request uses an unsupported body field

- **WHEN** an admitted caller submits a mail-list request to the offline or online channel with an unsupported body key such as `unread_only`
- **THEN** the gateway returns HTTP 422 with a detail entry for the unsupported field at `["body"]`
- **AND THEN** the response shows `read_state: "unread"` as the supported form for unread listing
- **AND THEN** the response and diagnostic log omit the submitted key and value

#### Scenario: A known mail-list field fails validation

- **WHEN** an admitted caller supplies a value of the wrong type or outside the accepted set for a declared mail-list field
- **THEN** the gateway returns HTTP 422 with the declared field path, such as `["body", "read_state"]`
- **AND THEN** it omits the supplied value and raw validator message

#### Scenario: A mail-list request fails proof before validation

- **WHEN** a mail-list request provides invalid proof or omits required proof
- **THEN** the gateway returns HTTP 401 with the applicable challenge information before returning any body validation guidance
