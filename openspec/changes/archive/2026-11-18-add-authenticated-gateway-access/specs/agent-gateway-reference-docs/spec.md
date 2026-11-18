# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway reference documentation explains current mailbox facade boundaries

The agent gateway reference documentation SHALL explain the current scope and boundaries of the mailbox facade in implemented v1 behavior.

At minimum, that boundary guidance SHALL explain how:

- `/v1/mail/*` uses current self or admin authorization on loopback and remote listeners
- operator-origin post and mailbox binding controls follow the live admin access rule, and owner-local attachment paths on private forms require verified admin proof
- live mailbox-facade availability differs from stable gateway-capability metadata
- mailbox notifier polling reads unread state through the same mailbox facade
- the gateway reference links to the mailbox reference for mailbox semantics and to the system-files reference for filesystem placement

#### Scenario: Reader can distinguish gateway capability from live mailbox-facade availability

- **WHEN** a reader needs to understand why a session is gateway-capable but does not currently expose mailbox routes
- **THEN** the gateway docs explain the difference between stable attachability metadata and a live gateway endpoint
- **AND THEN** the reader can identify the binding and caller requirements for `/v1/mail/*` in the current deployment

#### Scenario: Gateway docs explain notifier behavior through the shared mailbox facade

- **WHEN** a maintainer reads the gateway docs to understand mailbox notifier behavior
- **THEN** the docs explain that notifier unread checks use the same shared mailbox facade used for mailbox reads
- **AND THEN** the docs describe transport-specific state through the mailbox reference

## ADDED Requirements

### Requirement: Gateway reference documents access classes and public handoff

The gateway reference SHALL explain public, private, and admin access, endpoint-bound signed self and admin proof, and verified remote transport. It SHALL document public notifications and prompts, policy labeling, handoff-only responses, and permitted reply channels.

#### Scenario: Caller wants to use a public prompt

- **WHEN** a reader follows the public prompt example
- **THEN** the example identifies the expected HTTP handoff result and shows how to request a separate policy-permitted reply

#### Scenario: Operator deploys with private certificate trust

- **WHEN** a reader configures a gateway across hosts using deployment-provisioned trust
- **THEN** the reference explains the bind, connect, and advertised addresses, endpoint certificate verification, and independent caller credential selection

#### Scenario: Managed agent needs to use its private gateway

- **WHEN** a reader follows the agent's private mailbox example
- **THEN** it uses a scoped `houmao-mgr agents self ...` command that handles the signed challenge internally
- **AND** the example keeps the key and proof out of agent-visible instructions

### Requirement: Gateway reference documents admin enrollment and live membership

The gateway reference SHALL document zero or more launch keys, post-start first registration, SSH signature challenges, and live addition and removal. It SHALL explain that a valid empty list opens admin routes, removing the final key restores that access, and triggering a policy error cannot open a gateway.

#### Scenario: Admin enrolls after a keyless launch

- **WHEN** a reader follows post-start enrollment guidance for a gateway initialized with no keys
- **THEN** the example signs the first-key challenge and shows later admin and private proof requirements

#### Scenario: Admin considers removing the last key

- **WHEN** a reader follows the removal workflow
- **THEN** the documented outcome makes clear that the final removal opens admin operations to anyone who can reach the listener
