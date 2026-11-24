# Agent Gateway Delta

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

The shared mailbox routes SHALL be limited to mailbox status, listing, peeking, reading, ordinary `send`, operator-origin `post`, `reply`, explicit marking, moving, and archive behavior.

Ordinary `send`, `reply`, read, mark, move, and archive behavior SHALL continue using the shared mailbox abstraction across both the filesystem and `stalwart` transports. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Missing required proof or any invalid supplied proof SHALL return HTTP `401` with applicable challenge information before request processing. Request-validation failures on admitted `POST /v1/requests` SHALL return HTTP `422`. A validly resolved caller lacking the operation permission SHALL receive HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Summary status SHALL remain a normal empty-binding response when neither slot is configured. Lifecycle calls selecting an absent binding SHALL fail explicitly. Unqualified lifecycle routes SHALL NOT infer a channel. Protected mailbox routes SHALL apply caller authority and binding checks on loopback and broader listeners.

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

### Requirement: Shared gateway mailbox facade exposes lifecycle routes
The shared mailbox facade SHALL expose authorized `GET /v1/mail/status` as a summary of both optional bindings and the derived canonical mail identity. Mailbox-disabled agents SHALL receive a normal empty-binding summary.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The gateway SHALL expose channel-selected lifecycle routes under `/v1/mail/{channel}/` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, where `channel` is `offline` or `online`. The former unqualified lifecycle routes SHALL NOT infer a channel from the canonical mail identity.

List SHALL return triage metadata without marking read. Peek SHALL return selected content without changing read state. Read SHALL return content and mark read. Mark SHALL support recipient-local read/answered state. Move SHALL update supported boxes. Archive SHALL close inbox work through the selected backend.

All lifecycle requests SHALL identify their expected binding ID, obtained from status or current round context, and use runtime-owned authority and scoped references. A replaced binding SHALL fail explicitly even for send/post requests without a message reference. Unsupported operations, absent bindings, and backend failures SHALL be explicit. Callers SHALL NOT need filesystem indexes, mailbox scripts, or provider-native objects. The gateway SHALL authorize each mailbox operation against the selected target and binding. Operator-origin post and mailbox binding controls SHALL each require their corresponding permission.

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

#### Scenario: Authenticated remote admin uses both mail channels

- **WHEN** an authenticated administrator with the requested mailbox permission uses the explicit offline or online lifecycle route with a current expected binding ID
- **THEN** supported ordinary operations follow the same channel, reference, pagination, and mailbox-state semantics as local access
- **AND** the client needs no shared runtime filesystem

#### Scenario: Remote mailbox binding changes before delivery

- **WHEN** a remote request's expected binding no longer identifies the selected owner mailbox
- **THEN** the operation reports the existing scope conflict without delivery from the replacement binding

#### Scenario: Anonymous caller uses ordinary mail with an empty roster

- **WHEN** an unsigned caller accesses an enabled mailbox operation with a current binding ID while the roster is valid and empty
- **THEN** the gateway applies normal channel, reference, and delivery checks with anonymous caller provenance

### Requirement: Plugin Service Operations Respect Gateway Access Policy

Plugin custom routes, credential resolution, workers, and event intake SHALL require valid gateway deployment. A broader listener without validated access configuration SHALL fail before importing plugin code or activating resources. The host SHALL enforce each declared namespaced action on the selected plugin instance using live policy. Sanitized host-owned status SHALL remain available to admitted callers independently of plugin health.

#### Scenario: All-Interface Listener Has Configured Plugins

- **WHEN** a gateway selects host `0.0.0.0` and plugin selections without validated access configuration
- **THEN** startup is refused before implementation imports, credential resolution, or plugin workers
- **AND** no unauthenticated broader plugin surface is published

#### Scenario: Valid broader listener activates selected plugins

- **WHEN** a broader gateway listener has valid access configuration and valid plugin selections
- **THEN** selected plugins can activate under the normal supervised lifecycle
- **AND** custom routes apply their caller and instance grants while trusted background events use their own service identities and retain owner and readiness guards

