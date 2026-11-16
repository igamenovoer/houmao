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

## MODIFIED Requirements

### Requirement: `houmao-mgr mailbox init` bootstraps or validates one filesystem mailbox root
`houmao-mgr mailbox init` SHALL bootstrap or validate one filesystem mailbox root using the filesystem mailbox bootstrap contract.

The effective mailbox root SHALL resolve from:

1. explicit `--mailbox-root`,
2. `HOUMAO_GLOBAL_MAILBOX_DIR`,
3. the active project overlay mailbox root,
4. bootstrap `<cwd>/.houmao/mailbox` when no overlay exists and no stronger override applies.

A successful bootstrap SHALL create or validate the current-format filesystem mailbox layout, including protocol version, shared SQLite catalog, rules assets, mailbox directories root, locks root, and staging root. Initialization SHALL explicitly associate an unconfigured selected registry with that store or verify an existing matching association; it SHALL NOT silently replace the association.

#### Scenario: Init without overrides uses the active overlay mailbox root
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr mailbox init` without `--mailbox-root`
- **AND WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is unset
- **THEN** the command bootstraps or validates `/repo/.houmao/mailbox`
- **AND THEN** it does not bootstrap a shared mailbox root under `<platformdirs user config>/`

#### Scenario: Init cannot silently replace an existing registry store association
- **WHEN** the selected registry is already associated with another filesystem mail store
- **AND WHEN** initialization selects a different store
- **THEN** it fails with actionable configuration guidance without rewriting the association

### Requirement: `houmao-mgr mailbox repair` rebuilds filesystem mailbox index state locally
`houmao-mgr mailbox repair` SHALL rebuild one filesystem mailbox root's shared index state locally without requiring `houmao-server`.

Repair SHALL rebuild derived message and projection state in place while preserving durable registration IDs, owner claims, member authorization, and attachment authority. Missing or unreadable ownership authority SHALL produce an explicit recovery error rather than inferred ownership. The result SHALL report recovered derived state.

#### Scenario: Operator repairs a mailbox root locally
- **WHEN** an operator runs `houmao-mgr mailbox repair --mailbox-root /tmp/shared-mail`
- **THEN** the command rebuilds filesystem mailbox index state for `/tmp/shared-mail`
- **AND THEN** the result reports repair outcomes without requiring manual SQLite intervention

#### Scenario: Repair preserves membership authority
- **WHEN** a supported mailbox root contains durable members, registrations, and attachments
- **AND WHEN** an operator repairs its derived index state
- **THEN** existing ownership identities and authorization remain unchanged

#### Scenario: Lost ownership index is not reconstructed from address paths
- **WHEN** the authoritative ownership index is missing or unreadable
- **THEN** repair fails with explicit recovery guidance
- **AND THEN** it does not allocate new owners from directory names or message headers
