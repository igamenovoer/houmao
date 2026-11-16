# Spec Delta

## REMOVED Requirements

### Requirement: `project mailbox register` mirrors the generic mailbox overwrite-confirmation contract
**Reason**: Overwrite confirmation cannot authorize taking another agent's offline address under the new ownership contract.
**Migration**: Preserve project-aware root selection but use the generic conflict-rejecting registration service; explicitly release an address first and remove register `--yes`/force/stash usage.

## ADDED Requirements

### Requirement: Project mailbox registration preserves registry ownership rules
Project mailbox registration SHALL resolve the selected project root and apply the same owner/address conflict checks as generic administration. Agent claims SHALL use stable IDs. An occupied address SHALL fail without interactive overwrite or `--yes` bypass. A selected root that does not match the configured registry store SHALL fail rather than creating another implicit group.

#### Scenario: Project registration conflicts with an existing owner
- **WHEN** project-scoped registration targets an address belonging to another agent in the selected registry
- **THEN** it returns a conflict and preserves the existing mailbox
- **AND THEN** no confirmation prompt or overwrite flag permits takeover

#### Scenario: Project root belongs to the configured registry
- **WHEN** the selected overlay mailbox root matches the selected registry's configured store
- **AND WHEN** the requested address is free or already belongs to the same agent
- **THEN** registration uses that authority and preserves project-aware root selection

## MODIFIED Requirements

### Requirement: `houmao-mgr project mailbox messages` is structural inspection, not participant-local state reporting

The native `houmao-mgr project mailbox messages list` and `houmao-mgr project mailbox messages get` commands SHALL expose structural inspection over the current project's mailbox root for one explicitly selected mailbox address.

Those commands MAY return canonical message metadata and address-scoped projection metadata for the selected address, including message identity, thread identity, projection folder, projection path, canonical path, sender metadata, recipient metadata, body content, headers, and attachments.

Those commands SHALL NOT report participant-local mutable mailbox view-state fields such as `read`, `starred`, `archived`, or `deleted`, even though the command is scoped to one explicit address.

When an operator needs workflow state such as whether a processed message is still actionable unread mail for one agent, the supported surface SHALL be actor-scoped mail commands such as `houmao-mgr agents self mail ...` rather than `houmao-mgr project mailbox messages ...`.

#### Scenario: Project mailbox message list omits participant-local mutable state

- **WHEN** an operator runs `houmao-mgr project mailbox messages list --address alice@agents.localhost`
- **THEN** the command returns structural message summaries for that selected project-local address projection
- **AND THEN** each message summary may include fields such as `message_id`, `thread_id`, `subject`, `folder`, `projection_path`, and `canonical_path`
- **AND THEN** the payload does not include `read`, `starred`, `archived`, or `deleted`

#### Scenario: Project mailbox message get omits participant-local mutable state

- **WHEN** an operator runs `houmao-mgr project mailbox messages get --address alice@agents.localhost --message-id msg-123`
- **THEN** the command returns canonical message details together with the selected project-local address projection metadata
- **AND THEN** the payload may include sender, recipients, headers, body content, attachments, `folder`, and `projection_path`
- **AND THEN** the payload does not claim a single authoritative participant-local read, starred, archived, or deleted state

#### Scenario: Project mailbox verification guidance points operators to actor-scoped mail state

- **WHEN** an operator needs to verify that one managed agent has finished processing mailbox work and no longer has actionable unread mail
- **THEN** the supported completion boundary is an actor-scoped command such as `houmao-mgr agents single --agent-name alice mail list --channel offline --read-state unread`
- **AND THEN** `houmao-mgr project mailbox messages list|get` remains a structural inspection surface rather than the source of truth for that completion state
