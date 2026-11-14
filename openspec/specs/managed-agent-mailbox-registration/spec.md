## Purpose
Define late filesystem mailbox registration for existing local managed agents, including session binding persistence and activation-state reporting by runtime posture.

## Requirements
### Requirement: Scoped offline membership commands support existing local agent bodies
The scoped `agents single` and `agents self` command trees SHALL expose `mailbox offline status`, `join`, and `leave`. They SHALL resolve the stable agent owner and selected local or remote registry without requiring body restart. Remote body management SHALL remain outside communication-only registration authority.

#### Scenario: Offline-disabled body joins a remote registry
- **WHEN** an authorized operator selects an existing local body and joins a remote registry
- **THEN** its offline binding references the confirmed registry registration
- **AND THEN** the body process, conversation, stable agent ID, and online binding remain unchanged

#### Scenario: Joined tmux body needs no relaunch posture
- **WHEN** an adopted tmux body without relaunch metadata joins a registry successfully
- **THEN** offline operations become actionable without relaunch or mailbox-specific environment updates

### Requirement: Offline join and leave publish confirmed ownership outcomes
Join SHALL commit only the registration confirmed by the selected registry and preserve other bindings. Conflicts SHALL fail without overwrite prompts or force/stash takeover. Leave SHALL explicitly release membership, remove the offline binding, and preserve online mail. Partial publication failures SHALL be reported and support idempotent reconciliation.

#### Scenario: Address conflict does not mutate runtime bindings
- **WHEN** join receives an address conflict from the registry
- **THEN** the previous local bindings remain unchanged
- **AND THEN** neither `--yes` nor a removed takeover mode bypasses the conflict

#### Scenario: Registry committed but the local response was lost
- **WHEN** a caller retries the same owner/address join after an uncertain outcome
- **THEN** it can reconcile the existing registration and publish that binding
- **AND THEN** it does not create a second membership or overwrite another agent

#### Scenario: Offline leave preserves online identity
- **WHEN** an agent with both bindings explicitly leaves offline mail
- **THEN** its online binding and canonical online identity remain unchanged

### Requirement: Offline status distinguishes registration from connectivity
Offline status SHALL distinguish no configured binding, confirmed membership, explicit release, unavailable registry connectivity, and binding conflicts. It SHALL report current owner, address, binding revision, and safe registry locator without credential material. It SHALL NOT report `pending_relaunch` as a remedy for communication attachment.

#### Scenario: Registry outage leaves membership visible
- **WHEN** the registry cannot be reached after an earlier confirmed join
- **THEN** status reports the configured binding with unavailable connectivity
- **AND THEN** it does not claim that the address has been released
