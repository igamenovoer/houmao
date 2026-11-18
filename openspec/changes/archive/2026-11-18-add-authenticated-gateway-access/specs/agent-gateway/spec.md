# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Plugin Service Operations Preserve Loopback Listener Policy`
- TO: `### Requirement: Plugin Service Operations Respect Gateway Access Policy`

## MODIFIED Requirements

### Requirement: Each running gateway instance binds one resolved host and port
Each running gateway instance SHALL expose its gateway submit or status surface as an HTTP service bound on exactly one resolved listener address before that gateway instance starts accepting work.

Allowed listener hosts in this change are exactly `127.0.0.1` and `0.0.0.0`. Binding to `0.0.0.0` SHALL require valid explicit access settings and initialized owner access state before live publication or plugin activation. Both listeners SHALL apply the same route access rules, including the admin list's empty state.

When no explicit all-interface bind host is configured, the gateway companion SHALL default to binding on `127.0.0.1:<resolved-port>`.

The gateway companion SHALL attempt to bind that resolved port during startup and SHALL NOT silently switch to a different port if binding fails.

When no explicit gateway port is configured, the system SHALL request a system-assigned port during gateway bind and SHALL NOT pre-probe a free port in the parent runtime process.

When the resolved port is unavailable because another process already owns it or because the bind otherwise fails, startup of that gateway instance SHALL fail explicitly.

When a gateway instance starts successfully with a system-assigned port, the system SHALL persist that resolved host and port as the desired listener for that gateway root and SHALL reuse them on later restarts unless explicitly overridden.

#### Scenario: Gateway starts on the default loopback listener
- **WHEN** the system starts a gateway companion for a gateway-capable tmux-backed session with resolved gateway port `43123`
- **AND WHEN** no explicit all-interface bind host is configured
- **THEN** the gateway companion binds an HTTP service on `127.0.0.1:43123`
- **AND THEN** live gateway discovery for that instance reflects port `43123` rather than an unrelated substituted port

#### Scenario: Explicit all-interface bind uses 0.0.0.0
- **WHEN** the system starts a gateway companion with resolved gateway host `0.0.0.0`, port `43123`, and valid explicit access settings and owner state
- **THEN** the gateway companion binds an HTTP service on `0.0.0.0:43123`
- **AND THEN** the service is reachable through any host interface address that maps to that port

#### Scenario: Port conflict fails gateway attach or start
- **WHEN** the system attempts to start a gateway companion whose resolved gateway port is already bound by another process
- **THEN** the system fails that gateway start or attach operation with an explicit gateway-port conflict error
- **AND THEN** it does not silently retry on a different port for that launch attempt

#### Scenario: Successful system-assigned listener is reused on restart
- **WHEN** a gateway companion first starts successfully with a system-assigned port
- **THEN** the system records that resolved host and port as the desired listener for the gateway root
- **AND THEN** a later restart of that same gateway root reuses that listener unless a caller explicitly overrides it

#### Scenario: Broader binding requires explicit access policy

- **WHEN** an operator selects `0.0.0.0` without valid explicit access settings or initialized owner state
- **THEN** startup fails before live publication or plugin activation
- **AND** there is no live gateway publication from that attempt

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health, endpoint discovery, enabled public input, status, gateway-managed request submission, reminders, notifier control, and shared mailbox operations on the resolved listener address. Route admission SHALL enforce the selected target's public, private, and admin access classes.

The base API SHALL include public `GET /health` and `GET /v1/endpoint`, private `GET /v1/status`, and admin `POST /v1/requests`. The public input setting SHALL enable `POST /v1/messages` and `POST /v1/public/prompt`. Those two routes SHALL use the public handoff contract.

The gateway SHALL expose public `POST /v1/auth/challenge` for self, admin, and first-key registration proof. Admin `POST /v1/admin/keys` and `DELETE /v1/admin/keys/{key_id}` SHALL apply the live membership contract, including first registration on a running gateway with a valid empty list.

