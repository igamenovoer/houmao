# Local Email System

This stack starts Stalwart, Postgres, and Cypht for local development mail on `houmao.localhost`.

The stack intentionally uses:

- only host-local Docker images,
- ports `>=10000` with published ports bound to loopback,
- the password `admin` for the default development logins,
- runtime data under `dockers/email-system/.data/`.

## Files

- `compose.yaml`: local Stalwart + Postgres + Cypht stack
- `.env`: active local configuration consumed by the stack and helper scripts
- `env.example`: tracked env template with inline comments for every configurable variable
- `stalwart/config.toml`: repo-owned Stalwart development config
- `cypht/nginx.conf.template`: repo-owned high-port nginx template for Cypht
- `cypht/entrypoint.sh`: repo-owned Cypht entrypoint wrapper that renders nginx config from `.env`
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

The command creates a private `.env` from the template if needed, pulls the configured images that are missing, and waits for the services to become healthy. It then provisions the domain and both mailboxes.

To start again with the local images, run the ordinary startup command. It uses Compose's `--pull never` and reads the current local `.env`.

```bash
./dockers/email-system/up.sh
```

Edit `dockers/email-system/.env` to change ports, images, or credentials. If you change `MAIL_DOMAIN`, also set `STALWART_HOSTNAME` and `SEED_MAILBOX_EMAIL` for that domain. The operator address is derived from `MAIL_DOMAIN`. [Environment template](env.example)

## Local Endpoints and Accounts

| Service | Address |
| --- | --- |
| Stalwart Webadmin | `http://127.0.0.1:10082/login` |
| Cypht webmail | `http://127.0.0.1:10081/` |
| Stalwart management API | `http://127.0.0.1:10080/api` |
| Stalwart JMAP discovery | `http://127.0.0.1:10080/.well-known/jmap` |
| IMAP | `127.0.0.1:10143` |
| SMTP submission | `127.0.0.1:10587` |

Use port `10082` for Webadmin. Chromium blocks browser navigation to port `10080`.

| Username | Password | Mail address | Use |
| --- | --- | --- | --- |
| `admin` | `admin` | `admin@houmao.localhost` | Webadmin and Cypht |
| `houmao-operator` | `admin` | `houmao-operator@houmao.localhost` | Cypht |

Stalwart uses the lowercase operator username for sign-in. Mail sent to `HOUMAO-operator@houmao.localhost` reaches the operator mailbox. Cypht creates each user's sender profile on `houmao.localhost`.

The bundled Cypht service uses single-server mode to reach Stalwart on the private Compose network. In that mode, Compose enables Cypht's internal mail server setting for the loopback development stack.

## Prepare an Agent Mailbox for JMAP

The seeded `houmao.localhost` accounts support Cypht, IMAP, and SMTP. The pinned Stalwart release requires a recognized public suffix for JMAP sending identities. Choose a dedicated domain for JMAP in your sandbox. For a disposable local stack, use a reserved domain such as `example.com` and a separate address such as `alice@example.com`.

Use a provisioning profile with the selected address and the management API at `http://127.0.0.1:10080/api`. Provide management authorization from a private source. Explicit Houmao provisioning prepares the sending identity and Archive role, then verifies the account. Use the administrative launch instructions or the disposable-account workflow to run the provisioner. [Stalwart setup and first session](../../docs/reference/mailbox/operations/stalwart-setup-and-first-session.md#administrative-launch-time-provisioning) · [Instructional mail suite](../../tests/instructional/agent-mail-stalwart/README.md)

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

## Verification

Run the built-in verification helper:

```bash
./dockers/email-system/verify.sh
```

That verification path checks:

- the Stalwart webadmin login page
- the Cypht web UI
- the provisioned domain and both Stalwart mailboxes
- the JMAP API and upload origins advertised on the configured loopback HTTP port
- SMTP submission and IMAP delivery for the admin and operator mailboxes

Manual verification flow:

1. Sign into Webadmin at `http://127.0.0.1:10082/login` as `admin`.
2. Sign into Cypht at `http://127.0.0.1:10081/` as `admin` and send a test message to `HOUMAO-operator@houmao.localhost`.
3. Sign into Cypht as `houmao-operator` and confirm the message arrived.

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
