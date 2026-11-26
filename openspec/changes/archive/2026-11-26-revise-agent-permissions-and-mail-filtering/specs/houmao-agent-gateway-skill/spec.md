# Gateway Agent Skill Delta

## MODIFIED Requirements

### Requirement: `houmao-agent-gateway` routes by gateway-specific intent and keeps ordinary messaging on the existing skills
The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent and delegate ordinary prompt and mailbox work to the appropriate messaging or mailbox skill.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent:

- use scoped `gateway attach|detach|status` or `/houmao/agents/{agent_ref}/gateway...` for gateway lifecycle and summary state
- use scoped `gateway mail-notifier ...` or `/houmao/agents/{agent_ref}/gateway/mail-notifier` for mailbox notifier control
- use scoped `gateway reminders list|get|create|set|remove` or `/houmao/agents/{agent_ref}/gateway/reminders...` for reminder creation, inspection, update, and cancellation
- treat reminder delivery through the supported reminder surfaces as supporting both semantic `prompt` reminders and raw `send_keys` reminders
- select a direct live gateway HTTP route when the task needs its lower-level contract and the exact current target has been established
- document `POST /v1/mail/{channel}/policy/apply` as the gateway relay for independently authorized mailbox rule updates
- delegate independently signed direct requests to `agent-access` for the supported caller and target proof
- delegate versioned file operations to `agent-files`

The packaged skill SHALL delegate ordinary prompt turns, mailbox routing, ordinary mailbox work, and transport-specific mailbox work to `houmao-agent-messaging`, `houmao-process-emails-via-gateway`, or `houmao-agent-email-comms` according to the request.

The skill SHALL prefer the scoped manager or managed-agent projection when it satisfies the task. Direct gateway HTTP guidance SHALL carry the authorization, target binding, and operation constraints of the chosen endpoint.

#### Scenario: Reminders use the native gateway reminder surfaces when available
- **WHEN** the user asks to create, inspect, update, or cancel live gateway reminders
- **THEN** the skill directs the caller to the scoped manager reminders command or the matching `/houmao/agents/{agent_ref}/gateway/reminders...` projection when pair-managed authority is in use
- **AND THEN** it does not misdescribe reminders as an HTTP-only workflow when the supported higher-level reminder surfaces already exist

#### Scenario: Direct live reminder HTTP stays the lower-level contract
- **WHEN** the user asks to debug or inspect the exact live reminder HTTP contract
- **AND WHEN** supported discovery establishes the exact current gateway target
- **THEN** the skill describes the live `{gateway.base_url}/v1/reminders...` route family and its required caller proof
- **AND THEN** it keeps that direct route family positioned as the lower-level contract rather than the first-choice operator surface

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or mailbox work rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the current mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface

#### Scenario: The HTTP Reference Shows the Owner-Authorized Mail Policy Relay

- **WHEN** a mailbox owner consults `references/http-surface.md` to apply recipient rules
- **THEN** the reference identifies `POST /v1/mail/{channel}/policy/apply` on the verified current gateway
- **AND THEN** it explains that the owner signs the operation, exact backend and mailbox binding, expected policy revision, operation ID, and exact rule payload
- **AND THEN** it distinguishes gateway administrator admission from independently authenticated mailbox-owner authority and directs the owner to verify the committed revision and outcome through the trusted backend or connector
- **AND THEN** it explains confirmed, refused, unsupported, and uncertain backend outcomes without treating an unconfirmed relay as applied

#### Scenario: The HTTP Reference Shows Protected Mailbox Lifecycle Limits

- **WHEN** `references/http-surface.md` describes ordinary routes for a protected mailbox binding
- **THEN** it documents binding-scoped read, send, reply, and non-placement marking under their applicable scopes
- **AND THEN** it describes ordinary move, archive, and placement-changing mark as unsupported on the protected binding and routes owner filing through independent backend authority

#### Scenario: The HTTP Reference Explains Admission on a Keyed Gateway

- **WHEN** `references/http-surface.md` describes `admin_mode: keyed` in endpoint discovery
- **THEN** it distinguishes independently verified callers using eligible effective permissions from eligible unsigned callers using the configured default
- **AND THEN** it explains that the target can disable fallback for a verified principal and that invalid supplied proof is refused

### Requirement: Gateway system skill documents notifier notification mode

The packaged `houmao-agent-gateway` system skill SHALL describe `mail-notifier` in `commands/mail-notifier.md` as mailbox-driven notification control. Its guidance SHALL explain that `any_inbox` is the default and includes unarchived mail in the backend's authoritative Inbox. The opt-in `unread_only` mode limits this eligible set to unread mail.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The guidance SHALL mention that `unread_only` is a lower-noise mode and that read-but-unarchived mail will not by itself trigger future notifier prompts in that mode.

#### Scenario: Gateway skill shows default notifier mode

- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance states that `any_inbox` is the default notifier mode
- **AND THEN** it describes that default as notification for unarchived Inbox mail regardless of read or answered state, subject to ordinary readiness and admission rules

#### Scenario: Gateway skill shows unread-only opt-in mode

- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance documents `unread_only` as an opt-in notifier mode
- **AND THEN** it explains that read-but-unarchived mail is not notifier-eligible in that mode

#### Scenario: Gateway skill stays mail-specific

- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as mailbox-driven notification control
- **AND THEN** it does not describe notifier mode as a generic unfinished-job persistence mechanism

#### Scenario: Gateway Skill Explains Backend-Owned Inbox Placement

- **WHEN** a caller asks how sender blocking affects Inbox reminders
- **THEN** the guidance explains that the backend files matching new mail directly into Archive and that both modes observe open work in the authoritative Inbox
- **AND THEN** it explains that rule changes leave existing Inbox placement in effect and that unblocking leaves archived messages in Archive

#### Scenario: Processed Mail Is Still in a Protected Inbox

- **WHEN** the agent finishes processing mail on a protected binding that reserves filing for the mailbox owner
- **THEN** `commands/mail-notifier.md` explains that the agent can end the round after processing and any required reply while the backend retains placement control
- **AND THEN** it explains that `any_inbox` can repeat while the message remains in Inbox and `unread_only` follows its current read state
