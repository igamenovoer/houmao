## 1. Server Health Contract

- [x] 1.1 Update `houmao-server` health and current-instance payload builders so `startup_child=false` omits `child_cao` instead of projecting failing derived-port status
- [x] 1.2 Keep child-enabled behavior unchanged for default shallow-cut CAO-backed runs and verify the root health contract still distinguishes Houmao-server health from child-CAO health

## 2. Readiness Callers

- [x] 2.1 Update the mail ping-pong gateway demo startup waiter so the native managed-headless path only requires Houmao root health
- [x] 2.2 Audit other readiness waiters and move any CAO-dependent startup checks to explicit CAO readiness checks instead of root-health child metadata

## 3. Regression Coverage

- [x] 3.1 Add unit coverage for `GET /health` and `GET /houmao/server/current-instance` in both child-enabled and `startup_child=false` modes
- [x] 3.2 Add or update demo and integration tests to prove native managed-headless no-child startup succeeds without child-CAO health
