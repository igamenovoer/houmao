## ADDED Requirements

### Requirement: Loop skill defaults cross-agent communication to Houmao mail
The packaged loop skill SHALL state that cross-agent participant communication defaults to Houmao mail unless the intention source explicitly requests a non-mail communication mechanism.

The skill SHALL NOT require the user to decide whether ordinary cross-agent loop handoffs use mail when the intention source does not express a competing mechanism.

#### Scenario: Clarification avoids generic mail transport question
- **WHEN** a user runs `clarify intent` for a loop whose participants need cross-agent handoffs
- **AND WHEN** the intention source does not ask for a non-mail communication mechanism
- **THEN** the skill treats Houmao mail as the default cross-agent communication mechanism
- **AND THEN** the skill does not ask a foundational question about whether participants should communicate by mail

#### Scenario: Explicit non-mail intent remains supported
- **WHEN** the intention source explicitly asks for a non-mail communication mechanism
- **THEN** the skill may clarify how that mechanism should interact with or replace Houmao mail
- **AND THEN** the generated execplan does not force mail-only coordination against the accepted intention

### Requirement: Loop-generated material owns communication semantics
Generated execplans SHALL define loop-specific communication semantics when the loop is mail-driven.

Those semantics SHALL include the applicable participant routes, message families, payload fields or schemas, render templates, reply expectations, and any state or record effects caused by receiving or sending mail.

Generated execplans SHALL place those semantics under generated communication, collaboration, state, skill, agent, or harness surfaces rather than inside maintained Houmao mail-platform skill prose.

#### Scenario: Mail-driven execplan contains communication contracts
- **WHEN** the skill generates an execplan for a mail-driven loop
- **THEN** the execplan defines the loop-specific message families and sender/recipient routes
- **AND THEN** the execplan defines structured payload validation and human-readable render behavior for ordinary generated mail families

#### Scenario: Mail effects are represented as generated loop contracts
- **WHEN** receiving a generated message family changes loop state, creates a record, or requires a reply
- **THEN** the execplan records that effect in generated specs, harness behavior, or role skills
- **AND THEN** the effect is not left only as informal prose in an agent prompt

### Requirement: Houmao platform skills own mail mechanics
The packaged loop skill SHALL route mail transport, mailbox administration, ordinary mail operations, gateway-notified open-mail rounds, managed-agent message routing, and gateway lifecycle work through maintained Houmao skills.

The skill SHALL identify the maintained Houmao skill owners for these mechanics:
- `houmao-mailbox-mgr` for mailbox setup, inspection, repair, cleanup, export, registration, and late mailbox binding;
- `houmao-agent-email-comms` for ordinary mail status, list, read, send, post, reply, mark, move, and archive operations;
- `houmao-process-emails-via-gateway` for notifier-driven open-mail rounds when the current round provides the gateway base URL;
- `houmao-agent-messaging` for managed-agent prompt, interrupt, mailbox handoff, and gateway-backed communication routing;
- `houmao-agent-gateway` for gateway lifecycle and gateway posture.

Generated loop skills SHALL NOT implement custom mailbox storage, custom mailbox state management, or ad hoc gateway discovery when a maintained Houmao skill owns the mechanic.

#### Scenario: Generated agent preparation binds mail support
- **WHEN** a generated execplan requires mail-driven participants
- **THEN** generated agent bindings or preparation guidance include the maintained Houmao mail support skills needed by those participants
- **AND THEN** the generated loop does not duplicate mailbox administration or ordinary mail endpoint contracts as local platform mechanics

#### Scenario: Runtime mail action delegates to platform skill
- **WHEN** an execution subskill or generated role skill needs to send, read, reply to, or archive mail
- **THEN** it routes that action through maintained Houmao mail support
- **AND THEN** it treats the maintained Houmao mail skill behavior as authoritative for transport mechanics

### Requirement: Generated mail families use structured payload validation and Markdown rendering
For ordinary generated mail families, the execplan SHALL use the structured payload, schema validation, Markdown rendering, and Houmao mail send or reply pattern unless the intention source explicitly chooses another representation.

The default structured payload representation SHALL be TOML.

The generated rendered Markdown SHALL be the human-readable mail surface for agents, while the structured payload and schema SHALL remain available for validation, audit, and harness-controlled record application.

