# gateway-plugin-api Specification

## Purpose

Define how independently distributed trusted Python packages extend per-agent gateways through a public, versioned SDK, explicit owner-bound configuration, deterministic route ownership, supervised resources, and immediate ordinary-event dispatch with sender-owned retries.

## Requirements

### Requirement: External Packages Extend Gateways Through a Public SDK

Houmao SHALL publish supported plugin-author contracts under `houmao.gateway.plugins`. An independently distributed plugin SHALL be usable without modifying Houmao files or importing gateway implementation types. The plugin contract SHALL declare an explicit SDK version and configuration schema.

#### Scenario: Separately Installed Plugin Extends an Installed Houmao Wheel

- **WHEN** a conforming plugin package and the Houmao wheel are installed in a fresh environment and that plugin is explicitly configured
- **THEN** a normal gateway launch discovers and serves the plugin
- **AND THEN** neither package requires repository source paths or edits to Houmao's installed files

#### Scenario: Unsupported SDK Version Is Diagnosable

- **WHEN** a selected plugin declares an unsupported SDK version
- **THEN** its configured instances fail before resource activation with an explicit compatibility diagnostic
- **AND THEN** core routes and unrelated compatible instances remain available

### Requirement: Package Discovery Loads Only Explicitly Selected Implementations

The gateway SHALL discover plugin definitions through the `houmao.gateway_plugins` package entry-point group in its own execution environment. It SHALL import only explicitly selected implementations. Missing implementations, ambiguous selected names, and load errors SHALL fail affected instances explicitly.

#### Scenario: Unselected Installed Plugin Is Never Imported

- **WHEN** an installed distribution advertises a plugin that is absent from gateway configuration
- **THEN** gateway discovery does not import or activate that implementation

#### Scenario: Two Distributions Advertise the Same Selected Name

- **WHEN** multiple installed distributions advertise the same selected implementation name
- **THEN** every instance selecting that name reports ambiguity and remains inactive
- **AND THEN** diagnostics identify the competing distributions without selecting an import-order winner

#### Scenario: Package Is Missing From the Child Environment

- **WHEN** configuration selects an implementation unavailable in the gateway interpreter's environment
- **THEN** that instance reports an unavailable implementation
- **AND THEN** the gateway does not install packages or search the agent worktree for replacement code

### Requirement: Plugin Configuration Rejects Ambiguous Documents

The supported configuration interface SHALL validate document version, unique instance IDs, selected implementations, reference shapes, and finite resource bounds. It SHALL reject duplicate YAML or JSON keys, invalid IDs, and unknown host fields before applying or persisting a supplied configuration.

#### Scenario: Duplicate Instance Key Is Rejected Before Application

- **WHEN** an operator supplies a document repeating a plugin instance key
- **THEN** configuration fails explicitly before any candidate replaces persisted or active selections
- **AND THEN** parser key order does not silently choose a value

#### Scenario: Invalid Resource Limit Is Rejected

- **WHEN** a supplied event limit is non-finite, non-positive, or otherwise invalid for its declared bound
- **THEN** configuration is rejected before gateway or plugin process changes

#### Scenario: Invalid Implementation Configuration Fails Only Its Instance

- **WHEN** a valid host document contains settings rejected by one selected implementation's schema
- **THEN** that instance reports safe validation locations and remains inactive
- **AND THEN** unrelated valid instances can activate

### Requirement: Plugin Context Is Bound to the Gateway Owner

Each plugin context SHALL use manifest-backed agent and runtime identity plus the selected service binding. Ordinary requests SHALL NOT override owner, sender, credentials, or service identity. The supported context SHALL expose ordinary service/event operations without privileged operator control or service-administration authority.

#### Scenario: Caller Attempts to Replace the Sender

- **WHEN** an ordinary plugin request supplies a sender or credential override outside the configured owner binding
- **THEN** the plugin rejects that override before sending through the service
- **AND THEN** it does not use another agent's identity or credentials

#### Scenario: Two Owners Use the Same Implementation

- **WHEN** two agent gateways enable the same implementation with different service accounts
- **THEN** each instance uses its own owner's binding, credential selection, state, and event namespace

