## Purpose
Define the repository-owned local email-system stack for development mail workflows using Stalwart, Postgres, and Cypht.

## Requirements

### Requirement: Repository-owned local email stack
The repository SHALL provide a local Docker-based email stack under `dockers/email-system/` that is sufficient to start Stalwart, Postgres, and Cypht together for local mail usage.

The repo-owned stack materials SHALL include the compose entry point plus the operator-facing configuration and documentation needed to start the stack from repository context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Normal stack bring-up SHALL rely on the required images already being present on the host and SHALL NOT pull or check remote registries as part of startup.

The startup wrapper SHALL offer an explicit first-run option to pull the configured images that are missing before normal Compose startup.

#### Scenario: Operator starts the local email stack from repository-owned files
- **WHEN** an operator follows the documented local email-system workflow
- **THEN** the repository provides the compose and configuration assets under `dockers/email-system/` needed to start Stalwart, Postgres, and Cypht together
- **AND THEN** the operator does not need to assemble the stack from ad hoc host-local commands outside the repository

#### Scenario: Operator starts the stack with the required images already loaded locally
- **WHEN** the required Stalwart, Postgres, and Cypht images are already present on the host
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

### Requirement: Stack ports use only non-privileged high ports
Every stack-defined port SHALL be `>=10000`, including Stalwart HTTP, IMAP, and SMTP submission, Cypht HTTP, and Postgres. Published ports SHALL bind to host loopback. The default management API and Webadmin ports SHALL be `10080` and `10082`, respectively.

#### Scenario: Operator inspects the configured stack ports
- **WHEN** an operator reviews the compose configuration and repo-owned service config for the local email stack
- **THEN** every configured listener port and mapped service port used by the stack is `>=10000`
- **AND THEN** the stack does not depend on privileged or sub-10000 ports anywhere in its repo-owned configuration

#### Scenario: Cypht connects to Stalwart and Postgres on high ports
- **WHEN** Cypht starts inside the local email stack
- **THEN** its configured IMAP, SMTP, and Postgres connection targets all use ports `>=10000`
- **AND THEN** Cypht does not depend on upstream low-port defaults for those services

### Requirement: Stack runtime state is kept under `dockers/email-system/.data`
The local email stack SHALL persist service-owned mutable state under `dockers/email-system/.data/`.

At minimum, the stack SHALL persist Stalwart server state, Postgres database state for Cypht, and Cypht's file-backed user data and attachments through paths rooted under `dockers/email-system/.data/`.

The repository SHALL ignore `dockers/email-system/.data/` from Git so stack runtime state is not tracked as repository content.

#### Scenario: First boot creates service state in the temp runtime root
- **WHEN** an operator starts the local email stack for the first time
- **THEN** Stalwart, Postgres, and Cypht initialize their writable state through bind-mounted paths rooted under `dockers/email-system/.data/`
- **AND THEN** the repo-owned stack files remain configuration-only artifacts rather than mixed code-and-data directories

#### Scenario: Operator resets the local mail environment
- **WHEN** an operator intentionally clears `dockers/email-system/.data/` after stopping the stack
- **THEN** the next startup rebuilds the local mail environment from the repo-owned stack configuration
- **AND THEN** no additional hidden runtime state outside `dockers/email-system/.data/` is required for a clean reset

#### Scenario: Git does not track stack runtime state
- **WHEN** runtime files are created under `dockers/email-system/.data/`
- **THEN** the repository ignore rules exclude those files from Git tracking
- **AND THEN** developers do not need to clean runtime data out of normal source control changes

### Requirement: Cypht acts only as the Stalwart-backed mail client
The stack SHALL configure Cypht as the Stalwart-backed webmail client.

Cypht SHALL:

- persist its application data in the stack's Postgres service,
- use plain connections to Stalwart IMAP for authentication and Stalwart SMTP for submission on the private Compose network,
- run in single-server mode,
- create a default sender profile after login.

#### Scenario: Cypht boots against the stack-managed Postgres database
- **WHEN** the local email stack starts Cypht
- **THEN** Cypht initializes and uses the stack-managed Postgres database for its own application persistence
- **AND THEN** the stack does not require a separate SQLite database file for Cypht state

#### Scenario: Mailbox user logs into Cypht with Stalwart credentials
- **WHEN** a mailbox account exists in Stalwart and the user signs into Cypht with that mailbox username and password
- **THEN** Cypht authenticates the login against Stalwart IMAP
- **AND THEN** the user's default inbound and outbound mail configuration points at the same Stalwart-backed mailbox identity

#### Scenario: Cypht is not used to provision accounts
- **WHEN** an operator needs to create or modify mailbox accounts for the stack
- **THEN** the documented workflow directs that work to Stalwart administration or Stalwart API helpers rather than to Cypht UI features
- **AND THEN** Cypht remains limited to reading and sending mail for already-provisioned accounts

### Requirement: Development defaults minimize authentication friction
The local email stack SHALL use development-only low-friction authentication defaults.

The default username and password for Postgres and the Stalwart admin mailbox SHALL both be `admin`. The Stalwart operator mailbox SHALL use username `houmao-operator` and password `admin` by default.

The stack SHALL NOT require generated one-time admin passwords, secret injection, or additional auth layers as prerequisites for first local bring-up.

#### Scenario: Operator accesses authenticated stack services during initial bring-up
- **WHEN** the operator follows the default development workflow for the local email stack
- **THEN** Stalwart admin access and Postgres database authentication use `admin` / `admin` defaults
- **AND THEN** the operator does not need to retrieve generated secrets before bringing the stack into a usable state

#### Scenario: Operator logs into Cypht during initial bring-up
- **WHEN** the operator signs into Cypht using the default seeded Stalwart-backed mailbox identity
- **THEN** the development login flow uses the same low-friction `admin` / `admin` credential convention for that seeded mailbox identity
- **AND THEN** Cypht does not require a separate Cypht-local password distinct from the Stalwart-backed mailbox login

#### Scenario: Developer signs into the operator mailbox
- **WHEN** a developer signs into Cypht as `houmao-operator` with the default password `admin`
- **THEN** Cypht opens the operator mailbox on the configured domain

### Requirement: Mail account provisioning uses Stalwart's management API
The stack SHALL use Stalwart's management API to ensure the configured domain and individual mailboxes. Reruns SHALL reuse existing principals. Fresh setup SHALL default to `houmao.localhost` with `admin@houmao.localhost` and `houmao-operator@houmao.localhost`. The operator address SHALL use the configured domain.

#### Scenario: Operator provisions the initial mail domain and first mailbox account
- **WHEN** the operator runs the documented Stalwart provisioning workflow for a new local mail domain and mailbox user
- **THEN** the workflow uses Stalwart's management API to ensure the domain exists and create the mailbox principal
- **AND THEN** the resulting mailbox credentials can be used to sign into Cypht

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
