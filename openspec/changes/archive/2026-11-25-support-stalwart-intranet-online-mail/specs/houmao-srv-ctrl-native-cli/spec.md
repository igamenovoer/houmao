# Spec Delta

## MODIFIED Requirements

### Requirement: Scoped online mailbox commands manage live account bindings
The maintained `agents single` and `agents self` trees SHALL expose `mailbox online status|attach|refresh|reconnect|detach`. Attach SHALL accept provider endpoint, address, login identity, and a protected credential reference. Attach SHALL accept repeatable `--trust-jmap-origin` options. Account selection and replacement intent SHALL be explicit when needed. Mutations SHALL preserve agent ID, body conversation, and offline binding.

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

#### Scenario: The operator opts into a selected intranet origin
- **WHEN** an authorized caller passes one or more `--trust-jmap-origin` values on scoped `mailbox online attach`
- **THEN** the command submits each exact origin with the authorized attach request
- **AND THEN** scoped `mailbox online status` reports the configured origin approvals and applicable plaintext warning

### Requirement: Online management reports committed and uncertain outcomes safely
CLI output SHALL distinguish validated activation, stale-revision conflict, rejected credentials, endpoint failure, an unapproved or changed JMAP origin, incomplete account readiness, committed binding with projection failure, and uncertain in-flight mutation outcomes. Status SHALL expose safe binding/sync health rather than credential bytes, authorization headers, or raw provider exception dumps.

#### Scenario: Projection fails after activation
- **WHEN** online binding activation commits but a registry projection cannot be refreshed
- **THEN** the result identifies the committed revision and reconciliation need
- **AND THEN** it does not falsely claim that attachment was rolled back

#### Scenario: The account needs operator preparation
- **WHEN** the provider rejects the sending identity or reports a missing required mailbox role or permission
- **THEN** the CLI reports the specific readiness problem, gives a remediation, and exits nonzero

#### Scenario: A JMAP endpoint needs explicit approval
- **WHEN** attachment rejects an unapproved origin
- **THEN** the CLI reports the safe origin and the required approval or HTTPS configuration
- **AND THEN** it exits nonzero without displaying credentials or raw provider responses
