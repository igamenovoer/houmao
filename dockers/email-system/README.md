# Local Email System

This stack starts Stalwart v1.2.0 and Bulwark Webmail 1.21.3 for local development mail on `houmao.localhost`. The proxy serves Bulwark and its JMAP requests on port `10081`. Houmao uses the JMAP listener on port `10080`, and Stalwart serves Webadmin over HTTPS.

The stack intentionally uses:

- only host-local Docker images,
- ports `>=10000` with published ports bound to loopback,
- the password `admin` for the default development logins,
- Stalwart data under `dockers/email-system/.data/stalwart-v1/` and Bulwark settings in the `bulwark-data` Compose volume.

## Files

- `compose.yaml`: local Stalwart, JMAP HTTP proxy, and Bulwark stack
- `.env`: active local configuration consumed by the stack and helper scripts
- `env.example`: tracked env template with inline comments for every configurable variable
- `stalwart/config.json`: Stalwart 1.x RocksDB configuration
- `stalwart/jmap-http.conf.template`: loopback proxy that serves Bulwark and rewrites the advertised JMAP URLs to the client's published HTTP origin
- `provision_stalwart.py`: Stalwart management API helper for ensuring domains and mailbox accounts
- `smoke_mail_flow.py`: SMTP submission and IMAP delivery smoke test for both default mailboxes
- `up.sh`: first-run configuration, optional image preparation, and stack startup
- `verify.sh`: quick verification path for the local stack
- `down.sh`: stop the stack

## Set Up a Fresh Checkout

With Docker Compose v2 and Pixi installed, run this from the repository root.

```bash
./dockers/email-system/up.sh --pull-missing-images
```

The command creates a private `.env` from the template and pulls missing images. On first run it configures the Stalwart domain and listeners in recovery mode, then starts the services and provisions the default mailboxes. By default the admin can read the operator’s shared folders.

To start again with the local images, run the ordinary startup command. It uses Compose's `--pull never` and reads the current local `.env`.

```bash
./dockers/email-system/up.sh
```

Edit `dockers/email-system/.env` to change ports, images, or credentials. If you change `MAIL_DOMAIN`, also set `STALWART_HOSTNAME` and `SEED_MAILBOX_EMAIL` for that domain. The operator address is derived from `MAIL_DOMAIN`. [Environment template](env.example)

### Replace an Existing Stack

If the previous stack still runs Cypht, stop it before starting Bulwark on port `10081`. If the stack runs Stalwart 0.15, set `STALWART_IMAGE` in the local `.env` to the version in `env.example` and retire any Compose override that mounts the old TOML file. Run these commands from the repository root.

```bash
docker compose --env-file dockers/email-system/.env -f dockers/email-system/compose.yaml down --remove-orphans
./dockers/email-system/up.sh --pull-missing-images
```

Stalwart 1.x reuses `.data/stalwart-v1/` if that store already exists. On first start from Stalwart 0.15, it creates a fresh store there and leaves the previous store at `.data/stalwart/`.

## Local Endpoints and Accounts

| Service | Address |
| --- | --- |
| Stalwart Webadmin | `https://127.0.0.1:10082/admin/` |
| Bulwark webmail | `http://127.0.0.1:10081/` |
| Stalwart management API | `http://127.0.0.1:10080/jmap` |
| Stalwart JMAP discovery | `http://127.0.0.1:10080/.well-known/jmap` |
| IMAP | `127.0.0.1:10143` |
| SMTP submission | `127.0.0.1:10587` |

Use port `10082` for Webadmin. The development listener serves a self-signed certificate. Port `10080` is for the local HTTP API and is blocked for browser navigation in Chromium.

| Username | Password | Mail address | Use |
| --- | --- | --- | --- |
| `admin` | `admin` | `admin@houmao.localhost` | Webadmin and Bulwark |
| `houmao-operator` | `admin` | `houmao-operator@houmao.localhost` | Bulwark |

