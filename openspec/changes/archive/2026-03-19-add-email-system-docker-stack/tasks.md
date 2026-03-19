## 1. Stack Layout

- [x] 1.1 Create `dockers/email-system/` with the compose entry point, `.env`, `env.example`, and operator README for the local Stalwart + Postgres + Cypht stack
- [x] 1.2 Bind Stalwart, Postgres, and Cypht writable state under `dockers/email-system/.data/` and add a Git ignore rule so `.data/` stays untracked
- [x] 1.3 Configure the compose workflow to use the required host-local images without remote image checks or pulls during normal bring-up
- [x] 1.4 Route every configurable stack value through `dockers/email-system/.env` and document it in `dockers/email-system/env.example`
- [x] 1.5 Assign all stack-defined listener and mapped ports to values `>=10000`, including Stalwart admin/API, Stalwart IMAP, Stalwart SMTP submission, Cypht web UI, and Postgres
- [x] 1.6 Expose only the Stalwart webadmin/API port and the Cypht web UI port on the host by default while keeping IMAP/SMTP and Postgres internal to the Docker network

## 2. Cypht Mail-Client Wiring

- [x] 2.1 Add a `postgres:14.22` service to the stack for Cypht's persistent application database and store its data under `dockers/email-system/.data/postgres`
- [x] 2.2 Configure the Postgres service to listen on a stack-defined port `>=10000` for Cypht
- [x] 2.3 Configure Cypht to use the stack-managed Postgres database for its application bootstrap and persistent state on the assigned high port
- [x] 2.4 Configure Cypht for IMAP-auth login against Stalwart, default SMTP submission through Stalwart, single-server mode, and automatic default-profile creation using Stalwart ports `>=10000`
- [x] 2.5 Ensure the compose configuration and runtime directories let Cypht boot cleanly with its file-backed user settings and attachments paths

## 3. Stalwart API Provisioning

- [x] 3.1 Add a small Python provisioning CLI under `dockers/email-system/` that can authenticate to Stalwart's management API
- [x] 3.2 Configure Stalwart's repo-owned development config so its admin/API and required mail listeners use ports `>=10000`
- [x] 3.3 Implement idempotent domain and individual-mailbox provisioning through Stalwart principal-management endpoints
- [x] 3.4 Normalize development-time authentication defaults to `admin` / `admin` for Stalwart admin access, Postgres auth, and the default seeded mailbox identity

## 4. Operator Workflow And Verification

- [x] 4.1 Document first boot and startup of the compose stack using development-default `admin` / `admin` credentials instead of generated secret retrieval
- [x] 4.2 Document the Stalwart API workflow for creating the mail domain and mailbox accounts before any Cypht login
- [x] 4.3 Add a verification flow showing that a Stalwart-provisioned mailbox can sign into Cypht and read/send mail in the local stack
- [x] 4.4 Document cleanup and reset of `dockers/email-system/.data/` plus the development-only, low-security scope of the stack