Participant-to-participant mail SHALL be templated by default. Operator-origin mail MAY remain freeform and high priority while still being interpreted into generated loop records when the loop needs durable state.

#### Scenario: Generated mail send follows validation and rendering path
- **WHEN** a generated role sends a loop-defined mail family
- **THEN** the role prepares a structured payload for that message family
- **AND THEN** the generated harness or equivalent generated contract validates the payload before rendering
- **AND THEN** the rendered Markdown is sent through maintained Houmao mail support

#### Scenario: Human-readable mail does not replace machine contract
- **WHEN** an agent reads rendered generated mail
- **THEN** the execplan still preserves the corresponding structured schema or payload contract for validation and audit
- **AND THEN** later loop state or record actions can refer to the structured contract rather than relying only on freeform mail text

#### Scenario: Operator-origin mail remains available
- **WHEN** an operator sends a control, override, recovery, stop, resume, or freeform instruction that does not fit a generated participant request/reply template
- **THEN** the loop can accept that operator-origin mail as freeform mailbox text
- **AND THEN** any durable loop effect is represented as an interpreted generated record or event rather than as custom mailbox transport behavior

### Requirement: Mail-driven execplans include a generated communication registry
Mail-driven execplans SHALL include a generated communication registry that maps each generated mail family to its schema and renderer.

The default registry path SHALL be `<loop-dir>/execplan/specs/comms/templates.toml`.

The default generated comms package SHALL include JSON Schema files under `specs/comms/schemas/` and Markdown renderer templates under `specs/comms/renderers/`.

The generated harness or generated docs SHALL make the registry discoverable by short template name and by full schema id when the loop exposes harness email commands.

#### Scenario: Registry connects schema and renderer
- **WHEN** the skill generates a mail-driven execplan
- **THEN** `specs/comms/templates.toml` indexes each ordinary generated mail family
- **AND THEN** every indexed entry identifies a schema id, schema path, and renderer path

#### Scenario: Harness resolves generated template names
- **WHEN** a generated role skill needs to inspect, validate, or render a generated mail payload
- **THEN** the generated harness or generated docs expose the applicable template names
- **AND THEN** a role can resolve the template to the matching schema and renderer without guessing file paths

### Requirement: Templated mail payloads use a common envelope
Generated templated mail payloads SHALL use a common payload envelope unless the intention source explicitly selects another convention.

The default envelope SHALL include:
- `schema_id`;
- `schema_version`;
- `payload_id`;
- `kind`;
- `run_id`;
- `plan_revision`;
- `handoff_id` or another generated exchange id;
- `context`.

When a generated request expects a reply, the request payload SHALL identify the expected reply schema, normally through `requested_reply_schema_id`.

#### Scenario: Generated payload includes common envelope
- **WHEN** a generated role authors a templated participant mail payload
- **THEN** the payload includes the common envelope fields required by the generated schema
- **AND THEN** the payload can be tied back to the run, plan revision, exchange, and reason the mail was sent

#### Scenario: Request identifies expected reply schema
- **WHEN** a generated request message expects a structured reply
- **THEN** the request payload identifies the expected reply schema
- **AND THEN** the receiving role skill can construct the correct reply payload without asking the user which reply family to use

### Requirement: Rendered generated mail includes metadata and context
Generated rendered mail SHALL include machine-readable metadata and human-readable context by default.

The default rendered shape SHALL include:
- a fenced `houmao-email-metadata` block with schema id, schema version, kind, run id, plan revision, exchange or handoff id, and important routing or result references;
- a `Context` section explaining why the mail was sent;
- template-specific human-readable sections;
- an explicit reply request section when the sender expects a reply.

#### Scenario: Rendered mail carries metadata
- **WHEN** the generated harness renders a templated mail payload
- **THEN** the rendered Markdown contains a `houmao-email-metadata` block
- **AND THEN** the metadata identifies the generated mail contract needed to interpret the message

#### Scenario: Rendered mail carries agent-readable context
- **WHEN** a participant reads a generated rendered mail message
- **THEN** the message contains a human-readable context section
- **AND THEN** any expected reply is stated explicitly when the message requires one

### Requirement: Harness records payload lifecycle without owning mail delivery
When a mail-driven loop has runtime state, the generated harness SHALL support communication payload lifecycle records for templated mail.

