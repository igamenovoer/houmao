# Spec Delta

## ADDED Requirements

### Requirement: The Workbench Uses the Local Operator's Signing Key

For signed Houmao AG-UI access, the loopback workbench SHALL use the local operator's configured SSH signer for the verified target. It SHALL authorize an ephemeral operator session before signing or exposing host bridges with local authority. It SHALL keep gateway credential material and proof headers server-side and bind proof to the exact outbound request.

#### Scenario: Operators have different grants on one gateway

- **WHEN** Alice uses her local workbench to observe an agent and Bob uses his local workbench to start runs on the same agent
- **THEN** the gateway evaluates their requests under their respective enrolled keys
- **AND THEN** an operator with observation permission alone cannot use the workbench to start a run

#### Scenario: A loopback caller lacks the operator session

- **WHEN** another browser or local process invokes a signing operation without current operator session authority
- **THEN** the workbench refuses the request before selecting or using a signer

#### Scenario: Proxy content reaches the signed-mode frontend

- **WHEN** a generic proxy target returns executable content or server credentials
- **THEN** the workbench keeps that response out of the executable signing origin and prevents credentials from reaching the browser session

#### Scenario: The selected proof is unavailable or denied

- **WHEN** an explicitly selected signer cannot prove an operation or the gateway refuses it
- **THEN** the workbench returns the applicable error without dispatching under a different signer or retrying the operation unsigned

### Requirement: Signed Workbench Requests Use a Verified Target Binding

The workbench SHALL sign supported AG-UI operations for an explicitly approved target identity and trusted endpoint source. It SHALL verify the live listener and origin before signing and refuse redirects. Generic fetch and unapproved manual endpoints SHALL receive no operator proof. Supported unsigned AG-UI operations SHALL remain available.

#### Scenario: A manual destination differs from the enrolled target

- **WHEN** a pane points at a manually entered URL outside the signer binding or the gateway reports a conflicting identity
- **THEN** the workbench selects no signer for that endpoint and returns a safe diagnostic when proof is required

#### Scenario: A discovered agent reconnects to its live gateway

- **WHEN** an agent pane resolves a live replacement listener for the same approved target
- **THEN** the workbench verifies the new listener and its authorized origin before creating fresh proof

#### Scenario: An operator connects to an open gateway

- **WHEN** the operator selects a verified open gateway without selecting a signer
- **THEN** the workbench sends an unsigned request and current gateway policy determines access
