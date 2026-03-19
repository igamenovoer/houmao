## Why

The repository already carries local source references for Stalwart and Cypht, and this host already has a Cypht image, but there is no repo-owned, reproducible stack that brings them up together for real mail usage. We need a concrete local email system under the repository that makes Stalwart the account authority and keeps Cypht limited to mail reading and sending rather than administration.

## What Changes

- Add a repository-owned Docker Compose stack under `dockers/email-system/` for Stalwart, Postgres, and Cypht.
- Make the compose workflow rely on the images already present on the host and avoid remote image checks or pulls during normal startup.
- Add repo-owned bootstrap/configuration/documentation so the stack stores runtime data under `dockers/email-system/.data/` and keeps that directory ignored by Git.
- Add `dockers/email-system/.env` and `dockers/email-system/env.example` so every configurable stack value is sourced from one compose-local env surface.
- Configure Cypht to use Stalwart as its single backing mail system for login, mailbox access, and outbound mail submission.
- Configure Cypht to use Postgres for its own persistent application database inside the stack.
- Configure the stack to avoid privileged ports entirely and use only ports `>=10000`.
- Add a Stalwart-management workflow that creates domains and mailbox accounts through Stalwart's API instead of using Cypht as an admin surface.
- Use development-only `admin` / `admin` defaults anywhere the stack needs username/password authentication.
- Document the operator flow for first boot, Stalwart admin access, mailbox-account creation, and Cypht login.

## Capabilities

### New Capabilities
- `email-system-docker-stack`: Repository-owned local Docker email system using Stalwart for administration and mailbox authority, and Cypht for end-user mail reading and sending.

### Modified Capabilities
None.

## Impact

- New repository content under `dockers/email-system/`
- New runtime-owned local data under `dockers/email-system/.data/`, ignored by Git
- Compose-local `.env` and tracked `env.example` config surfaces for all configurable stack values
- Docker Compose usage, non-privileged port allocation (`>=10000`), Postgres-backed Cypht state, development-default credentials, and stack bootstrap docs
- Docker Compose usage that relies on preloaded local images rather than registry pulls during bring-up
- Stalwart admin/API provisioning flow for domains and mailbox accounts
- Cypht configuration for IMAP-auth and single-server mail usage