### Requirement: Credentials Use an Explicit Private Reference

Plugin credentials SHALL be resolved only from the selected owner-private external file reference during an active lifespan. Missing, unsafe, or unreadable references SHALL fail explicitly. SDK credential access SHALL NOT enumerate other bindings, scan homes, fall back to ambient auth, or accept replacement paths from ordinary route requests.

#### Scenario: Missing Selected File Does Not Use Ambient Credentials

- **WHEN** the selected credential file is missing while another credential is available in the environment or user home
- **THEN** credential resolution fails for the affected instance
- **AND THEN** the gateway does not use that ambient credential as a fallback

#### Scenario: Unsafe Credential File Is Rejected

- **WHEN** a credential reference targets the project checkout, a symlink, an unexpected owner, or a file whose permissions expose its contents to other users
- **THEN** the instance reports a safe credential-reference error without reading or publishing the material

#### Scenario: Selected Credential Source Is Refreshed

- **WHEN** credentials rotate in the same authorized file and a running plugin refreshes that source
- **THEN** it can reconnect using the refreshed material without changing the owner binding or restarting the agent body

### Requirement: Private State Follows Stable Service Binding Identity

Plugin state SHALL remain contained within its owner, runtime, instance, implementation, and stable service-binding scope. Gateway restarts and credential rotation SHALL preserve that scope. Replacing the service/account binding SHALL NOT reuse the previous binding's cursor. Private state SHALL NOT serve as a message cache or retry spool.

#### Scenario: Gateway Restart Preserves a Service Cursor

- **WHEN** the same configured binding restarts in another gateway process
- **THEN** its saved service cursor and binding-scoped configuration remain available
- **AND THEN** process IDs and package load order do not create a fresh binding

#### Scenario: Instance Name Is Reused for Another Account

- **WHEN** configuration reuses an instance name for a different authenticated service/account binding
- **THEN** the new binding receives separate private state
- **AND THEN** the previous account's cursor or sender identity is not reused for the replacement

#### Scenario: Plugin State Path Escapes Its Scope

- **WHEN** a requested plugin-state path would traverse outside its binding root or follow a symlink outside it
- **THEN** scoped state access rejects the path without touching the escaped target

### Requirement: The Host Assigns Plugin HTTP Namespaces

Plugin HTTP routes SHALL be confined to the host-assigned `/v1/plugins/{instance_id}/` namespace. The host SHALL reserve its status subtree and core routes. SDK v1 SHALL reject unsupported global application mutations and route forms that cannot be validated deterministically before activation.

#### Scenario: Two Plugins Declare the Same Relative Endpoint

- **WHEN** distinct valid instances `team-chat` and `team-mail` both declare `POST /send`
- **THEN** their routes are `/v1/plugins/team-chat/send` and `/v1/plugins/team-mail/send`
- **AND THEN** neither declaration claims the other instance's URL

#### Scenario: Plugin Tries to Claim a Core or Reserved Endpoint

- **WHEN** a plugin declaration attempts to escape its namespace or replace the host-owned `_status` subtree
- **THEN** its registration fails before activation
- **AND THEN** the host endpoint remains authoritative

#### Scenario: Unsupported Route Mutation Is Rejected

- **WHEN** a plugin supplies root middleware, independent startup handlers, nested mounts, custom converters, or other unsupported global route mutations
- **THEN** the host rejects the instance's registration with a safe explanation

### Requirement: Route Conflicts Disable Every Participating Plugin

The host SHALL validate the complete candidate route set before activation. Overlapping effective methods and matching path patterns SHALL constitute a conflict, including equivalent parameter names and catch-alls. Every participating plugin instance SHALL remain inactive; core routes and unrelated instances SHALL remain available.

#### Scenario: Equivalent Parameter Names Collide

- **WHEN** an instance declares `GET /messages/{id}` and `GET /messages/{name}`
- **THEN** the host rejects the instance's route set as conflicting
- **AND THEN** diagnostics identify both declarations

#### Scenario: Literal and Parameterized Paths Overlap

- **WHEN** an instance declares `GET /messages/latest` and `GET /messages/{id}`
- **THEN** both declarations are treated as overlapping for registration
- **AND THEN** ordering the literal route first does not waive the conflict

