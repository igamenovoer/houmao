## Purpose
Define the repository-owned local email-system stack for development mail workflows using Stalwart, Postgres, and Cypht.

## Requirements

### Requirement: Repository-owned local email stack
The repository SHALL provide a local Docker-based email stack under `dockers/email-system/` that is sufficient to start Stalwart, Postgres, and Cypht together for local mail usage.

The repo-owned stack materials SHALL include the compose entry point plus the operator-facing configuration and documentation needed to start the stack from repository context.

Normal stack bring-up SHALL rely on the required images already being present on the host and SHALL NOT pull or check remote registries as part of startup.

#### Scenario: Operator starts the local email stack from repository-owned files
- **WHEN** an operator follows the documented local email-system workflow
- **THEN** the repository provides the compose and configuration assets under `dockers/email-system/` needed to start Stalwart, Postgres, and Cypht together
- **AND THEN** the operator does not need to assemble the stack from ad hoc host-local commands outside the repository

#### Scenario: Operator starts the stack with the required images already loaded locally
- **WHEN** the required Stalwart, Postgres, and Cypht images are already present on the host
- **THEN** the documented compose bring-up path starts the stack without pulling or checking remote registries
- **AND THEN** local image presence is treated as a prerequisite rather than something normal startup resolves by network fetch

### Requirement: Stack configuration is centralized in `.env` and `env.example`
The local email stack SHALL provide `dockers/email-system/.env` and `dockers/email-system/env.example`.

The tracked `env.example` SHALL enumerate every stack value intended to be configurable.

The active `.env` file in the compose directory SHALL be the local source for those configurable values during normal stack bring-up.

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
The local email stack SHALL avoid privileged ports entirely.

Every stack-defined listener port and inter-service connection target SHALL use a port number `>=10000`.

That requirement SHALL apply to at least:

- Stalwart admin/API access,
- Stalwart IMAP access used by Cypht,
- Stalwart SMTP submission used by Cypht,
- the Cypht web UI listener,
- the Postgres listener used by Cypht.

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
The stack SHALL configure Cypht as a Stalwart-backed mail client rather than an account-administration surface.

Cypht SHALL:

- use the stack's Postgres service for its own persistent application database,
- authenticate users against Stalwart IMAP,
- use Stalwart for default outbound SMTP submission,
- run in single-server mode so the Stalwart-backed mailbox is the one mail source exposed by the stack,
- auto-create a usable default profile for a mailbox user after successful login.

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

Where username/password authentication is required by the stack, the default credentials SHALL be `admin` / `admin` unless a protocol requires the username to be represented differently for the same seeded identity.

The stack SHALL NOT require generated one-time admin passwords, secret injection, or additional auth layers as prerequisites for first local bring-up.

#### Scenario: Operator accesses authenticated stack services during initial bring-up
- **WHEN** the operator follows the default development workflow for the local email stack
- **THEN** Stalwart admin access and Postgres database authentication use `admin` / `admin` defaults
- **AND THEN** the operator does not need to retrieve generated secrets before bringing the stack into a usable state

#### Scenario: Operator logs into Cypht during initial bring-up
- **WHEN** the operator signs into Cypht using the default seeded Stalwart-backed mailbox identity
- **THEN** the development login flow uses the same low-friction `admin` / `admin` credential convention for that seeded mailbox identity
- **AND THEN** Cypht does not require a separate Cypht-local password distinct from the Stalwart-backed mailbox login

### Requirement: Mail account provisioning uses Stalwart's management API
The local email stack SHALL include a repeatable provisioning workflow that uses Stalwart's management API to manage the mail domain and mailbox accounts needed by the stack.

That workflow SHALL support domain creation or confirmation plus mailbox-principal creation for individual users, and it SHALL be designed so operators can rerun it without creating duplicate resources unintentionally.

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
