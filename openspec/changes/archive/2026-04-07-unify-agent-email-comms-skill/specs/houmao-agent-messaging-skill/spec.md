## REMOVED Requirements

### Requirement: `houmao-agent-messaging` delegates transport-specific mailbox behavior to existing Houmao mailbox skills
**Reason**: The legacy split ordinary-mailbox skills are being replaced by one unified ordinary mailbox skill.
**Migration**: Delegate notifier rounds to `houmao-process-emails-via-gateway` and delegate ordinary mailbox actions plus transport-specific guidance to `houmao-agent-email-comms`.

## ADDED Requirements

### Requirement: `houmao-agent-messaging` delegates mailbox behavior to the current Houmao mailbox skills
When mailbox-related messaging requires notifier-round workflow, ordinary mailbox actions, or transport-specific guidance, the packaged `houmao-agent-messaging` skill SHALL direct the agent to the current Houmao mailbox skills instead of duplicating that detail locally.

At minimum, that delegation SHALL cover:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The packaged `houmao-agent-messaging` skill SHALL keep its own mailbox coverage at the communication-routing level and SHALL NOT restate filesystem layout, Stalwart credential handling, or the lower-level `/v1/mail/*` contract in full.

#### Scenario: Gateway mailbox round work delegates to the processing skill
- **WHEN** the messaging task becomes a notifier-driven mailbox-processing round with a live gateway mailbox facade
- **THEN** the skill directs the agent to `houmao-process-emails-via-gateway`
- **AND THEN** it does not duplicate that round workflow inside `houmao-agent-messaging`

#### Scenario: Ordinary mailbox follow-up delegates to the unified ordinary-mailbox skill
- **WHEN** the messaging task needs ordinary mailbox follow-up, live mailbox discovery, or transport-local mailbox guidance
- **THEN** the skill directs the agent to `houmao-agent-email-comms`
- **AND THEN** it does not restate that ordinary mailbox guidance as part of the generic managed-agent messaging skill
