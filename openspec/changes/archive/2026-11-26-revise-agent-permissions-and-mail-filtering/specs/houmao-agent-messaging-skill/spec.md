# Agent Messaging Skill Delta

## ADDED Requirements

### Requirement: Messaging Selects a Route by Intent and Reports the Selected Outcome
The packaged `houmao-agent-messaging` skill SHALL tell the agent to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target or messaging intent that is not explicit in current or recent conversation context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL select commands by communication intent:

- use `houmao-mgr agents single ... request` to ask a peer to perform work as an attributed request
- use scoped `houmao-mgr agents single|self ... prompt` for an explicitly intended synchronous conversational turn through verified native execution authority
- use scoped `houmao-mgr agents single|self ... interrupt` for the transport-neutral interrupt path with its applicable authority
- use the supported managed-agent gateway request route or gateway `/v1/requests` with the applicable admission lane for explicitly requested durable queue behavior
- use scoped `gateway prompt|interrupt` or the applicable signed direct gateway route for explicit gateway controls
- use scoped `gateway send-keys` for authorized exact raw control input
- use scoped `mail resolve-live` when the task needs mailbox discovery, current mailbox capability, or the exact live `gateway.base_url` before mailbox handoff
- use scoped `state` when the next action needs current runtime posture and `gateway status` when it needs verified gateway status

For outbound agent mail, `commands/mail.md` SHALL use a known or resolved recipient address for the explicit channel and act through the sending agent's verified mailbox binding. It SHALL report the selected transport's outcome with recipient mail rules, placement, notification, and processing left unspecified.

The skill SHALL prefer `houmao-mgr agents ...` and managed-agent `/houmao/agents/*` routes over direct gateway listener URLs when those higher-level surfaces already satisfy the current task.

#### Scenario: Ordinary conversation uses the default prompt path
- **WHEN** an authorized execution owner requests a direct conversational turn with a managed agent and wants to wait for its outcome
- **THEN** the skill directs the caller to use the scoped `houmao-mgr agents single ... prompt` or verified self equivalent
- **AND THEN** it preserves the synchronous execution path

#### Scenario: Raw terminal shaping uses send-keys instead of prompt submission
- **WHEN** the user requests slash-command menus, arrow navigation, `Escape`, or partial typing in a live TUI session
- **THEN** the skill directs an authorized caller to scoped `gateway send-keys`
- **AND THEN** it identifies this as raw terminal shaping with its own authority

#### Scenario: Queued control uses the gateway request surface
- **WHEN** the user explicitly wants a durable gateway queue for a direct prompt or interrupt
- **THEN** the skill uses the authorized request queue route and selects the typed effect for the intended operation
- **AND THEN** it preserves the queue receipt and distinguishes immediate `gateway prompt` admission from durable queue admission

#### Scenario: Mailbox work uses discovery before handoff
- **WHEN** the user asks for mailbox-related work against a managed agent
- **THEN** the skill directs the agent to use scoped `mail resolve-live` or the equivalent managed-agent discovery route first when current mailbox posture or `gateway.base_url` is needed
- **AND THEN** it hands ordinary mailbox operations off to the applicable mailbox skill after discovery

#### Scenario: Missing target requires a user question
- **WHEN** the selected messaging action still lacks a required target after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing selector before proceeding
- **AND THEN** it does not guess the target managed agent

#### Scenario: Recipient contact is enough for ordinary mail

- **WHEN** a managed agent needs to send ordinary mail to a named peer
- **THEN** the skill uses the peer's known address or the peer's `mail resolve-live` result for the requested channel
- **AND THEN** the skill sends through `agents self mail send` using the sender's verified binding without preflighting the recipient gateway's roles
- **AND THEN** it describes online confirmation as provider-confirmed submission and offline confirmation as transport-confirmed deposit
- **AND THEN** it reports transport confirmation without inferring the backend's placement, agent notification, or processing

#### Scenario: The Mail Transport Refuses Submission or Deposit

- **WHEN** verified Alice submits ordinary mail to Bob and the selected transport refuses submission or deposit
- **THEN** the skill reports that transport's refusal and keeps Alice as the sender
- **AND THEN** it performs no retry through a different recipient channel or Bob's delegated mailbox sender identity

#### Scenario: Bob's Backend Applies His Mailbox Policy

- **WHEN** Bob asks how his mailbox policy affects an ordinary incoming message
- **THEN** the skill explains that his mailbox backend checks sender metadata at delivery and files matching new messages directly into Archive outside ordinary Inbox work and reminders
- **AND THEN** it explains that rule changes leave existing Inbox mail in place and that unblocking leaves archived mail in Archive
- **AND THEN** it preserves the same sender-facing acceptance receipt whether the backend files the message in Inbox or Archive and treats sender metadata separately from verified gateway identity

#### Scenario: Gateway is detached for a normal prompt

- **WHEN** a direct conversational turn is explicitly requested and the target has no live gateway
- **THEN** the skill uses the scoped managed-agent prompt command through the recorded owner route if authorized and available
- **AND THEN** it reports unavailability when no authorized owner route can admit the prompt

