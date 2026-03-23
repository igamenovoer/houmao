# Local Filestash Repo Browser

This helper starts a local Filestash instance for browsing this repository's files and generated artifacts through one loopback-only web UI.

The helper intentionally uses:

- only host-local Docker images during normal bring-up,
- the upstream Filestash image `machines/filestash:latest` embedded directly in the compose file,
- only loopback exposure on a port `>=10000`,
- a read-only mount of this repository at `/repo`,
- a single operator-facing `Repo` connection label,
- a low-friction development password configured in `.env`,
- runtime data under [`dockers/dev-helpers/filestash/.data`](/data1/huangzhe/code/houmao/dockers/dev-helpers/filestash/.data).

## Files

- `compose.yaml`: repo-owned Filestash helper stack
- `.env`: active local helper configuration consumed by the helper scripts and compose port/path settings
- `env.example`: tracked template for supported helper configuration values
- `config/config.json`: repo-owned seed config copied into runtime state before startup
- `up.sh`: prepares writable runtime state, syncs the seed config, and starts the helper
- `verify.sh`: quick verification path for helper health and seeded access flow
- `down.sh`: stop the helper stack

## Prerequisites

The required Filestash image must already exist on the host:

```bash
docker images --format '{{.Repository}}:{{.Tag}}' | rg '^machines/filestash:latest$'
```

If it is missing, fetch it explicitly before normal bring-up:

```bash
docker pull machines/filestash:latest
```

Normal helper startup does not pull from remote registries. The compose file embeds `machines/filestash:latest`, sets `pull_policy: never`, and the provided startup wrapper uses `docker compose ... up --pull never`.

The startup wrapper also requires:

- `node`, to render the bcrypt admin credential from `.env` into the runtime Filestash config
- `jq`, to render and validate the runtime config

## Configure

The helper reads [`dockers/dev-helpers/filestash/.env`](/data1/huangzhe/code/houmao/dockers/dev-helpers/filestash/.env). To reset those values to the tracked defaults:

```bash
cp dockers/dev-helpers/filestash/env.example dockers/dev-helpers/filestash/.env
```

The default development password is the value of `FILESTASH_DEFAULT_PASSWORD` in `.env`. The tracked default is `admin`.

The seeded Filestash application config is tracked in [`dockers/dev-helpers/filestash/config/config.json`](/data1/huangzhe/code/houmao/dockers/dev-helpers/filestash/config/config.json). `up.sh` renders the runtime `.data/config/config.json` from that seed plus the current `.env` values before the helper starts.

## Start

From the repository root:

```bash
./dockers/dev-helpers/filestash/up.sh
```

That command:

1. prepares the helper `.data/` directory with writable permissions for the Filestash container user
2. copies the repo-owned seed config into `.data/config/config.json`
3. starts the compose stack with `--pull never`
4. waits for `healthz` to report a passing configuration

Default local endpoint:

- Filestash login and repo browser: `http://127.0.0.1:18334/login`

Default local access:

- connection label: `Repo`
- password: value of `FILESTASH_DEFAULT_PASSWORD` from `.env` (tracked default: `admin`)

After entering the default password on the login page, Filestash lands in the mounted repository root and shows hidden files by default.

## Verification

Run the built-in verification helper:

```bash
./dockers/dev-helpers/filestash/verify.sh
```

That verification path checks:

- compose sees the helper container
- `/healthz` reports a passing configuration
- `/api/config` exposes the single seeded `Repo` connection and middleware mapping
- the seeded password-only access flow accepts the configured `.env` password
- the authenticated session resolves to the mounted repository root
- the default root listing exposes hidden repository files such as `.git` and `.gitignore`

Manual verification flow:

1. Open `http://127.0.0.1:18334/login`.
2. Enter the password from `FILESTASH_DEFAULT_PASSWORD` in `dockers/dev-helpers/filestash/.env`.
3. Confirm Filestash lands in the repository root.
4. Confirm hidden files such as `.gitignore` are visible in the browser tree.
5. Open a Markdown file, image, or other artifact from the repo and confirm it renders.

## Stop And Reset

Stop the helper:

```bash
./dockers/dev-helpers/filestash/down.sh
```

Reset all helper runtime state:

```bash
rm -rf dockers/dev-helpers/filestash/.data
```

The `.data` directory is Git-ignored and is the only runtime state location used by this helper.

## Development Scope

This helper is intentionally development-only:

- no credential hardening
- no external network exposure beyond `127.0.0.1`
- no normal registry pulls during bring-up
- no browser-side repository mutation because the repo mount is read-only
- no live log tailing or other production file-service guarantees
