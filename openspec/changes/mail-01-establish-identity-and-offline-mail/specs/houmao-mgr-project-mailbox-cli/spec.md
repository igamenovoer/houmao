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
