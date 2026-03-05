## 1. Runtime Startup Window Hygiene

- [x] 1.1 Record the bootstrap tmux `window_id` (and name/index for diagnostics) immediately after `_create_tmux_session` in `backends/cao_rest.py`.
- [x] 1.2 Resolve the created CAO terminal tmux `window_id` from `create_terminal(...).name` using bounded retry (`tmux list-windows` mapping name -> id).
- [x] 1.3 Best-effort select the CAO terminal window by `window_id` as the session's current tmux window (fixes shell-first attach even when pruning fails).
- [x] 1.4 Implement targeted bootstrap-window pruning by `window_id`: when `bootstrap_window_id != terminal_window_id`, kill only `bootstrap_window_id`.
- [x] 1.5 Ensure selection/pruning is best-effort and non-fatal: on error, keep `start-session` successful and emit a warning diagnostic.
- [x] 1.6 Ensure guard behavior skips prune when bootstrap and terminal resolve to the same tmux `window_id`.
- [x] 1.7 Surface cleanup warnings to the `start-session` CLI as stderr `warning:` lines while keeping JSON output unchanged.

## 2. Regression and Behavior Tests

- [x] 2.1 Extend CAO backend unit tests to verify successful startup prunes the bootstrap window and keeps the CAO terminal window/session active.
- [x] 2.2 Add a unit test that simulates bootstrap-window prune failure and verifies launch success plus warning diagnostics.
- [x] 2.3 Add a unit test covering the "same window" branch to verify prune is skipped and terminal remains active.
- [x] 2.4 Non-regression coverage already exists: `test_cao_backend_uses_tmux_env_and_query_contract` asserts `AGENTSYS-...` naming and `AGENTSYS_MANIFEST_PATH` tmux env publication.
- [x] 2.5 Add a unit test that simulates failing to resolve `terminal.name` -> tmux `window_id` within the bounded retry policy and verifies launch success plus warning diagnostics (no prune).

## 3. Operator-Facing Validation Notes

- [x] 3.1 Update `docs/reference/brain_launch_runtime.md` with expected CAO attach behavior (first attach lands on agent window; bootstrap shell window is not expected after successful launch).
- [x] 3.2 Add a short manual verification checklist for CAO-backed startup (`tmux list-windows -t AGENTSYS-...`, attach behavior, and warning-path expectations).
