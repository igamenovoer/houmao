# Agent Gateway Reference Docs Delta

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
- **THEN** the reference explains that enrolled administrators and callers under a valid empty roster can use every supported mailbox action on the selected binding
- **AND THEN** it documents distinct grants for keyed non-admins, including operator-origin post, binding controls, and owner-local attachment paths, along with the path validation that applies to every caller

### Requirement: Gateway reference documents access classes and public handoff

The gateway reference SHALL explain policy decisions for verified callers, target domains, resources, and actions. It SHALL describe endpoint-bound signing and verified remote transport. It SHALL document public notifications and prompts, policy labeling, handoff-only responses, and permitted reply channels.

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
- **THEN** the reference explains `admin_mode`, supported proof and challenge information, enabled public actions, and the limits of cached discovery

#### Scenario: Operator grants one operation to an enrolled caller

- **WHEN** a reader wants to authorize a caller for one operation on a selected agent
- **THEN** the reference shows how to select the principal, target domain, resource, and action
- **AND THEN** it explains the distinct authority for local execution, scoped peer actions, and configured service identities

#### Scenario: Operator enrolls a peer under a different account

- **WHEN** the source agent is stopped or runs under another OS account
- **THEN** the reference shows how the target owner enrolls its approved logical identity and public key
- **AND THEN** the example explains that source placement and relaunch do not change the grant, while key revocation or replacement changes usable proof

### Requirement: Gateway reference documents admin enrollment and live membership

The gateway reference SHALL document initial owner provisioning, first-key registration, the SSHSIG challenge, and per-key admin enrollment and removal. It SHALL explain that a valid empty roster opens the full target-domain gateway-admin role and that unavailable policy fails closed.

#### Scenario: Admin enrolls after a keyless launch

- **WHEN** a reader follows post-start enrollment guidance for a gateway initialized with no keys
- **THEN** the example signs the first-key challenge and shows how enrolled callers prove their identity for allowed operations

#### Scenario: Admin considers removing the last key

- **WHEN** a reader follows the removal workflow
- **THEN** the documented outcome explains that every supported client-facing action in the target domain reopens, including owner-file mail attachments and installed plugin actions
- **AND THEN** it explains that owner-local policy administration, OS ownership, internal service identities, and each operation's ordinary guards retain their own requirements

#### Scenario: An operator rotates the only administrator key

- **WHEN** a reader wants to replace the final administrator key while the target stays keyed
- **THEN** the reference shows enrolling the replacement as admin before removing the old admin entry
- **AND THEN** it explains that ordinary keys do not keep a target keyed and distinguishes admin removal from credential revocation

#### Scenario: Operator compares open and keyed access

- **WHEN** a reader evaluates the effect of enrolling the first administrator
- **THEN** the reference explains that the enrolled administrator retains the same target-domain permissions that every caller had under the valid empty roster
- **AND THEN** it shows that a keyed non-admin can use its scoped grants and receives a refusal for actions outside its effective permissions

#### Scenario: Operator upgrades a gateway with an empty roster

- **WHEN** a reader checks the effect of upgrading a keyless gateway
- **THEN** the reference explains how to manually initialize current owner policy with the intended administrators or a deliberately empty roster
- **AND THEN** it explains that older authorization formats fail closed and require operator reprovisioning and updates to clients and plugins

### Requirement: Gateway reference documents owner-local Web browser entry

The gateway reference SHALL document immediate open-mode entry, keyed terminal login, and open or signed ticket issuance through the API and scoped CLI. It SHALL explain selection of an enrolled signer with `web.enter` permission, bearer handling, expiry, owner-loopback reachability, and the native provider's responsibility for authenticated browser sessions.

#### Scenario: An operator follows the Web entry instructions

- **WHEN** a reader needs to open a live managed Web agent in keyed mode
- **THEN** the reference shows how to open the bare entry URL, optionally select a local key file, and run the generated command with `ssh-keygen` and `curl`
- **AND THEN** it describes trusted endpoint review, blank-path SSH agent selection, automatic browser continuation, and starting again after expiry
- **AND THEN** it explains trimming of surrounding whitespace and SSH-agent selection when trimming leaves the field empty

#### Scenario: A script requests a Web entry ticket

- **WHEN** a reader follows the API or scoped CLI workflow
- **THEN** the reference shows how to obtain a one-time link unsigned in open mode and with proof from an enrolled signer authorized for `web.enter` in keyed mode
- **AND THEN** it tells the operator to keep the link private and explains native session selection after redemption

#### Scenario: The browser runs outside the execution context

- **WHEN** a reader configures access from another machine or network namespace
- **THEN** the reference explains the required gateway and native loopback forwards with exact addresses and ports, including the terminal callback's gateway address
- **AND THEN** it distinguishes this workflow from the advertised HTTPS gateway and explains that native session lifetime follows provider policy

#### Scenario: An operator opens a gateway with no keys

- **WHEN** a reader follows the bare owner-local entry URL for a live Web agent with a valid empty roster
- **THEN** the reference describes immediate entry into the native UI without an interactive sign-in step

### Requirement: Gateway reference documents the operator dashboard

The gateway reference SHALL show how to find the live gateway address and open its dashboard at the base URL. It SHALL explain the displayed summary, when the Web action appears, and how to reach an owner-local gateway from another execution context.

#### Scenario: An operator looks for a live Web agent

- **WHEN** a reader follows the dashboard instructions
- **THEN** the reference gives an owner-local URL example and explains immediate entry in verified open mode and sign-in with an enrolled signer authorized for Web entry in keyed mode

#### Scenario: An operator opens the dashboard through the advertised address

- **WHEN** a reader needs Web entry from an advertised proxy deployment
- **THEN** the reference explains the owner-local connection or private TCP forwards needed for browser entry