The reminder HTTP API SHALL additionally expose `POST /v1/reminders`, `GET /v1/reminders`, `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, and `DELETE /v1/reminders/{reminder_id}`.

The HTTP API SHALL expose the private dual-binding summary `GET /v1/mail/status` and channel-selected lifecycle routes `POST /v1/mail/{channel}/{operation}` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`. Routine lifecycle operations SHALL be private and operator-origin `post` SHALL be admin. The channel SHALL be explicitly `offline` or `online`, and lifecycle requests SHALL identify the expected binding ID.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier/{channel}`, `GET /v1/mail-notifier/{channel}`, and `DELETE /v1/mail-notifier/{channel}`.

Public `GET /health` SHALL return only process health and gateway protocol-version information in a structured response suitable for runtime launch-readiness checks.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

Private `GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The reminder routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The reminder request models SHALL support either semantic `prompt` delivery or raw `send_keys` delivery, but SHALL require exactly one of those delivery forms for each reminder definition.

Reminder-route validation failures SHALL return HTTP `422`. Unknown reminder identifiers on `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` SHALL return HTTP `404`.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, listing, peeking, reading, ordinary `send`, operator-origin `post`, `reply`, explicit marking, moving, and archive behavior.

Ordinary `send`, `reply`, read, mark, move, and archive behavior SHALL continue using the shared mailbox abstraction across both the filesystem and `stalwart` transports. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Missing or invalid required proof SHALL return HTTP `401` with applicable challenge information before request processing. Request-validation failures on admitted `POST /v1/requests` SHALL return HTTP `422`. Insufficient authority SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

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

### Requirement: Shared gateway mailbox facade exposes lifecycle routes
The shared mailbox facade SHALL expose private `GET /v1/mail/status` as a summary of both optional bindings and the derived canonical mail identity. Mailbox-disabled agents SHALL receive a normal empty-binding summary.

The gateway SHALL expose channel-selected lifecycle routes under `/v1/mail/{channel}/` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, where `channel` is `offline` or `online`. The former unqualified lifecycle routes SHALL NOT infer a channel from the canonical mail identity.

List SHALL return triage metadata without marking read. Peek SHALL return selected content without changing read state. Read SHALL return content and mark read. Mark SHALL support recipient-local read/answered state. Move SHALL update supported boxes. Archive SHALL close inbox work through the selected backend.

All lifecycle requests SHALL identify their expected binding ID, obtained from status or current round context, and use runtime-owned authority and scoped references. A replaced binding SHALL fail explicitly even for send/post requests without a message reference. Unsupported operations, absent bindings, and backend failures SHALL be explicit. Callers SHALL NOT need filesystem indexes, mailbox scripts, or provider-native objects. Ordinary mail operations SHALL require signed self or admin proof. Operator-origin post and mailbox binding controls SHALL use the admin route class.

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

- **WHEN** an authenticated admin uses the explicit offline or online lifecycle route with a current expected binding ID
- **THEN** supported ordinary operations follow the same channel, reference, pagination, and mailbox-state semantics as local access
- **AND** the client needs no shared runtime filesystem

#### Scenario: Remote mailbox binding changes before delivery

- **WHEN** a remote request's expected binding no longer identifies the selected owner mailbox
- **THEN** the operation reports the existing scope conflict without delivery from the replacement binding

### Requirement: Plugin Service Operations Respect Gateway Access Policy

Plugin custom routes, credential resolution, workers, and event intake SHALL require valid gateway deployment. A broader listener without validated access configuration SHALL fail before importing plugin code or activating resources. Plugin routes SHALL enforce their declared access class using live policy. Sanitized host-owned status SHALL remain available to admitted callers independently of plugin health.

#### Scenario: All-Interface Listener Has Configured Plugins

- **WHEN** a gateway selects host `0.0.0.0` and plugin selections without validated access configuration
- **THEN** startup is refused before implementation imports, credential resolution, or plugin workers
- **AND** no unauthenticated broader plugin surface is published