#### Scenario: Catch-All Overlaps Another Endpoint

- **WHEN** a terminal catch-all can match another route with an intersecting method set
- **THEN** the host rejects every plugin instance participating in that conflict before activating resources

#### Scenario: Distinct Methods Share a Path

- **WHEN** an instance declares `GET /messages` and `POST /messages` with disjoint effective method sets
- **THEN** both operations can register at that path

#### Scenario: Registration Order Is Reversed

- **WHEN** the same conflicting candidate set is provided in another configuration or distribution order
- **THEN** the same instances fail with equivalent conflict evidence
- **AND THEN** no first-registered or last-registered plugin becomes the winner

#### Scenario: Conflicting Instance Is Never Activated

- **WHEN** staged route validation fails for an instance
- **THEN** that instance does not resolve credentials, connect to a service, or start workers
- **AND THEN** its status remains readable while custom-route calls return a safe unavailable response

### Requirement: Plugin Resources Have a Supervised Lifespan

The host SHALL supervise per-instance startup, workers, cancellation, and cleanup with finite cooperative deadlines. Partial initialization and unexpected worker failures SHALL revoke the affected instance's dispatch access, release acquired resources, and remain diagnosable. Unrelated instances and core control SHALL continue operating.

#### Scenario: Startup Fails After Acquiring a Client

- **WHEN** a plugin acquires a client and then fails during startup
- **THEN** acquired resources are closed, supervised workers are canceled, and its instance reports failed
- **AND THEN** an ordinary core status or operator-control request remains available

#### Scenario: One Listener Fails

- **WHEN** a supervised listener terminates unexpectedly
- **THEN** its instance reports the worker failure and refuses ordinary event dispatch
- **AND THEN** another plugin's workers and core workers continue

#### Scenario: Cooperative Shutdown Cancels Outstanding Work

- **WHEN** the gateway shuts down with active plugin workers
- **THEN** the host closes plugin request admission, cancels and awaits those workers, and exits their resource lifespans before stopping required core facilities
- **AND THEN** a cleanup timeout is reported without holding the terminal-mutation lock indefinitely
- **AND THEN** interrupted event requests fail where a response is possible and retain no payload for later resend

### Requirement: Loaded Plugins Manage Their Configured Service Connection

A loaded plugin SHALL support its documented connect, reconnect, detach, and selected-source credential-refresh behavior without restarting the agent body. Those transitions SHALL remain within the configured owner/service binding. Changing plugin code, selected implementation, immutable configuration, or credential references SHALL require a gateway restart.

#### Scenario: Service Is Temporarily Unavailable

- **WHEN** a loaded plugin cannot connect to its configured endpoint
- **THEN** connection status reports the failure and any bounded reconnect progress independently of core health
- **AND THEN** successful reconnect uses the same owner binding without replaying cached message payloads

#### Scenario: Route Caller Tries to Replace the Implementation

- **WHEN** an ordinary HTTP caller attempts to install plugin code, select another implementation, or replace the configured account
- **THEN** the supported plugin API offers no authority to apply that change

### Requirement: Plugin Status Remains Readable During Failure

The gateway SHALL expose `GET /v1/plugins` and `GET /v1/plugins/{instance_id}/_status` as host-owned status surfaces. Reads SHALL use maintained snapshots and report lifecycle, connection, resource, active-request, and safe error information without service network calls. Unknown instances SHALL return 404.

#### Scenario: Failed Plugin Status Is Queried

- **WHEN** a caller queries the status of a known instance whose startup or registration failed
- **THEN** the host returns that instance's sanitized failure status
- **AND THEN** it does not invoke the failed plugin to obtain health information

#### Scenario: Unknown Instance Is Queried

- **WHEN** a caller requests an unconfigured instance's status
- **THEN** the host returns 404 rather than guessing another instance

### Requirement: Plugin Diagnostics Exclude Private Material

Default plugin status and host diagnostics SHALL exclude credentials, credential paths, raw configuration values, event bodies, authorization headers, environment secrets, and unsanitized provider exceptions. Registration and validation errors SHALL identify safe implementation, instance, method, path, field-location, and error-code metadata where applicable.

