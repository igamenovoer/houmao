# Local Email System

This stack starts Stalwart, Postgres, and Cypht for local development mail flows.

The stack intentionally uses:

- only host-local Docker images,
- only ports `>=10000`,
- `admin` / `admin` for every operator-facing development credential surface,
- runtime data under [`dockers/email-system/.data`](/data1/huangzhe/code/houmao/dockers/email-system/.data).

## Files

- `compose.yaml`: local Stalwart + Postgres + Cypht stack
- `.env`: active local configuration consumed by the stack and helper scripts
- `env.example`: tracked env template with inline comments for every configurable variable
- `stalwart/config.toml`: repo-owned Stalwart development config
- `cypht/nginx.conf.template`: repo-owned high-port nginx template for Cypht
- `cypht/entrypoint.sh`: repo-owned Cypht entrypoint wrapper that renders nginx config from `.env`
- `provision_stalwart.py`: Stalwart management API helper for ensuring domains and mailbox accounts
- `smoke_mail_flow.py`: SMTP submission + IMAP delivery smoke test for the seeded mailbox
- `up.sh`: startup path that uses local images only and seeds the default mailbox
- `verify.sh`: quick verification path for the local stack
- `down.sh`: stop the stack

## Prerequisites

The required images must already exist on the host:

```bash
docker images --format '{{.Repository}}:{{.Tag}}' | rg '^(stalwartlabs/stalwart:latest|postgres:14.22|cypht/cypht:latest)$'
```

Normal bring-up does not pull or check remote registries. The compose file sets `pull_policy: never`, and the provided startup wrapper uses `docker compose ... up --pull never`.

## Configure

The stack reads [`dockers/email-system/.env`](/data1/huangzhe/code/houmao/dockers/email-system/.env). If you want to reset it to the tracked defaults:

```bash
cp dockers/email-system/env.example dockers/email-system/.env
```

Every supported configuration value is documented inline in [`dockers/email-system/env.example`](/data1/huangzhe/code/houmao/dockers/email-system/env.example).

## Start

From the repository root:

```bash
./dockers/email-system/up.sh
```

That command:

1. starts the compose stack with `--pull never`
2. waits for the Stalwart management API to respond
3. ensures the configured mail domain exists
4. ensures the seeded mailbox from `.env` exists

Default development endpoints:

- Stalwart webadmin and API: `http://127.0.0.1:10080`
- Cypht webmail: `http://127.0.0.1:10081`

Default development credentials:

- Stalwart admin/API: `admin` / `admin`
- Seeded mailbox login for Cypht: `admin` / `admin`

The stack also defines a hidden fallback-bootstrap login in `.env` so the provisioning helper can grant the real `admin` mailbox the Stalwart admin role. That bootstrap credential is not needed for normal webadmin or Cypht usage.

The seeded mailbox uses the email address from `.env`:

- `admin@example.test` by default

Cypht uses `DEFAULT_EMAIL_DOMAIN` so the default profile address resolves to `admin@example.test` even though the IMAP login username stays `admin`.

## Provision More Mailboxes

Create or ensure another mailbox account:

```bash
pixi run python dockers/email-system/provision_stalwart.py \
  --env-file dockers/email-system/.env \
  ensure-account \
  --name alice \
  --email alice@example.test \
  --password admin
```

Ensure the domain only:

```bash
pixi run python dockers/email-system/provision_stalwart.py \
  --env-file dockers/email-system/.env \
  ensure-domain \
  --name example.test
```

## Verification

Run the built-in verification helper:

```bash
./dockers/email-system/verify.sh
```

That verification path checks:

- the Stalwart webadmin login page
- the Cypht web UI
- the provisioned Stalwart principals
- SMTP submission and IMAP delivery for the seeded mailbox

Manual verification flow:

1. Open `http://127.0.0.1:10080` and confirm Stalwart webadmin is reachable with `admin` / `admin`.
2. Open `http://127.0.0.1:10081`.
3. Log into Cypht with the seeded mailbox credentials `admin` / `admin`.
4. Confirm Cypht shows a default profile address of `admin@example.test`.
5. Send a test message from `admin@example.test` to itself.
6. Refresh the inbox and confirm the message is readable.

## Stop And Reset

Stop the stack:

```bash
./dockers/email-system/down.sh
```

Reset all runtime state:

```bash
rm -rf dockers/email-system/.data
```

The `.data` directory is Git-ignored and is the only runtime state location used by this stack.

## Development Scope

This stack is intentionally development-only:

- no credential hardening
- no TLS for IMAP/SMTP inside the compose network
- plain IMAP and SMTP auth enabled on the internal Docker network for Cypht compatibility
- no privileged ports
- no registry pulls during normal bring-up