#### Scenario: Valid broader listener activates selected plugins

- **WHEN** a broader gateway listener has valid access configuration and valid plugin selections
- **THEN** selected plugins can activate under the normal supervised lifecycle
- **AND** custom routes enforce caller authority while background ordinary events retain owner and readiness guards

### Requirement: Live gateway HTTP clients bypass ambient proxies by default
The live gateway HTTP client SHALL connect directly to its explicit remote base URL or resolved owner-local gateway listener by default and SHALL NOT use ambient proxy environment variables such as `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or their lowercase variants for gateway requests.

This direct-by-default policy SHALL apply consistently to all requests made through the shared gateway client, including health, endpoint discovery, challenge and key operations, status, public notifications and prompts, request submission, prompt control, TUI control, reminder, mail, mail-notifier, and memory calls.

The direct-by-default policy SHALL NOT require mutating process-wide `NO_PROXY` or `no_proxy` values.

When resolving an owner-local listener whose bind host is `0.0.0.0`, the client SHALL connect through `127.0.0.1` while applying the same proxy policy. An explicit remote base URL SHALL retain its configured origin and path prefix and SHALL NOT be rewritten as caller-local loopback.

#### Scenario: Gateway health bypasses proxy-contaminated environments by default
- **WHEN** a live gateway listener is reachable on `127.0.0.1:<port>`
- **AND WHEN** the caller environment defines `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **AND WHEN** the caller environment does not define loopback `NO_PROXY` or `no_proxy`
- **THEN** a gateway client health request reaches the live gateway listener directly
- **AND THEN** the request does not fail solely because the configured proxy cannot reach or forward the loopback listener

#### Scenario: Gateway proxy bypass is shared across gateway client calls
- **WHEN** a caller uses the shared gateway client for status, request submission, control, reminder, mail, notifier, or memory operations
- **AND WHEN** the caller environment contains ambient proxy variables
- **THEN** those gateway client requests use the same direct-by-default proxy policy as health checks
- **AND THEN** each operation's behavior is not dependent on process-wide `NO_PROXY` mutation

#### Scenario: Explicit remote endpoint remains remote

- **WHEN** a client is configured with an advertised HTTPS base URL containing an agent-specific path prefix
- **THEN** requests use that origin and prefix with the existing direct-by-default proxy policy
- **AND** wildcard owner-listener metadata does not replace it with caller-local loopback

## ADDED Requirements

### Requirement: Gateway separates bind local-connect and advertised addresses

The gateway SHALL distinguish its bind address, owner-local connect URL, and explicit advertised remote URL. Live local discovery SHALL retain owner-qualified listener facts. Advertised URLs SHALL be validated non-secret HTTP or HTTPS base URLs under the transport policy. They SHALL NOT be inferred from inbound Host or forwarded headers, or imply a caller-local filesystem or loopback endpoint.

#### Scenario: TLS proxy has a different reachable address

- **WHEN** a gateway binds owner loopback and an operator configures a distinct HTTPS proxy URL
- **THEN** local controls use the owner-local endpoint
- **AND** remote discovery exports the configured HTTPS URL independently of the listener address

#### Scenario: Incoming host header disagrees with configured advertisement

- **WHEN** a request supplies a different Host or forwarded host
- **THEN** it does not change the gateway's advertised endpoint

### Requirement: Public endpoint discovery reports a minimal descriptor

GET /v1/endpoint SHALL return a secret-free descriptor with target and presence identity, protocol, open or key-required admin access, private access requirements, enabled public operations, and the configured advertised URL if present. The descriptor SHALL reflect unavailable admin policy explicitly. Detailed status SHALL require private access.

#### Scenario: Anonymous caller discovers a protected gateway

- **WHEN** a caller reads the endpoint descriptor without credentials
- **THEN** it receives the current access requirements and enabled public operations
- **AND** detailed status, owner-local paths, and roster contents are absent

#### Scenario: The first key is registered after advertisement

- **WHEN** a caller reads the endpoint descriptor after the first-key registration commits
- **THEN** it reports key-required admin access

