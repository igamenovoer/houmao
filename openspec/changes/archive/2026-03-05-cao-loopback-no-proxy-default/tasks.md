## 1. Loopback Policy Foundations

- [x] 1.1 Add a shared loopback CAO base-URL detector for `localhost`/`127.0.0.1` paths used by launcher and runtime codepaths
- [x] 1.2 Add a shared loopback `NO_PROXY/no_proxy` injector that appends loopback entries (merge+dedupe) unless `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`

## 2. Launcher Loopback No-Proxy Behavior

- [x] 2.1 Update launcher `status` health probe path to apply loopback `NO_PROXY` injection before probing supported loopback base URLs
- [x] 2.2 Update launcher `start` startup polling probes to use the same loopback `NO_PROXY` injection behavior
- [x] 2.3 Add/adjust launcher unit tests to verify (a) default loopback `NO_PROXY` injection bypasses ambient proxies and (b) `AGENTSYS_PRESERVE_NO_PROXY_ENV=1` preserves caller behavior

## 3. Runtime CAO REST Loopback Behavior

- [x] 3.1 Update `CaoRestClient` request path to rely on loopback `NO_PROXY` injection (no specialized proxy handlers) for supported loopback base URLs while preserving existing API shape/validation behavior
- [x] 3.2 Add/adjust CAO REST client unit tests covering (a) default injection bypass and (b) preserve-mode compatibility, plus non-loopback compatibility

## 4. CAO tmux Environment Policy

- [x] 4.1 Update CAO-backed tmux launch environment composition to inject loopback `NO_PROXY/no_proxy` entries by default for loopback CAO sessions (without stripping proxy vars)
- [x] 4.2 Ensure tmux env composition preserves allowlisted credential env vars and respects `AGENTSYS_PRESERVE_NO_PROXY_ENV=1` by leaving `NO_PROXY/no_proxy` untouched
- [x] 4.3 Add/adjust CAO backend unit tests validating tmux session env `NO_PROXY/no_proxy` behavior for loopback sessions (default inject vs preserve)

## 5. Runtime Subprocess Env Policy (Non-CAO Backends)

- [x] 5.1 Update headless backend subprocess env composition to inject loopback `NO_PROXY/no_proxy` entries by default (unless `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`)
- [x] 5.2 Update Codex app-server backend subprocess env composition to inject loopback `NO_PROXY/no_proxy` entries by default (unless `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`)
- [x] 5.3 Add/adjust unit tests validating non-CAO backend subprocess env `NO_PROXY/no_proxy` behavior (default inject vs preserve)

## 6. Documentation and Validation

- [x] 6.1 Update CAO launcher and brain-launch-runtime reference docs to define the loopback no-proxy default and expected operator behavior
- [x] 6.2 Run targeted validation (unit tests and a CAO loopback smoke flow under proxy-heavy shell env), plus an opt-out smoke using `AGENTSYS_PRESERVE_NO_PROXY_ENV=1` for traffic-watching proxies, and document outcomes in the change notes