#### Scenario: Provider Exception Contains a Secret

- **WHEN** a plugin failure includes secret material in a provider exception
- **THEN** default host diagnostics report a safe failure code and context without publishing that exception text or secret

#### Scenario: Route Conflict Is Reported

- **WHEN** the host reports a route conflict
- **THEN** diagnostics identify the involved instances, methods, patterns, and counterpart declarations
- **AND THEN** they contain no credential or configuration-value dump

### Requirement: Ordinary Events Use Immediate Request-Scoped Dispatch

The SDK SHALL dispatch valid ordinary events immediately only when the gateway, plugin, and current agent body are ready. Success SHALL follow confirmed dispatch to that body. It SHALL NOT acknowledge a pending message, cache an event for later delivery, or enqueue a retry. Invalid and oversized input SHALL fail explicitly within finite request bounds.

#### Scenario: Ready Body Receives an Ordinary Event

- **WHEN** an authorized plugin dispatches a valid event to a ready body and the adapter confirms handoff to that same body
- **THEN** the request succeeds with a dispatched result and its source event ID
- **AND THEN** success does not claim that the agent finished processing the message or completed its turn

#### Scenario: Busy Body Refuses an Event

- **WHEN** the body is busy or not decisively ready when an event arrives
- **THEN** the request returns a retryable readiness error without waiting for readiness
- **AND THEN** no message payload is accepted into a deferred inbox or retry spool

#### Scenario: Invalid or Oversized Event Is Supplied

- **WHEN** the supplied event violates its schema or configured finite envelope-size bound
- **THEN** the request returns a non-retryable input error without dispatch or deferred acceptance

#### Scenario: Old Worker Uses a Revoked Context

- **WHEN** a worker tries to dispatch after its instance's context generation has been revoked
- **THEN** the SDK returns an explicit unavailable error
- **AND THEN** it does not retain the message or send it through a replacement context

### Requirement: Senders Retain Messages After Unsuccessful Dispatch

The sender SHALL own retention and retry of unsuccessful plugin messages. The SDK SHALL distinguish retryable readiness/availability failures from invalid input and report uncertain dispatch honestly. Gateway recovery SHALL NOT initiate another attempt. Source IDs SHALL remain correlation metadata without a generic durable deduplication or exactly-once guarantee.

#### Scenario: Readiness Error Reaches an HTTP Sender

- **WHEN** an event request is refused because the body is not ready
- **THEN** the HTTP-facing plugin response reports a readiness conflict with `retryable=true`
- **AND THEN** the sender retains the message and chooses when to make another request

#### Scenario: Gateway Is Absent or Dies During a Request

- **WHEN** no gateway can answer or its process dies before completing the response
- **THEN** the sender treats connection failure, connection loss, or timeout as an unsuccessful attempt
- **AND THEN** a later gateway start does not resend that message automatically

#### Scenario: Body Failure Is Reported to the Upstream Service

- **WHEN** a body dies or restarts before an in-flight event request can complete successfully
- **THEN** the plugin returns or propagates a retryable failure rather than positively acknowledging upstream consumption
- **AND THEN** the message is not cached on the agent side for replay

#### Scenario: Response Is Lost After Actual Dispatch

- **WHEN** the body receives the message but the sender cannot obtain the successful response
- **THEN** the attempt is uncertain from the sender's perspective and retry can cause a duplicate
- **AND THEN** this API does not claim exactly-once delivery or reconstruct a durable success receipt after restart

### Requirement: Ordinary Event Content Cannot Acquire Control Authority

Plugin event submissions SHALL remain ordinary notifications. They SHALL NOT select interrupt, raw input, reset, execution override, or admission-bypass behavior. The delivered envelope SHALL retain host provenance and treat service content as message text, including text resembling native control commands.

#### Scenario: Peer Sends a Context-Control Command as Text

- **WHEN** an ordinary service event contains only `/new`, `/compact`, or control-key-looking text
- **THEN** delivery treats it as content in an ordinary notification envelope
- **AND THEN** it does not execute a gateway control intent or raw key sequence

#### Scenario: Submission Requests Privileged Delivery

