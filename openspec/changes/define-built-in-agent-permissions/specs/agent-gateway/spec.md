# Spec Delta

## ADDED Requirements

### Requirement: Typed Work Requests Enter as Attributed Content

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

#### Scenario: Assigned observer submits an identified work request
- **WHEN** Alice proves an identity assigned only `agent-observer` and submits a work request to Bob with an `agent-requester` default
- **THEN** the gateway refuses the work-request effect under Alice's explicit role

#### Scenario: Assigned observer submits a separate unsigned work request
- **WHEN** Alice holds only `agent-observer` and separately submits a valid work request without proof to keyed Bob with the `agent-requester` default
- **THEN** the gateway admits the request under the default and attributes it to an anonymous caller
- **AND THEN** normal request validation and readiness checks still apply

#### Scenario: A request carries invalid proof
- **WHEN** a caller submits invalid proof alongside a work request that would be allowed without proof
- **THEN** the gateway refuses the request at proof validation

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
- **WHEN** a request admitted under Bob's default reaches dispatch after Bob changes the default to `agent-observer` or assigns that observer role to the verified caller
- **THEN** the gateway settles the request with a typed refusal before native delivery

#### Scenario: An anonymous request stays anonymous at handoff
- **WHEN** an unsigned work request is pending under Bob's requester default and Bob assigns Alice an observer role before handoff
- **THEN** the assignment leaves the anonymous admission eligible while the default and other prerequisites remain current

### Requirement: Gateway Administration Sets the Default Permission Group

`PUT /v1/admin/default-permission-group` SHALL accept schema version `1` and one built-in `default_permission_group`. The gateway SHALL require `admin.default-group.set` on `policy`, recheck authority at commit, and update the target's retained policy. It SHALL return the committed group and setting revision. Operation-specific proof and roster rules SHALL apply independently.

#### Scenario: An administrator sets Bob's default to operator
- **WHEN** a caller authorized as `agent-admin` sets `default_permission_group` to `agent-operator` on Bob's gateway
- **THEN** the gateway stores the selected group in Bob's policy
- **AND THEN** later unassigned callers use the selected group subject to the exact operation's prerequisites

#### Scenario: A caller uses the admin default to change it
- **WHEN** Bob has a keyed roster and has selected `agent-admin` as the default group
- **THEN** an otherwise unassigned caller, including an unsigned caller, can set the default under effective admin authority when transport prerequisites hold

#### Scenario: A requester attempts to change the default
- **WHEN** a caller with only `agent-requester` asks to change `default_permission_group`
- **THEN** the gateway refuses the admin-exclusive effect before committing a policy change

#### Scenario: An administrator supplies a group outside the built-in catalog
- **WHEN** an authorized administrator supplies an unknown or owner-defined group as the default
- **THEN** the gateway rejects the value before committing a policy change

### Requirement: Native Control Requires Its Exact Effect

Queued `submit_prompt` and immediate prompt control SHALL require `agent.prompt.direct` on `agent`. Before dispatch, the gateway SHALL classify any text the qualified target can interpret as a native slash command and also require `agent.command.invoke`. Native session selection, model override, non-ready prompt admission, interruption, and raw terminal input SHALL each retain their independently checked effects.

#### Scenario: Direct text is delivered unchanged
- **WHEN** an authorized caller submits an ordinary direct prompt through a compatible native surface
- **THEN** the gateway gives the native surface the submitted text verbatim
- **AND THEN** existing queue or immediate admission behavior applies to the selected route

#### Scenario: Slash command arrives through a direct text route
- **WHEN** a caller submits a native-interpretable `/compact` through the durable queue or immediate direct prompt route
- **THEN** the gateway requires both direct prompt and command invocation authority before native delivery
- **AND THEN** the operation must use a qualified native control path

#### Scenario: Slash control changes the native session
- **WHEN** a supported slash command selects or resets the native conversation
- **THEN** the command also requires the applicable native session-selection permission

#### Scenario: Target cannot qualify the command path
- **WHEN** a command can be interpreted by the target and the gateway cannot qualify its control dispatch
- **THEN** the gateway refuses the command with an explicit capability or validation result before native delivery

#### Scenario: Request-only caller selects another control path
- **WHEN** a caller with only `agent.request.submit` selects direct prompt or an available slash, interrupt, or raw terminal control
- **THEN** gateway admission refuses the missing control permission before the native effect

#### Scenario: Legacy broad grant no longer authorizes input
- **WHEN** a keyed nonadministrator has a retained `agent.prompt` grant and their current role supplies neither work-request nor direct-control permission
- **THEN** the gateway requires a current grant for the chosen effect before accepting the input

### Requirement: Reminder Input Uses Current Control Permissions

