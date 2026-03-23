## Context

The repository already carries local source references for Stalwart and Cypht, and this host already has the required container images available locally, but there is no repo-owned stack that starts the full mail system together in a repeatable way.

The intended service split is narrow and explicit:

- Stalwart is the mail-system authority.
- Stalwart creates and stores domains and mailbox accounts.
- Cypht is only the end-user mail UI for login, reading, and sending.

That split matches the upstream source behavior. Stalwart's container self-initializes its server state under `/opt/stalwart` on first boot and exposes a management API with principal-creation endpoints for domains and accounts. Cypht's container boot flow always initializes its application database before starting the web stack, and upstream supports Postgres-backed bootstrap, IMAP-backed login, a default SMTP server, single-server mode, and automatic default-profile creation.

This host already has the images needed for that shape available locally:

- `stalwartlabs/stalwart:latest`
- `cypht/cypht:latest`
- `postgres:14.22`

For this repository, the stack is explicitly development-oriented and is not trying to preserve production-grade security posture. Runtime state must live under `dockers/email-system/.data/` beside the compose assets, and that runtime directory must stay ignored by Git.

## Goals / Non-Goals

**Goals:**

- Add a repo-owned Docker Compose stack under `dockers/email-system/` that starts Stalwart, Postgres, and Cypht together.
- Make normal stack bring-up rely on the host's preloaded images rather than remote registry checks or pulls.
- Persist Stalwart, Postgres, and Cypht runtime state under `dockers/email-system/.data/`.
- Centralize all configurable stack values in `dockers/email-system/.env` with a tracked `dockers/email-system/env.example`.
- Avoid privileged ports entirely by assigning all stack-defined listeners and connection targets to ports `>=10000`.
- Configure Cypht to authenticate against Stalwart IMAP and submit mail through Stalwart SMTP so the same mailbox credentials work in both places.
- Keep Cypht in a single-server, mail-client-only role instead of an account-administration role.
- Provide a repeatable Stalwart API workflow for creating domains and mailbox accounts.
- Minimize development-time auth friction by using `admin` / `admin` defaults anywhere the stack requires username/password authentication.
- Document the local operator flow from first boot through account provisioning and Cypht login.

**Non-Goals:**

- Making Cypht an account-provisioning or server-administration surface.
- Designing a public-internet-ready mail deployment with DNS, certificates, spam controls, or hardened network exposure.
- Replacing Houmao's own mailbox transport/runtime work with this stack.
- Supporting multiple independent mail backends or multi-server Cypht aggregation in this change.
- Hardening credentials, rotating secrets, or introducing separate auth layers beyond what is needed for local development.

## Decisions

### Decision 1: The stack lives under `dockers/email-system/` and stores mutable state under `dockers/email-system/.data/`

The repository will own the launch files, helper scripts, environment templates, and operator documentation under `dockers/email-system/`.

Mutable service state will be bind-mounted under:

- `dockers/email-system/.data/stalwart`
- `dockers/email-system/.data/cypht/users`
- `dockers/email-system/.data/cypht/attachments`
- `dockers/email-system/.data/postgres`

The repository will ignore `dockers/email-system/.data/` from Git so runtime state stays local to the developer machine.

Why:

- The repo needs a single obvious entry point for local bring-up.
- Keeping runtime state adjacent to the compose files makes the stack self-contained and easier to inspect during development.
- Resetting the mail environment should be as simple as stopping the stack and clearing `dockers/email-system/.data/`.

Alternatives considered:

- Keeping compose files outside the repository or relying on ad hoc `docker run` commands. Rejected because it would make the environment harder to reproduce and review.
- Storing runtime data under `tmp/mail-service/`. Rejected because the operator asked for stack-local data rooted directly under the compose directory.

### Decision 2: The stack uses three services: Stalwart, Postgres, and Cypht

The initial stack will contain:

- one Stalwart service for admin, storage, IMAP, and SMTP responsibilities,
- one Postgres service for Cypht's application database,
- one Cypht service for the webmail UI.

Cypht will use the locally available `postgres:14.22` image for its own persistent application database.

Normal compose bring-up will treat these host-local images as prerequisites and will not pull or check remote registries as part of starting the stack.

Why:

