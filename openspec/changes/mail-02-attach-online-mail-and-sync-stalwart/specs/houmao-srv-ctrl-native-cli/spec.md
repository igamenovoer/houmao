# Spec Delta

## ADDED Requirements

### Requirement: Scoped online mailbox commands manage live account bindings
The maintained `agents single` and `agents self` trees SHALL expose `mailbox online status|attach|refresh|reconnect|detach`. Attach SHALL accept provider endpoint, address, login identity, and a protected credential reference; account selection and replacement intent SHALL be explicit when needed. Mutations SHALL preserve agent ID, body conversation, and offline binding.

#### Scenario: Operator attaches a hub-provisioned account
- **WHEN** an operator runs scoped `mailbox online attach` with valid Stalwart account inputs
- **THEN** the command reports the committed binding ID/revision and canonical mail identity
- **AND THEN** it does not require management credentials or a body relaunch

#### Scenario: Refresh rejects another account
- **WHEN** scoped `mailbox online refresh` resolves credentials for an account different from the current binding
- **THEN** the command returns an explicit identity mismatch and preserves the current binding

#### Scenario: Detached provider mail is retained
- **WHEN** an operator runs scoped `mailbox online detach`
- **THEN** only the online binding is removed and provider mail remains intact

### Requirement: Native mailbox listing is paged and metadata-only
Scoped `mail list --channel offline|online` SHALL use a finite default `--limit`, enforce a maximum, accept `--cursor`, and return one metadata page with continuation and clearly scoped counts. It SHALL not fetch subsequent pages automatically. The removed `--include-body` flag SHALL fail clearly and point to peek/read.

#### Scenario: Operator continues an online metadata page
- **WHEN** a caller supplies the previous response's cursor with the same channel and filters
- **THEN** the command returns one bounded continued page without body retrieval

#### Scenario: Removed content-list flag is used
- **WHEN** a caller supplies `--include-body` to list
- **THEN** argument validation rejects it before mailbox I/O

### Requirement: Online management reports committed and uncertain outcomes safely
CLI output SHALL distinguish validated activation, stale-revision conflict, rejected credentials, endpoint failure, committed binding with projection failure, and uncertain in-flight mutation outcomes. Status SHALL expose safe binding/sync health rather than credential bytes, authorization headers, or raw provider exception dumps.

#### Scenario: Projection fails after activation
- **WHEN** online binding activation commits but a registry projection cannot be refreshed
- **THEN** the result identifies the committed revision and reconciliation need
- **AND THEN** it does not falsely claim that attachment was rolled back
