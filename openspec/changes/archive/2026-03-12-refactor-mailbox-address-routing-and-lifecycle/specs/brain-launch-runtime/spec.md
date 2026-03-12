## ADDED Requirements

### Requirement: Runtime mail send and reply commands require full recipient addresses and explicit body inputs
The runtime `mail` command surface SHALL treat `send` and `reply` as explicit mailbox operations rather than prompt-composition helpers.

For `mail send`, the runtime SHALL require recipients in full mailbox-address form for all `--to` and `--cc` inputs.

For `mail send` and `mail reply`, the runtime SHALL require explicit body input through `--body-file` or `--body-content`.

The runtime SHALL reject `--instruction` for `mail send` and `mail reply`.

#### Scenario: Mail send accepts full mailbox address plus explicit inline body
- **WHEN** a developer invokes `mail send` for a resumed mailbox-enabled session with `--to AGENTSYS-bob@agents.localhost` and `--body-content`
- **THEN** the runtime accepts the request as a mailbox operation
- **AND THEN** the resulting mailbox request preserves the sender identity already bound to that session

#### Scenario: Mail send rejects ambiguous short recipient names
- **WHEN** a developer invokes `mail send` with `--to bob`
- **THEN** the runtime fails fast with an explicit validation error
- **AND THEN** the error explains that a full mailbox address is required

#### Scenario: Mail send or reply rejects missing explicit body input
- **WHEN** a developer invokes `mail send` or `mail reply` without `--body-file` and without `--body-content`
- **THEN** the runtime fails fast before prompting the live agent session
- **AND THEN** the error explains that explicit mail body content is required

#### Scenario: Mail send or reply rejects instruction-style composition
- **WHEN** a developer invokes `mail send` or `mail reply` with `--instruction`
- **THEN** the runtime rejects that request explicitly
- **AND THEN** the operator is directed to use `--body-file` or `--body-content` instead

### Requirement: Runtime mailbox prompt payloads carry explicit content and address data without instruction fields
When the runtime translates `mail send` or `mail reply` into a runtime-owned mailbox prompt for a live session, the structured mailbox request payload SHALL carry explicit address and body data rather than an instruction asking the agent to improvise the final message.

For `mail send`, the structured request payload SHALL include full mailbox addresses for recipients and explicit Markdown body content.

For `mail reply`, the structured request payload SHALL include the target `message_id` plus explicit Markdown body content.

The structured request payload for `send` and `reply` SHALL NOT include an `instruction` field.

#### Scenario: Mail send payload carries explicit recipient addresses and body content
- **WHEN** the runtime prepares a `mail send` prompt request for a mailbox-enabled session
- **THEN** the structured mailbox request payload contains explicit full-form recipient addresses and explicit body content
- **AND THEN** that payload does not include an `instruction` field for content generation

#### Scenario: Mail reply payload carries explicit reply body and target message id
- **WHEN** the runtime prepares a `mail reply` prompt request for a mailbox-enabled session
- **THEN** the structured mailbox request payload contains the target `message_id` and explicit body content for the reply
- **AND THEN** that payload does not depend on free-form instruction text to determine the reply content

### Requirement: Runtime filesystem mailbox env bindings follow the active mailbox registration path
When the runtime starts or refreshes a mailbox-enabled filesystem session, it SHALL derive mailbox filesystem bindings from the active mailbox registration rather than by reconstructing a mailbox path from `principal_id`.

At minimum, `AGENTSYS_MAILBOX_FS_INBOX_DIR` SHALL point at the inbox path for the active mailbox registration for the session's bound mailbox address.

If runtime bootstrap or refresh can detect that the target mailbox root still uses the unsupported principal-keyed layout from the earlier implementation, it SHALL fail explicitly and direct the operator to delete and re-bootstrap that mailbox root.

#### Scenario: Start session publishes address-based inbox binding
- **WHEN** the runtime starts a mailbox-enabled session whose active registration is `AGENTSYS-research@agents.localhost`
- **THEN** `AGENTSYS_MAILBOX_FS_INBOX_DIR` points at the inbox path for that active registration
- **AND THEN** the runtime does not derive that path by concatenating `mailboxes/<principal_id>/inbox`

#### Scenario: Refresh mailbox bindings follows the current active registration path
- **WHEN** the runtime refreshes mailbox bindings for an active mailbox-enabled session after resolving the active registration
- **THEN** `AGENTSYS_MAILBOX_FS_INBOX_DIR` is updated from the active mailbox registration path for that address
- **AND THEN** subsequent runtime-controlled mailbox work uses the refreshed path

#### Scenario: Unsupported stale mailbox root fails binding refresh explicitly
- **WHEN** the runtime attempts to bootstrap or refresh mailbox bindings against a stale principal-keyed mailbox root from the earlier implementation
- **THEN** the runtime fails explicitly
- **AND THEN** the error tells the operator to delete and re-bootstrap the mailbox root rather than silently deriving incorrect bindings