- Upstream Cypht supports `pgsql`, and its container already runs the same DB bootstrap flow against that driver.
- The required images are already present on this host, so the development workflow does not need registry interaction just to start the stack.
- A dedicated database service is a better fit than SQLite for Cypht's persistent application state once the operator has asked to use the available Postgres image.

Alternatives considered:

- SQLite for Cypht. Rejected because the operator asked to use the locally available Postgres image for the email system.
- A MariaDB sidecar for Cypht. Rejected because Postgres is already present locally and Cypht supports it directly.
- Allowing normal bring-up to pull or check registries opportunistically. Rejected because the operator wants the stack to use the images already loaded on the host without remote-image traffic.
- Using host-installed services instead of a compose-defined stack. Rejected because it weakens reproducibility.

### Decision 3: All configurable values are centralized in `.env` and `env.example`

The stack will provide:

- `dockers/email-system/.env` for the developer's active local configuration,
- `dockers/email-system/env.example` as the tracked reference template.

Every stack value intended to be configurable will be sourced through that env surface rather than being hard-coded only in the compose file, repo-owned service configs, or helper scripts.

At minimum, that includes:

- image names and tags,
- assigned ports,
- development credentials,
- mail domain and seeded mailbox identity,
- data-root paths and other operator-tunable stack settings.

Why:

- The stack is already gaining multiple local-development constraints: host-local images, high ports, low-friction credentials, and stack-local data paths.
- Centralizing those values makes the stack easier to inspect and revise without editing multiple files for routine changes.
- A tracked `env.example` gives the repository one explicit declaration of what is configurable.

Alternatives considered:

- Hard-code most values directly in `compose.yaml` and only externalize a few secrets. Rejected because the operator asked for everything configurable to live in the compose-local env files.
- Spread defaults across compose, helper scripts, and service config files. Rejected because it makes the stack harder to reason about and document.

### Decision 4: The stack uses only non-privileged high ports

All stack-defined listeners and connection targets will use ports `>=10000`.

That includes:

- Stalwart admin/API listener,
- Stalwart IMAP listener used by Cypht auth and mailbox access,
- Stalwart SMTP submission listener used by Cypht outbound mail,
- Cypht web UI listener,
- Postgres listener used by Cypht.

The implementation will not rely on upstream default low-port bindings such as Stalwart's default IMAP or SMTP ports, Cypht's default port `80`, or Postgres's default port `5432`. Instead, the repo-owned development stack will provide explicit port assignments in the high-port range and wire every inter-service connection to those assigned ports.

Why:

- The operator explicitly asked to avoid privileged ports entirely.
- Using only high ports avoids root-style low-port assumptions and keeps the stack consistent across host and container boundaries.
- Making port policy explicit in the compose stack avoids accidental fallback to upstream defaults.

Alternatives considered:

- Remap only host ports while leaving container listeners on low ports. Rejected because the operator asked to never use privileged ports, not merely to avoid exposing them on the host.
- Keep upstream internal listener defaults and only customize Cypht connection settings. Rejected because it would still leave low-port listeners inside the stack.

### Decision 5: Cypht uses IMAP-auth single-server mode against Stalwart

Cypht will be configured to:

- use Postgres for its own persistent application database,
- authenticate users through Stalwart IMAP,
- auto-register the authenticated IMAP mailbox as the default inbound source,
- auto-register Stalwart as the default SMTP submission target,
- auto-create a default sending profile,
- run in `single_server_mode` so users cannot add unrelated mail sources.

For the initial local stack, Cypht and Stalwart will communicate on the internal Docker network. Host exposure will be limited by default to:

- Stalwart webadmin/API on a host HTTP port,
- Cypht web UI on a host HTTP port.

IMAP, SMTP submission, and Postgres will remain container-network-only in the default compose layout, but their configured listener ports will still be in the `>=10000` range.

Why:

- This gives users one mailbox identity and one password across server and client.
- It keeps Cypht aligned with the user's stated role: read and send mail, not administer accounts.
- It avoids inventing a separate Cypht-local identity system for a stack that already has a mailbox authority.

Alternatives considered:

- Cypht database authentication with manually entered mail servers. Rejected because it creates a second identity plane and more operator setup.
- Full multi-account Cypht usage. Rejected because it conflicts with the desired "Stalwart is the one backing mail system" model.

### Decision 6: Account and domain provisioning goes through Stalwart's management API, not through Cypht

The stack will include a repo-owned provisioning workflow that calls Stalwart's management API to:

