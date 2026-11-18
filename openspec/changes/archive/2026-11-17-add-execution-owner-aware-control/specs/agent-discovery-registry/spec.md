# Agent Discovery Registry Spec Delta

## ADDED Requirements

### Requirement: Owner lifecycle records preserve execution bindings

Owner-side managed-agent lifecycle records SHALL identify the persisted execution binding alongside logical agent identity and existing runtime pointers. Publication, resume, stop, and relaunch SHALL preserve that binding independently of volatile presence. Registry content SHALL remain secret-free and SHALL NOT itself grant delegation or replace owner-side manifest authority.

#### Scenario: Stopped agent retains execution ownership

- **WHEN** an execution-bound managed agent stops while retaining relaunchable runtime artifacts
- **THEN** its owner lifecycle record preserves the execution binding and logical agent ID
- **AND THEN** current live handles are cleared according to the existing stopped lifecycle contract

#### Scenario: Relaunch updates presence without changing owner

- **WHEN** an execution-bound managed agent is relaunched successfully
- **THEN** owner publication reports the new generation with the original execution binding
- **AND THEN** it does not replace execution ownership with the invoking controller's account

### Requirement: Operator execution locators remain separate from runtime presence and communication imports

The operator registry SHALL store executor-managed locators separately from owner-local runtime records and external communication-only imports. A locator SHALL contain the authoritative agent ID, friendly name, configured route reference, captured execution binding, and safe owner lookup information. It SHALL omit credentials, copied manifests, mutable runtime state, and authority-implying caller-local control endpoints.

#### Scenario: Delegated launch publishes a routing locator after owner admission

- **WHEN** a delegated launch succeeds and the owner returns its admitted binding and managed-agent identity
- **THEN** the operator publishes a locator for that identity in the execution-locator collection
- **AND THEN** the actual manifest and runtime lifecycle record remain owned by the target context

#### Scenario: Foreign path and loopback endpoint are not local authority

- **WHEN** a target context reports a manifest path, home path, or owner-loopback gateway address
- **THEN** the operator treats those values as context-qualified metadata
- **AND THEN** it does not open the path locally or connect to the same loopback port on the operator's host as a substitute

#### Scenario: Conflicting bindings cannot replace an existing logical identity

- **WHEN** publication would associate one known authoritative agent ID with a different execution binding
- **THEN** publication reports an identity/context conflict
- **AND THEN** it does not silently overwrite the existing locator or claim a second owner

### Requirement: Local registry cleanup cannot infer foreign liveness or remove owner state

Local stale-presence cleanup SHALL NOT classify execution locators using caller-local tmux probes or local lease rules. A failed owner connection SHALL indicate unavailable or unverified state rather than stopped state. Removing an operator locator SHALL remove only the lexical locator entry and SHALL NOT stop an agent, remove owner artifacts, or change communication-only imports or offline membership.

#### Scenario: Local tmux absence preserves execution locator

- **WHEN** a local cleanup pass finds no caller-local tmux session corresponding to an execution locator
- **THEN** it preserves that locator without inferring that the owner-side agent is dead

#### Scenario: Locator removal leaves owner runtime intact

- **WHEN** an operator removes an execution locator
- **THEN** only that operator-owned lexical registry entry is removed
- **AND THEN** the owner-side agent, manifest, runtime files, and independent communication records remain intact

### Requirement: Failed operator publication preserves an admitted owner launch

If owner launch succeeds but operator locator publication fails, Houmao SHALL report partial success with the admitted agent identity and execution context. It SHALL NOT create another agent to repair publication. Explicit reconciliation through the authorized owner route SHALL be able to recover and publish that agent's locator without repeating birth.

#### Scenario: Operator cannot publish after owner launch

- **WHEN** owner launch completes but the operator registry cannot accept the returned locator
- **THEN** the result identifies the admitted agent and reports failed locator publication
- **AND THEN** the existing owner agent remains the recovery target without an automatic second launch

#### Scenario: Explicit reconciliation repairs only the routing locator

- **WHEN** the operator explicitly reconciles an admitted agent through its authorized owner route
- **THEN** Houmao verifies that owner's agent identity and binding before publishing the locator
- **AND THEN** it does not repeat launch or replace the owner runtime state

