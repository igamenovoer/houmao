# Spec Delta

## ADDED Requirements

### Requirement: Bundled Stalwart advertises the published loopback JMAP origin
JMAP discovery on the bundled stack SHALL advertise API and upload URLs on the published `127.0.0.1` origin and its configured Stalwart HTTP port. Stack verification SHALL check those advertised origins through the host's discovery endpoint. The Webadmin alias SHALL remain usable on its configured browser port.

#### Scenario: Fresh checkout exposes a direct JMAP endpoint
- **WHEN** a developer brings up the stack with defaults
- **THEN** discovery via `http://127.0.0.1:10080/.well-known/jmap` advertises API and upload URLs at `http://127.0.0.1:10080`
- **AND THEN** the developer can use a suitably provisioned normal account under the default origin policy

#### Scenario: A custom host port is advertised
- **WHEN** the developer sets a different Stalwart HTTP port in the active stack environment
- **THEN** verification checks that discovery advertises the configured port for JMAP requests and uploads

### Requirement: Bundled stack docs provide a send-capable JMAP sandbox path
The setup guide SHALL document the seeded `houmao.localhost` Cypht, IMAP, and SMTP mailboxes and an explicit provisioning path for JMAP test accounts on a domain that the pinned Stalwart release accepts for sending identities.

#### Scenario: Developer prepares accounts for agent mail verification
- **WHEN** a developer follows the online JMAP mail test setup
- **THEN** the guide identifies an explicitly selected sandbox domain, normal mailbox credentials, and the direct discovery endpoint
- **AND THEN** the seeded administrator and operator accounts remain available for the local webmail workflow
