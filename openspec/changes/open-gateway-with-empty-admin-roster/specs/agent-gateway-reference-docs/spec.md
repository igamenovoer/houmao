# agent-gateway-reference-docs Delta

## MODIFIED Requirements

### Requirement: Gateway reference documentation explains current mailbox facade boundaries

The gateway reference SHALL explain the v1 mailbox facade's caller authority, live availability, and role in notifier polling. It SHALL link to the mailbox reference for mailbox semantics and to the system-files reference for file placement.

#### Scenario: Reader can distinguish gateway capability from live mailbox-facade availability

- **WHEN** a reader needs to understand why a session is gateway-capable but does not currently expose mailbox routes
- **THEN** the gateway docs explain the difference between stable attachability metadata and a live gateway endpoint
- **AND THEN** the reader can identify the binding and caller requirements for `/v1/mail/*` in the current deployment

#### Scenario: Gateway docs explain notifier behavior through the shared mailbox facade

- **WHEN** a maintainer reads the gateway docs to understand mailbox notifier behavior
- **THEN** the docs explain that notifier unread checks use the same shared mailbox facade used for mailbox reads
- **AND THEN** the docs describe transport-specific state through the mailbox reference

#### Scenario: Reader Can Determine Mailbox Caller Authority
- **WHEN** a reader checks which authorization a mailbox operation requires
- **THEN** the reference explains anonymous mailbox access with a valid empty roster and the private route proof rule once keys are enrolled
- **AND THEN** it documents the live admin rule for operator-origin post, binding controls, and owner-local attachment paths

### Requirement: Gateway reference documents access classes and public handoff

The gateway reference SHALL explain route access under open, keyed, and unavailable policy. It SHALL describe endpoint-bound signing and verified remote transport. It SHALL document public notifications and prompts, policy labeling, handoff-only responses, and permitted reply channels.

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

#### Scenario: Operator reads endpoint access metadata

- **WHEN** a reader inspects the live gateway descriptor
- **THEN** the reference explains the effective admin and private proof values and the role of cached discovery

### Requirement: Gateway reference documents admin enrollment and live membership

The gateway reference SHALL document zero or more launch keys, post-start first registration, SSH signature challenges, and live addition and removal. It SHALL explain that a valid empty list opens enabled private and admin routes, removing the final key restores open access, and unavailable policy fails closed.

#### Scenario: Admin enrolls after a keyless launch

- **WHEN** a reader follows post-start enrollment guidance for a gateway initialized with no keys
- **THEN** the example signs the first-key challenge and shows later admin and private proof requirements

#### Scenario: Admin considers removing the last key

- **WHEN** a reader follows the removal workflow
- **THEN** the documented outcome makes clear that the final removal opens enabled operations to anyone who can reach them

#### Scenario: Operator upgrades a gateway with an empty roster

- **WHEN** a reader checks the effect of upgrading a keyless gateway
- **THEN** the reference explains the wider access and how to enroll a key for proof-required operation

### Requirement: Gateway reference documents owner-local Web browser entry

The gateway reference SHALL document immediate open-mode entry, keyed terminal login, and open or signed ticket issuance through the API and scoped CLI. It SHALL explain enrolled signer selection, bearer handling, expiry, owner-loopback reachability, and the native provider's responsibility for authenticated browser sessions.

#### Scenario: An operator follows the Web entry instructions

- **WHEN** a reader needs to open a live managed Web agent with registered admin keys
- **THEN** the reference shows how to open the bare entry URL, optionally select a local key file, and run the generated command with `ssh-keygen` and `curl`
- **AND THEN** it describes trusted endpoint review, blank-path SSH agent selection, automatic browser continuation, and starting again after expiry
- **AND THEN** it explains trimming of surrounding whitespace and SSH-agent selection when trimming leaves the field empty

#### Scenario: A script requests a Web entry ticket

- **WHEN** a reader follows the API or scoped CLI workflow
- **THEN** the reference shows how to obtain a one-time link unsigned in open mode and with enrolled admin proof in keyed mode
- **AND THEN** it tells the operator to keep the link private and explains native session selection after redemption

#### Scenario: The browser runs outside the execution context

- **WHEN** a reader configures access from another machine or network namespace
- **THEN** the reference explains the required gateway and native loopback forwards with exact addresses and ports, including the terminal callback's gateway address
- **AND THEN** it distinguishes this workflow from the advertised HTTPS gateway and explains that native session lifetime follows provider policy

#### Scenario: An operator opens a gateway with no keys

- **WHEN** a reader follows the bare owner-local entry URL for a live Web agent with a valid empty roster
- **THEN** the reference describes immediate entry into the native UI without an interactive sign-in step
