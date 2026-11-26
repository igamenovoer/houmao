# Agent Gateway Delta

## ADDED Requirements

### Requirement: Gateway Notifier Aggregates the Current Eligible Inbox Set

When a mail notifier is enabled, the gateway SHALL use messages the selected backend exposes in its Inbox that satisfy the configured mode. It SHALL apply current readiness and queue admission. A poll can produce one reminder for the eligible set. An unchanged eligible set SHALL remain eligible for later reminder cycles.

#### Scenario: Multiple eligible messages are represented by one reminder

- **WHEN** the notifier observes multiple eligible Inbox messages in one cycle
- **THEN** it can enqueue one aggregate reminder instead of requiring a reminder per message
- **AND THEN** any message details it presents are limited to the eligible set

#### Scenario: Unchanged eligible mail can generate a later reminder

- **WHEN** a prior reminder has been enqueued or delivered and a later poll finds the same eligible set with an agent ready for work
- **THEN** the gateway can admit a later reminder despite the unchanged set

#### Scenario: Operator activity does not retire mail eligibility

- **WHEN** an operator command or unrelated session activity intervenes after an earlier reminder and eligible work remains
- **THEN** the gateway can admit a later reminder when readiness allows

### Requirement: Typed Work Requests Use Current Caller Authority and Attribution

`POST /v1/requests` SHALL accept `submit_work_request` with bounded, nonempty text and require `agent.request.submit` on `agent`. The gateway SHALL use verified attribution or explicit anonymous provenance for each admitted request. It SHALL present caller text as quoted content under the agent's current instructions. The request SHALL use the current conversation, configured model, and ready-only native handoff.

#### Scenario: Alice sends a scoped work request to Bob
- **WHEN** Alice's verified peer key has `agent.request.submit` on Bob and she submits “Review PR 42”
- **THEN** Bob's input identifies Alice as the verified requester and delivers the quoted task under Bob's current instructions
- **AND THEN** the response identifies the existing request and reports acceptance or handoff separately from task completion

#### Scenario: Caller supplies command-looking request content
- **WHEN** a valid work request contains `/compact`, `<[Escape]>`, or text that claims an administrator identity
- **THEN** Bob receives that content as quoted request data with the proof-derived attribution
- **AND THEN** the gateway performs zero native slash commands or raw terminal actions from the request text

#### Scenario: Work request supplies execution controls
- **WHEN** a caller includes caller identity, raw input, an admission override, a session selector, or a model override in a work-request payload
- **THEN** request validation rejects the fields
- **AND THEN** existing next-prompt overrides remain available to their original authorized path

#### Scenario: Open gateway accepts unsigned work requests
- **WHEN** the target has an initialized empty admin roster and an unsigned caller submits a valid work request
- **THEN** the gateway applies open administrator authority and explicitly attributes the work request to an anonymous caller

#### Scenario: Keyed gateway accepts a request from a new peer
- **WHEN** Bob has a keyed roster, `default_permission_group` is `agent-requester`, and a new peer submits a valid work request without Bob-side enrollment
- **THEN** the request uses Bob's default permissions
- **AND THEN** the gateway preserves independently verified attribution when available and explicitly records anonymous provenance for unsigned input

#### Scenario: An identified caller has default fallback disabled
- **WHEN** Alice proves her identity and submits a work request to keyed Bob with an `agent-requester` default, where Bob disabled her default fallback and granted her only status read
- **THEN** the gateway refuses the work-request effect under Alice's verified identity

#### Scenario: The caller separately submits an unsigned work request
- **WHEN** Alice separately submits a valid work request without proof to keyed Bob with the `agent-requester` default and disabled fallback for her verified identity
- **THEN** the gateway admits the request under the default and attributes it to an anonymous caller
- **AND THEN** normal request validation and readiness checks still apply

#### Scenario: A request carries invalid proof
- **WHEN** a caller submits invalid proof alongside a work request that would be allowed without proof
- **THEN** the gateway refuses the request at proof validation

### Requirement: Gateway Administration Sets Principal Default Fallback

`PUT /v1/admin/principals/{principal_id}/default-fallback` SHALL accept an `enabled` boolean for an enrolled principal on the selected target. The gateway SHALL require the admin-exclusive `admin.default-fallback.set` effect on `policy`, recheck authority at commit, and return the retained setting and its committed revision.

#### Scenario: Bob limits his verified caller to exact grants

- **WHEN** Bob's authorized administrator disables default fallback for Alice through his verified gateway
- **THEN** the gateway records Alice's setting on Bob's retained policy
- **AND THEN** later verified calls from Alice use only otherwise applicable authority

#### Scenario: A requester tries to change fallback

- **WHEN** a caller with only `agent-requester` tries to change a principal's setting
- **THEN** the gateway refuses the operation before committing any policy change

