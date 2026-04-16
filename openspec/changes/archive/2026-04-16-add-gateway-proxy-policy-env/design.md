## Context

`GatewayClient` is the shared HTTP client for direct calls to a live per-agent gateway listener. It is used by runtime attach readiness, runtime gateway-aware control, passive/pair proxy paths, and gateway service helpers. The gateway listener is constrained to local hosts (`127.0.0.1` or `0.0.0.0`, with clients connecting through loopback), but `urllib` honors ambient `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` unless bypassed. In environments with proxy variables but no loopback `NO_PROXY`, gateway attach can time out while the gateway process is actually healthy because the parent process polls the proxy instead of the listener.

Existing CAO and headless paths inject loopback entries into `NO_PROXY` by default and use `HOUMAO_PRESERVE_NO_PROXY_ENV=1` to leave the caller environment untouched. The gateway client can use a tighter approach because it owns the low-level HTTP call to a loopback-only gateway endpoint: bypass proxies in the client itself, without mutating `NO_PROXY` or `no_proxy`.

## Goals / Non-Goals

**Goals:**

- Make live gateway HTTP calls direct by default, independent of ambient proxy variables.
- Provide `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` for operators who intentionally need gateway calls to use normal proxy handling.
- Preserve consistent behavior across readiness probes, direct gateway CLI operations, passive/pair proxy routes, mail/notifier/reminder/memory calls, and other `GatewayClient` users.
- Improve attach timeout diagnostics by including the last observed health probe error when the gateway publishes a listener but readiness never succeeds.

**Non-Goals:**

- Do not change CAO, `houmao-server`, provider CLI, or agent subprocess proxy policy.
- Do not add new CLI flags for gateway proxy policy in this change.
- Do not expose proxy credentials or proxy configuration in gateway status, manifests, or durable runtime artifacts.
- Do not broaden live gateway hosts beyond the existing local gateway host contract.

## Decisions

1. Default `GatewayClient` to a proxy-disabled opener.

   Rationale: the live gateway endpoint is local control-plane traffic, not general user egress. Client-local proxy bypass avoids global `os.environ` mutation, avoids races between concurrent requests, and makes the policy apply even when callers forget to set `NO_PROXY`.

   Alternative considered: inject loopback `NO_PROXY` before every gateway call. This matches CAO helper patterns but is less precise here because gateway client calls are already centralized and loopback-only.

2. Use `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` as the explicit opt-in.

   Rationale: this name says exactly which subsystem changes behavior and avoids overloading `HOUMAO_PRESERVE_NO_PROXY_ENV`, whose meaning is about preserving environment variables during environment mutation. The gateway client bypass path does not mutate environment, so a separate env var is clearer.

   Alternative considered: reuse `HOUMAO_PRESERVE_NO_PROXY_ENV=1`. That would be confusing because there is no `NO_PROXY` injection to preserve, and operators asking to respect proxy settings need a direct gateway-client switch.

3. Resolve proxy policy at `GatewayClient` construction.

   Rationale: callers already instantiate a client per resolved live gateway endpoint. Construction-time resolution keeps request methods simple and makes tests deterministic. If an operator changes the environment, newly constructed clients pick up the change.

4. Keep attach readiness health-based and improve timeout detail.

   Rationale: the health endpoint remains the authoritative readiness signal. Retaining the last `GatewayHttpError` only improves diagnostics; it does not change readiness semantics or replace the health endpoint with file-state heuristics.

## Risks / Trade-offs

- [Risk] Operators using an HTTP proxy to observe gateway traffic will no longer see that traffic by default. -> Mitigation: document and test `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` as the opt-in.
- [Risk] A gateway caller could expect `NO_PROXY` to control behavior globally. -> Mitigation: make gateway behavior subsystem-specific and name the env var accordingly.
- [Risk] Proxy-respecting mode can reintroduce readiness timeouts in misconfigured environments. -> Mitigation: preserve direct mode as default and surface the last health probe error on timeout.

## Migration Plan

No data migration is required. Existing gateway callers get direct loopback behavior by default. Operators who intentionally need proxy-aware gateway calls can set `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` in the caller environment before running `houmao-mgr`, `houmao-server`, or any process that constructs `GatewayClient`.

Rollback is limited to removing the env override and restoring direct gateway client behavior; no persisted runtime state is affected.

## Open Questions

None.
