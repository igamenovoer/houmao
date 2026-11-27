# Spec Delta

## ADDED Requirements

### Requirement: Managed Hermes Records Its Profile Home and Project Link

Houmao SHALL record the execution context, prepared Hermes root, native profile identity, canonical home, and project-local home link in its owned build and runtime binding. Native launches SHALL use the canonical profile. Houmao SHALL manage the link as a separate project artifact.

#### Scenario: A Project Launch Creates a Named Profile

- **WHEN** the normal project launch resolves a new managed Hermes identity and a prepared execution-owner root
- **THEN** it reserves a unique native profile under that root and projects the selected launch inputs into that profile
- **AND THEN** its project runtime home path is a symlink to the canonical profile and native launch and self resolution use the recorded profile binding
- **AND THEN** tool execution uses the independently selected project workspace

#### Scenario: A Profile or Link Conflicts With Another Owner

- **WHEN** the selected profile already belongs to another agent, the canonical target escapes the prepared root, or the project link path is occupied by an unrelated artifact
- **THEN** launch refuses with an actionable ownership conflict before overwriting the artifact or replacing a running agent

#### Scenario: A Preserved Home Is Reused

- **WHEN** an authorized start or relaunch selects a compatible preserved named-profile home
- **THEN** it verifies the exact recorded owner, root, and profile and reuses that canonical home
- **AND THEN** it validates or restores the owned project link and publishes a fresh managed generation after native readiness

#### Scenario: A Clean Replacement Discards One Profile

- **WHEN** an operator requests clean replacement of a managed named-profile worker
- **THEN** Houmao verifies that worker's selected installation and replacement authority before retiring it
- **AND THEN** it settles the predecessor's profile lifecycle and removes only its authorized profile and project link before publishing the replacement

#### Scenario: Failed Startup Leaves No Admitted Worker

- **WHEN** startup fails after allocating a profile, a project link, or a managed client
- **THEN** rollback releases those acquired artifacts when their recorded ownership and quiescence can be verified
- **AND THEN** an unresolved cleanup keeps the scoped evidence and reports partial rollback without publishing successful runtime authority
