# CAO Server Launcher

`gig_agents.cao.server_launcher` provides a repo-owned launcher for
managing a local `cao-server` process with explicit config and deterministic
runtime artifacts.

## Install requirement

The launcher starts `cao-server` from `PATH` only.

- Install CAO with `uv` (example): `uv tool install cli-agent-orchestrator`
- Verify: `command -v cao-server`

If start fails with "`cao-server` not found on PATH", install CAO separately and
rerun `command -v cao-server` before retrying launcher commands.

The launcher does **not** run vendored sources from `extern/`.

## Config file (TOML)

Use a server config file and pass it via `--config`.

Example file: `config/cao-server-launcher/local.toml`.

```toml
base_url = "http://localhost:9889"
runtime_root = "tmp/agents-runtime"
home_dir = "/data/agents/cao-home"
proxy_policy = "clear"
startup_timeout_seconds = 15
```

Validation rules:

- Unknown keys are rejected.
- `proxy_policy` must be `clear` or `inherit`.
- `base_url` is currently restricted to:
  - `http://localhost:9889`
  - `http://127.0.0.1:9889`
- `home_dir` must be absolute, existing, and writable.

## CLI

```bash
pixi run python -m gig_agents.cao.tools.cao_server_launcher status --config config/cao-server-launcher/local.toml
pixi run python -m gig_agents.cao.tools.cao_server_launcher start --config config/cao-server-launcher/local.toml
pixi run python -m gig_agents.cao.tools.cao_server_launcher stop --config config/cao-server-launcher/local.toml
```

Each command emits structured JSON for scripting (`base_url`, health info,
pid/log/pidfile paths, and stop diagnostics).

Supported ad-hoc overrides:

- `--base-url`
- `--runtime-root`
- `--home-dir`
- `--proxy-policy`
- `--startup-timeout-seconds`

## Runtime artifacts

When launching (or managing pidfile state), artifacts live under:

`runtime_root/cao-server/<host>-<port>/`

- `cao-server.pid`
- `cao-server.log`
- `launcher_result.json`

## Proxy policy contract

Proxy policy affects only the launched `cao-server` process environment:

- `clear` (default): removes
  `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY` and lowercase equivalents.
- `inherit`: keeps those variables from the caller environment.

In both modes, `NO_PROXY` and `no_proxy` are merged non-destructively to ensure
loopback coverage includes `localhost`, `127.0.0.1`, and `::1`.

For launcher-owned health probes (`status`, and `start` startup polling) against
supported loopback base URLs (`http://localhost:9889`,
`http://127.0.0.1:9889`), the launcher applies the same loopback
`NO_PROXY`/`no_proxy` merge+append behavior by default before each probe so
ambient `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` do not proxy loopback health
traffic.

Opt-out switch:

- Set `AGENTSYS_PRESERVE_NO_PROXY_ENV=1` to preserve caller-provided
  `NO_PROXY`/`no_proxy` exactly (no launcher injection for probes or spawned
  process env). This is useful for traffic-watching proxy workflows.

## CAO home/workdir/state contract

`home_dir` is applied as `HOME` for the launched CAO server process.

Implications:

- CAO state is written under `HOME/.aws/cli-agent-orchestrator/`.
- CAO `working_directory` must be inside this `HOME` tree.
- Repos may be read-only, but `HOME` itself must stay writable.

Recommended layout for `/data/...` workflows:

- `HOME`: `/data/<user>/cao-home`
- repos: `/data/<user>/cao-home/repos/<project>`
- state: `/data/<user>/cao-home/.aws/cli-agent-orchestrator/`

## Manual `/data/...` verification recipe

1. Create a writable CAO home:
   `mkdir -p /data/$USER/cao-home/repos && cp -a <repo> /data/$USER/cao-home/repos/`.
2. Point launcher config `home_dir` to `/data/$USER/cao-home`.
3. Start CAO:
   `pixi run python -m gig_agents.cao.tools.cao_server_launcher start --config <config>`.
4. Start a CAO-backed runtime session with `--workdir` inside that home tree.
5. Confirm session start succeeds for `/data/...` workdir.
6. Confirm CAO state exists under
   `/data/$USER/cao-home/.aws/cli-agent-orchestrator/`.
7. Stop CAO:
   `pixi run python -m gig_agents.cao.tools.cao_server_launcher stop --config <config>`.
