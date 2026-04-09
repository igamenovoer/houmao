## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` explains the ordinary mailbox-address pattern and the reserved Houmao mailbox namespace
When the packaged `houmao-mailbox-mgr` skill guides ordinary mailbox account creation or late filesystem mailbox binding, it SHALL explain the split between canonical mailbox principal id and ordinary mailbox address.

At minimum, that guidance SHALL explain:

- ordinary managed-agent principal ids use the canonical `HOUMAO-<agentname>` form,
- ordinary managed-agent mailbox addresses use `<agentname>@houmao.localhost`,
- mailbox local parts beginning with `HOUMAO-` under `houmao.localhost` are reserved for Houmao-owned system principals rather than ordinary managed-agent mailbox addresses.

When the user has not specified a mailbox domain, the skill SHALL recommend `houmao.localhost` as the ordinary default domain instead of teaching `agents.localhost` as the ordinary account-creation pattern.

When the skill uses examples for ordinary mailbox account creation, it SHALL use examples such as address `research@houmao.localhost` with principal id `HOUMAO-research`.

The skill SHALL NOT suggest `HOUMAO-<agentname>@houmao.localhost` as the ordinary managed-agent mailbox-address pattern.

#### Scenario: Generic mailbox account creation guidance recommends the Houmao domain and split identity
- **WHEN** a user asks `houmao-mailbox-mgr` how to choose mailbox identity values for one ordinary managed agent
- **AND WHEN** the user has not already supplied a full mailbox address
- **THEN** the skill recommends an address such as `research@houmao.localhost`
- **AND THEN** the same guidance distinguishes that address from principal id `HOUMAO-research`

#### Scenario: Reserved mailbox local-part rule is explained during mailbox account creation
- **WHEN** the skill gives an example or recommendation for ordinary mailbox account creation under `houmao.localhost`
- **THEN** it explains that mailbox local parts beginning with `HOUMAO-` are reserved for Houmao-owned system principals
- **AND THEN** it does not present `HOUMAO-research@houmao.localhost` as the normal mailbox-address example for an ordinary managed agent
