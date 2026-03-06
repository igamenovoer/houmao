## Why

Local CAO loopback traffic (`localhost`/`127.0.0.1`) can still be routed through
ambient proxy variables in the caller shell, causing flaky startup/status and
unexpected network paths. We need a repo-owned default that keeps loopback CAO
communication off proxies without changing upstream CAO sources.
The same ambient proxy environment can also unintentionally proxy loopback HTTP
calls made by runtime-launched agent subprocesses.

## What Changes

- Define a default loopback no-proxy contract for CAO launcher, runtime CAO REST calls, and runtime-launched agent subprocesses.
- Ensure launcher health probes and runtime CAO REST calls bypass proxies for
  supported loopback CAO base URLs by default by injecting loopback entries into
  `NO_PROXY`/`no_proxy`.
- Ensure CAO-backed tmux session environment injects loopback `NO_PROXY`/`no_proxy`
  entries by default (without stripping proxy variables) so agent egress proxy
  behavior remains intact while loopback control-plane traffic stays direct.
- Ensure non-CAO `brain-launch-runtime` subprocess backends (for example, Codex
  app-server and headless CLIs) also receive loopback `NO_PROXY`/`no_proxy`
  injection by default so any loopback HTTP calls made by those tools bypass
  ambient proxies.
- Add an explicit operator-facing opt-out switch: when
  `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the system SHALL not modify `NO_PROXY` or
  `no_proxy` and will respect the caller-provided values (for example, for
  traffic-watching development proxies like mitmproxy).
- Add tests and demo/validation coverage proving loopback traffic remains
  direct and reproducible under proxy-heavy shell environments.

## Capabilities

### New Capabilities
- `cao-loopback-no-proxy`: Enforce and verify default no-proxy behavior for local CAO loopback communication across launcher/runtime/tmux boundaries (and ensure runtime-launched subprocess backends receive the same loopback `NO_PROXY` defaults).

### Modified Capabilities
- `brain-launch-runtime`: Enforce loopback `NO_PROXY`/`no_proxy` injection across backend launch environments (CAO tmux sessions and non-CAO subprocess backends), while preserving proxy vars for agent egress.
- `cao-rest-client-contract`: Require loopback CAO API requests to bypass ambient proxies by default.

## Impact

- Affected runtime modules:
  - `src/gig_agents/cao/server_launcher.py`
  - `src/gig_agents/cao/rest_client.py`
  - `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py`
  - `src/gig_agents/agents/brain_launch_runtime/backends/headless_base.py`
  - `src/gig_agents/agents/brain_launch_runtime/backends/codex_app_server.py`
- Affected docs:
  - `docs/reference/cao_server_launcher.md`
  - `docs/reference/brain_launch_runtime.md`
- Affected tests:
  - launcher and CAO REST client unit coverage
  - backend env-composition tests (CAO tmux, headless, codex app-server)