The default lifecycle record SHALL include payload id, schema id, kind, exchange or handoff id, source payload, status, optional platform message id, optional failure reason, and timestamps.

The generated harness MAY expose email commands for schema inspection, payload validation, Markdown rendering, lifecycle apply, and lifecycle query.

The generated harness SHALL NOT be treated as the owner of mailbox delivery. Sending, reading, replying, and archiving mail SHALL remain delegated to maintained Houmao mail support.

#### Scenario: Payload lifecycle is recorded after validation
- **WHEN** a generated role validates a templated mail payload and the loop has runtime state
- **THEN** the generated harness can record the source payload and lifecycle status
- **AND THEN** later validation or query surfaces can relate loop state to the payload id and platform message id when available

#### Scenario: Harness apply is not mail delivery
- **WHEN** a generated role records a payload through a harness lifecycle command
- **THEN** the command records loop-local payload facts
- **AND THEN** the role still uses maintained Houmao mail support for actual mailbox send, reply, read, or archive operations

### Requirement: Mail-driven loops include generic notice and acknowledgement families
Generated mail-driven loops SHALL include generic `freeform-notice` and `ack` mail families by default unless the intention source explicitly forbids them or defines equivalent families.

The `freeform-notice` family SHALL cover participant-facing or operator-origin information that does not fit a task-specific request/reply template but still needs validated context, action, and reply expectation fields.

The `ack` family SHALL cover acknowledgement of a handoff or mail without changing substantive loop state.

#### Scenario: Freeform notice handles unsupported participant-facing content
- **WHEN** a participant or operator needs to send loop-relevant content that does not fit a generated task-specific request/reply template
- **THEN** the generated loop provides a `freeform-notice` family or an explicitly equivalent family
- **AND THEN** the notice still records context, requested action, and reply expectation

#### Scenario: Ack handles receipt-only replies
- **WHEN** a participant only needs to acknowledge receipt of a handoff or mail
- **THEN** the generated loop provides an `ack` family or an explicitly equivalent family
- **AND THEN** the acknowledgement does not imply a substantive state transition unless another generated contract says so

### Requirement: Mail-received event skills process one bounded mail event
Generated mail-driven role skills SHALL use on-event handlers for concrete received mail events or message families.

A generated mail-received skill SHALL define its trigger, owning participant role, required context lookup, payload validation needs, role-owned action, reply behavior, archive behavior, and stopping point.

The trigger SHOULD identify the received generated schema id or message family when the loop uses templated participant mail.

Generated mail-received skills SHALL archive processed mail only after required work and required replies have succeeded.

#### Scenario: Role skill handles one received message family
- **WHEN** a participant receives a generated message family that has an associated on-event skill
- **THEN** the skill processes that bounded mail event for the owning role
- **AND THEN** the skill does not recursively drive unrelated loop phases beyond the event response

#### Scenario: Processed mail is archived after success
- **WHEN** a generated mail-received skill completes required work for a selected message
- **AND WHEN** any required reply has been sent successfully
- **THEN** the skill may archive that processed mail through maintained Houmao mail support
- **AND THEN** it does not archive unfinished, deferred, or reply-required-but-unanswered mail

### Requirement: Clarification focuses on loop-specific mail decisions
The `clarify intent` workflow SHALL treat Houmao mail transport and maintained mail-skill delegation as defaults for ordinary cross-agent loop communication.

Clarification SHALL focus mail questions on loop-specific decisions such as participant routes, message families, required payload fields, reply expectations, aggregation behavior, state or record effects, and whether any scheduler-like responsibility belongs in an on-tick skill.

#### Scenario: Clarification asks about message family details
- **WHEN** the intention source implies a participant handoff but does not define the message family details
- **THEN** the clarify workflow asks about the sender, recipient, payload fields, reply expectation, and resulting loop state or record effect
- **AND THEN** it does not ask the user to design Houmao mailbox transport mechanics

#### Scenario: Tick behavior is separated from received-mail behavior
- **WHEN** a loop needs aggregation, scheduling, reconciliation, completion checks, or “what now?” decisions after mail arrives
- **THEN** the clarify workflow identifies whether that behavior belongs to an on-tick skill instead of one received-mail event handler
