# CAO Server Launcher

`houmao.cao.server_launcher` provides a repo-owned launcher for managing a local `cao-server` process with explicit config, detached standalone startup semantics, and deterministic runtime artifacts.

For the canonical launcher-owned artifact tree, derived CAO home placement, and operator filesystem-preparation guidance, use [CAO Server](./system-files/cao-server.md) and [Operator Preparation](./system-files/operator-preparation.md).

## Install requirement

The launcher starts `cao-server` from `PATH` only.

- Install CAO with `uv` from the supported fork (example): `uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@hz-release`
- Verify: `command -v cao-server`

If start fails with "`cao-server` not found on PATH", install CAO separately and
rerun `command -v cao-server` before retrying launcher commands.

The launcher does **not** run vendored sources from `extern/`.

## Config file (TOML)

Use a server config file and pass it via `--config`.

Example file: `config/cao-server-launcher/local.toml`.

```toml
base_url = "http://localhost:9889"
runtime_root = "/data/agents/houmao-runtime"
home_dir = "/data/agents/cao-home"
proxy_policy = "clear"
startup_timeout_seconds = 15
```

Any supported loopback port is allowed, for example `http://127.0.0.1:9991`.

Validation rules:

- Unknown keys are rejected.
- `proxy_policy` must be `clear` or `inherit`.
- `base_url` must be a loopback `http` URL with an explicit port:
  - `http://localhost:<port>`
  - `http://127.0.0.1:<port>`
- `home_dir` must be absolute, existing, and writable.

## CLI

```bash
pixi run python -m houmao.cao.tools.cao_server_launcher status --config config/cao-server-launcher/local.toml
pixi run python -m houmao.cao.tools.cao_server_launcher start --config config/cao-server-launcher/local.toml
pixi run python -m houmao.cao.tools.cao_server_launcher stop --config config/cao-server-launcher/local.toml
```

One-shot CLI overrides apply before validation and do not rewrite the config file:

```bash
pixi run python -m houmao.cao.tools.cao_server_launcher start \
  --config config/cao-server-launcher/local.toml \
  --base-url http://127.0.0.1:9991
```

Each command emits structured JSON for scripting (`base_url`, health info, pid/log/pidfile paths, ownership metadata paths, and stop diagnostics).

Supported ad-hoc overrides:

- `--base-url`
- `--runtime-root`
- `--home-dir`
- `--proxy-policy`
- `--startup-timeout-seconds`

## Runtime artifacts

Launcher-owned artifacts live under a deterministic per-server subtree documented in [CAO Server](./system-files/cao-server.md). That centralized page covers `cao_servers/<host>-<port>/launcher/`, the derived sibling `home/` tree, and the legacy cleanup note for the older `cao-server/` layout.

`start` now means "bootstrap a detached standalone local service and wait until it becomes healthy." Once `start` returns successfully, a later independent `status` command should still be able to reach the same service unless it has been explicitly stopped or crashed independently.

When `start` launches a new process, it derives the selected port from `base_url`
and passes it to `cao-server` via `CAO_PORT`.

## Proxy policy contract

Proxy policy affects only the launched `cao-server` process environment:

- `clear` (default): removes
  `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY` and lowercase equivalents.
- `inherit`: keeps those variables from the caller environment.

In both modes, `NO_PROXY` and `no_proxy` are merged non-destructively to ensure
loopback coverage includes `localhost`, `127.0.0.1`, and `::1`.

For launcher-owned health probes (`status`, and `start` startup polling) against
supported loopback base URLs (`http://localhost:<port>`,
`http://127.0.0.1:<port>`), the launcher applies the same loopback
`NO_PROXY`/`no_proxy` merge+append behavior by default before each probe so
ambient `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` do not proxy loopback health
traffic.

If a non-default requested port never becomes healthy and the spawned process is
still listening on `9889`, launcher `start` fails explicitly with a compatibility
diagnostic indicating that the installed `cao-server` appears to ignore
`CAO_PORT`.

Opt-out switch:

- Set `AGENTSYS_PRESERVE_NO_PROXY_ENV=1` to preserve caller-provided
  `NO_PROXY`/`no_proxy` exactly (no launcher injection for probes or spawned
  process env). This is useful for traffic-watching proxy workflows.

## CAO home/workdir/state contract

`home_dir` is applied as `HOME` for the launched CAO server process.

Implications:

- CAO state is written under `HOME/.aws/cli-agent-orchestrator/`.
- `home_dir` is the launcher-managed state/profile-store anchor for the CAO process.
- Repos and later session workdirs may live elsewhere; the repo-owned launcher/runtime contract does not require them to be nested under `home_dir`.
- Repos may be read-only, but `HOME` itself must stay writable.

Use [CAO Server](./system-files/cao-server.md) for the launcher/home ownership boundary and [Operator Preparation](./system-files/operator-preparation.md) for `/data/...` layout patterns, writable-path preparation, redirection surfaces, and cleanup expectations.
