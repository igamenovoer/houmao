## 1. Startup Progress Plumbing

- [x] 1.1 Add demo-layer startup progress helpers that emit short human-readable phase breadcrumbs without changing the existing final `start` JSON payload.
- [x] 1.2 Update the blocking `start-session` subprocess path so the demo can print recurring waiting feedback while the child process is still running and still persist the same stdout/stderr logs and `CommandResult` shape.

## 2. Operator-Facing Startup UX

- [x] 2.1 Hook `start_demo` into the new progress helpers so startup surfaces meaningful phase messages before and during the Claude readiness wait.
- [x] 2.2 Update `run_demo.sh`/wrapper documentation to explain that startup now prints progress on the way to the final success payload and that stdout remains machine-readable JSON.

## 3. Regression Coverage

- [x] 3.1 Add or update unit tests covering stage breadcrumbs, recurring waiting feedback during long startup, and preservation of the final stdout JSON contract.
- [x] 3.2 Run the relevant demo/unit validation to confirm `start` no longer appears dead during normal Claude startup waits.