### Requirement: Public endpoint discovery reports a minimal descriptor

GET /v1/endpoint SHALL publish a secret-free descriptor with target and presence identity, protocol, current `admin_mode`, supported proof protocol and challenge location, enabled public actions, and the configured advertised URL when present. Permission to read detailed status SHALL come from current policy.

#### Scenario: Anonymous caller discovers a protected gateway

- **WHEN** a caller reads the endpoint descriptor without credentials
- **THEN** it receives the current administrator mode, supported proof protocol and challenge location, and enabled public actions
- **AND** detailed status, owner-local paths, roster contents, route access labels, and per-caller grants are absent

#### Scenario: The first key is registered after advertisement

- **WHEN** a caller reads the endpoint descriptor after the first-key registration commits
- **THEN** it reports `admin_mode: keyed`

#### Scenario: The roster is valid and empty

- **WHEN** a caller reads the endpoint descriptor with a valid empty roster
- **THEN** it reports `admin_mode: open`

#### Scenario: Policy is unavailable

- **WHEN** the live gateway cannot read its required access state
- **THEN** it reports `admin_mode: unavailable`

### Requirement: Public input accepts bounded notifications and prompts

Owner enablement in valid target policy SHALL make both public input operations available to anonymous callers. POST /v1/messages SHALL accept bounded source_event_id, text, and optional metadata for a notification. POST /v1/public/prompt SHALL accept bounded source_event_id and prompt for a direct request. Both routes SHALL use strict schemas, finite envelope limits, and a bounded admission budget.

#### Scenario: Public input is disabled by default

- **WHEN** an unconfigured gateway starts and receives a public notification or prompt attempt
- **THEN** both public input operations are unavailable
- **AND** health and endpoint discovery still report their public data

#### Scenario: Uncredentialed caller sends a notification

- **WHEN** a caller sends a valid notice about a message to an enabled gateway and a ready body
- **THEN** the gateway hands off a notification that the agent can act on through its existing access

#### Scenario: Uncredentialed caller submits a prompt

- **WHEN** a caller submits a valid public prompt to an enabled gateway and a ready body
- **THEN** the gateway can start an ordinary turn for the current agent

#### Scenario: Public input exceeds a limit

- **WHEN** public input exceeds its supported envelope or admission limit
- **THEN** the gateway refuses it without starting body work
- **AND** exhausting the admission budget returns HTTP 429

### Requirement: Owner-file inputs on private mail routes follow current elevated access

Send, reply, and post with an owner-local attachment path SHALL require permission for both the mailbox operation and the path form. The gateway-admin role SHALL include both permissions, including under a valid empty roster. The gateway SHALL check authorization before filesystem or provider access and apply existing attachment validation in the recorded owner context.

#### Scenario: Self supplies an owner-local file path

- **WHEN** a self caller in keyed mode has ordinary mailbox access and supplies an owner-local attachment path without permission for that form
- **THEN** the gateway returns HTTP 403 before opening the path or invoking a provider

#### Scenario: Self sends mail without owner-file inputs

- **WHEN** a self caller permitted to send or reply supplies a valid ordinary form without owner-local attachment paths
- **THEN** the operation uses the configured mailbox owner and its normal delivery semantics

#### Scenario: Admitted caller attaches an owner-local file

- **WHEN** a caller with both permissions uses a supported local-path attachment form
- **THEN** the path is interpreted in the recorded owner context under existing attachment validation

#### Scenario: An anonymous caller uses an owner-file attachment

- **WHEN** an unsigned caller supplies a supported owner-local attachment form under a valid empty roster
- **THEN** the gateway authorizes both the mailbox operation and the attachment form through the open gateway-admin role
- **AND THEN** it applies existing attachment validation before any delivery with anonymous caller provenance

#### Scenario: An enrolled administrator attaches an owner-local file

- **WHEN** a verified administrator supplies the same supported attachment form in keyed mode
- **THEN** the gateway authorizes both actions through the gateway-admin role and applies the same owner-context path validation