### Requirement: Gateway Relays Owner-Authorized Mail Policy Updates

`POST /v1/mail/{channel}/policy/apply` SHALL relay a mailbox-owner-signed request for the exact backend, mailbox binding, mail rules, expected policy revision, and operation ID. The gateway SHALL require effective gateway administration to relay it. The selected backend or its trusted management connector SHALL independently verify the owner proof. The gateway SHALL report the applied revision only after backend commit.

#### Scenario: The selected mailbox has been replaced

- **WHEN** a caller supplies an expected binding that no longer matches the selected channel
- **THEN** the gateway reports a binding conflict before forwarding a policy update
- **AND THEN** the backend verifies the exact binding independently before changing policy

#### Scenario: A caller has mailbox access without administration

- **WHEN** a caller with ordinary mailbox access tries to apply mail policy
- **THEN** the gateway refuses to relay the update
- **AND THEN** the caller retains their existing permissions for ordinary mailbox operations

#### Scenario: A gateway administrator submits a request without mailbox-owner proof

- **WHEN** an enrolled administrator or an anonymous caller with open-roster administration tries to apply new rules without valid proof from the mailbox owner
- **THEN** the backend's rules and revision remain unchanged
- **AND THEN** gateway administration, including open-roster authority, supplies no backend policy authority

#### Scenario: The selected backend cannot apply the request

- **WHEN** a submitted update has a stale expected revision, or the binding lacks a qualified backend policy interface
- **THEN** the gateway reports a conflict or unsupported operation as applicable
- **AND THEN** it performs no local filtering fallback

#### Scenario: The mailbox owner changes a sender rule

- **WHEN** the backend commits an owner-authorized update that adds or removes a sender from the blocklist
- **THEN** the new revision governs placement of later deliveries
- **AND THEN** previously delivered messages keep their existing placement

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

List SHALL return triage metadata without marking read. Peek SHALL return selected content without changing read state. Read SHALL return content and mark read. Mark SHALL support recipient-local read/answered state. Where the selected binding permits gateway placement changes, move SHALL update supported boxes and archive SHALL close inbox work through the selected backend. On a protected binding, ordinary gateway move, archive, and placement-changing mark operations SHALL fail explicitly. The gateway SHALL retain binding-scoped reading, sending, replying, and read or answered state changes.

All lifecycle requests SHALL identify their expected binding ID, obtained from status or current round context, and use runtime-owned authority and scoped references. A replaced binding SHALL fail explicitly even for send/post requests without a message reference. Unsupported operations, absent bindings, and backend failures SHALL be explicit. Callers SHALL NOT need filesystem indexes, mailbox scripts, or provider-native objects. The gateway SHALL authorize each mailbox operation against the selected target and binding. Operator-origin post and mailbox binding controls SHALL each require their corresponding permission. The ordinary Inbox view SHALL come from the backend without gateway filtering or placement overrides.

#### Scenario: Peek does not mutate read state through the gateway
- **WHEN** a caller peeks through the selected channel using a matching scoped reference
- **THEN** it receives that message's content without changing recipient read state

#### Scenario: Read mutates read state through the gateway
- **WHEN** a caller reads through the selected channel using a matching scoped reference
- **THEN** it receives that message's content and read state becomes true for that mailbox owner

#### Scenario: Archive shortcut remains available
- **WHEN** a caller archives selected references through their matching channel and the binding permits ordinary gateway archive
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

#### Scenario: Ordinary mailbox calls cannot change placement on a protected binding

- **WHEN** a caller requests move, archive, or an archive-equivalent mark via ordinary lifecycle routes on a protected binding
- **THEN** the operation fails explicitly and the backend leaves placement unchanged
- **AND THEN** the caller can still use authorized read, send, reply, and non-placement mark operations

#### Scenario: A mailbox listing uses the backend's Inbox view

- **WHEN** the selected backend files new blocked mail directly in Archive
- **THEN** the ordinary listing reports only the backend's Inbox view
- **AND THEN** an ordinary Inbox read of that mail fails, including when the caller supplies a cached or guessed reference

#### Scenario: An authorized mailbox owner files processed mail

- **WHEN** a mailbox owner independently authorizes filing of processed Inbox mail on a protected binding
- **THEN** the backend can apply the filing through its owner-authorized interface
- **AND THEN** the agent's ordinary gateway permissions stay the same

### Requirement: Gateway reply marks the parent message answered
When a channel-selected gateway reply succeeds, the adapter SHALL mark the parent message `answered=true` and `read=true` for the owning mailbox. Reply SHALL preserve originating channel and binding scope and SHALL NOT archive the parent message.

#### Scenario: Gateway reply acknowledges without closing the mail
- **WHEN** a caller replies through the matching channel and binding
- **THEN** the parent becomes read and answered for that owner
- **AND THEN** it remains open inbox work until the backend archives it or applies another placement change

