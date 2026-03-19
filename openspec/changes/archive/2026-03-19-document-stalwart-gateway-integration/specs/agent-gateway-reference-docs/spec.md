## ADDED Requirements

### Requirement: Gateway reference documentation covers the shared mailbox facade
The agent gateway reference documentation SHALL document the gateway mailbox facade as a first-class gateway surface rather than leaving mailbox-gateway interaction implicit inside low-level contract pages alone.

At minimum, the gateway reference SHALL explain:

- that `/v1/mail/*` is the shared mailbox surface for supported mailbox operations,
- how the gateway resolves mailbox capability from `attach.json` to the runtime-managed session manifest,
- that the gateway constructs a transport-specific mailbox adapter behind one shared gateway-facing contract,
- that the facade may serve either filesystem-backed or Stalwart-backed sessions,
- that direct transport-specific mailbox behavior may still exist when no live gateway is attached.

The gateway reference SHALL provide an operator-facing or maintainer-facing page under the gateway subtree that introduces this mailbox facade before or alongside the exact route contract page.

#### Scenario: Reader finds mailbox facade guidance from the gateway subtree
- **WHEN** a reader opens the gateway reference to understand current gateway capabilities
- **THEN** the gateway docs make the mailbox facade discoverable from the gateway entry path
- **AND THEN** the reader can reach a page that explains why `/v1/mail/*` exists and how it relates to manifest-backed adapter resolution

#### Scenario: Gateway docs explain transport-backed mailbox adaptation
- **WHEN** a maintainer uses the gateway reference to understand mailbox behavior for attached sessions
- **THEN** the gateway docs explain that the shared mailbox routes are backed by transport-specific adapters resolved from the attached session metadata
- **AND THEN** the docs do not describe the shared gateway contract as if it were hard-wired to the filesystem transport alone

### Requirement: Gateway reference documentation explains current mailbox facade boundaries
The agent gateway reference documentation SHALL explain the current scope and boundaries of the mailbox facade in implemented v1 behavior.

At minimum, that boundary guidance SHALL explain:

- that `/v1/mail/*` remains available only for loopback-bound live gateway listeners,
- that mailbox-facade availability is separate from the existence of stable gateway-capability metadata,
- that mailbox notifier polling reads unread state through the same mailbox facade instead of a transport-local side channel,
- where the gateway reference should defer to the mailbox reference for mailbox semantics and to the system-files reference for broader filesystem placement.

#### Scenario: Reader can distinguish gateway capability from live mailbox-facade availability
- **WHEN** a reader needs to understand why a session is gateway-capable but does not currently expose mailbox routes
- **THEN** the gateway docs explain the difference between stable attachability metadata and a live loopback-bound gateway listener
- **AND THEN** the reader can tell when `/v1/mail/*` is actually available

#### Scenario: Gateway docs explain notifier behavior through the shared mailbox facade
- **WHEN** a maintainer reads the gateway docs to understand mailbox notifier behavior
- **THEN** the docs explain that notifier unread checks use the same shared mailbox facade used for mailbox reads
- **AND THEN** the docs do not present filesystem mailbox-local SQLite polling as the universal notifier contract