Bulwark signs in directly to Stalwart over JMAP. Use the lowercase operator username for sign-in. Mail sent to `HOUMAO-operator@houmao.localhost` reaches the operator mailbox.

## Prepare an Agent Mailbox for JMAP

Keep agent qualification accounts separate from the seeded `houmao.localhost` accounts. For a disposable local stack, use a reserved domain such as `example.com` and an address such as `alice@example.com`.

Use a provisioning profile with the selected address and the management API at `http://127.0.0.1:10080/jmap`. Provide management authorization from a private source. Explicit Houmao provisioning prepares the sending identity and Archive role, then verifies the account. Use the administrative launch instructions or the disposable-account workflow to run the provisioner. [Stalwart setup and first session](../../docs/reference/mailbox/operations/stalwart-setup-and-first-session.md#administrative-launch-time-provisioning) · [Instructional mail suite](../../tests/instructional/agent-mail-stalwart/README.md)

For live attachment of a prepared account, use its normal login, private mailbox credential, and discovery URL `http://127.0.0.1:10080/.well-known/jmap`. For a custom `STALWART_HTTP_PORT`, use that same port for discovery and management. Stalwart advertises its JMAP API and upload URLs at the published loopback origin, which the default Houmao connection policy accepts. [Attach the gateway and account](../../docs/reference/mailbox/operations/stalwart-setup-and-first-session.md#attach-the-gateway-and-account)

## Provision More Mailboxes

Create or ensure another mailbox account:

```bash
pixi run python dockers/email-system/provision_stalwart.py \
  --env-file dockers/email-system/.env \
  ensure-account \
  --name alice \
  --email alice@houmao.localhost \
  --password admin
```

Ensure the domain only:

```bash
pixi run python dockers/email-system/provision_stalwart.py \
  --env-file dockers/email-system/.env \
  ensure-domain \
  --name houmao.localhost
```

## View Shared Mailboxes as Admin

Startup grants `admin` read-only access to the seeded operator folders. It disables the `impersonate` permission on that account so Stalwart lists folders shared through ACLs. `admin` keeps the Webadmin role. For additional accounts, share each folder you want `admin` to read.

1. As the folder owner, grant `admin@houmao.localhost` IMAP Lookup and Read (`lr`). An authenticated IMAP session can send `A001 SETACL "INBOX" "admin@houmao.localhost" "lr"`. Repeat for other folders using their full IMAP names.
2. Sign in to Bulwark as `admin`. In the sidebar, open **Shared → houmao-operator@houmao.localhost → Inbox**. Opening a message in the read-only share leaves its read status as set by the operator.

## Verification

Run the built-in verification helper:

```bash
./dockers/email-system/verify.sh
```

That verification path checks:

- the Stalwart Webadmin login page
- the Bulwark web UI and its connection to Stalwart
- the provisioned domain and both Stalwart mailboxes
- the JMAP API and upload origins advertised on the configured loopback HTTP port
- SMTP submission and IMAP delivery for the admin and operator mailboxes

Manual verification flow:

1. Sign in to Webadmin at `https://127.0.0.1:10082/admin/` as `admin`.
2. Sign in to Bulwark at `http://127.0.0.1:10081/` as `admin` and send a test message to `houmao-operator@houmao.localhost`.
3. As `admin`, open the operator's shared inbox and confirm the message arrived.

## Stop and Reset

Stop the stack:

```bash
./dockers/email-system/down.sh
```

Discard the current Stalwart data and Bulwark settings:

```bash
docker compose --env-file dockers/email-system/.env -f dockers/email-system/compose.yaml down --volumes
sudo rm -rf dockers/email-system/.data/stalwart-v1
```

## Development Scope

This stack is intentionally development-only:

- no credential hardening
- no TLS for IMAP/SMTP inside the compose network
- plain IMAP and SMTP auth enabled for local development clients
- no privileged ports
- no registry pulls during normal bring-up
