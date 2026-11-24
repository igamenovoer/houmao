# Spec Delta

## ADDED Requirements

### Requirement: Versioned File Operations Use Shared Gateway Authorization

The live target gateway SHALL authorize each file operation through the retained owner policy for its exact mount resource and declared action. A keyed nonadmin SHALL use current enrolled caller proof and hold the corresponding permission. Current named admins and callers admitted under a valid empty roster SHALL have access to every supported file action.

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

File requests SHALL use direct SSHSIG v2 caller proof or valid unsigned open access at the verified target gateway. Before each protected effect or disclosure, it SHALL recheck the target generation, listener, exact permission, credential enrollment, and original authority. That authority SHALL retain the qualifying admin entry or open epoch where applicable. Unsigned callers SHALL retain anonymous provenance.

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

#### Scenario: Open access resumes after an earlier admission

- **WHEN** a signed or unsigned request received open authority and the roster becomes keyed and then empty again before the effect
- **THEN** the gateway refuses the operation under its earlier open epoch
- **AND THEN** a fresh request can use the current open epoch

#### Scenario: A file route receives delegated proof

- **WHEN** a file route receives relay or backing-service proof in place of direct caller admission
- **THEN** the gateway refuses the request before effects

#### Scenario: The verified live target is unavailable

- **WHEN** the client cannot reach a verified live target gateway, including cases where the passive service can resolve the target
- **THEN** the file operation reports unavailable through the direct client path
- **AND THEN** no passive fallback carries out the operation
