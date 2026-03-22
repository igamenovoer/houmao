# filestash-dev-helper Specification

## Purpose
Define the repository-owned Filestash development helper stack, including its runtime state layout, default access flow, and development-only documentation contract.

## Requirements

### Requirement: Repository-owned Filestash helper stack
The repository SHALL provide a local Docker-based Filestash helper stack under `dockers/dev-helpers/filestash/` that is sufficient to start a repository artifact browser from repository context.

The repo-owned stack materials SHALL include the compose entry point plus the operator-facing scripts, seed configuration, and documentation needed to start, stop, verify, and reset the helper.

#### Scenario: Operator starts the Filestash helper from repository-owned files
- **WHEN** an operator follows the documented Filestash helper workflow
- **THEN** the repository provides the compose and helper assets under `dockers/dev-helpers/filestash/` needed to start the local Filestash service
- **AND THEN** the operator does not need to assemble the helper from ad hoc one-off Docker commands outside the repository

### Requirement: Normal startup treats the upstream image as a local prerequisite
The Filestash helper SHALL use the upstream published Filestash image `machines/filestash:latest` embedded in the repo-owned helper stack.

Normal helper bring-up SHALL rely on that image already being present on the host and SHALL NOT pull from remote registries as part of standard startup.

#### Scenario: Operator starts the helper with the required image already loaded locally
- **WHEN** the configured Filestash image is already present on the host
- **THEN** the documented helper bring-up path starts the service without pulling or checking remote registries
- **AND THEN** host-local image presence is treated as a prerequisite rather than something routine startup resolves by network fetch

### Requirement: Helper runtime state lives under `.data`
The Filestash helper SHALL persist mutable runtime state under `dockers/dev-helpers/filestash/.data/`.

At minimum, the helper SHALL keep its writable Filestash config, logs, and other mutable application state under that runtime root, and repository ignore rules SHALL exclude that runtime state from Git tracking.

The documented startup path SHALL prepare the runtime state path so the Filestash container can write to it successfully.

#### Scenario: First boot creates writable runtime state under the helper directory
- **WHEN** an operator starts the Filestash helper for the first time
- **THEN** the service initializes its writable state through paths rooted under `dockers/dev-helpers/filestash/.data/`
- **AND THEN** the repo-owned helper files remain configuration and orchestration assets rather than mixed code-and-runtime-data directories

#### Scenario: Operator resets the helper by clearing `.data`
- **WHEN** an operator intentionally removes `dockers/dev-helpers/filestash/.data/` after stopping the helper
- **THEN** the next startup rebuilds the helper state from the repo-owned helper configuration
- **AND THEN** no hidden writable state outside the documented `.data/` root is required for a clean local reset

### Requirement: Helper exposes the repository as a default read-only browse surface
The Filestash helper SHALL bind-mount the repository into the container as a read-only filesystem and SHALL expose that mounted repository root as the default browsing surface for the operator.

The default browsing flow SHALL NOT require the operator to type an internal container path such as `/repo` manually.

The default repository browser view SHALL make hidden files visible so the helper can be used to inspect the full repository tree rather than only non-dotfile content.

#### Scenario: Operator lands in the mounted repository root after authenticating
- **WHEN** the operator follows the documented helper access flow successfully
- **THEN** the operator is placed in the mounted repository root exposed by the helper
- **AND THEN** the operator does not need to enter a container-internal path manually to start browsing the repository

#### Scenario: Hidden repository files are visible in the default browser view
- **WHEN** the operator browses a repository directory that contains dotfiles
- **THEN** the helper shows those hidden files in the default view
- **AND THEN** the helper supports inspection of the full repository tree rather than only non-hidden files

### Requirement: Helper access is deterministic, loopback-only, and low-friction
The Filestash helper SHALL provide a deterministic repo-owned access flow that does not require browser-side first-run admin setup before the helper becomes usable.

The default operator-facing access path SHALL accept the default development password `admin` and SHALL enter the mounted repository browsing flow for that helper.

The helper SHALL bind only to `127.0.0.1` on a non-privileged host port `>=10000`.

#### Scenario: Operator uses the default local access flow
- **WHEN** the operator follows the documented initial access path for the Filestash helper
- **THEN** the helper accepts the documented default development password `admin`
- **AND THEN** successful authentication takes the operator into the mounted repository browsing flow without requiring browser-side bootstrap configuration

#### Scenario: Helper is not exposed on non-loopback interfaces
- **WHEN** the operator inspects the helper's published host binding
- **THEN** the Filestash web listener is bound only on `127.0.0.1`
- **AND THEN** the published host port is a non-privileged port number `>=10000`

### Requirement: Helper documentation is explicitly development-only
The Filestash helper documentation SHALL describe the service as a local development helper rather than a production-ready file service.

That documentation SHALL cover the upstream image prerequisite, the start workflow, the verification path, the default local access convention, and the reset path for `.data/`.

#### Scenario: Operator reads the helper documentation
- **WHEN** an operator follows the documentation for `dockers/dev-helpers/filestash/`
- **THEN** the docs describe the helper as local and development-oriented
- **AND THEN** the docs explain how to start, verify, access, and reset the helper from repository context
