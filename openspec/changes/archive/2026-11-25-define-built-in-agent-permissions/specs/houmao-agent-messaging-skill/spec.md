# Spec Delta

## ADDED Requirements

### Requirement: Messaging Guidance Separates Work Requests and Direct Control

The skill SHALL use the typed work-request command through a verified gateway or qualified direct passive path. It SHALL select the path and proof before submission and explain default admission without enrollment. Direct prompts, native slash commands, and interruption SHALL require explicit intent and applicable authority. Observation, raw keys, and admission overrides SHALL retain separate effects.

#### Scenario: Alice Requests That Bob Review a Patch

- **WHEN** Alice has `builtin:agent-requester` or a higher cumulative peer role on Bob and wants to ask Bob to review a patch
- **THEN** the skill routes the work through `agents single --agent-id <bob-id> request --text <text>` with the stable peer signer
- **AND THEN** it reports the available request admission or handoff evidence and relies on separately authorized surfaces for any later output

#### Scenario: New Alice Contacts Bob Through the Default Group

- **WHEN** Alice has no explicit `builtin:` group assignment on Bob and needs to submit a work request
- **THEN** the skill selects the verified target and uses the typed request command without requiring enrollment on Bob
- **AND THEN** it uses verified identity when selected and supported, or selects unsigned input before submission where the operation permits it
- **AND THEN** it reports the target's admission outcome and preserves the distinction between verified and anonymous attribution

#### Scenario: Bob Recognizes an Explicit Observer Assignment

- **WHEN** Alice's verified identity has Bob's explicit `builtin:agent-observer` assignment
- **THEN** the skill treats that assignment as the applicable group for her identity and reports Bob's refusal of an ungranted work request
- **AND THEN** it does not switch from rejected signed input to the unsigned lane, even if the default would authorize that lane

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
- **AND THEN** it reports the mail transport's outcome under Bob's retained recipient policy

## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-messaging` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-messaging` as a parent-scoped child of `houmao-shared-routines`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That skill SHALL instruct agents to communicate with already-existing Houmao-managed agents through these scoped manager and HTTP surfaces:

- `agents single ... state` or verified `agents self state`
- `agents single ... request` for attributed work requests
- scoped `gateway status`, `mail resolve-live`, `prompt`, and `interrupt`
- scoped `gateway prompt|interrupt|send-keys`
- scoped `gateway tui state|history|note-prompt`
- managed-agent HTTP routes under `/houmao/agents/*`

The child `SKILL-MAIN.md` SHALL route to one local action-specific document for `discover`, `request`, `prompt`, `interrupt`, `gateway-queue`, `send-keys`, `mail`, or `reset-context`. The catalog and skill SHALL expose `mail` as the canonical handoff command and `mail-handoff` as its alias.

That packaged skill SHALL remain the canonical Houmao-owned skill for communication with already-running managed agents whether the caller is another managed agent or an external operator.

That packaged skill SHALL delegate the following operations to their owning routines:

- managed-agent launch, join, stop, relaunch, and cleanup
- project specialist and project agent authoring and lifecycle commands
- ordinary mailbox status, reads, writes, and archive
- filesystem or Stalwart mailbox transport internals
- gateway attach and detach

#### Scenario: Installed skill points the agent at supported communication surfaces
- **WHEN** an agent opens the installed `houmao-agent-messaging` skill through its parent
- **THEN** the skill directs the agent to supported work-request, direct prompt, interrupt, gateway, mailbox-discovery, and managed-agent HTTP surfaces

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** `SKILL-MAIN.md` directs the agent to the local document for the requested action
- **AND THEN** `mail` and `mail-handoff` select the same mailbox handoff document

#### Scenario: Installed skill keeps lifecycle and mailbox-operation internals out of scope
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** it delegates managed-agent lifecycle, ordinary mailbox work, and mailbox transport internals

### Requirement: `houmao-agent-messaging` chooses the communication path that matches caller intent
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

For outbound agent mail, the skill SHALL use a known or resolved recipient address for the explicit channel and act through the sending agent's verified mailbox binding. It SHALL account for the recipient's retained delivery policy, including the default for unassigned senders, even while the recipient has no active runtime or gateway.

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
- **AND THEN** the skill sends through `agents self mail send` using the sender's verified binding and reports the recipient transport's admission or refusal
- **AND THEN** the recipient can apply its default without enrolling the sender, independently of live state or gateway status

#### Scenario: Bob Refuses Mail From an Observer

- **WHEN** verified Alice holds only `builtin:agent-observer` on keyed Bob and the recipient transport denies her mail
- **THEN** the skill reports Bob's recipient-policy refusal and keeps Alice as the sender
- **AND THEN** it performs no retry through a different recipient channel or Bob's delegated mailbox sender identity

#### Scenario: Gateway is detached for a normal prompt

- **WHEN** a direct conversational turn is explicitly requested and the target has no live gateway
- **THEN** the skill uses the scoped managed-agent prompt command through the recorded owner route if authorized and available
- **AND THEN** the skill reports unavailability when no authorized owner route can admit the prompt
