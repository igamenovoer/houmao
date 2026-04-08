## ADDED Requirements

### Requirement: `houmao-mgr project mailbox` mirrors the reserved operator mailbox behavior
The project-scoped mailbox CLI SHALL mirror the reserved operator mailbox-account behavior of the generic filesystem mailbox CLI under the selected project mailbox root.

`houmao-mgr project mailbox init` SHALL provision or confirm `HOUMAO-operator@houmao.localhost` under the selected overlay mailbox root.

`houmao-mgr project mailbox accounts list|get` SHALL expose that reserved account as project-local mailbox registration state instead of hiding it.

Project-scoped destructive lifecycle commands SHALL protect that reserved account in the same way as the generic mailbox CLI.

#### Scenario: Project mailbox init confirms the reserved operator account
- **WHEN** an operator runs `houmao-mgr project mailbox init`
- **THEN** the selected project mailbox root contains the reserved account `HOUMAO-operator@houmao.localhost`
- **AND THEN** the project-scoped mailbox CLI can inspect that account through `accounts list|get`

#### Scenario: Project mailbox cleanup preserves the reserved operator account
- **WHEN** an operator runs `houmao-mgr project mailbox cleanup`
- **AND WHEN** the selected project mailbox root contains the active reserved operator account
- **THEN** cleanup preserves that account
- **AND THEN** the project mailbox root keeps the operator-origin sender registration available for later mailbox delivery