A caller who creates or updates a reminder that submits verbatim native text SHALL have its direct prompt and any applicable command permissions. A raw-input reminder SHALL require raw terminal input permission. The gateway SHALL check the originating caller's current authority for the exact delivery effect at handoff.

#### Scenario: A requester schedules direct input
- **WHEN** a verified caller has work-request and reminder creation permissions and submits a verbatim prompt reminder
- **THEN** the gateway rejects the missing direct prompt effect before storing the reminder

#### Scenario: A reminder's command authority expires
- **WHEN** an existing slash-command reminder becomes due after its admitted caller loses command authority
- **THEN** the gateway refuses native delivery even if the caller retains its reminder-management permission

## MODIFIED Requirements

### Requirement: The gateway serializes terminal-mutating work and applies admission policy
The gateway SHALL accept structured local requests for gateway-managed work and SHALL apply gateway-owned admission policy before execution.

The public terminal-mutating request kinds SHALL be exactly `submit_work_request`, `submit_prompt`, and `interrupt`.

Mailbox transport operations SHALL use the dedicated `/v1/mail/*` routes rather than introducing new public terminal-mutating request kinds.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The HTTP submission contract SHALL expose typed per-kind payloads. Any persisted `payload_json` field remains an internal storage detail rather than part of the public protocol contract.

For accepted terminal-mutating requests, the gateway SHALL persist them durably, SHALL serialize execution through a single active terminal-mutation slot per managed agent, and SHALL order eligible work according to gateway policy such as priority, timing constraints, or coalescing rules.

The gateway SHALL be able to reject requests explicitly when permissions or local policy do not allow them.

The gateway SHALL determine terminal-mutating request admission using the published request-admission state rather than only gateway-process liveness.

Already accepted but not-yet-started terminal-mutating work SHALL remain durable while bounded managed-agent recovery is in progress.

If the managed agent fails while a terminal-mutating request is active, the gateway SHALL record an explicit failed or outcome-unknown result for that request and SHALL NOT silently replay it against a replacement managed-agent instance unless the backend adapter has positively established safe continuity.

When managed-agent recovery or reconciliation state makes safe execution impossible, the gateway SHALL reject new terminal-mutating admission explicitly rather than accepting work that it cannot safely apply.

#### Scenario: Prompt submission is accepted as a typed request
- **WHEN** a caller submits a `submit_prompt` request with a prompt-string payload
- **THEN** the gateway validates and durably enqueues that request
- **AND THEN** the accepted response includes a durable request identifier

#### Scenario: Interrupt submission is accepted as a typed request
- **WHEN** a caller submits an `interrupt` request for a gateway-managed session
- **THEN** the gateway records it as a gateway-managed control action
- **AND THEN** the caller does not need to bypass the gateway with direct concurrent terminal mutation

#### Scenario: Mailbox send does not create a new public terminal-mutating request kind
- **WHEN** a caller uses the gateway to perform mailbox `send`
- **THEN** that operation uses the dedicated gateway mailbox surface rather than `POST /v1/requests`
- **AND THEN** mailbox delivery leaves the public request-kind set unchanged

#### Scenario: Concurrent terminal-mutating requests are serialized
- **WHEN** multiple accepted terminal-mutating requests target the same managed agent concurrently
- **THEN** the gateway allows at most one of those requests to hold the active execution slot at a time
- **AND THEN** later eligible requests remain queued until the active terminal-mutation slot is released

#### Scenario: Disallowed request is rejected before execution
- **WHEN** a submitted gateway request violates configured permission or policy rules
- **THEN** the gateway rejects that request explicitly
- **AND THEN** the rejected request is not executed against the managed terminal surface

#### Scenario: Accepted queued work survives transient upstream outage
- **WHEN** terminal-mutating work has already been accepted durably and the managed agent becomes unavailable before that work begins
- **THEN** the gateway preserves that queued work durably
- **AND THEN** execution remains paused until recovery or reconciliation reopens safe admission

#### Scenario: Active prompt is not replayed blindly after upstream replacement
- **WHEN** a `submit_prompt` request is active and the managed agent fails unexpectedly before the gateway can confirm a terminal outcome
- **AND WHEN** bounded recovery later rebinds the logical session to a replacement managed-agent instance
- **THEN** the gateway records the interrupted request as failed or outcome-unknown
- **AND THEN** the gateway does not silently replay that same prompt against the replacement upstream instance

#### Scenario: New prompt admission is rejected while recovery blocks safe execution
- **WHEN** a caller submits a new `submit_prompt` request while the gateway's request-admission state is paused or closed because the managed agent is unavailable, recovering, or awaiting reconciliation
- **THEN** the gateway rejects that request with explicit unavailable or conflict semantics
- **AND THEN** the gateway does not pretend that queued execution can proceed safely

