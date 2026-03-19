## ADDED Requirements

### Requirement: System-files reference documentation explains Stalwart mailbox secret lifecycle boundaries
The system-files reference documentation SHALL explain how runtime-managed filesystem artifacts represent Stalwart-backed mailbox bindings without persisting inline secrets.

At minimum, the system-files reference SHALL explain:

- that the session manifest persists a secret-free mailbox binding rather than inline Stalwart credentials,
- that persisted mailbox data identifies credential material through a durable reference such as `credential_ref`,
- where runtime-owned durable credential-related artifacts live relative to the runtime root and session root,
- where session-local materialized credential files may appear when direct or gateway-backed mailbox access needs them,
- which of those path families are durable operator-facing artifacts versus current implementation-detail or secret-bearing surfaces.

That explanation SHALL keep the broader mailbox semantics in the mailbox subtree while making the filesystem placement and contract level explicit in the system-files subtree.

#### Scenario: Reader can distinguish manifest persistence from secret-bearing files
- **WHEN** a reader opens the system-files reference to understand a Stalwart-backed session root
- **THEN** the docs explain that `manifest.json` keeps a secret-free mailbox binding and not inline credentials
- **AND THEN** the docs explain where the corresponding credential reference and any materialized secret files belong in the runtime-managed filesystem model

#### Scenario: Operator can tell durable state from cleanup-sensitive secret material
- **WHEN** an operator needs to understand which Stalwart-related runtime files are durable state and which are secret-bearing or session-local artifacts
- **THEN** the system-files docs identify the relevant path families and their contract level clearly
- **AND THEN** the operator is not left to infer cleanup or handling expectations solely from source code