- **WHEN** a plugin tries to submit an ordinary event with an interrupt kind or readiness-bypass option
- **THEN** the SDK rejects the unsupported authority selection
- **AND THEN** the agent's ordinary admission guards remain authoritative

### Requirement: Plugin route authority is declared and enforced by the host

Plugin HTTP routes SHALL use private or admin access through the supported SDK. Omitted declarations SHALL use the admin class. Invalid declarations, including public access, SHALL fail the instance before resource activation. The host SHALL apply the matched access class and current roster before invoking plugin code. A valid empty roster permits unsigned calls to both classes.

#### Scenario: Private plugin route admits self and admin

- **WHEN** the agent's current self or an admin invokes a plugin route classified as private
- **THEN** the host permits normal instance and operation admission under the existing owner binding

#### Scenario: Undeclared route is called by self

- **WHEN** a self caller invokes a plugin route without an access declaration while the admin list has entries
- **THEN** the host returns HTTP 403 before the plugin handler runs

#### Scenario: Admin plugin route follows open access

- **WHEN** an anonymous caller invokes an admin plugin route while the initialized list is empty
- **THEN** the host admits it with anonymous provenance
- **AND** an unsigned private plugin operation also receives anonymous admission

#### Scenario: Plugin declares an unsupported authority

- **WHEN** staged plugin routes contain an unknown or public access value
- **THEN** the affected instance fails registration before credentials, connections, or workers activate
- **AND** unrelated valid instances and classified core routes remain available

### Requirement: Authenticated plugin routes preserve owner and caller separation

Admitted plugin calls SHALL retain the configured owner, service binding, provider credential, and ordinary-event dispatch contract. The initiating HTTP principal and the plugin sender SHALL have distinct provenance. The host SHALL keep caller credentials out of plugin contexts.

#### Scenario: Remote CCCC caller sends ordinary chat or Mail

- **WHEN** current self or an admin invokes a private CCCC chat or Mail route
- **THEN** the configured gateway owner's Group and Actor remain authoritative
- **AND** backend-specific delivery, consumption, cursor, and uncertain-outcome semantics remain unchanged

#### Scenario: Self calls plugin connection management

- **WHEN** a self caller requests connect, disconnect, reconnect, or credential refresh on a key-required admin plugin route
- **THEN** HTTP 403 is returned before changing connection state or refreshing a source

#### Scenario: Remote request claims another plugin owner

- **WHEN** a caller provides an alternate sender, provider credential, or service binding through ordinary request content
- **THEN** the plugin rejects that override under the existing owner-bound contract

### Requirement: Plugin background resources share the secured deployment boundary

A selected plugin's activation and ordinary background dispatch SHALL use the validated gateway deployment policy. Broader listeners with valid settings SHALL support the same supervised resources as loopback listeners. Background workers SHALL use their configured service authority independently of HTTP caller admission.

#### Scenario: Broader listener receives a service event

- **WHEN** a running plugin on a validated broader listener receives an ordinary service event
- **THEN** existing readiness, current-body, and confirmed-handoff checks determine delivery
- **AND** the background worker uses its service authority

#### Scenario: Invalid deployment is rejected before plugin import

- **WHEN** a broader listener lacks validated access configuration
- **THEN** selected plugin code is not imported and service resources do not activate

### Requirement: Route admission precedes plugin lifecycle error handling

The gateway SHALL apply the route's current admission policy before exposing plugin lifecycle, registration, or connection failures. Sanitized host-owned plugin status SHALL remain available to admitted callers without invoking external service code.

#### Scenario: Unauthenticated caller probes a failed instance

- **WHEN** an uncredentialed caller requests a failed plugin's private or admin route while the roster has keys
- **THEN** the response is HTTP 401 without exposing its failure details

#### Scenario: Authorized caller inspects a failed instance

- **WHEN** an authorized caller requests the host-owned status of a failed plugin
- **THEN** it receives the existing sanitized failure snapshot independently of plugin health

#### Scenario: Anonymous caller inspects a failed instance

- **WHEN** an unsigned caller requests the host-owned status of a failed plugin while the roster is valid and empty
- **THEN** it receives the existing sanitized failure snapshot