### Requirement: Gateway coalesces adjacent queued control intents
The gateway SHALL coalesce adjacent accepted queued control-intent records before those records execute against the managed agent.

Control-intent records SHALL be limited to queued `interrupt` requests and queued `submit_prompt` requests whose entire trimmed prompt exactly matches a recognized context-control command. The initial recognized context-control commands SHALL include `/compact`, `/clear`, and `/new`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The gateway SHALL treat ordinary prompts, `submit_work_request` records, internal `mail_notifier_prompt` records, unsupported stored request kinds, and different managed-agent instance epochs as coalescing boundaries. The gateway SHALL NOT coalesce `running`, `completed`, `failed`, or already `coalesced` records.

The gateway SHALL preserve ordinary prompt order and content exactly.

#### Scenario: Duplicate interrupts collapse to one interrupt
- **WHEN** the accepted queue contains an adjacent run of multiple `interrupt` requests for the same managed-agent instance epoch
- **THEN** the gateway executes at most one interrupt for that run
- **AND THEN** the redundant interrupt records are marked as coalesced instead of running independently

#### Scenario: Duplicate context command prompts collapse to one prompt
- **WHEN** the accepted queue contains adjacent `submit_prompt` records whose trimmed prompts are all `/compact`
- **THEN** the gateway executes at most one `/compact` prompt for that run
- **AND THEN** the redundant `/compact` records are marked as coalesced instead of running independently

#### Scenario: Later context commands supersede earlier pending context commands
- **WHEN** the accepted queue contains an adjacent run of context-control prompts `/compact`, `/clear`, and `/new` for the same managed-agent instance epoch
- **THEN** the gateway executes only the strongest final effective context action for that run
- **AND THEN** `/new` supersedes pending `/clear` and `/compact`, and `/clear` supersedes pending `/compact`

#### Scenario: Mixed interrupt and context commands preserve one interrupt intent
- **WHEN** the accepted queue contains an adjacent run with one or more `interrupt` records and one or more recognized context-control prompt records for the same managed-agent instance epoch
- **THEN** the gateway preserves one effective interrupt intent and one final effective context-control prompt
- **AND THEN** the effective interrupt executes before the effective context-control prompt

#### Scenario: Ordinary prompts break coalescing runs
- **WHEN** an ordinary `submit_prompt` record appears between two control-intent records in the accepted queue
- **THEN** the gateway treats the ordinary prompt as a hard coalescing boundary
- **AND THEN** the gateway preserves the ordinary prompt order and does not merge control intents across it

#### Scenario: Internal notifier prompts are not coalesced
- **WHEN** an accepted internal `mail_notifier_prompt` record appears in the queue
- **THEN** the gateway does not classify that record as a coalescible control intent
- **AND THEN** the gateway does not merge ordinary or control work across that notifier record

#### Scenario: Epoch boundaries prevent coalescing
- **WHEN** adjacent accepted control-intent records have different `managed_agent_instance_epoch` values
- **THEN** the gateway does not coalesce those records together
- **AND THEN** existing replay and reconciliation safeguards remain authoritative for old-epoch work

#### Scenario: Coalescing leaves durable audit evidence
- **WHEN** the gateway removes an accepted request from execution by coalescing it into effective control work
- **THEN** the gateway marks that request with terminal state `coalesced`
- **AND THEN** the gateway records enough result metadata and gateway event data to identify the effective request or action that superseded it

#### Scenario: Coalesced records do not count as active queue depth
- **WHEN** a request has terminal state `coalesced`
- **THEN** gateway queue-depth reporting excludes that request
- **AND THEN** only accepted and running work contributes to active queue depth

#### Scenario: Work request content cannot join a control run
- **WHEN** a queued work request containing `/compact` appears between accepted control intents
- **THEN** the gateway treats the work request as a coalescing boundary
- **AND THEN** the original work request remains eligible for attributed delivery as request content

### Requirement: Due effective reminders remain gateway-owned low-priority internal prompt delivery
When the effective reminder becomes due, the gateway SHALL treat delivery of that reminder as gateway-owned internal execution behavior rather than as a new externally visible public request kind.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Before a due effective reminder starts execution, the gateway SHALL require:

- request admission to be open
- no active terminal-mutating execution
- zero durable public queue depth
- the effective reminder not to be paused

If those conditions are not satisfied when the effective reminder becomes due, the gateway SHALL keep that reminder pending in memory and SHALL retry later instead of dropping the reminder or converting it into durable queued work.

A paused effective reminder SHALL keep its ranking position and SHALL continue blocking lower-ranked reminders until it is resumed, reranked, or removed.

Repeating reminders SHALL maintain at most one pending due occurrence per reminder. Missed intervals during a busy or paused period SHALL NOT produce a catch-up burst of multiple immediate deliveries once the reminder becomes eligible again.

