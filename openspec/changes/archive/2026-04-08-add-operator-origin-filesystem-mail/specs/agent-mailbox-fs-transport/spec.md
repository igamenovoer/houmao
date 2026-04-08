## ADDED Requirements

### Requirement: Filesystem mailbox roots provision and protect the reserved operator account
The filesystem mailbox transport SHALL treat `HOUMAO-operator@houmao.localhost` as a reserved system mailbox registration under each initialized mailbox root.

That reserved registration SHALL use the Houmao-owned principal id `HOUMAO-operator` and SHALL be provisioned or confirmed as part of mailbox-root bootstrap.

When an otherwise valid filesystem mailbox root lacks that reserved registration later, operator-origin delivery flows MAY self-heal by recreating or confirming it before delivery.

Generic filesystem mailbox lifecycle operations SHALL protect the reserved operator registration:

- cleanup SHALL preserve it while it is active,
- generic unregister or purge flows SHALL reject destructive removal by default,
- account inspection MAY annotate it as a system account.

#### Scenario: Filesystem mailbox bootstrap creates the reserved operator registration
- **WHEN** the runtime bootstraps or validates a new filesystem mailbox root
- **THEN** the root contains an active registration for `HOUMAO-operator@houmao.localhost`
- **AND THEN** that registration uses the reserved Houmao-owned principal id rather than an ordinary managed-agent principal id

#### Scenario: Cleanup preserves the reserved operator registration
- **WHEN** an operator runs filesystem mailbox cleanup against a mailbox root that contains the active reserved operator registration
- **THEN** cleanup preserves that reserved registration
- **AND THEN** the cleanup flow does not report `HOUMAO-operator@houmao.localhost` as an inactive or disposable mailbox account