### Requirement: Messaging Guidance Distinguishes Typed Requests From Direct Control

The skill's `commands/request.md` SHALL use the typed work-request command through a verified gateway or qualified direct passive path. It SHALL select the path and proof before submission and explain eligibility for default admission. Direct prompts, native slash commands, and interruption SHALL require explicit intent and applicable authority. Observation, raw keys, and admission overrides SHALL retain separate effects.

#### Scenario: Alice Requests That Bob Review a Patch

- **WHEN** Alice has `builtin:agent-requester` or a higher cumulative peer role on Bob and wants to ask Bob to review a patch
- **THEN** the skill routes the work through `agents single --agent-id <bob-id> request --text <text>` with the stable peer signer
- **AND THEN** it reports the available request admission or handoff evidence and relies on separately authorized surfaces for any later output

#### Scenario: New Alice Contacts Bob Through the Default Group

- **WHEN** Alice has no explicit `builtin:` group assignment on Bob, qualifies for fallback, and needs to submit a work request
- **THEN** the skill selects the verified target and uses the typed request command without requiring enrollment on Bob
- **AND THEN** it uses independently verified identity when available on the selected path, or uses explicit `--unsigned` when the caller has selected anonymous submission and the operation permits it
- **AND THEN** it reports unsupported proof or verification refusal as applicable and preserves the selected caller attribution
- **AND THEN** it reports the target's admission outcome and preserves the distinction between verified and anonymous attribution

#### Scenario: Bob Refuses a Signed Work Request from Status-Only Alice

- **WHEN** Alice has Bob's exact status grant and default fallback is disabled for her verified identity
- **THEN** the skill reports Bob's refusal of an ungranted work request
- **AND THEN** it preserves the signed refusal even if the configured default would authorize a separate unsigned request

#### Scenario: Alice Intentionally Submits an Unsigned Work Request

- **WHEN** Alice explicitly chooses unsigned submission before contacting Bob and Bob's current default permits the typed request
- **THEN** `commands/request.md` uses `--unsigned` and reports anonymous attribution
- **AND THEN** it explains that Bob's verified per-principal fallback restriction applies to requests carrying Alice's proof

#### Scenario: Alice Submits a Slash Command as Request Content

- **WHEN** a work request contains the text `/compact`
- **THEN** the skill explains that Bob receives attributed request content
- **AND THEN** it reserves native slash invocation for the explicitly authorized direct lane

#### Scenario: Alice Has Direct Turn Control

- **WHEN** Alice intends to send text verbatim, invoke a supported slash command, or interrupt Bob's current turn
- **THEN** the skill uses the corresponding supported direct operation under the same selected target and applicable caller proof
- **AND THEN** it identifies `builtin:agent-operator` or separate direct grants as the applicable authority
- **AND THEN** raw keys and session, model, or admission overrides retain their own authorization

#### Scenario: Alice Maintains Bob's Common Plugins

- **WHEN** Alice has `builtin:agent-maintainer` on Bob and asks Bob to act on a plugin change
- **THEN** the skill routes communication through the attributed work-request command
- **AND THEN** it hands qualified skill and MCP editing and publication to the file-edit workflow
- **AND THEN** the common-plugin role alone does not authorize a direct prompt, slash command, or interruption

#### Scenario: The Work Request Cannot Be Admitted

- **WHEN** Alice's selected request path is unavailable or denies her work request
- **THEN** the skill preserves the requested operation and reports the reason
- **AND THEN** it performs no direct prompt, raw-key, unsigned, mail, or other-path retry

#### Scenario: Carol Sends Wrapped Work to Bob Through the Passive Server

- **WHEN** Bob's gateway is detached and Carol chooses a qualified direct passive work-request path
- **THEN** the routine uses the typed request command and reports the admission or handoff evidence from the passive server
- **AND THEN** the routine preserves the distinction among accepted work, confirmed handoff, and eventual task completion

#### Scenario: Carol Contacts Bob While His Gateway Is Detached

- **WHEN** Carol wants to ask detached Bob to review a patch and chooses mail for the handoff
- **THEN** the routine uses Carol's own sender binding and Bob's verified mailbox address
- **AND THEN** it reports the mail transport's outcome without contacting Bob's gateway to check recipient permissions
- **AND THEN** it explains that Bob's backend applies its configured placement policy while his gateway is detached

## REMOVED Requirements

### Requirement: `houmao-agent-messaging` chooses the communication path that matches caller intent

**Reason**: Ordinary mail uses transport delivery and placement under the recipient backend's rules.

**Migration**: Teach sender binding and explicit channel selection, transport receipts, and backend-owned placement.

### Requirement: Messaging Guidance Separates Work Requests and Direct Control

**Reason**: The revised policy checks explicit grants and fallback for a verified status-only caller.

**Migration**: Teach the typed request and direct control paths and preserve proof and attribution through refusal.