When a due effective reminder uses semantic `prompt` delivery, the gateway SHALL submit exactly that reminder prompt through the existing internal prompt-delivery path.

When a due effective reminder uses `send_keys` delivery, the gateway SHALL submit raw control input through the same exact control-input lane used by gateway send-keys behavior.

For send-keys reminders:

- the gateway SHALL interpret `<[key-name]>` tokens using the same raw control-input grammar used by the gateway send-keys path,
- the reminder SHALL NOT expose a reminder-specific `escape_special_keys` override,
- the gateway SHALL NOT submit `title` or `prompt` text as terminal input for that reminder,
- `ensure_enter=true` SHALL ensure that the delivered control-input sequence ends with exactly one trailing Enter,
- `ensure_enter=false` SHALL preserve the supplied sequence exactly.

#### Scenario: Busy gateway defers a due effective reminder
- **WHEN** the effective reminder becomes due while request admission is blocked, active execution is running, or durable public queue depth is non-zero
- **THEN** the gateway does not start that reminder immediately
- **AND THEN** the effective reminder remains pending in memory until a later safe execution opportunity

#### Scenario: Paused effective reminder blocks lower-ranked due reminders
- **WHEN** the effective reminder is paused and one or more lower-ranked reminders are already due
- **THEN** the gateway does not submit the paused reminder delivery
- **AND THEN** it also does not submit the lower-ranked reminder deliveries while the paused effective reminder still owns the ranking slot

#### Scenario: Due reminder does not expand the public request-kind set
- **WHEN** an effective reminder is delivered after becoming due
- **THEN** that delivery happens through gateway-owned internal behavior rather than a new public `POST /v1/requests` kind
- **AND THEN** the public request-kind set remains unchanged

#### Scenario: Send-keys reminder delivers raw control input without title or prompt text
- **WHEN** a due effective reminder uses `send_keys`
- **THEN** the gateway submits the reminder's control-input sequence through the raw control-input lane
- **AND THEN** it does not synthesize `title` or semantic `prompt` text into that terminal input

#### Scenario: Send-keys reminder with ensure-enter true ends with one trailing Enter
- **WHEN** a due effective reminder uses `send_keys` with `ensure_enter=true`
- **THEN** the gateway delivers a control-input sequence that ends with one trailing Enter
- **AND THEN** it does not deliver two trailing Enter presses when the caller already supplied `<[Enter]>`

#### Scenario: Send-keys reminder with ensure-enter false preserves exact sequence
- **WHEN** a due effective reminder uses `send_keys` with `ensure_enter=false`
- **THEN** the gateway delivers the supplied control-input sequence exactly
- **AND THEN** it does not append an implicit Enter

### Requirement: Ordinary Plugin Event Refusals Are Immediate

The gateway SHALL attempt plugin-event dispatch only with ready gateway/plugin state, open core admission, idle available body, and applicable readiness, pending-input, and active-hook guards. A failed readiness check SHALL return a retryable error without waiting, caching, queueing, or scheduling the message for later delivery.

#### Scenario: Busy Headless Agent Refuses an Event

- **WHEN** a plugin event arrives while a headless turn is active
- **THEN** the gateway returns HTTP 409 with a retryable readiness error
- **AND THEN** it starts no overlapping turn and stores no pending plugin message

#### Scenario: Ready TUI Still Has Provider Pending Input

- **WHEN** an event targets a TUI whose tracked pending input is `yes` or `unknown`
- **THEN** the gateway returns a retryable readiness error even if the surface otherwise looks ready
- **AND THEN** it does not enqueue the event through the durable request queue

#### Scenario: Active Hook Posture Blocks a Visually Ready TUI

- **WHEN** a TUI surface is stable and ready with no pending input but an active hook channel reports active or blocked work
- **THEN** the event request fails immediately instead of waiting for a different hook posture
- **AND THEN** stale, unavailable, or disabled hook channels add no gates beyond the established TUI-only rules

#### Scenario: Existing Accepted Work Conflicts With Immediate Dispatch

- **WHEN** existing gateway work prevents immediate plugin-event dispatch
- **THEN** the event request returns a retryable conflict and existing work retains its normal scheduling
- **AND THEN** the plugin request does not join that queue or hold the execution lock while waiting

#### Scenario: Readiness Changes Before Dispatch

- **WHEN** initial checks pass but the body becomes inadmissible before dispatch
- **THEN** the original request returns an error and relinquishes its attempt
- **AND THEN** later readiness does not resume that request in the background

#### Scenario: Plugin Dispatch Does Not Add a Queued Request Kind

- **WHEN** a plugin event is dispatched through the immediate semantic path
- **THEN** no queued plugin-event request is created
- **AND THEN** the public request-kind set remains unchanged
