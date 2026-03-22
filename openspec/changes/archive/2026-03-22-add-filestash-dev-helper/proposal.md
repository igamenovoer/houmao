## Why

The repository already produces development artifacts that are easier to inspect in a browser than in a terminal, including Markdown docs, images, videos, and generated logs, but there is no repo-owned local service that exposes those files in a consistent way. Adding a first development helper around Filestash gives contributors a repeatable way to browse the repository contents during development without relying on ad hoc host tooling or one-off container commands.

## What Changes

- Add a repository-owned Filestash helper stack under `dockers/dev-helpers/filestash/` with compose, helper scripts, and operator-facing documentation.
- Mount the repository into the Filestash container as a read-only browsable filesystem so developers can inspect docs, images, videos, logs, and other repo artifacts through one local web UI.
- Preseed a low-friction local login and connection flow so the helper is usable immediately after startup and does not require manual Filestash admin setup.
- Define the helper's local runtime conventions, including loopback-only access, a non-privileged host port, runtime state placement, and the expected upstream image prerequisite.

## Capabilities

### New Capabilities
- `filestash-dev-helper`: Repository-owned Filestash development helper for browsing this repository's files and generated artifacts through a local Docker service.

### Modified Capabilities

None.

## Impact

- Affected code and content: new repo-owned assets under `dockers/dev-helpers/filestash/`, related ignore rules, and operator-facing docs.
- Affected dependency surface: local development now depends on the upstream `machines/filestash:latest` container image being available on the host for this helper.
- Affected workflows: developers gain a documented local browser-based inspection path for repository artifacts instead of relying only on shell tools.
- Scope note: this change introduces the first dev helper and its conventions for Filestash only; it does not define the full future catalog of development helpers.
