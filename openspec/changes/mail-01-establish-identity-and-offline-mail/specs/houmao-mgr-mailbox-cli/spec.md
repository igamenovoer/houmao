# Spec Delta

## REMOVED Requirements

### Requirement: `houmao-mgr mailbox register` and `unregister` expose operator mailbox lifecycle control
**Reason**: Registration overwrite confirmation and force/stash takeover conflict with exclusive offline address ownership.
**Migration**: Keep administrative register/unregister commands, but use conflict-rejecting registration and explicit prior release; remove register overwrite flags and update scripts using them.

## ADDED Requirements

### Requirement: Administrative offline registration enforces registry ownership
Administrative register/unregister SHALL use the selected registry's ownership index and configured filesystem store. Agent ownership SHALL use persisted `agent_id`; human and reserved system principals SHALL retain their own identity rules. Register SHALL reject another owner's address without overwrite prompts, force/stash modes, or `--yes` bypass. Unregister SHALL explicitly release ownership non-destructively by default.

#### Scenario: Free address is registered safely
- **WHEN** an authorized operator registers an unowned address in the selected registry's configured store
- **THEN** the command creates or reuses the matching registration and reports its identity

#### Scenario: Administrative register cannot overwrite another agent
- **WHEN** an operator registers an address already owned by another agent
- **THEN** the command returns a conflict without changing that owner's mailbox
- **AND THEN** selecting removed overwrite flags or takeover modes does not bypass the conflict

#### Scenario: Administrative release retains canonical history
- **WHEN** an authorized operator unregisters an address with the default leave policy
- **THEN** its routing registration is deactivated and retained history remains scoped to its previous owner

### Requirement: Mailbox maintenance root selection does not change registry authority
Existing project-aware filesystem root selection SHALL remain available for maintenance. Membership mutations SHALL verify that the selected root belongs to the selected registry configuration. A mismatch SHALL fail with actionable configuration guidance rather than silently creating another mail group inside the same registry or rewriting its store selection.

#### Scenario: Project default differs from configured registry store
- **WHEN** registration resolves a project mailbox root different from the selected registry's configured store
- **THEN** it fails before allocating an address
- **AND THEN** it does not silently move the registry or register into an unrelated root
