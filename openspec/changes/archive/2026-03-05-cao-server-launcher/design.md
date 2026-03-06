## Context

This repo already supports CAO-backed sessions via `backend=cao_rest` in
`gig_agents.agents.brain_launch_runtime`. That flow assumes:

- a `cao-server` is already running and reachable at `--cao-base-url`, and
- CAO will accept the requested `--workdir`.

In practice, two issues repeatedly break developer workflows:

1. **Proxy environments break localhost CAO connectivity.**
   Our CAO REST client uses `urllib`, which honors `HTTP_PROXY` / `HTTPS_PROXY`
   unless `NO_PROXY` is configured. This can route `http://localhost:9889` CAO
   calls through a proxy and fail unexpectedly.

2. **CAO rejects workdirs outside the CAO server’s “home” tree.**
   Upstream CAO validates `working_directory` is under `os.path.expanduser("~")`
   (after realpath normalization). Repos under `/data/...` therefore fail if CAO
   is started with the normal `$HOME` (for example `/home/huangzhe`).

We already have ad-hoc `cao-server` auto-start logic in `scripts/demo/*`, but it
is not shared or configurable (proxy policy, trusted workdir root, log/pid
locations). We need a first-class launcher utility inside the main package with
a clear operational contract for starting/stopping CAO separately from
`brain_launch_runtime`.

Constraints:

- Do not patch vendored upstream CAO code under `extern/` (treat as reference).
- Prefer safe defaults; “trust workdir” must be explicit/configured.
- No auto-start: CAO server start is always an explicit step using a server
  config file.
- The launcher should be usable by both scripts and the runtime CLI, but CAO
  server lifecycle is managed separately (no `start-session` integration).

## Goals / Non-Goals

**Goals:**

- Provide a shared CAO server launcher (Python API + CLI) that can explicitly:
  - `status`: health-check CAO at a base URL,
  - `start`: start (or reuse) a local `cao-server` process and wait until healthy,
  - `stop`: stop a pidfile-tracked server with best-effort identity checks.
- Make CAO-backed workflows reliable under common proxy setups by defaulting to
  a deterministic CAO server process environment (proxy-policy `clear` by
  default, with opt-in `inherit`).
- Support “trusted workdir root” so CAO can accept workdirs outside the real `~`
  (implemented by controlling the CAO server process `HOME`).
- Keep `brain_launch_runtime` as a pure CAO client: it continues to assume CAO
  is already running at `--cao-base-url`.

**Non-Goals:**

- Modifying upstream CAO validation rules or adding allowlist env vars in the CAO
  server itself.
- Making CAO auto-start the default behavior for all users.
- Fully automating interactive tmux flows (attach/prompt/inspect loops).

## Decisions

- **Implement a new launcher module under `src/gig_agents/cao/`.**
  - `gig_agents.cao.server_launcher` will expose a typed config object
    and `status/start/stop` functions.
  - A small CLI wrapper (module `python -m ...`) will be added for scripts and
    manual use.

- **CAO server lifecycle is managed separately from `brain_launch_runtime`.**
  - We will not add `start-session` flags for “ensure CAO server”.
  - Docs/scripts will use a two-step flow:
    1. start CAO server via the launcher CLI using a server config file
    2. start a CAO-backed session with `brain_launch_runtime --backend cao_rest`

- **Manage lifecycle artifacts under the runtime root.**
  - The launcher will write:
    - a pid file (for stop/reuse), and
    - a log file (stdout/stderr)
    under `runtime_root/cao-server/<host>-<port>/`.
  - The launcher will report whether it started a new server or reused an
    existing healthy one.

- **Proxy policy is explicit and affects the launched server environment.**
  - Default policy: clear proxy env vars for the launched `cao-server` process
    (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and lowercase equivalents).
  - Optional policy: inherit proxy env vars from the caller.
  - In both cases: preserve and merge `NO_PROXY/no_proxy` to include loopback
    (`localhost,127.0.0.1,::1`) non-destructively.
  - The launcher does **not** implement client-side “no-proxy” bypass logic for
    its own CAO HTTP calls; if the environment proxies localhost CAO and breaks
    connectivity, we want it to fail visibly and be fixed via environment
    configuration.

- **Trusted workdir root is implemented by setting `HOME` for the CAO server
  process.**
  - This matches upstream CAO’s `working_directory` validation behavior without
    requiring upstream changes.
  - The launcher will validate the trusted home directory exists and is an
    absolute path.
  - Contract: CAO state is stored under `HOME/.aws/cli-agent-orchestrator/` for
    the CAO server process, so changing `HOME` relocates CAO DB/logs and
    requires `HOME` to be writable.