### Requirement: Public input accepts bounded notifications and prompts

Owner enablement SHALL make both public input routes callable by anyone. POST /v1/messages SHALL accept bounded source_event_id, text, and optional metadata for a notification. POST /v1/public/prompt SHALL accept bounded source_event_id and prompt for a direct request. Both routes SHALL use strict schemas, finite envelope limits, and a bounded admission budget.

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

### Requirement: The gateway labels public input and preserves existing agent policy

The gateway SHALL assign public origin from the matched route and carry it with the turn. It SHALL wrap caller content with a gateway-authored instruction to follow the request only within existing policy and permissions. The caller's text, metadata, and reply directions SHALL be presented as quoted content.

#### Scenario: An admin uses a public route

- **WHEN** an admin credential holder chooses the public prompt route
- **THEN** the delivered prompt and its turn provenance identify public input

#### Scenario: Caller supplies an administrator claim in text

- **WHEN** public text includes instructions or markers claiming another origin or authority
- **THEN** the text remains inside the quoted content of the gateway-authored public envelope

### Requirement: Public input carries ordinary execution authority

Public input SHALL use readiness, pending-input, hook, incarnation, and finite-handoff guards. It SHALL use the current conversation without consuming admin session or model overrides. Its schema SHALL reject control fields. Native-looking command and raw-key text SHALL be inserted as literal content.

#### Scenario: Public caller submits a native command string

- **WHEN** public input includes text resembling a native control action
- **THEN** delivery uses the literal public envelope in the current conversation

#### Scenario: Public caller supplies control fields

- **WHEN** a public request supplies admission policy, session or model selection, interruption, or scheduling fields
- **THEN** validation rejects the request before dispatch

#### Scenario: Admin has prepared a one-shot session change

- **WHEN** a public input request arrives while an admin override is pending
- **THEN** its dispatch preserves that override for an eligible admin request

### Requirement: Public requests return only handoff outcomes

Public success SHALL confirm handoff to the captured body and return the source event ID. The HTTP contract SHALL be limited to handoff, refusal, and uncertainty. The gateway SHALL treat a caller's requested reply channel as content for the agent to evaluate under its existing policy.

#### Scenario: Public prompt requests an answer by mail

- **WHEN** public prompt text asks the agent to deliver a result to an email address or agreed shared file
- **THEN** the gateway renders that direction as content and instructs the agent to honor it only if policy permits
- **AND** the HTTP response contains only the handoff outcome, with any answer delivered separately by the agent

#### Scenario: Target is busy or unavailable

- **WHEN** a public request reaches a target that cannot admit ordinary work
- **THEN** it receives an immediate conflict or unavailable result
- **AND** a later ready state produces no delivery until the sender makes another request

#### Scenario: Confirmation or body identity is lost

- **WHEN** the gateway cannot confirm handoff to the captured body
- **THEN** it reports refusal or uncertainty and retains no request for later delivery
- **AND** a sender retry after uncertain handoff may duplicate delivery

### Requirement: Owner-file inputs on private mail routes require verified admin proof

Private send and reply forms that dereference an owner-local attachment path SHALL require verified admin proof. A current self caller can use ordinary forms that omit these inputs. The gateway SHALL check path-form authority before filesystem or provider access. Admin-class post SHALL apply its own route admission and attachment validation.

#### Scenario: Self supplies an owner-local file path

- **WHEN** a self caller supplies an owner-local attachment path in send or reply
- **THEN** the gateway returns HTTP 403 before opening the path or invoking a provider

#### Scenario: Self sends mail without owner-file inputs

- **WHEN** a self caller supplies a valid ordinary send or reply with no owner-local attachment paths
- **THEN** the operation uses the configured mailbox owner and its normal delivery semantics

#### Scenario: Admitted caller attaches an owner-local file

- **WHEN** an admitted caller uses an existing supported local-path attachment form
- **THEN** the path is interpreted in the recorded owner context under existing attachment validation

