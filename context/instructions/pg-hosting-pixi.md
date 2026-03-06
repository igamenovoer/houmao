# Local Postgres + pgvector via Pixi (`pg-hosting`)

This guide runs Postgres and `pgvector` from Pixi without Docker.

Defaults used in this guide:
- User: `postgres`
- Password: `postgres` (development-only)
- Port: `55432`
- Runtime root: `tmp/pg-hosting`

## 1) Install the environment

```bash
pixi install -e pg-hosting --manifest-path pyproject.toml
```

## 2) Initialize a fresh local cluster

```bash
pixi run -e pg-hosting pg-init
```

What this does:
- Creates a fresh cluster at `tmp/pg-hosting/pgdata`
- Sets host auth to `scram-sha-256` and local auth to `trust`
- Initializes user `postgres` with password `postgres`

## 3) Start Postgres in background (localhost only)

```bash
pixi run -e pg-hosting pg-start
pixi run -e pg-hosting pg-ready
```

`pg-start` binds to `127.0.0.1` and uses non-default port `55432`.

## 4) Connect and enable pgvector

Check connection:

```bash
pixi run -e pg-hosting psql "postgresql://postgres:postgres@127.0.0.1:55432/postgres" -c "SELECT version();"
```

Enable extension:

```bash
pixi run -e pg-hosting pg-enable-vector
```

Quick vector smoke query:

```bash
pixi run -e pg-hosting psql "postgresql://postgres:postgres@127.0.0.1:55432/postgres" -c "SELECT '[1,2,3]'::vector;"
```

## 5) Stop Postgres and verify

```bash
pixi run -e pg-hosting pg-stop
pixi run -e pg-hosting pg-ready
```

After stop, `pg-ready` should report not-ready.

## Reset local state

To start from a clean cluster:

```bash
rm -rf tmp/pg-hosting/pgdata tmp/pg-hosting/sock tmp/pg-hosting/postgres.log tmp/pg-hosting/pwfile
```

`tmp/` is already git-ignored in this repository, so runtime artifacts stay out of commits.
