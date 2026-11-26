# Native Agent Home Refresh Delta

## MODIFIED Requirements

### Requirement: Native Home Inspection Identifies the Active Agent Home

Home inspection SHALL report the resolved native home, its selector variable when known, and the selected active agent identity. It SHALL use current runtime authority without guessing from the caller's operating-system home, changing home contents, or starting execution. An active headless envelope between workers SHALL remain inspectable.

#### Scenario: Native Home Differs From the Caller Home
- **WHEN** an operator inspects an agent whose native home is `/runtime/worker-home` while the caller's home is `/home/operator`
- **THEN** the result identifies `/runtime/worker-home` and the selected agent
- **AND** it does not substitute the caller's home, project worktree, or session-artifact directory

#### Scenario: Headless Worker Is Between Turns
- **WHEN** an active managed headless envelope has no currently running provider worker
- **THEN** home inspection reports its authoritative native home without creating a worker or conversation

#### Scenario: Home Authority Is Unknown
- **WHEN** a target has no verified native-home selection in its active runtime
- **THEN** inspection returns an explicit unsupported or unavailable result without selecting an ambient home

#### Scenario: Inspection Leaves Private Material Unread
- **WHEN** an authorized caller inspects a native home containing credentials
- **THEN** the home descriptor reports no configuration contents, credential values, or environment dump
- **AND** home inspection leaves that material unread and unchanged

### Requirement: Common Control Retains Target and Privacy Boundaries

Home/common inspection and refresh SHALL bind to one active locally managed agent. Managed actions SHALL NOT mutate another managed agent's home, shared package installation, or unrelated execution. Missing, ambiguous, stopped, replaced, retired adopted, or external communication-only targets SHALL fail without adoption or recovery. Diagnostics SHALL exclude private material.

#### Scenario: Two Managed Agents Have Distinct Homes
- **WHEN** one of two managed agents in the same project is refreshed after external edits
- **THEN** its broad native operation remains within its owned execution scope
- **AND** the other managed agent's home, process, conversation, and resources remain unchanged

#### Scenario: Target Disappears
- **WHEN** the captured runtime stops or is replaced before native handoff
- **THEN** the request fails or reports uncertainty for that identity without reviving or retargeting execution

#### Scenario: Native Failure Contains Secrets
- **WHEN** a native error contains raw configuration, provider exceptions, or credentials
- **THEN** common results retain only safe reasons and effect evidence
- **AND** no private skill body, configuration document, credential value, or credential-derived fingerprint is published

#### Scenario: Retired Adoption Cannot Supply Home Authority
- **WHEN** a home inspection or refresh selects a retired adopted runtime with a saved native home
- **THEN** Houmao refuses the retired target without inspecting the home or initiating native refresh
- **AND THEN** the provider process and home contents remain intact