### Requirement: Gateway notifier records structured per-poll decision auditing for later review

When gateway-owned notifier behavior is enabled, the gateway SHALL record one structured notifier-decision audit record for each enabled poll cycle in a queryable SQLite audit table under the gateway state root.

#### Scenario: Acceptance criteria

- **GIVEN** an enabled notifier poll cycle
- **THEN** its audit record identifies poll time, owner, channel, and binding
- **AND THEN** it reports the mode-eligible Inbox count and set identity or equivalent summary, admission state, active execution, queue depth, outcome, and enqueue identifiers or skip detail when applicable
- **AND THEN** detailed history remains available independently of the compact `GET /v1/mail-notifier/{channel}` snapshot and the rate-limited human log

#### Scenario: Busy poll records an explicit skip decision

- **WHEN** a notifier poll cycle finds eligible Inbox work while gateway admission is closed, active execution is running, or queue depth is non-zero
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record identifies the decision as a busy or ineligible skip and includes the eligibility inputs that caused the skip

#### Scenario: Enqueue poll records the created reminder request

- **WHEN** a notifier poll cycle finds eligible Inbox work and the gateway enqueues an internal reminder prompt
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record includes the reminder decision outcome and the created internal request identifier

#### Scenario: Durable audit history remains the detailed inspection surface

- **WHEN** an operator or demo helper needs the latest detailed notifier decision data
- **THEN** it can inspect the durable SQLite notifier audit history under the gateway root
- **AND THEN** the compact notifier status contract remains available separately

### Requirement: Queued Work Requests Recheck Ready Handoff

The gateway SHALL retain a work request's caller, target, and operation authority through queue admission and native handoff. The gateway SHALL recheck current authority and a qualified native readiness boundary before delivering the attributed request. The queue SHALL expose the existing typed acceptance, failure, and uncertainty evidence for these requests.

#### Scenario: Bob is busy before queued work reaches handoff
- **WHEN** the gateway accepts a work request and Bob's native work prevents ready-only delivery
- **THEN** the existing queue and recovery rules govern when the request becomes eligible
- **AND THEN** queue acceptance is reported separately from delivery

#### Scenario: The caller loses request authority while queued
- **WHEN** an admitted work request reaches dispatch after its grant, open epoch, or bound target generation ceased to be current
- **THEN** the gateway settles the work request before native effects with a typed refusal
- **AND THEN** the refusal retains the original attribution and request identity

#### Scenario: A queued request loses default authority
- **WHEN** a request admitted under Bob's default reaches dispatch after Bob changes the default setting or disables default fallback for the verified caller
- **THEN** the gateway settles the request with a typed refusal before native delivery

#### Scenario: An anonymous request stays anonymous at handoff
- **WHEN** an unsigned work request is pending under Bob's requester default and Bob disables default fallback for Alice's verified identity before handoff
- **THEN** the anonymous admission remains eligible while the default and other prerequisites remain current

### Requirement: Gateway Administration Sets the Default Permission Group

`PUT /v1/admin/default-permission-group` SHALL accept schema version `1` and a supported built-in `default_permission_group`. The gateway SHALL require `admin.default-group.set` on `policy`, recheck authority at commit, and update the target's retained policy. It SHALL return the committed group and setting revision. Operation-specific proof and roster rules SHALL apply independently.

#### Scenario: An administrator sets Bob's default to operator
- **WHEN** a caller authorized as `agent-admin` sets `default_permission_group` to `agent-operator` on Bob's gateway
- **THEN** the gateway stores the selected group in Bob's policy
- **AND THEN** later eligible callers use the selected group subject to the exact operation's prerequisites

#### Scenario: A caller uses the admin default to change it
- **WHEN** Bob has a keyed roster and has selected `agent-admin` as the default group
- **THEN** an otherwise unassigned caller, including an unsigned caller, can set the default under effective admin authority when transport prerequisites hold

#### Scenario: A requester attempts to change the default
- **WHEN** a caller with only `agent-requester` asks to change `default_permission_group`
- **THEN** the gateway refuses the admin-exclusive effect before committing a policy change

#### Scenario: An administrator supplies a group outside the built-in catalog
- **WHEN** an authorized administrator supplies a retired, unknown, or owner-defined group as the default
- **THEN** the gateway rejects the value before committing a policy change

## REMOVED Requirements

### Requirement: Gateway notifier wake-up semantics are unread-set based rather than per-message based

**Reason**: The eligible set applies the selected notification mode to the backend's Inbox view.

**Migration**: Use Gateway Notifier Aggregates the Current Eligible Inbox Set for reminder aggregation and periodic repeat behavior.

### Requirement: Typed Work Requests Enter as Attributed Content

**Reason**: Status-only access now combines an exact grant with disabled fallback.

**Migration**: Use verified principal fallback and preserve independent anonymous admission.
