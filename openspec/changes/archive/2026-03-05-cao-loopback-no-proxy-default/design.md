## Context

The repository already provides:

- a CAO launcher with `proxy_policy=clear` default for the spawned `cao-server`
  process, and
- a CAO-backed runtime path (`brain_launch_runtime` + `cao_rest`) that talks to
  CAO over HTTP and configures per-session tmux environments.
- non-CAO `brain_launch_runtime` backends (for example, Codex app-server and
  Claude/Gemini headless CLIs) that spawn local subprocesses with environment
  maps derived from `os.environ`.

In proxy-heavy developer shells, we observed four separate loopback gaps:

1. launcher health probes (`status` and `start` polling) still use caller proxy env,
2. runtime CAO REST calls still use caller proxy env, and
3. CAO-backed tmux sessions inherit caller proxy env by default.
4. runtime-launched non-CAO agent subprocesses inherit caller proxy env by
   default; if they (or their dependencies) make loopback HTTP calls, those can
   still be routed through proxies when `NO_PROXY` is missing or incomplete.

This can route `localhost`/`127.0.0.1` traffic through external proxies and
break startup/health flows (`502`, flakiness), despite local CAO usage.

Constraint: do not modify upstream CAO source code; enforce behavior in
repository-owned launcher/runtime layers.

## Goals / Non-Goals

**Goals:**

- Make local CAO loopback communication (`localhost`/`127.0.0.1`) no-proxy by
  default across launcher probes, runtime REST calls, CAO-backed tmux env, and
  runtime-launched agent subprocess environments.
- Keep provider credential env behavior intact (allowlisted credentials still
  flow to CAO-backed agents).
- Preserve current behavior for non-loopback CAO base URLs unless explicitly
  changed by operator policy.
- Provide deterministic tests and docs for the loopback no-proxy contract.

**Non-Goals:**

- Changing upstream CAO server internals or vendor code.
- Clearing or disabling outbound proxies globally for runtime-launched tools; this change only ensures loopback entries exist in `NO_PROXY`/`no_proxy` by default.
- Supporting new CAO base URL values beyond currently supported launcher policy.

## Decisions

1. **Treat loopback CAO base URLs as a default no-proxy zone enforced via `NO_PROXY` injection**
   - Applies to `http://localhost:9889` and `http://127.0.0.1:9889`.
   - For these URLs, repo-owned CAO HTTP clients SHALL rely on standard proxy
     behavior by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`
     (append when missing, create when absent).
   - Opt-out: when `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the system SHALL not
     modify `NO_PROXY` or `no_proxy` and will respect caller-provided values
     (for example, to route localhost traffic through a traffic-watching proxy
     like mitmproxy).
   - Alternative considered: specialized per-request transport (for example
     `urllib` proxy handlers); rejected in favor of a simpler, env-driven policy.

2. **Preserve proxy vars for CAO-backed tmux sessions; enforce loopback no-proxy via `NO_PROXY` only**
   - Do not strip `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` from tmux session env so
     CAO-managed agents can still use outbound proxies for external traffic.
   - In default mode, ensure `NO_PROXY` and `no_proxy` include loopback entries
     (`localhost,127.0.0.1,::1`) by merge+append semantics.
   - In preserve mode (`AGENTSYS_PRESERVE_NO_PROXY_ENV=1`), do not modify
     `NO_PROXY`/`no_proxy` in tmux env.

3. **Apply loopback `NO_PROXY` injection to runtime-launched agent subprocess environments**
   - When `brain_launch_runtime` starts non-CAO backends via subprocess (for
     example, Codex app-server and Claude/Gemini headless CLIs), default mode
     SHALL ensure `NO_PROXY` and `no_proxy` include loopback entries
     (`localhost,127.0.0.1,::1`) by merge+append semantics.
   - In preserve mode (`AGENTSYS_PRESERVE_NO_PROXY_ENV=1`), do not modify
     `NO_PROXY`/`no_proxy` in spawned process env.
   - This keeps loopback traffic off ambient proxies without requiring upstream
     tool changes.

4. **Keep behavior policy-scoped rather than global**
   - No-proxy default is enforced only for loopback hosts (CAO control-plane and runtime-launched subprocesses) via `NO_PROXY`/`no_proxy` injection.
   - Non-loopback CAO endpoints can continue using inherited proxy behavior.
   - Alternative considered: clear proxies for all CAO URLs; rejected due to
     potential enterprise remote CAO deployments behind required proxies.

5. **Verify via unit tests + runtime/demo assertions**
   - Add unit coverage for loopback client transport and tmux env composition.
   - Keep a reproducible demo check where loopback remains healthy even when
     caller shell has proxy env vars set.
   - Alternative considered: docs-only guidance; rejected because regressions are subtle.

## Risks / Trade-offs

- [Risk] Existing users may depend on proxied loopback behavior in unusual setups.
  -> Mitigation: provide an explicit preserve opt-out (`AGENTSYS_PRESERVE_NO_PROXY_ENV=1`)
     and document it alongside loopback defaults.

- [Risk] Divergent proxy handling between launcher and runtime could reappear.
  -> Mitigation: define one explicit loopback contract and test both layers.

- [Risk] Loopback `NO_PROXY` injection could surprise users who intentionally configured
  `NO_PROXY` to route localhost through a proxy.
  -> Mitigation: merge+append semantics plus preserve opt-out (`AGENTSYS_PRESERVE_NO_PROXY_ENV=1`).

## Migration Plan

1. Add a shared helper that appends loopback entries to `NO_PROXY`/`no_proxy`
   unless `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`.
2. Update launcher health-probe path to apply the helper before loopback probes
   so default urllib proxy behavior bypasses loopback.
3. Update CAO REST client request path to apply the helper before loopback CAO
   calls so default urllib proxy behavior bypasses loopback.
4. Update CAO-backed tmux env composition to apply the helper (and avoid proxy
   stripping) for loopback CAO sessions.
5. Update non-CAO backend subprocess env composition to apply the helper for
   runtime-launched agent processes.
6. Add/adjust unit tests for launcher, rest client, tmux env, and non-CAO
   backend subprocess env composition.
7. Update reference docs (`cao_server_launcher.md`, `brain_launch_runtime.md`) with the new contract.
8. Validate with demo/runtime command sequence under proxy-heavy shell env.

Rollback:

- Revert loopback `NO_PROXY/no_proxy` injection and restore prior behavior where
  launcher/runtime/tmux/subprocess paths do not modify `NO_PROXY/no_proxy`.

## Open Questions

- How should we expose and document the preserve switch consistently across
  launcher and runtime surfaces (`AGENTSYS_PRESERVE_NO_PROXY_ENV=1`)?