- ensure the target domain exists,
- create or update mailbox principals for individual users,
- keep account creation separate from Cypht's user-facing mail workflow.

The authoritative provisioning contract is Stalwart's API rather than a click path in either web UI. The initial repo-owned helper will be a small Python CLI under `dockers/email-system/` so it can live beside the compose assets and run through the repository's existing Python workflow.

Why:

- Stalwart is the mailbox authority and already exposes the right principal-management surface.
- The user explicitly wants Cypht excluded from admin responsibilities.
- An API-driven workflow is scriptable and easier to make idempotent than a UI-only process.

Alternatives considered:

- Manual provisioning only through Stalwart's webadmin UI. Rejected because it is less repeatable and harder to automate.
- Importing accounts into Cypht or using Cypht as an admin shim. Rejected because it would only configure a client, not create server-owned accounts.

### Decision 7: Development defaults minimize authorization friction

This change will optimize for reproducible development convenience rather than security hardening.

That means:

- documentation will clearly describe the stack as local/dev only,
- initial service wiring may use plain IMAP/SMTP inside the Docker network,
- authenticated services and helpers will default to `admin` / `admin` wherever username/password authentication is required,
- Stalwart admin access, Postgres database auth, and the default seeded mailbox flow will prioritize predictable development credentials over isolation or secret rotation,
- operator-facing documentation will avoid presenting this stack as production-ready mail infrastructure.

Why:

- The immediate need is a working local integration environment.
- Trying to solve DNS, certificates, public MX delivery, production hardening, and stricter credential isolation here would expand the scope dramatically.

Alternatives considered:

- Generated one-time admin secrets or environment-specific secret injection. Rejected because the operator asked to minimize auth friction and use `admin` / `admin` defaults in development.
- Treating the stack as a production deployment template. Rejected because the repo does not need that complexity for this change.

## Risks / Trade-offs

- Reusing `admin` / `admin` across stack-authenticated surfaces removes credential isolation almost entirely. → Mitigation: accept that trade-off explicitly because this stack is development-only and not a security target.
- Stalwart normally generates admin credentials on first boot, so the bootstrap flow must normalize those credentials back to `admin` / `admin`. → Mitigation: make that normalization part of the repo-owned development bootstrap path and document it as an expected step.
- Adding a Postgres sidecar makes the stack slightly heavier than a SQLite-backed deployment. → Mitigation: use the already-present `postgres:14.22` image, keep the container scope limited to Cypht app state, and store its data under `dockers/email-system/.data/postgres`.
- If one of the required images is missing locally, a no-pull workflow will fail immediately instead of self-healing by fetching it. → Mitigation: document the required local image tags explicitly and treat their presence as a prerequisite for development bring-up.
- Requiring all configurable values to flow through env files adds one more layer between stack behavior and service config. → Mitigation: keep `env.example` complete and documented so the env layer stays the single readable source of configuration truth.
- Avoiding all low ports means the stack cannot rely on upstream default listener configs. → Mitigation: provide repo-owned config overrides so Stalwart, Cypht, and Postgres all listen on explicit ports `>=10000`.
- Keeping runtime data under `dockers/email-system/.data/` places mutable state near repo-owned config. → Mitigation: keep it in a hidden `.data/` directory and ignore that path from Git.
- If developers later need external IMAP/SMTP clients, the default internal-only mail ports may feel restrictive. → Mitigation: keep the default compose layout conservative and document how optional host port exposure can be added later without changing the base design.
- API provisioning needs careful idempotency so reruns do not create duplicate domains or accounts. → Mitigation: design the provisioning helper flow around "ensure" semantics backed by Stalwart principal queries and updates.

## Migration Plan

This change is additive.

Implementation will:

- add the new stack files under `dockers/email-system/`,
- add `dockers/email-system/.env` and `dockers/email-system/env.example`,
- add helper assets for Stalwart API provisioning,
- add operator documentation for bring-up, provisioning, verification, and reset,
- create runtime state only under `dockers/email-system/.data/`,
- keep `dockers/email-system/.data/` ignored by Git.

Rollback is straightforward:

- stop and remove the compose stack,
- remove `dockers/email-system/.data/` if a full reset is desired,
- delete or ignore the new stack files if the change is reverted before adoption.

No existing repository runtime needs in-place migration for this change.

## Open Questions

None currently.
