## ADDED Requirements

### Requirement: `houmao-mgr mailbox` reflects the reserved operator mailbox account
The generic filesystem mailbox CLI SHALL reflect the reserved operator mailbox account `HOUMAO-operator@houmao.localhost`.

`houmao-mgr mailbox init` SHALL provision or confirm that reserved account for the resolved filesystem mailbox root.

`houmao-mgr mailbox accounts list|get` SHALL expose that reserved account as mailbox registration state instead of hiding it.

Generic destructive lifecycle commands SHALL protect that reserved account:

- `unregister` SHALL reject destructive removal of the reserved operator account by default,
- `cleanup` SHALL preserve the active reserved operator account.

#### Scenario: Generic mailbox init confirms the reserved operator account
- **WHEN** an operator runs `houmao-mgr mailbox init`
- **THEN** the resulting mailbox root state includes the reserved account `HOUMAO-operator@houmao.localhost`
- **AND THEN** later `accounts list` can inspect that account through the same mailbox-root CLI family

#### Scenario: Generic mailbox unregister rejects the reserved operator account
- **WHEN** an operator runs `houmao-mgr mailbox unregister --address HOUMAO-operator@houmao.localhost`
- **THEN** the command fails explicitly instead of removing the reserved system mailbox registration
- **AND THEN** the mailbox root continues preserving the operator-origin sender account

