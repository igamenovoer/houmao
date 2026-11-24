# Spec Delta

## ADDED Requirements

### Requirement: Versioned File Operations Use Shared Gateway Authorization

The live target gateway SHALL authorize file operations through shared Casbin policy for the exact mount and action. The target owner SHALL control enrollment and revocation of peer SSH public keys for stable logical agents. In a keyed domain, a nonadmin SHALL prove possession of an enrolled key through normal caller proof and hold the exact grant. Current named administrators and callers admitted under a valid empty roster SHALL have access to every supported file operation.

#### Scenario: An enrolled peer uses a scoped file operation

- **WHEN** an enrolled logical agent signs the exact file request with its enrolled key and current policy grants the operation on the selected mount
- **THEN** the gateway authorizes it under that peer identity
- **AND THEN** a source restart, execution context change, or unavailable source liveness evidence leaves the enrollment valid

#### Scenario: A peer requests a different mount or operation

- **WHEN** a verified nonadmin invokes a file operation on a keyed gateway outside that caller's grant
- **THEN** the gateway refuses the operation before effects

#### Scenario: A caller claims an enrolled identity

- **WHEN** a caller presents a logical agent label or a managed self credential without proving possession of that agent's enrolled peer key
- **THEN** the gateway assigns no authority from that peer enrollment

#### Scenario: An administrator invokes a supported file operation

- **WHEN** a caller using a current admin-enrolled key or admitted under a valid empty roster requests a supported file operation
- **THEN** gateway-admin policy supplies its required permissions for the selected target
- **AND THEN** proof, input, target, and runtime requirements still apply

### Requirement: File Effects Require Current Direct Target Authority

File requests SHALL use the verified live target gateway directly. Before an effect, it SHALL recheck the bound target generation and listener incarnation, exact mount and action, current credential and policy, and admitted authority. Revalidation SHALL include the original admin enrollment or open epoch when applicable. Unsigned callers SHALL retain anonymous provenance.

#### Scenario: A peer's credential or grant changes after admission

- **WHEN** the owner revokes the credential or removes permission for the mount and action before the operation takes effect
- **THEN** the gateway refuses the pending operation under its earlier admission

#### Scenario: A publisher loses admin qualification

- **WHEN** the signing key loses the admin roster entry that authorized an admitted push before handoff
- **THEN** the gateway refuses the push and retains the candidate
- **AND THEN** another request may publish the candidate under current call authority

#### Scenario: The target body or gateway incarnation changes

- **WHEN** the bound target generation or listener incarnation changes before the operation takes effect
- **THEN** the gateway refuses to apply the pending operation to the replacement

#### Scenario: Anonymous access resumes after an earlier admission

- **WHEN** an anonymous operation was admitted under an empty roster that later becomes keyed and then empty again before the operation takes effect
- **THEN** the operation is refused under its earlier open epoch
- **AND THEN** a fresh request can use the current open epoch

#### Scenario: The verified live target is unavailable

- **WHEN** the client cannot reach a verified live target gateway, including cases where the passive service can resolve the target
- **THEN** the file operation reports unavailable through the direct client path
- **AND THEN** no passive fallback carries out the operation
