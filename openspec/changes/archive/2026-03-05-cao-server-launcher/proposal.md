## Why

CAO-backed sessions currently assume a `cao-server` is already running and that the
developer environment (proxy vars, `$HOME`, etc.) is compatible with CAO defaults.
In practice this is fragile:

- Local CAO health checks can be broken by proxy environment variables (localhost
  requests accidentally routed through a proxy).
- CAO rejects `working_directory` values that are outside the CAO server’s notion
  of the user home directory, which prevents launching CAO-backed sessions in
  repos located outside `~` (for example under `/data/...`).

We need a first-class, configurable CAO server launcher so CAO-backed workflows
become reliable and repeatable.

## What Changes

- Add a **standalone CAO server launcher** utility in the main Python package
  (Python API + small CLI) to explicitly manage a local `cao-server` process:
  - `start`: start (or reuse) a local server and wait until healthy
  - `status`: report health at the configured base URL
  - `stop`: stop a pidfile-tracked server with best-effort identity checks
- The launcher is configured via a **server config file** (no “auto-start on
  session start”).
- Manage lifecycle artifacts under the runtime root at:
  `runtime_root/cao-server/<host>-<port>/` (pid, log, optional diagnostics).
- Support a configurable proxy policy for the **launched CAO server process**
  environment:
  - `clear` (default): unset proxy env vars for the launched server
  - `inherit`: keep proxy env vars from the launching environment
  - In both modes: preserve and merge `NO_PROXY/no_proxy` to include loopback
    (`localhost,127.0.0.1,::1`) non-destructively.
- Support a configurable CAO “trusted home” by setting the CAO server process
  `HOME`:
  - This enables CAO terminals to use workdirs outside the real `~`, because
    CAO requires `working_directory` to be within the CAO server process home
    tree.
  - CAO writes state under `HOME/.aws/cli-agent-orchestrator/`, so `HOME` must
    be writable and users should choose a directory layout intentionally.
- Do not modify or run vendored CAO sources under `extern/`; the launcher uses
  the official `uv` installation (`cao-server` on `PATH`).
- Upstream CAO currently binds to `localhost:9889` via hard-coded constants, so
  the config’s `base_url` is intentionally restricted to upstream-supported
  values for now (kept for future use; changing it raises a config validation
  error until CAO host/port configurability is confirmed).
- Add docs/scripts that adopt the launcher contract (explicit server start
  step, proxy policy, CAO home/workdir/state behavior).

## Capabilities

### New Capabilities
- `cao-server-launcher`: Start/status/stop a local CAO server with policy
  controls (proxy policy for the server process env, CAO home/trust via `HOME`,
  pid/log artifact layout, health check).

## Impact

- Code: new module(s) under `src/gig_agents/cao/` plus wiring from
  `src/gig_agents/cao/tools/...` for the user-facing launcher CLI.
- Scripts/docs: update interactive/demo entry points to rely on the shared
  launcher; add reference docs for configuration and expected behavior.
- Runtime behavior: may launch background `cao-server` processes, may override
  CAO server `HOME` (which relocates CAO state under `HOME/.aws/...`), and will
  manage pid/log artifacts under the runtime root.