- **Use only `cao-server` from `PATH`.**
  - The launcher will invoke `cao-server` as a subprocess (expecting an official
    `uv tool install` style installation).
  - The launcher will not run CAO server from vendored sources under
    `extern/orphan/...` via `PYTHONPATH`.

- **Stop semantics are pidfile-based with best-effort identity verification.**
  - `stop` reads the pidfile under `runtime_root/cao-server/<host>-<port>/` and
    verifies (best-effort) that the pid appears to be a `cao-server` process
    before sending signals.

## CAO Server Launcher Config

The CAO server launcher is configured via a **server config file** (see Q2 in
the discuss doc: no auto-start and no `brain_launch_runtime` integration).

### Upstream limitation: fixed port

Upstream CAO (as currently observed) hard-codes its server host/port to
`localhost:9889` and does not expose CLI flags/env vars to change it. This means
we cannot reliably support arbitrary `base_url` values for a vanilla
`cao-server` launch yet.

Reference: `context/issues/known/issue-cao-server-fixed-port-9889.md`.

Contract for this change:

- The config includes `base_url` for future use.
- For now, the launcher only supports `base_url` values that match upstream:
  `http://localhost:9889` (and `http://127.0.0.1:9889` as an equivalent loopback
  spelling).
- Any other `base_url` is rejected (schema validation error) until we confirm
  CAO supports configurable host/port.

### Where the config lives

- Repo-tracked **example** config(s) live under:
  - `config/cao-server-launcher/`
- Users/scripts pass an explicit `--config` path to the launcher CLI. The file
  can live anywhere (for example under a user-owned directory in `/data/...`),
  but the repo should provide a known-good example for documentation and tests.

### Config file format (example)

File format: TOML.

```toml
# Example: config/cao-server-launcher/local.toml

# CAO HTTP API base URL.
#
# Upstream CAO currently binds to localhost:9889 via hard-coded constants, so
# this value is *intentionally restricted* for now. Changing it will raise a
# config validation error until upstream host/port configurability is confirmed.
base_url = "http://localhost:9889"
# Alternate supported spelling (equivalent loopback): "http://127.0.0.1:9889"

# Root for pid/log artifacts written by the launcher.
runtime_root = "tmp/agents-runtime"

# CAO server process HOME. This is the trust root for CAO working directories
# and also where CAO writes its own state under `HOME/.aws/cli-agent-orchestrator/`.
home_dir = "/data/agents/cao-home"

# Proxy handling for the launched `cao-server` process environment.
# - "clear": unset HTTP(S)_PROXY/ALL_PROXY (default)
# - "inherit": keep proxy env vars from the launcher process
proxy_policy = "clear"

# Startup wait for `GET /health` to become healthy after spawning `cao-server`.
startup_timeout_seconds = 15
```

### Schema validation requirement

Config files are **schema-validated** at load time (fail fast):

- unknown keys are rejected (typo protection),
- invalid enums (for example `proxy_policy`) are rejected,
- `base_url` is restricted to the supported upstream values (`http://localhost:9889`
  and `http://127.0.0.1:9889`) until CAO host/port configurability is confirmed,
- values with structural constraints (URLs, paths, timeouts) are validated, and
- errors include the config path plus the failing field(s) to keep debugging
  straightforward.

Alternatives considered:

- Patch CAO to accept an allowlist of trusted workdir prefixes. Rejected because
  this repo treats `extern/` as third-party reference and we want to avoid
  maintaining a fork.
- Operational workaround: run everything under `~`. Rejected because the repo is
  commonly located under `/data/...` and the goal is to support that layout.

## Risks / Trade-offs

- [Risk] Overriding CAO server `HOME` relocates CAO state and may create a new
  `.aws/cli-agent-orchestrator` tree under the trusted root.
  -> Mitigation: keep default `HOME` unchanged unless explicitly configured; add
  docs with recommended trusted-home choices (for example a stable `/data/...`
  user directory rather than a repo root).

- [Risk] Clearing proxy env vars for the launched CAO server can break provider
  connectivity in environments that require proxies.
  -> Mitigation: make proxy inheritance configurable (`inherit`); keep the
  default “clear” policy scoped to the CAO server subprocess environment only
  (do not mutate global user shell state).

- [Risk] Starting background processes can leave orphan `cao-server` instances.
  -> Mitigation: write pid/log artifacts, provide an explicit stop operation,
  and make start/stop explicit (no hidden “ensure on session start”).

- [Risk] Concurrent callers can race and start multiple servers on the same
  port.
  -> Mitigation: rely on health-check-first, and on failure detect “address in
  use”/early exit and re-check health; prefer single pid file location under
  `runtime_root/cao-server/<host>-<port>/`.
