## Purpose
Define the repository-owned development email stack using Stalwart, a loopback JMAP proxy, and Bulwark Webmail.

## Requirements

### Requirement: Repository-owned local email stack
The repository SHALL provide a local Docker-based email stack under `dockers/email-system/` that starts Stalwart, the JMAP HTTP proxy, and Bulwark together for local mail usage.

The repo-owned stack materials SHALL include the compose entry point plus the operator-facing configuration and documentation needed to start the stack from repository context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Normal stack bring-up SHALL rely on the required images already being present on the host and SHALL NOT pull or check remote registries as part of startup.

The startup wrapper SHALL offer an explicit first-run option to pull the configured images that are missing before normal Compose startup.

#### Scenario: Operator starts the local email stack from repository-owned files
- **WHEN** an operator follows the documented local email-system workflow
- **THEN** the repository provides the compose and configuration assets under `dockers/email-system/` needed to start Stalwart, the JMAP proxy, and Bulwark together
- **AND THEN** the operator does not need to assemble the stack from ad hoc host-local commands outside the repository

#### Scenario: Operator starts the stack with the required images already loaded locally
- **WHEN** the configured Stalwart, JMAP proxy, and Bulwark images are already present on the host
- **THEN** the documented compose bring-up path starts the stack without pulling or checking remote registries
- **AND THEN** local image presence is treated as a prerequisite rather than something normal startup resolves by network fetch

#### Scenario: Developer sets up the stack on a fresh checkout
- **WHEN** a developer runs `dockers/email-system/up.sh --pull-missing-images`
- **THEN** the wrapper pulls the configured images that are missing locally
- **AND THEN** Compose starts from those local images

### Requirement: Stack configuration is centralized in `.env` and `env.example`
The local email stack SHALL provide `dockers/email-system/.env` and `dockers/email-system/env.example`.

The tracked `env.example` SHALL enumerate every stack value intended to be configurable.

The active `.env` file in the compose directory SHALL be the local source for those configurable values during normal stack bring-up.

The startup wrapper SHALL initialize a private `.env` from `env.example` when the active file is absent and SHALL use an existing `.env` as supplied.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Repo-owned compose files, helper scripts, and service config templates SHALL treat those env files as the configuration source rather than scattering independently configurable literals across multiple files.

#### Scenario: Operator inspects the configurable stack surface
- **WHEN** an operator reviews `dockers/email-system/env.example`
- **THEN** the file lists the stack values the operator is expected to configure
- **AND THEN** those values correspond to the settings consumed by compose and the repo-owned stack helpers

#### Scenario: Operator changes a configurable stack value
- **WHEN** an operator updates a supported configuration value in `dockers/email-system/.env`
- **THEN** the compose stack and repo-owned helper paths consume that updated value from the env file
- **AND THEN** the operator does not need to edit multiple unrelated repository files for one supported configuration change

### Requirement: Published stack ports use loopback high ports
Every published stack port SHALL bind to host loopback and use a port of at least `10000`. The default Stalwart management and JMAP HTTP port SHALL be `10080`, the Bulwark HTTP port `10081`, and the Stalwart Webadmin HTTPS port `10082`.

#### Scenario: Operator inspects the configured stack ports
- **WHEN** an operator reviews the compose configuration and repo-owned service config for the local email stack
- **THEN** every published host port uses loopback and a port of at least `10000`
- **AND THEN** the proxy reaches Bulwark through the internal loopback listener in their shared network namespace

#### Scenario: Browser clients connect through the published webmail listener
- **WHEN** a developer opens Bulwark at the configured webmail origin
- **THEN** the proxy serves the webmail interface and its Stalwart JMAP requests at that origin

### Requirement: Stack runtime state uses a bind mount and a named volume
The stack SHALL persist Stalwart server state in `dockers/email-system/.data/stalwart-v1/` and Bulwark application data in the Compose volume `bulwark-data`. The repository SHALL ignore `dockers/email-system/.data/`.

#### Scenario: First boot creates service state in the temp runtime root
- **WHEN** an operator starts the local email stack for the first time
- **THEN** Stalwart initializes its data directory through the bind mount and Bulwark initializes its application data in the named volume
- **AND THEN** the repo-owned stack files remain configuration-only artifacts rather than mixed code-and-data directories

#### Scenario: Operator resets the local mail environment
- **WHEN** an operator stops the stack and intentionally removes the Bulwark volume and Stalwart data directory through the documented reset procedure
- **THEN** the next startup rebuilds the local mail environment from the repo-owned stack configuration

