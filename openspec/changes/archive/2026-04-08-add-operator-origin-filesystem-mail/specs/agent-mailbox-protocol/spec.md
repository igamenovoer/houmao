## ADDED Requirements

### Requirement: Default managed mailbox addresses use `houmao.localhost` and reserve `HOUMAO-*`
The system SHALL derive new default managed-agent mailbox addresses as `<agentname>@houmao.localhost`.

Mailbox local parts beginning with `HOUMAO-` SHALL be reserved for Houmao-owned system principals rather than ordinary managed-agent or human-participant defaults.

The reserved namespace SHALL include `HOUMAO-operator@houmao.localhost`.

This requirement changes the default address-derivation policy only. Explicit mailbox bindings that already use another valid address remain valid unless later reconfigured.

#### Scenario: New managed agent derives a human-readable Houmao mailbox address
- **WHEN** the system derives the default mailbox address for managed agent `research`
- **THEN** the derived default address is `research@houmao.localhost`
- **AND THEN** the principal id remains independently tracked from that email-like address

#### Scenario: Reserved `HOUMAO-*` mailbox local part is rejected for ordinary agent naming
- **WHEN** an ordinary managed-agent mailbox binding or default-address derivation would produce `HOUMAO-alpha@houmao.localhost`
- **THEN** the system rejects that ordinary participant address as reserved for Houmao-owned system principals
- **AND THEN** only Houmao-owned reserved principals may use the `HOUMAO-*` mailbox local-part namespace