#### Scenario: Git does not track stack runtime state
- **WHEN** runtime files are created under `dockers/email-system/.data/`
- **THEN** the repository ignore rules exclude those files from Git tracking
- **AND THEN** developers do not need to clean runtime data out of normal source control changes

### Requirement: Bulwark uses Stalwart JMAP for webmail
Bulwark SHALL use Stalwart for mailbox login and mail operations through JMAP on the published webmail origin. Stalwart SHALL own mailbox accounts, sending identities, and access to shared folders.

#### Scenario: Mailbox user signs into Bulwark with Stalwart credentials
- **WHEN** a provisioned mailbox user signs into Bulwark with the mailbox username and password
- **THEN** Bulwark authenticates against Stalwart JMAP and uses that mailbox for reading and sending

#### Scenario: Admin opens the operator shared inbox
- **WHEN** the seeded admin opens the operator inbox through Bulwark
- **THEN** Stalwart grants the configured read-only access and the message's read state remains under the operator mailbox's control

#### Scenario: Operator provisions a mailbox account
- **WHEN** an operator needs to create or modify mailbox accounts for the stack
- **THEN** the documented workflow directs that work to Stalwart administration or Stalwart API helpers

### Requirement: Development defaults minimize authentication friction
The local email stack SHALL use development-only low-friction authentication defaults.

The default username and password for the Stalwart admin mailbox SHALL both be `admin`. The Stalwart operator mailbox SHALL use username `houmao-operator` and password `admin` by default.

The stack SHALL NOT require generated one-time admin passwords, secret injection, or additional auth layers as prerequisites for first local bring-up.

#### Scenario: Operator accesses authenticated stack services during initial bring-up
- **WHEN** the operator follows the default development workflow for the local email stack
- **THEN** Stalwart Webadmin and Bulwark accept the seeded `admin` / `admin` mailbox credentials
- **AND THEN** the operator does not need to retrieve generated secrets before bringing the stack into a usable state

#### Scenario: Developer signs into the operator mailbox
- **WHEN** a developer signs into Bulwark as `houmao-operator` with the default password `admin`
- **THEN** Bulwark opens the operator mailbox on the configured domain using those Stalwart credentials

### Requirement: Mail account provisioning uses Stalwart's management API
The stack SHALL use Stalwart's management API to ensure the configured domain and individual mailboxes. Reruns SHALL reuse existing principals. Fresh setup SHALL default to `houmao.localhost` with `admin@houmao.localhost` and `houmao-operator@houmao.localhost`. The operator address SHALL use the configured domain.

#### Scenario: Operator provisions the initial mail domain and first mailbox account
- **WHEN** the operator runs the documented Stalwart provisioning workflow for a new local mail domain and mailbox user
- **THEN** the workflow uses Stalwart's management API to ensure the domain exists and create the mailbox principal
- **AND THEN** the resulting mailbox credentials can be used to sign into Bulwark

#### Scenario: Operator reruns provisioning for an existing mailbox account
- **WHEN** the operator reruns the provisioning workflow for a domain or mailbox account that already exists
- **THEN** the workflow detects or reconciles the existing Stalwart-managed resources instead of blindly creating duplicates
- **AND THEN** the stack remains usable without requiring a full reset of `dockers/email-system/.data/`

### Requirement: The stack is explicitly scoped to local development
The local email stack SHALL document itself as a local/development environment and SHALL NOT present itself as a production-ready internet mail deployment.

#### Scenario: Operator reads the stack bring-up documentation
- **WHEN** an operator follows the documentation for `dockers/email-system/`
- **THEN** the docs describe the stack as local/dev oriented
- **AND THEN** the docs avoid implying that DNS, TLS, MX delivery, credential hardening, or production hardening are fully handled by this change

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
The setup guide SHALL document access to the seeded `houmao.localhost` mailboxes through Bulwark, IMAP, and SMTP. It SHALL document explicit provisioning for JMAP test accounts on a domain that the pinned Stalwart release accepts for sending identities.

#### Scenario: Developer prepares accounts for agent mail verification
- **WHEN** a developer follows the online JMAP mail test setup
- **THEN** the guide identifies an explicitly selected sandbox domain, normal mailbox credentials, and the direct discovery endpoint
- **AND THEN** the seeded administrator and operator accounts remain available for the local webmail workflow
